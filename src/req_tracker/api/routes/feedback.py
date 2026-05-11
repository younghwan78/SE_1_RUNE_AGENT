"""Feedback and eval candidate APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from req_tracker.api.security import require_role
from req_tracker.evals.datasets import build_eval_candidates, feedback_counts_by_reason
from req_tracker.evals.runner import run_local_eval_gate
from req_tracker.feedback.models import FeedbackEvent
from req_tracker.feedback.service import build_improvement_candidates

router = APIRouter(tags=["feedback"])


class ImprovementActivationRequest(BaseModel):
    """Controlled promotion request after eval has passed."""

    reviewer_approved: bool = False
    canary_passed: bool = False


@router.post("/feedback")
def record_feedback(request: Request, event: FeedbackEvent) -> dict[str, Any]:
    """Record feedback in local runtime state."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    runtime.approvals.feedback.append(event)
    runtime.audit.record(
        action="feedback_recorded",
        actor_id=event.user_id,
        actor_role=event.user_role,
        target_type=event.target_type,
        target_id=event.target_id,
        reason_code=event.reason_code,
        metadata={"feedback_id": event.feedback_id, "action": event.action},
    )
    runtime.persist_approval_state()
    return event.model_dump(mode="json")


@router.get("/eval/candidates")
def eval_candidates(request: Request) -> list[dict[str, Any]]:
    """Return feedback grouped as eval dataset candidates."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    return [
        candidate.model_dump(mode="json")
        for candidate in build_eval_candidates(runtime.approvals.feedback)
    ]


@router.get("/eval/gate")
def eval_gate(request: Request) -> dict[str, Any]:
    """Run the local eval gate for current feedback-derived datasets."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    candidates = build_eval_candidates(runtime.approvals.feedback)
    result = run_local_eval_gate(candidates, settings.new_id("eval"))
    return result.model_dump(mode="json")


@router.get("/improvements/candidates")
def improvement_candidates(request: Request) -> list[dict[str, Any]]:
    """Return controlled improvement candidates derived from feedback."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    return [
        candidate.model_dump(mode="json")
        for candidate in build_improvement_candidates(runtime.approvals.feedback)
    ]


@router.post("/improvements/{candidate_id}/activate")
def activate_improvement(
    request: Request,
    candidate_id: str,
    payload: ImprovementActivationRequest | None = None,
) -> dict[str, Any]:
    """Promote an improvement only through eval, review, canary, and active stages."""
    require_role(request, "admin")
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    promotion = payload or ImprovementActivationRequest()
    candidates = build_improvement_candidates(runtime.approvals.feedback)
    candidate = next(
        (item for item in candidates if item.candidate_id == candidate_id),
        None,
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="improvement candidate not found")

    eval_candidates_for_gate = build_eval_candidates(runtime.approvals.feedback)
    gate = run_local_eval_gate(eval_candidates_for_gate, settings.new_id("eval"))
    if gate.status != "passed":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "eval gate blocked activation",
                "blockers": gate.blockers,
                "eval_run_id": gate.eval_run_id,
            },
        )
    candidate.eval_run_id = gate.eval_run_id
    if not promotion.reviewer_approved:
        candidate.status = "review_ready"
        promotion_status = "review_required"
    elif not promotion.canary_passed:
        candidate.status = "canary"
        promotion_status = "canary_required"
    else:
        candidate.status = "active"
        promotion_status = "active"
    result = candidate.model_dump(mode="json")
    result["promotion_status"] = promotion_status
    result["eval_gate"] = gate.model_dump(mode="json")
    return result


@router.get("/feedback/summary")
def feedback_summary(request: Request) -> dict[str, int]:
    """Return local feedback counts by reason."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    return feedback_counts_by_reason(runtime.approvals.feedback)

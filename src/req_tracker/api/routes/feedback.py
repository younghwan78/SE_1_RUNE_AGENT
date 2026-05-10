"""Feedback and eval candidate APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from req_tracker.evals.datasets import build_eval_candidates, feedback_counts_by_reason
from req_tracker.evals.runner import run_local_eval_gate
from req_tracker.feedback.models import FeedbackEvent
from req_tracker.feedback.service import build_improvement_candidates

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
def record_feedback(request: Request, event: FeedbackEvent) -> dict[str, Any]:
    """Record feedback in local runtime state."""
    runtime = request.app.state.runtime
    runtime.approvals.feedback.append(event)
    runtime.persist_approval_state()
    return event.model_dump(mode="json")


@router.get("/eval/candidates")
def eval_candidates(request: Request) -> list[dict[str, Any]]:
    """Return feedback grouped as eval dataset candidates."""
    runtime = request.app.state.runtime
    return [
        candidate.model_dump(mode="json")
        for candidate in build_eval_candidates(runtime.approvals.feedback)
    ]


@router.get("/eval/gate")
def eval_gate(request: Request) -> dict[str, Any]:
    """Run the local eval gate for current feedback-derived datasets."""
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    candidates = build_eval_candidates(runtime.approvals.feedback)
    result = run_local_eval_gate(candidates, settings.new_id("eval"))
    return result.model_dump(mode="json")


@router.get("/improvements/candidates")
def improvement_candidates(request: Request) -> list[dict[str, Any]]:
    """Return controlled improvement candidates derived from feedback."""
    runtime = request.app.state.runtime
    return [
        candidate.model_dump(mode="json")
        for candidate in build_improvement_candidates(runtime.approvals.feedback)
    ]


@router.post("/improvements/{candidate_id}/activate")
def activate_improvement(request: Request, candidate_id: str) -> dict[str, Any]:
    """Block activation unless the eval gate currently passes."""
    runtime = request.app.state.runtime
    settings = request.app.state.settings
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
    candidate.status = "active"
    return candidate.model_dump(mode="json")


@router.get("/feedback/summary")
def feedback_summary(request: Request) -> dict[str, int]:
    """Return local feedback counts by reason."""
    runtime = request.app.state.runtime
    return feedback_counts_by_reason(runtime.approvals.feedback)

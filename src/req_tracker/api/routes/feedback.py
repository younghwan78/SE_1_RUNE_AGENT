"""Feedback and eval candidate APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from req_tracker.api.idempotency import (
    explicit_model_payload,
    prepare_idempotency,
    record_idempotency_response,
)
from req_tracker.api.security import require_role
from req_tracker.evals.datasets import build_eval_candidates, feedback_counts_by_reason
from req_tracker.evals.runner import run_local_eval_gate
from req_tracker.feedback.models import FeedbackEvent, ImprovementCandidate, ImprovementStatus
from req_tracker.feedback.service import build_improvement_candidates

router = APIRouter(tags=["feedback"])


class ImprovementActivationRequest(BaseModel):
    """Controlled promotion request after eval has passed."""

    reviewer_approved: bool = False
    canary_passed: bool = False


class ImprovementRollbackRequest(BaseModel):
    """Controlled rollback request after canary or active regression."""

    rolled_back_by: str | None = None
    reason_code: str = "canary_regression"
    comment: str | None = None


@router.post("/feedback")
def record_feedback(request: Request, event: FeedbackEvent) -> dict[str, Any]:
    """Record feedback in local runtime state."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    idempotency = prepare_idempotency(
        request=request,
        runtime=runtime,
        command="feedback.record",
        payload=explicit_model_payload(event),
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response
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
    result = event.model_dump(mode="json")
    record_idempotency_response(
        runtime=runtime,
        context=idempotency,
        command="feedback.record",
        project_key=None,
        response=result,
    )
    return result


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
        _apply_recorded_decision(candidate, runtime.improvement_decisions).model_dump(mode="json")
        for candidate in build_improvement_candidates(runtime.approvals.feedback)
    ]


@router.post("/improvements/{candidate_id}/activate")
def activate_improvement(
    request: Request,
    candidate_id: str,
    payload: ImprovementActivationRequest | None = None,
) -> dict[str, Any]:
    """Promote an improvement only through eval, review, canary, and active stages."""
    user = require_role(request, "admin")
    runtime = request.app.state.runtime
    settings = request.app.state.settings
    promotion = payload or ImprovementActivationRequest()
    candidates = build_improvement_candidates(runtime.approvals.feedback)
    candidate = _find_candidate(candidate_id, candidates)
    if candidate is None:
        raise HTTPException(status_code=404, detail="improvement candidate not found")
    candidate = _apply_recorded_decision(candidate, runtime.improvement_decisions)
    idempotency = prepare_idempotency(
        request=request,
        runtime=runtime,
        command="improvements.activate",
        payload={
            "candidate_id": candidate_id,
            "promotion": explicit_model_payload(promotion),
        },
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response
    target_status = _activation_target_status(promotion)
    _require_forward_improvement_transition(candidate.status, target_status)

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
    candidate.reviewed_by = user.user_id if promotion.reviewer_approved else None
    result = candidate.model_dump(mode="json")
    result["promotion_status"] = promotion_status
    result["eval_gate"] = gate.model_dump(mode="json")
    result["decision_type"] = "activation"
    result["previous_status"] = runtime.improvement_decisions.get(candidate_id, {}).get(
        "status",
        "draft",
    )
    runtime.record_improvement_decision(candidate_id=candidate_id, decision=result)
    runtime.audit.record(
        action="improvement_activated",
        actor_id=user.user_id,
        actor_role=user.role,
        target_type="improvement_candidate",
        target_id=candidate_id,
        metadata={
            "candidate_type": candidate.candidate_type,
            "promotion_status": promotion_status,
            "eval_run_id": gate.eval_run_id,
        },
    )
    runtime.persist_approval_state()
    record_idempotency_response(
        runtime=runtime,
        context=idempotency,
        command="improvements.activate",
        project_key=None,
        response=result,
    )
    return result


@router.post("/improvements/{candidate_id}/rollback")
def rollback_improvement(
    request: Request,
    candidate_id: str,
    payload: ImprovementRollbackRequest | None = None,
) -> dict[str, Any]:
    """Rollback a canary or active improvement to its recorded previous version."""
    user = require_role(request, "admin")
    runtime = request.app.state.runtime
    rollback = payload or ImprovementRollbackRequest()
    candidates = build_improvement_candidates(runtime.approvals.feedback)
    candidate = _find_candidate(candidate_id, candidates)
    if candidate is None:
        raise HTTPException(status_code=404, detail="improvement candidate not found")
    candidate = _apply_recorded_decision(candidate, runtime.improvement_decisions)
    idempotency = prepare_idempotency(
        request=request,
        runtime=runtime,
        command="improvements.rollback",
        payload={
            "candidate_id": candidate_id,
            "rollback": explicit_model_payload(rollback),
        },
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response
    if candidate.status not in {"canary", "active"}:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "improvement is not rollbackable",
                "current_status": candidate.status,
                "rollbackable_statuses": ["canary", "active"],
            },
        )
    previous_status = candidate.status
    candidate.status = "rolled_back"
    actor_id = rollback.rolled_back_by or user.user_id
    result = candidate.model_dump(mode="json")
    result["decision_type"] = "rollback"
    result["previous_status"] = previous_status
    result["rollback_status"] = "rolled_back"
    result["restored_version_id"] = candidate.before_version_id
    result["rolled_back_by"] = actor_id
    result["reason_code"] = rollback.reason_code
    result["comment"] = rollback.comment
    runtime.record_improvement_decision(candidate_id=candidate_id, decision=result)
    runtime.audit.record(
        action="improvement_rolled_back",
        actor_id=actor_id,
        actor_role=user.role,
        target_type="improvement_candidate",
        target_id=candidate_id,
        reason_code=rollback.reason_code,
        metadata={
            "candidate_type": candidate.candidate_type,
            "previous_status": previous_status,
            "restored_version_id": candidate.before_version_id,
        },
    )
    runtime.persist_approval_state()
    record_idempotency_response(
        runtime=runtime,
        context=idempotency,
        command="improvements.rollback",
        project_key=None,
        response=result,
    )
    return result


@router.get("/feedback/summary")
def feedback_summary(request: Request) -> dict[str, int]:
    """Return local feedback counts by reason."""
    require_role(request, "developer")
    runtime = request.app.state.runtime
    return feedback_counts_by_reason(runtime.approvals.feedback)


def _find_candidate(
    candidate_id: str,
    candidates: list[ImprovementCandidate],
) -> ImprovementCandidate | None:
    return next((item for item in candidates if item.candidate_id == candidate_id), None)


def _apply_recorded_decision(
    candidate: ImprovementCandidate,
    decisions: dict[str, dict[str, Any]],
) -> ImprovementCandidate:
    decision = decisions.get(candidate.candidate_id)
    if decision is None:
        return candidate
    return candidate.model_copy(
        update={
            "status": decision.get("status", candidate.status),
            "eval_run_id": decision.get("eval_run_id", candidate.eval_run_id),
            "reviewed_by": decision.get("reviewed_by", candidate.reviewed_by),
        }
    )


def _activation_target_status(promotion: ImprovementActivationRequest) -> ImprovementStatus:
    if not promotion.reviewer_approved:
        return "review_ready"
    if not promotion.canary_passed:
        return "canary"
    return "active"


def _require_forward_improvement_transition(
    current_status: ImprovementStatus,
    target_status: ImprovementStatus,
) -> None:
    order = {
        "draft": 0,
        "eval_running": 1,
        "review_ready": 2,
        "approved": 3,
        "canary": 4,
        "active": 5,
        "rolled_back": 6,
        "rejected": 6,
    }
    if current_status in {"rolled_back", "rejected"}:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "improvement candidate is closed",
                "current_status": current_status,
            },
        )
    if order[target_status] < order[current_status]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "improvement promotion cannot move backwards",
                "current_status": current_status,
                "requested_status": target_status,
            },
        )

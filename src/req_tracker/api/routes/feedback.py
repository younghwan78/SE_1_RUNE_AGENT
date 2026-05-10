"""Feedback and eval candidate APIs."""

from typing import Any

from fastapi import APIRouter, Request

from req_tracker.evals.datasets import build_eval_candidates, feedback_counts_by_reason
from req_tracker.feedback.models import FeedbackEvent

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
def record_feedback(request: Request, event: FeedbackEvent) -> dict[str, Any]:
    """Record feedback in local runtime state."""
    runtime = request.app.state.runtime
    runtime.approvals.feedback.append(event)
    return event.model_dump(mode="json")


@router.get("/eval/candidates")
def eval_candidates(request: Request) -> list[dict[str, Any]]:
    """Return feedback grouped as eval dataset candidates."""
    runtime = request.app.state.runtime
    return [
        candidate.model_dump(mode="json")
        for candidate in build_eval_candidates(runtime.approvals.feedback)
    ]


@router.get("/feedback/summary")
def feedback_summary(request: Request) -> dict[str, int]:
    """Return local feedback counts by reason."""
    runtime = request.app.state.runtime
    return feedback_counts_by_reason(runtime.approvals.feedback)


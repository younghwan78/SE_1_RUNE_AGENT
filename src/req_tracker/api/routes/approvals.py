"""Approval APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from req_tracker.approvals.models import ApprovalDecision

router = APIRouter(tags=["approvals"])


@router.get("/approvals")
def list_approvals(request: Request) -> list[dict[str, Any]]:
    """List approval items."""
    runtime = request.app.state.runtime
    return [item.model_dump(mode="json") for item in runtime.approvals.items.values()]


@router.post("/approvals/{approval_id}/decision")
def decide_approval(
    request: Request,
    approval_id: str,
    decision: ApprovalDecision,
) -> dict[str, Any]:
    """Apply an approval decision."""
    if decision.approval_id != approval_id:
        raise HTTPException(status_code=400, detail="approval_id mismatch")
    runtime = request.app.state.runtime
    if approval_id not in runtime.approvals.items:
        raise HTTPException(status_code=404, detail="approval not found")
    item = runtime.approvals.decide(decision, runtime.graph)
    result: dict[str, Any] = item.model_dump(mode="json")
    return result

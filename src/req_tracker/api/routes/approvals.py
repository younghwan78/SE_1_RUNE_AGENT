"""Approval APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from req_tracker.api.idempotency import (
    explicit_model_payload,
    prepare_idempotency,
    record_idempotency_response,
)
from req_tracker.api.security import require_project
from req_tracker.approvals.models import ApprovalDecision

router = APIRouter(tags=["approvals"])


@router.get("/approvals")
def list_approvals(
    request: Request,
    project_key: str | None = None,
) -> list[dict[str, Any]]:
    """List approval items."""
    require_project(request, project_key, "developer")
    runtime = request.app.state.runtime
    approvals = list(runtime.approvals.items.values())
    if project_key is not None:
        approvals = [item for item in approvals if item.project_key == project_key]
    return [item.model_dump(mode="json") for item in approvals]


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
    require_project(request, runtime.approvals.items[approval_id].project_key, "operator")
    idempotency = prepare_idempotency(
        request=request,
        runtime=runtime,
        command="approvals.decision",
        payload={
            "approval_id": approval_id,
            "decision": explicit_model_payload(decision),
        },
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response
    item = runtime.approvals.decide(decision, runtime.graph)
    runtime.audit.record(
        action="approval_decided",
        actor_id=decision.decided_by,
        actor_role=item.owner_role,
        project_key=item.project_key,
        target_type="approval",
        target_id=approval_id,
        reason_code=decision.reason_code,
        metadata={
            "decision_action": decision.action,
            "result_status": item.status,
            "proposal_ref": item.proposal_ref,
        },
    )
    runtime.persist_approval_state()
    result: dict[str, Any] = item.model_dump(mode="json")
    record_idempotency_response(
        runtime=runtime,
        context=idempotency,
        command="approvals.decision",
        project_key=item.project_key,
        response=result,
    )
    return result

"""Audit APIs."""

from typing import Any

from fastapi import APIRouter, Request

from req_tracker.api.security import require_project, require_role
from req_tracker.audit.models import AuditAction

router = APIRouter(tags=["audit"])


@router.get("/audit/events")
def list_audit_events(
    request: Request,
    project_key: str | None = None,
    action: AuditAction | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List audit events."""
    require_role(request, "operator")
    require_project(request, project_key, "operator")
    runtime = request.app.state.runtime
    capped_limit = min(max(limit, 1), 500)
    return [
        event.model_dump(mode="json")
        for event in runtime.audit.list_events(
            project_key=project_key,
            action=action,
            limit=capped_limit,
        )
    ]


@router.get("/audit/retention")
def audit_retention_report(request: Request) -> dict[str, Any]:
    """Return audit retention policy and current non-destructive status."""
    require_role(request, "operator")
    runtime = request.app.state.runtime
    report: dict[str, Any] = runtime.audit.retention_report()
    return report


@router.post("/audit/retention/archive-prune")
def archive_and_prune_audit_events(request: Request) -> dict[str, Any]:
    """Archive and prune audit events selected by the active retention policy."""
    user = require_role(request, "admin")
    runtime = request.app.state.runtime
    result: dict[str, Any] = runtime.audit.archive_and_prune(
        archive_writer=runtime.audit_archive_store,
    )
    runtime.audit.record(
        action="audit_archive_pruned",
        actor_id=user.user_id,
        actor_role=user.role,
        target_type="audit_retention",
        target_id="default",
        metadata=result,
    )
    runtime.persist_approval_state()
    return result

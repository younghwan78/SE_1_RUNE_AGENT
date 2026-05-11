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

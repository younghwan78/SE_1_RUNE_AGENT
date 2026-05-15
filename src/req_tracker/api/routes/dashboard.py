"""Dashboard read-model APIs."""

from typing import Any

from fastapi import APIRouter, Request

from req_tracker.api.security import require_project
from req_tracker.dashboard.service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
def dashboard_summary(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, Any]:
    """Return first-viewport product dashboard summary."""
    require_project(request, project_key, "viewer")
    service = _service(request)
    return service.summary(project_key).model_dump(mode="json")


@router.get("/dashboard/work-queue")
def dashboard_work_queue(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    status: str = "open",
    limit: int = 50,
) -> dict[str, Any]:
    """Return prioritized reviewer/operator work queue items."""
    require_project(request, project_key, "developer")
    service = _service(request)
    return service.work_queue(project_key, status=status, limit=limit).model_dump(mode="json")


@router.get("/dashboard/source-health")
def dashboard_source_health(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, Any]:
    """Return source sync health without secrets or transport details."""
    require_project(request, project_key, "developer")
    service = _service(request)
    return service.source_health(project_key).model_dump(mode="json")


@router.get("/dashboard/run-health")
def dashboard_run_health(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    limit: int = 10,
) -> dict[str, Any]:
    """Return recent run health for dashboard state."""
    require_project(request, project_key, "viewer")
    service = _service(request)
    return service.run_health(project_key, limit=limit).model_dump(mode="json")


@router.get("/dashboard/risk-summary")
def dashboard_risk_summary(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    limit: int = 10,
) -> dict[str, Any]:
    """Return risk and finding summary for dashboard panels."""
    require_project(request, project_key, "viewer")
    service = _service(request)
    return service.risk_summary(project_key, limit=limit).model_dump(mode="json")


@router.get("/dashboard/recent-activity")
def dashboard_recent_activity(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    limit: int = 20,
) -> dict[str, Any]:
    """Return sanitized recent activity for operator dashboard review."""
    require_project(request, project_key, "operator")
    service = _service(request)
    return service.recent_activity(project_key, limit=limit).model_dump(mode="json")


def _service(request: Request) -> DashboardService:
    settings = request.app.state.settings
    return DashboardService(request.app.state.runtime, new_id=settings.new_id)

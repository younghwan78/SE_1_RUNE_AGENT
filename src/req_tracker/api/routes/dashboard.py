"""Dashboard read-model APIs."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from req_tracker.api.idempotency import (
    prepare_idempotency,
    record_idempotency_response,
)
from req_tracker.api.security import require_project
from req_tracker.dashboard.models import (
    WorkQueueAssignment,
    WorkQueueAssignmentRequest,
    WorkQueueAssignmentsResponse,
    WorkQueuePreferences,
    WorkQueuePreferencesUpdate,
)
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


@router.get("/dashboard/work-queue/preferences")
def dashboard_work_queue_preferences(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, Any]:
    """Return backend-backed work queue preferences for the current user."""
    user = require_project(request, project_key, "developer")
    preference = _load_preferences(request, project_key=project_key, user_id=user.user_id)
    return preference.model_dump(mode="json")


@router.put("/dashboard/work-queue/preferences")
def update_dashboard_work_queue_preferences(
    request: Request,
    payload: WorkQueuePreferencesUpdate,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, Any]:
    """Persist backend-backed work queue preferences for the current user."""
    user = require_project(request, project_key, "developer")
    preference = WorkQueuePreferences(
        project_key=project_key,
        user_id=user.user_id,
        saved_filters=payload.saved_filters,
        updated_at=datetime.now(UTC),
    )
    preference_id = _preference_id(project_key, user.user_id)
    request.app.state.runtime.record_dashboard_preference(
        preference_id=preference_id,
        project_key=project_key,
        preference={
            "preference_id": preference_id,
            **preference.model_dump(mode="json"),
        },
    )
    request.app.state.runtime.audit.record(
        action="dashboard_preferences_saved",
        actor_id=user.user_id,
        actor_role=user.role,
        project_key=project_key,
        target_type="dashboard_preferences",
        target_id=preference_id,
        metadata={"saved_filter_count": len(payload.saved_filters)},
    )
    return preference.model_dump(mode="json")


@router.get("/dashboard/work-queue/assignments")
def dashboard_work_queue_assignments(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, Any]:
    """Return backend-backed work queue assignments for a project."""
    require_project(request, project_key, "developer")
    assignments = [
        WorkQueueAssignment.model_validate(_public_assignment_payload(payload))
        for payload in request.app.state.runtime.dashboard_assignments.values()
        if payload.get("project_key") == project_key and payload.get("assigned_to") is not None
    ]
    assignments.sort(key=lambda item: item.queue_id)
    return WorkQueueAssignmentsResponse(
        project_key=project_key,
        assignments=assignments,
    ).model_dump(mode="json")


@router.post("/dashboard/work-queue/assignments/{queue_id}")
def update_dashboard_work_queue_assignment(
    request: Request,
    queue_id: str,
    payload: WorkQueueAssignmentRequest,
) -> dict[str, Any]:
    """Assign or clear a work queue item with idempotency support."""
    user = require_project(request, payload.project_key, "developer")
    idempotency = prepare_idempotency(
        request=request,
        runtime=request.app.state.runtime,
        command="dashboard.work_queue_assignment",
        payload={"queue_id": queue_id, **payload.model_dump(mode="json")},
    )
    if idempotency.cached_response is not None:
        return idempotency.cached_response

    assigned_to = payload.assignee_id or user.user_id if payload.action == "assign" else None
    assignment = WorkQueueAssignment(
        project_key=payload.project_key,
        queue_id=queue_id,
        assigned_to=assigned_to,
        assigned_by=user.user_id,
        updated_at=datetime.now(UTC),
    )
    assignment_id = _assignment_id(payload.project_key, queue_id)
    response = assignment.model_dump(mode="json")
    request.app.state.runtime.record_dashboard_assignment(
        assignment_id=assignment_id,
        project_key=payload.project_key,
        assignment={
            "assignment_id": assignment_id,
            **response,
        },
    )
    request.app.state.runtime.audit.record(
        action="dashboard_work_queue_assignment_updated",
        actor_id=user.user_id,
        actor_role=user.role,
        project_key=payload.project_key,
        target_type="work_queue_item",
        target_id=queue_id,
        metadata={"action": payload.action, "assigned_to": assigned_to},
    )
    record_idempotency_response(
        runtime=request.app.state.runtime,
        context=idempotency,
        command="dashboard.work_queue_assignment",
        project_key=payload.project_key,
        response=response,
    )
    return response


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


def _load_preferences(
    request: Request,
    *,
    project_key: str,
    user_id: str,
) -> WorkQueuePreferences:
    stored = request.app.state.runtime.dashboard_preferences.get(
        _preference_id(project_key, user_id)
    )
    if stored is not None:
        return WorkQueuePreferences.model_validate(_public_preference_payload(stored))
    return WorkQueuePreferences(
        project_key=project_key,
        user_id=user_id,
        updated_at=datetime.now(UTC),
    )


def _preference_id(project_key: str, user_id: str) -> str:
    return f"work_queue_preferences:{project_key}:{user_id}"


def _assignment_id(project_key: str, queue_id: str) -> str:
    return f"work_queue_assignment:{project_key}:{queue_id}"


def _public_preference_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "preference_id"}


def _public_assignment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "assignment_id"}

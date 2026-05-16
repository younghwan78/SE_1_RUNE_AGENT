"""Dashboard summary service tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings
from req_tracker.dashboard.service import DashboardService


def test_dashboard_service_empty_health_is_unknown(tmp_path: Path) -> None:
    app = create_app(Settings(artifact_root=tmp_path / "artifacts"))
    runtime = app.state.runtime

    summary = DashboardService(runtime).summary("RUNE_CAM_ALPHA")

    assert summary.traceability_health == "unknown"
    assert summary.counts.total_nodes == 0
    assert summary.last_run is None


def test_dashboard_work_queue_prioritizes_critical_findings_before_approvals(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(artifact_root=tmp_path / "artifacts"))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs/analyze",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_dashboard_service_queue",
            },
        )
        assert response.status_code == 200
        runtime = app.state.runtime

    queue = DashboardService(runtime).work_queue("RUNE_CAM_ALPHA", limit=20)

    assert queue.counts.finding == 6
    assert queue.counts.critical == 1
    assert queue.counts.approval == 7
    assert queue.items[0].priority == "critical"
    assert queue.items[0].item_type == "finding"

"""Dashboard API contract tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def test_dashboard_summary_empty_state_is_unknown(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "v1"
    assert payload["traceability_health"] == "unknown"
    assert payload["last_run"] is None
    assert payload["counts"]["total_nodes"] == 0
    assert payload["counts"]["pending_approvals"] == 0


def test_dashboard_summary_after_compact_analysis(client: TestClient) -> None:
    run = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_dashboard_alpha",
        },
    )
    assert run.status_code == 200

    summary = client.get("/api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA")
    queue = client.get("/api/v1/dashboard/work-queue?project_key=RUNE_CAM_ALPHA")
    risk = client.get("/api/v1/dashboard/risk-summary?project_key=RUNE_CAM_ALPHA")

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["traceability_health"] == "attention_required"
    assert payload["last_run"]["run_id"] == "run_dashboard_alpha"
    assert payload["counts"]["total_nodes"] == 10
    assert payload["counts"]["pending_edges"] == 7
    assert payload["counts"]["pending_approvals"] == 7
    assert payload["counts"]["open_findings"] == 5
    assert payload["source_freshness"]["dummy"] == "fresh"

    assert queue.status_code == 200
    queue_payload = queue.json()
    assert queue_payload["counts"]["finding"] == 5
    assert queue_payload["counts"]["approval"] == 7
    assert queue_payload["items"][0]["priority"] in {"critical", "high"}
    assert queue_payload["items"][0]["actions"]

    assert risk.status_code == 200
    assert risk.json()["risk_by_severity"]["high"] >= 1


def test_dashboard_scale_fixture_summarizes_large_graph(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_SCALE_150",
            "run_id": "run_dashboard_scale",
        },
    )
    assert response.status_code == 200

    summary = client.get("/api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA")
    work_queue = client.get(
        "/api/v1/dashboard/work-queue?project_key=RUNE_CAM_ALPHA&limit=200"
    )

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["counts"]["total_nodes"] == 150
    assert payload["counts"]["pending_edges"] == 103
    assert payload["counts"]["pending_approvals"] == 103
    assert payload["counts"]["orphan_nodes"] == 9
    assert payload["counts"]["open_findings"] == 47

    assert work_queue.status_code == 200
    queue_payload = work_queue.json()
    assert queue_payload["counts"]["approval"] == 103
    assert queue_payload["counts"]["finding"] == 47
    assert len(queue_payload["items"]) <= 200


def test_dashboard_summary_updates_after_approval_commit(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_dashboard_approval",
        },
    )
    assert response.status_code == 200
    approval = client.get("/api/v1/approvals?project_key=RUNE_CAM_ALPHA").json()[0]

    before = client.get("/api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA").json()
    decision = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json={
            "approval_id": approval["approval_id"],
            "action": "approve",
            "decided_by": "dashboard_reviewer",
        },
    )
    assert decision.status_code == 200
    after = client.get("/api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA").json()

    assert before["counts"]["approved_edges"] == 0
    assert after["counts"]["approved_edges"] == 1
    assert after["counts"]["pending_approvals"] == before["counts"]["pending_approvals"] - 1
    assert after["counts"]["pending_edges"] == before["counts"]["pending_edges"] - 1


def test_dashboard_source_health_after_export_adapter(tmp_path: Path) -> None:
    export_path = tmp_path / "jira.jsonl"
    export_path.write_text(
        (
            '{"external_id":"CAM-REQ-EXPORT-001","source_type":"jira",'
            '"source_url":"export://jira/CAM-REQ-EXPORT-001",'
            '"project_key":"RUNE_CAM_ALPHA","title":"CAM-REQ-EXPORT-001",'
            '"body_text":"Exported requirement body.","created_at":"2026-01-01T00:00:00Z",'
            '"updated_at":"2026-01-02T00:00:00Z","labels":["requirement"],'
            '"links":[],"metadata":{"mbse_type":"Requirement"},'
            '"access_scope":["RUNE_CAM_ALPHA"],"data_classification":"public_internal"}\n'
        ),
        encoding="utf-8",
    )
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            datasource_mode="jira_export",
            source_export_path=export_path,
        )
    )
    with TestClient(app) as client:
        run = client.post(
            "/api/v1/runs/ingest",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_dashboard_jira_export",
            },
        )
        assert run.status_code == 200
        health = client.get("/api/v1/dashboard/source-health?project_key=RUNE_CAM_ALPHA")

    assert health.status_code == 200
    sources = {item["source_type"]: item for item in health.json()["sources"]}
    assert sources["jira"]["status"] == "fresh"
    assert sources["jira"]["artifact_count"] == 1
    assert sources["jira"]["cursor_id"] == "src_cursor_jira_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA"


def test_dashboard_rbac_project_filtering(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            auth_mode="api_key",
            api_key="secret",
        )
    )
    headers = {
        "x-rune-api-key": "secret",
        "x-rune-role": "viewer",
        "x-rune-projects": "OTHER_PROJECT",
    }
    with TestClient(app) as client:
        denied = client.get(
            "/api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA",
            headers=headers,
        )
        developer_only = client.get(
            "/api/v1/dashboard/work-queue?project_key=RUNE_CAM_ALPHA",
            headers={**headers, "x-rune-projects": "RUNE_CAM_ALPHA"},
        )

    assert denied.status_code == 403
    assert developer_only.status_code == 403

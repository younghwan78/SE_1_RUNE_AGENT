"""Debug workbench API tests."""

from urllib.parse import quote

from fastapi.testclient import TestClient


def test_debug_run_summary_and_artifact_read(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_debug_1",
        },
    )
    assert response.status_code == 200

    runs = client.get("/api/v1/debug/runs")
    assert runs.status_code == 200
    assert any(run["run_id"] == "run_debug_1" for run in runs.json())

    summary = client.get("/api/v1/debug/runs/run_debug_1/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["run"]["run_id"] == "run_debug_1"
    assert payload["counts"]["steps"] >= 7
    assert payload["counts"]["artifact_refs"] >= 2
    assert payload["graph_deltas"]

    artifact_ref = payload["artifact_refs"][0]
    artifact = client.get(f"/api/v1/debug/artifact?artifact_ref={quote(artifact_ref)}")
    assert artifact.status_code == 200
    assert artifact.json()


def test_debug_run_summary_requires_existing_run(client: TestClient) -> None:
    response = client.get("/api/v1/debug/runs/missing/summary")
    assert response.status_code == 404


def test_debug_approval_lineage_links_run_step_delta_feedback_and_audit(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_lineage_1",
        },
    )
    assert response.status_code == 200
    approval = client.get("/api/v1/approvals").json()[0]
    decision = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json={
            "approval_id": approval["approval_id"],
            "action": "reject",
            "decided_by": "reviewer",
            "reason_code": "wrong_relation",
        },
    )
    assert decision.status_code == 200

    lineage = client.get(f"/api/v1/debug/approvals/{approval['approval_id']}/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    assert payload["approval"]["approval_id"] == approval["approval_id"]
    assert payload["run"]["run_id"] == "run_lineage_1"
    assert payload["step"]["step_id"] == approval["created_from_step_id"]
    assert payload["graph_delta"]["delta_id"] == approval["graph_delta_ref"]
    assert payload["feedback"][0]["reason_code"] == "wrong_relation"
    assert payload["audit_events"][0]["action"] == "approval_decided"
    assert payload["counts"]["graph_delta_operations"] >= 1


def test_debug_approval_lineage_requires_existing_approval(client: TestClient) -> None:
    response = client.get("/api/v1/debug/approvals/missing/lineage")
    assert response.status_code == 404

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

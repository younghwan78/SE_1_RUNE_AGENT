"""Schedule API contract tests."""

from fastapi.testclient import TestClient


def test_schedule_status_configure_and_run_now(client: TestClient) -> None:
    status = client.get("/api/v1/schedule")
    assert status.status_code == 200
    assert status.json()["enabled"] is False

    configured = client.put(
        "/api/v1/schedule",
        json={
            "enabled": False,
            "interval_seconds": 5,
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_MULTI_SOURCE",
            "run_id_prefix": "test_sched",
        },
    )
    assert configured.status_code == 200
    assert configured.json()["interval_seconds"] == 5

    run = client.post("/api/v1/schedule/run-now")
    assert run.status_code == 200
    run_id = run.json()["run_id"]
    assert run_id.startswith("test_sched_")

    detail = client.get(f"/api/v1/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "succeeded"

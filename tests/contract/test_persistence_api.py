"""Persistence-backed runtime contract tests."""

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings
from req_tracker.storage.sqlite_store import SQLiteStateStore


def test_sqlite_state_store_persists_runtime_outputs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "runtime.sqlite3"
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            state_store="sqlite",
            sqlite_state_path=db_path,
        )
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs/analyze",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_persist_1",
            },
        )
        assert response.status_code == 200

        approval = client.get("/api/v1/approvals").json()[0]
        decision = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decision",
            json={
                "approval_id": approval["approval_id"],
                "action": "approve",
                "decided_by": "reviewer",
            },
        )
        assert decision.status_code == 200

    store = SQLiteStateStore(db_path)
    counts = store.counts_by_collection()
    assert counts["agent_runs"] == 1
    assert counts["agent_step_traces"] >= 7
    assert counts["source_artifacts"] == 10
    assert counts["graph_nodes"] == 10
    assert counts["approval_items"] >= 1
    assert counts["graph_edges"] == 1

"""SQLite state repository tests."""

from req_tracker.debug.models import AgentRun
from req_tracker.storage.sqlite_store import SQLiteStateStore


def test_sqlite_store_upserts_and_lists_contract_payloads(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStateStore(tmp_path / "state.sqlite3")
    run = AgentRun(
        run_id="run_sqlite_1",
        run_type="analysis",
        project_key="RUNE_CAM_ALPHA",
        triggered_by="tester",
        trigger_source="manual",
    )

    store.upsert(
        collection="agent_runs",
        entity_id=run.run_id,
        project_key=run.project_key,
        payload=run,
    )
    stored = store.get("agent_runs", run.run_id)

    assert stored is not None
    assert stored["run_id"] == "run_sqlite_1"
    assert store.counts_by_collection() == {"agent_runs": 1}
    stored_runs = store.list("agent_runs", project_key="RUNE_CAM_ALPHA")
    assert stored_runs[0]["project_key"] == "RUNE_CAM_ALPHA"

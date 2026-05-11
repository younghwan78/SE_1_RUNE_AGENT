"""Runtime state failure-path tests."""

import pytest

from req_tracker.api.state import RuntimeState
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.storage.sqlite_store import SQLiteStateStore


def test_run_started_audit_event_is_persisted_immediately(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStateStore(tmp_path / "runtime.sqlite3")
    runtime = RuntimeState.create(tmp_path / "artifacts", state_store=store)

    runtime._record_run_started(
        run_id="run_started_flush",
        project_key="RUNE_CAM_ALPHA",
        scenario="RUNE_CAM_ALPHA",
        run_type="analysis",
        triggered_by="operator",
        trigger_source="manual",
    )

    persisted = store.list("audit_events")
    assert len(persisted) == 1
    assert persisted[0]["action"] == "run_started"
    assert persisted[0]["target_id"] == "run_started_flush"


class FailingWorkflow:
    """Workflow double that fails after creating traceable run state."""

    def __init__(self, traces: InMemoryTraceRepository) -> None:
        self.traces = traces

    def run(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        triggered_by: str,
        trigger_source: str,
    ) -> None:
        self.traces.create_run(
            run_id=run_id,
            run_type="analysis",
            project_key=project_key,
            triggered_by=triggered_by,
            trigger_source=trigger_source,  # type: ignore[arg-type]
        )
        self.traces.mark_run_running(run_id)
        raise RuntimeError(f"analysis failed for {scenario}")

    def ingest(
        self,
        *,
        run_id: str,
        project_key: str,
        scenario: str,
        triggered_by: str,
        trigger_source: str,
    ) -> None:
        self.traces.create_run(
            run_id=run_id,
            run_type="ingestion",
            project_key=project_key,
            triggered_by=triggered_by,
            trigger_source=trigger_source,  # type: ignore[arg-type]
        )
        self.traces.mark_run_running(run_id)
        raise RuntimeError(f"ingestion failed for {scenario}")


def test_analysis_failure_records_failed_run_and_audit_event(
    tmp_path,  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SQLiteStateStore(tmp_path / "runtime.sqlite3")
    runtime = RuntimeState.create(tmp_path / "artifacts", state_store=store)
    monkeypatch.setattr(
        RuntimeState,
        "workflow",
        lambda self: FailingWorkflow(self.traces),
    )

    with pytest.raises(RuntimeError, match="analysis failed"):
        runtime.run_analysis(
            run_id="run_failure_analysis",
            project_key="RUNE_CAM_ALPHA",
            scenario="RUNE_CAM_ALPHA",
            triggered_by="reviewer",
            trigger_source="api",
        )

    run = runtime.traces.runs["run_failure_analysis"]
    assert run.status == "failed"
    assert run.failure_code == "RuntimeError"
    assert run.failure_message == "analysis failed for RUNE_CAM_ALPHA"
    audit_events = [
        event
        for event in runtime.audit.events.values()
        if event.target_id == "run_failure_analysis"
    ]
    assert [event.action for event in audit_events] == ["run_started", "run_completed"]
    assert audit_events[-1].outcome == "failed"
    assert audit_events[-1].reason_code == "RuntimeError"
    assert audit_events[-1].metadata["run_type"] == "analysis"
    assert store.get("agent_runs", "run_failure_analysis")["status"] == "failed"
    persisted_audit = store.list("audit_events")
    assert {event["action"] for event in persisted_audit} == {
        "run_started",
        "run_completed",
    }


def test_ingestion_failure_records_failed_run_and_audit_event(
    tmp_path,  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = RuntimeState.create(tmp_path / "artifacts")
    monkeypatch.setattr(
        RuntimeState,
        "workflow",
        lambda self: FailingWorkflow(self.traces),
    )

    with pytest.raises(RuntimeError, match="ingestion failed"):
        runtime.run_ingestion(
            run_id="run_failure_ingestion",
            project_key="RUNE_CAM_ALPHA",
            scenario="RUNE_CAM_ALPHA",
            triggered_by="scheduler",
            trigger_source="schedule",
        )

    run = runtime.traces.runs["run_failure_ingestion"]
    assert run.status == "failed"
    audit_events = [
        event
        for event in runtime.audit.events.values()
        if event.target_id == "run_failure_ingestion"
    ]
    assert [event.action for event in audit_events] == ["run_started", "run_completed"]
    assert audit_events[-1].actor_id == "scheduler"
    assert audit_events[-1].actor_role == "system"
    assert audit_events[-1].outcome == "failed"
    assert audit_events[-1].metadata["run_type"] == "ingestion"

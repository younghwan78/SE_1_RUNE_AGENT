"""Persistence-backed runtime contract tests."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.api.state import RuntimeState
from req_tracker.audit.models import AuditRetentionPolicy
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
    assert counts["agent_step_traces"] >= 8
    assert counts["llm_call_traces"] == 3
    assert counts["source_artifacts"] == 10
    assert counts["source_sync_cursors"] == 1
    assert counts["graph_nodes"] == 10
    assert counts["approval_items"] >= 1
    assert counts["graph_edges"] == 1


def test_sqlite_state_store_restores_dashboard_preferences_and_assignments(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "runtime.sqlite3"
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        state_store="sqlite",
        sqlite_state_path=db_path,
    )
    headers = {"x-rune-user": "reviewer_1", "x-rune-role": "developer"}
    first_app = create_app(settings)
    with TestClient(first_app) as client:
        preference = client.put(
            "/api/v1/dashboard/work-queue/preferences?project_key=RUNE_CAM_ALPHA",
            headers=headers,
            json={
                "saved_filters": {
                    "Mine": {
                        "item_type": "approval",
                        "priority": "high",
                        "owner": "assigned_to_me",
                    }
                }
            },
        )
        assignment = client.post(
            "/api/v1/dashboard/work-queue/assignments/q_restore_001",
            headers={**headers, "Idempotency-Key": "idem-dashboard-assignment-restore"},
            json={"project_key": "RUNE_CAM_ALPHA", "action": "assign"},
        )

    assert preference.status_code == 200
    assert assignment.status_code == 200

    second_app = create_app(settings)
    with TestClient(second_app) as client:
        restored_preference = client.get(
            "/api/v1/dashboard/work-queue/preferences?project_key=RUNE_CAM_ALPHA",
            headers=headers,
        )
        restored_assignments = client.get(
            "/api/v1/dashboard/work-queue/assignments?project_key=RUNE_CAM_ALPHA",
            headers=headers,
        )

    assert restored_preference.status_code == 200
    assert restored_preference.json()["saved_filters"]["Mine"]["priority"] == "high"
    assert restored_assignments.status_code == 200
    assert restored_assignments.json()["assignments"][0]["queue_id"] == "q_restore_001"


def test_sqlite_state_store_restores_runtime_after_restart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "runtime.sqlite3"
    artifact_root = tmp_path / "artifacts"
    settings = Settings(
        artifact_root=artifact_root,
        state_store="sqlite",
        sqlite_state_path=db_path,
    )
    first_app = create_app(settings)
    with TestClient(first_app) as client:
        response = client.post(
            "/api/v1/runs/analyze",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_restore_1",
            },
        )
        assert response.status_code == 200
        finding = client.get("/api/v1/findings").json()[0]
        finding_status = client.post(
            f"/api/v1/findings/{finding['finding_id']}/status",
            json={"status": "acknowledged", "updated_by": "reviewer"},
        )
        assert finding_status.status_code == 200
        activation = client.post(
            "/api/v1/admin/prompt-versions/pv_edge_linking_v1/activate",
            json={
                "activated_by": "admin@example.com",
                "eval_passed": True,
                "reviewer_approved": True,
                "canary_passed": True,
            },
        )
        assert activation.status_code == 200
        for index in range(2):
            feedback = client.post(
                "/api/v1/feedback",
                json={
                    "feedback_id": f"fb_restore_improvement_{index}",
                    "target_type": "edge",
                    "target_id": f"edge_restore_improvement_{index}",
                    "action": "rejected",
                    "user_id": "reviewer",
                    "user_role": "System Architect",
                    "reason_code": "wrong_relation",
                },
            )
            assert feedback.status_code == 200
        improvements = client.get("/api/v1/improvements/candidates")
        improvement_id = improvements.json()[0]["candidate_id"]
        improvement = client.post(
            f"/api/v1/improvements/{improvement_id}/activate",
            json={"reviewer_approved": True, "canary_passed": True},
        )
        assert improvement.status_code == 200
        rollback = client.post(f"/api/v1/improvements/{improvement_id}/rollback")
        assert rollback.status_code == 200
        replay = client.post(
            "/api/v1/runs/run_restore_1/replay",
            json={"replay_run_id": "replay_restore_1", "scenario": "RUNE_CAM_ALPHA"},
        )
        assert replay.status_code == 200
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

    second_app = create_app(settings)
    with TestClient(second_app) as client:
        runs = client.get("/api/v1/debug/runs")
        graph = client.get("/api/v1/graph/projection?project_key=RUNE_CAM_ALPHA")
        approvals = client.get("/api/v1/approvals")
        audit = client.get("/api/v1/audit/events?project_key=RUNE_CAM_ALPHA")
        activation_audit = client.get("/api/v1/audit/events?action=prompt_version_activated")
        rollback_audit = client.get("/api/v1/audit/events?action=improvement_rolled_back")
        restored_improvements = client.get("/api/v1/improvements/candidates")
        llm_calls = client.get("/api/v1/runs/run_restore_1/llm-calls")
        steps = client.get("/api/v1/runs/run_restore_1/steps")
        replay_steps = client.get("/api/v1/runs/replay_restore_1/steps")
        replay_diff = client.get("/api/v1/replays/replay_restore_1/diff")
        findings = client.get("/api/v1/findings")
        finding_detail = client.get(f"/api/v1/findings/{finding['finding_id']}")

    assert runs.status_code == 200
    restored_runs = {run["run_id"]: run for run in runs.json()}
    assert restored_runs["run_restore_1"]["run_type"] == "analysis"
    assert restored_runs["replay_restore_1"]["run_type"] == "replay"
    assert graph.status_code == 200
    assert graph.json()["counts"]["visible_approved_edges"] == 1
    assert approvals.status_code == 200
    assert any(item["status"] == "approved" for item in approvals.json())
    assert llm_calls.status_code == 200
    restored_llm_calls = llm_calls.json()
    assert len(restored_llm_calls) == 3
    assert {call["model_profile_id"] for call in restored_llm_calls} == {"dummy-local"}
    assert {call["prompt_version_id"] for call in restored_llm_calls} == {
        "pv_node_extraction_v1",
        "pv_edge_linking_v1",
        "pv_finding_reasoning_v1",
    }
    assert steps.status_code == 200
    restored_llm_step = next(
        step for step in steps.json() if step["stage_name"] == "llm_assisted_reasoning"
    )
    assert restored_llm_step["retrieval_context_ref"] == "candidate_edges"
    assert restored_llm_step["validation_result"]["status"] == "passed"
    assert replay_steps.status_code == 200
    assert any(
        step["stage_name"] == "llm_assisted_reasoning" for step in replay_steps.json()
    )
    assert replay_diff.status_code == 200
    assert replay_diff.json()["source_run_id"] == "run_restore_1"
    assert replay_diff.json()["replay_run_id"] == "replay_restore_1"
    assert replay_diff.json()["compared_model_profile_ids"] == ["dummy-local"]
    assert replay_diff.json()["compared_prompt_version_ids"] == [
        "pv_node_extraction_v1",
        "pv_edge_linking_v1",
        "pv_finding_reasoning_v1",
    ]
    runtime = second_app.state.runtime
    restored_cursor = runtime.source_sync_cursors[
        "src_cursor_dummy_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA"
    ]
    assert restored_cursor.run_id == "run_restore_1"
    assert restored_cursor.artifact_count == 10
    assert restored_cursor.page_count == 1
    assert restored_cursor.completed_cursor is not None
    assert restored_cursor.completed_cursor.offset == 10
    assert (
        runtime.registry_activations["prompt_version:pv_edge_linking_v1"]["status"]
        == "active"
    )
    assert findings.status_code == 200
    assert findings.json()
    assert finding_detail.status_code == 200
    assert finding_detail.json()["approval_status"] == "acknowledged"
    assert audit.status_code == 200
    assert {event["action"] for event in audit.json()} >= {
        "run_started",
        "run_completed",
        "approval_decided",
        "finding_status_changed",
    }
    restored_run_started = next(
        event
        for event in audit.json()
        if event["action"] == "run_started" and event["target_id"] == "run_restore_1"
    )
    assert restored_run_started["metadata"]["run_type"] == "analysis"
    assert restored_run_started["metadata"]["trigger_source"] == "api"
    restored_replay_completed = next(
        event
        for event in audit.json()
        if event["action"] == "run_completed" and event["target_id"] == "replay_restore_1"
    )
    assert restored_replay_completed["metadata"]["run_type"] == "replay"
    assert restored_replay_completed["metadata"]["source_run_id"] == "run_restore_1"
    assert activation_audit.status_code == 200
    assert activation_audit.json()[0]["action"] == "prompt_version_activated"
    assert rollback_audit.status_code == 200
    assert rollback_audit.json()[0]["action"] == "improvement_rolled_back"
    assert restored_improvements.status_code == 200
    restored_improvement = next(
        item
        for item in restored_improvements.json()
        if item["candidate_id"] == improvement_id
    )
    assert restored_improvement["status"] == "rolled_back"
    assert (
        second_app.state.runtime.improvement_decisions[improvement_id]["status"]
        == "rolled_back"
    )


def test_sqlite_state_store_restores_analyze_idempotency_after_restart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "runtime.sqlite3"
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        state_store="sqlite",
        sqlite_state_path=db_path,
    )
    payload = {
        "project_key": "RUNE_CAM_ALPHA",
        "scenario": "RUNE_CAM_ALPHA",
        "run_id": "run_idempotency_restore",
    }

    first_app = create_app(settings)
    with TestClient(first_app) as client:
        first = client.post(
            "/api/v1/runs/analyze",
            json=payload,
            headers={"Idempotency-Key": "idem-restore-1"},
        )
        assert first.status_code == 200

    store = SQLiteStateStore(db_path)
    assert store.counts_by_collection()["idempotency_results"] == 1

    second_app = create_app(settings)
    with TestClient(second_app) as client:
        second = client.post(
            "/api/v1/runs/analyze",
            json=payload,
            headers={"Idempotency-Key": "idem-restore-1"},
        )
        conflict = client.post(
            "/api/v1/runs/analyze",
            json={**payload, "scenario": "RUNE_CAM_ALPHA_VARIANT"},
            headers={"Idempotency-Key": "idem-restore-1"},
        )
        runs = client.get("/api/v1/runs?project_key=RUNE_CAM_ALPHA")

    assert second.status_code == 200
    assert second.json()["run"]["run_id"] == "run_idempotency_restore"
    assert conflict.status_code == 409
    assert runs.status_code == 200
    assert [run["run_id"] for run in runs.json()].count("run_idempotency_restore") == 1


def test_sqlite_state_store_restores_replay_idempotency_after_restart(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "runtime.sqlite3"
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        state_store="sqlite",
        sqlite_state_path=db_path,
    )

    first_app = create_app(settings)
    with TestClient(first_app) as client:
        analyze = client.post(
            "/api/v1/runs/analyze",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_replay_restore_idem",
            },
        )
        first = client.post(
            "/api/v1/runs/run_replay_restore_idem/replay",
            json={
                "replay_run_id": "replay_restore_idem",
                "scenario": "RUNE_CAM_ALPHA",
            },
            headers={"Idempotency-Key": "idem-replay-restore-1"},
        )
    assert analyze.status_code == 200
    assert first.status_code == 200

    second_app = create_app(settings)
    with TestClient(second_app) as client:
        second = client.post(
            "/api/v1/runs/run_replay_restore_idem/replay",
            json={
                "replay_run_id": "replay_restore_idem",
                "scenario": "RUNE_CAM_ALPHA",
            },
            headers={"Idempotency-Key": "idem-replay-restore-1"},
        )
        conflict = client.post(
            "/api/v1/runs/run_replay_restore_idem/replay",
            json={
                "replay_run_id": "replay_restore_idem_conflict",
                "scenario": "RUNE_CAM_ALPHA",
            },
            headers={"Idempotency-Key": "idem-replay-restore-1"},
        )
        uncached = client.post(
            "/api/v1/runs/run_replay_restore_idem/replay",
            json={
                "replay_run_id": "replay_restore_uncached",
                "scenario": "RUNE_CAM_ALPHA",
            },
        )

    assert second.status_code == 200
    assert second.json() == first.json()
    assert conflict.status_code == 409
    assert uncached.status_code == 404
    assert uncached.json()["detail"] == "run analysis result not available for replay"


def test_sqlite_state_store_restores_audit_archive_prune_idempotency_after_restart(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    db_path = tmp_path / "runtime.sqlite3"
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        state_store="sqlite",
        sqlite_state_path=db_path,
        audit_max_events=1,
    )

    first_app = create_app(settings)
    with TestClient(first_app) as client:
        analyze = client.post(
            "/api/v1/runs/analyze",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_audit_archive_restore",
            },
        )
        first = client.post(
            "/api/v1/audit/retention/archive-prune",
            headers={"Idempotency-Key": "idem-audit-archive-restore-1"},
        )
    assert analyze.status_code == 200
    assert first.status_code == 200
    assert first.json()["archived_events"] >= 1

    second_app = create_app(settings)
    with TestClient(second_app) as client:
        second = client.post(
            "/api/v1/audit/retention/archive-prune",
            headers={"Idempotency-Key": "idem-audit-archive-restore-1"},
        )
        audit = client.get("/api/v1/audit/events?action=audit_archive_pruned")

    assert second.status_code == 200
    assert second.json() == first.json()
    assert audit.status_code == 200
    assert len(audit.json()) == 1


def test_runtime_archive_prune_deletes_pruned_audit_rows_from_state_store(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStateStore(tmp_path / "runtime.sqlite3")
    runtime = RuntimeState.create(
        tmp_path / "artifacts",
        state_store=store,
        audit_policy=AuditRetentionPolicy(retention_days=1, max_events=100),
    )
    event = runtime.audit.record(
        action="run_completed",
        actor_id="system",
        target_type="run",
        target_id="run_old_audit",
        project_key="RUNE_CAM_ALPHA",
    )
    runtime.audit.events[event.audit_id] = event.model_copy(
        update={"created_at": datetime(2020, 1, 1, tzinfo=UTC)}
    )
    runtime.persist_approval_state()

    result = runtime.archive_and_prune_audit()

    assert result["pruned_audit_ids"] == [event.audit_id]
    assert store.get("audit_events", event.audit_id) is None

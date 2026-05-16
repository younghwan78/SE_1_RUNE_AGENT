"""Replay and feedback API tests."""

from fastapi.testclient import TestClient


def test_replay_and_feedback_eval_api(client: TestClient) -> None:
    client.post(
        "/api/v1/runs/analyze",
        json={"project_key": "RUNE_CAM_ALPHA", "scenario": "RUNE_CAM_ALPHA", "run_id": "run_rf_1"},
    )
    replay = client.post(
        "/api/v1/runs/run_rf_1/replay",
        json={"replay_run_id": "replay_rf_1", "scenario": "RUNE_CAM_ALPHA"},
    )
    assert replay.status_code == 200
    replay_run = client.get("/api/v1/runs/replay_rf_1")
    assert replay_run.status_code == 200
    assert replay_run.json()["run_type"] == "replay"
    assert replay_run.json()["triggered_by"] == "replay"
    assert replay_run.json()["trigger_source"] == "system"
    audit = client.get("/api/v1/audit/events?project_key=RUNE_CAM_ALPHA")
    replay_audit = [
        event for event in audit.json() if event["target_id"] == "replay_rf_1"
    ]
    assert {event["action"] for event in replay_audit} == {
        "run_started",
        "run_completed",
    }
    completed_replay_audit = next(
        event for event in replay_audit if event["action"] == "run_completed"
    )
    assert completed_replay_audit["metadata"]["run_type"] == "replay"
    assert completed_replay_audit["metadata"]["source_run_id"] == "run_rf_1"
    diff = replay.json()["diff"]
    assert diff["node_diff"]["added"] == []
    assert diff["edge_diff"]["removed"] == []
    assert replay.json()["compared_model_profile_ids"] == ["dummy-local"]
    assert replay.json()["compared_prompt_version_ids"] == [
        "pv_node_extraction_v1",
        "pv_edge_linking_v1",
        "pv_finding_reasoning_v1",
    ]

    stored_diff = client.get("/api/v1/replays/replay_rf_1/diff")
    assert stored_diff.status_code == 200
    assert stored_diff.json()["source_run_id"] == "run_rf_1"
    assert stored_diff.json()["replay_run_id"] == "replay_rf_1"
    assert stored_diff.json()["compared_model_profile_ids"] == ["dummy-local"]
    assert stored_diff.json()["compared_prompt_version_ids"] == [
        "pv_node_extraction_v1",
        "pv_edge_linking_v1",
        "pv_finding_reasoning_v1",
    ]
    assert stored_diff.json()["diff"]["node_diff"]["added"] == []

    feedback = client.post(
        "/api/v1/feedback",
        json={
            "feedback_id": "fb_api_1",
            "target_type": "edge",
            "target_id": "edge_x",
            "action": "rejected",
            "user_id": "reviewer",
            "user_role": "System Architect",
            "reason_code": "wrong_relation",
        },
    )
    assert feedback.status_code == 200
    summary = client.get("/api/v1/feedback/summary")
    assert summary.json()["wrong_relation"] == 1
    candidates = client.get("/api/v1/eval/candidates")
    assert candidates.json()[0]["dataset_path"] == "edge_linking/rejected_edges.jsonl"

    improvements = client.get("/api/v1/improvements/candidates")
    assert improvements.status_code == 200
    candidate_id = improvements.json()[0]["candidate_id"]
    blocked = client.post(f"/api/v1/improvements/{candidate_id}/activate")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["message"] == "eval gate blocked activation"


def test_replay_idempotency_key_reuses_original_replay_result(client: TestClient) -> None:
    client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_replay_idempotent",
        },
    )

    first = client.post(
        "/api/v1/runs/run_replay_idempotent/replay",
        json={"scenario": "RUNE_CAM_ALPHA"},
        headers={"Idempotency-Key": "idem-replay-1"},
    )
    second = client.post(
        "/api/v1/runs/run_replay_idempotent/replay",
        json={"scenario": "RUNE_CAM_ALPHA"},
        headers={"Idempotency-Key": "idem-replay-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    runs = client.get("/api/v1/runs?project_key=RUNE_CAM_ALPHA")
    assert runs.status_code == 200
    assert [run["run_id"] for run in runs.json()].count(first.json()["replay_run_id"]) == 1


def test_improvement_activation_requires_review_and_canary_after_eval_passes(
    client: TestClient,
) -> None:
    for index in range(2):
        feedback = client.post(
            "/api/v1/feedback",
            json={
                "feedback_id": f"fb_gate_pass_{index}",
                "target_type": "edge",
                "target_id": f"edge_gate_pass_{index}",
                "action": "rejected",
                "user_id": "reviewer",
                "user_role": "System Architect",
                "reason_code": "wrong_relation",
            },
        )
        assert feedback.status_code == 200

    improvements = client.get("/api/v1/improvements/candidates")
    candidate_id = improvements.json()[0]["candidate_id"]
    review_ready = client.post(f"/api/v1/improvements/{candidate_id}/activate")
    canary = client.post(
        f"/api/v1/improvements/{candidate_id}/activate",
        json={"reviewer_approved": True, "canary_passed": False},
    )
    active = client.post(
        f"/api/v1/improvements/{candidate_id}/activate",
        json={"reviewer_approved": True, "canary_passed": True},
    )
    backwards = client.post(f"/api/v1/improvements/{candidate_id}/activate")

    assert review_ready.status_code == 200
    assert review_ready.json()["status"] == "review_ready"
    assert review_ready.json()["promotion_status"] == "review_required"
    assert canary.status_code == 200
    assert canary.json()["status"] == "canary"
    assert canary.json()["promotion_status"] == "canary_required"
    assert active.status_code == 200
    assert active.json()["status"] == "active"
    assert active.json()["promotion_status"] == "active"
    assert backwards.status_code == 409
    assert backwards.json()["detail"]["message"] == "improvement promotion cannot move backwards"


def test_active_improvement_can_be_rolled_back_and_audited(
    client: TestClient,
) -> None:
    for index in range(2):
        feedback = client.post(
            "/api/v1/feedback",
            json={
                "feedback_id": f"fb_improvement_rollback_{index}",
                "target_type": "edge",
                "target_id": f"edge_improvement_rollback_{index}",
                "action": "rejected",
                "user_id": "reviewer",
                "user_role": "System Architect",
                "reason_code": "wrong_relation",
            },
        )
        assert feedback.status_code == 200

    improvements = client.get("/api/v1/improvements/candidates")
    candidate_id = improvements.json()[0]["candidate_id"]
    active = client.post(
        f"/api/v1/improvements/{candidate_id}/activate",
        json={"reviewer_approved": True, "canary_passed": True},
    )
    rollback = client.post(
        f"/api/v1/improvements/{candidate_id}/rollback",
        json={
            "rolled_back_by": "admin@example.com",
            "reason_code": "canary_regression",
            "comment": "reject rate increased during local rehearsal",
        },
        headers={"Idempotency-Key": "idem-improvement-rollback-1"},
    )
    retry = client.post(
        f"/api/v1/improvements/{candidate_id}/rollback",
        json={
            "rolled_back_by": "admin@example.com",
            "reason_code": "canary_regression",
            "comment": "reject rate increased during local rehearsal",
        },
        headers={"Idempotency-Key": "idem-improvement-rollback-1"},
    )
    after = client.get("/api/v1/improvements/candidates")
    audit = client.get("/api/v1/audit/events?action=improvement_rolled_back")

    assert active.status_code == 200
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"
    assert rollback.json()["rollback_status"] == "rolled_back"
    assert rollback.json()["previous_status"] == "active"
    assert rollback.json()["restored_version_id"] == "local_active"
    assert retry.status_code == 200
    assert retry.json() == rollback.json()
    assert after.json()[0]["status"] == "rolled_back"
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "improvement_rolled_back"


def test_draft_improvement_cannot_be_rolled_back(client: TestClient) -> None:
    for index in range(2):
        feedback = client.post(
            "/api/v1/feedback",
            json={
                "feedback_id": f"fb_improvement_draft_rollback_{index}",
                "target_type": "edge",
                "target_id": f"edge_improvement_draft_rollback_{index}",
                "action": "rejected",
                "user_id": "reviewer",
                "user_role": "System Architect",
                "reason_code": "wrong_relation",
            },
        )
        assert feedback.status_code == 200

    improvements = client.get("/api/v1/improvements/candidates")
    candidate_id = improvements.json()[0]["candidate_id"]
    rollback = client.post(f"/api/v1/improvements/{candidate_id}/rollback")

    assert rollback.status_code == 409
    assert rollback.json()["detail"]["message"] == "improvement is not rollbackable"


def test_improvement_activation_idempotency_key_reuses_eval_response(
    client: TestClient,
) -> None:
    for index in range(2):
        feedback = client.post(
            "/api/v1/feedback",
            json={
                "feedback_id": f"fb_improvement_idem_{index}",
                "target_type": "edge",
                "target_id": f"edge_improvement_idem_{index}",
                "action": "rejected",
                "user_id": "reviewer",
                "user_role": "System Architect",
                "reason_code": "wrong_relation",
            },
        )
        assert feedback.status_code == 200

    improvements = client.get("/api/v1/improvements/candidates")
    candidate_id = improvements.json()[0]["candidate_id"]
    first = client.post(
        f"/api/v1/improvements/{candidate_id}/activate",
        json={"reviewer_approved": True, "canary_passed": False},
        headers={"Idempotency-Key": "idem-improvement-1"},
    )
    second = client.post(
        f"/api/v1/improvements/{candidate_id}/activate",
        json={"reviewer_approved": True, "canary_passed": False},
        headers={"Idempotency-Key": "idem-improvement-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_feedback_idempotency_key_avoids_duplicate_feedback_events(
    client: TestClient,
) -> None:
    payload = {
        "feedback_id": "fb_idempotent_1",
        "target_type": "edge",
        "target_id": "edge_idempotent",
        "action": "rejected",
        "user_id": "reviewer",
        "user_role": "System Architect",
        "reason_code": "wrong_relation",
    }
    first = client.post(
        "/api/v1/feedback",
        json=payload,
        headers={"Idempotency-Key": "idem-feedback-1"},
    )
    second = client.post(
        "/api/v1/feedback",
        json=payload,
        headers={"Idempotency-Key": "idem-feedback-1"},
    )
    conflict = client.post(
        "/api/v1/feedback",
        json={**payload, "reason_code": "weak_evidence"},
        headers={"Idempotency-Key": "idem-feedback-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert conflict.status_code == 409

    summary = client.get("/api/v1/feedback/summary")
    assert summary.status_code == 200
    assert summary.json()["wrong_relation"] == 1


def test_feedback_api_normalizes_command_style_actions(client: TestClient) -> None:
    feedback = client.post(
        "/api/v1/feedback",
        json={
            "feedback_id": "fb_api_alias_1",
            "target_type": "edge",
            "target_id": "edge_alias",
            "action": "reject",
            "user_id": "reviewer",
            "user_role": "System Architect",
            "reason_code": "wrong relation",
        },
    )
    summary = client.get("/api/v1/feedback/summary")

    assert feedback.status_code == 200
    assert feedback.json()["action"] == "rejected"
    assert feedback.json()["reason_code"] == "wrong_relation"
    assert summary.status_code == 200
    assert summary.json()["wrong_relation"] == 1

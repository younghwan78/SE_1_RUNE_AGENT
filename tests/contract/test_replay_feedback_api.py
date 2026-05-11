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
    assert replay_run.json()["triggered_by"] == "replay"
    assert replay_run.json()["trigger_source"] == "system"
    diff = replay.json()["diff"]
    assert diff["node_diff"]["added"] == []
    assert diff["edge_diff"]["removed"] == []

    stored_diff = client.get("/api/v1/replays/replay_rf_1/diff")
    assert stored_diff.status_code == 200
    assert stored_diff.json()["source_run_id"] == "run_rf_1"
    assert stored_diff.json()["replay_run_id"] == "replay_rf_1"
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

    assert review_ready.status_code == 200
    assert review_ready.json()["status"] == "review_ready"
    assert review_ready.json()["promotion_status"] == "review_required"
    assert canary.status_code == 200
    assert canary.json()["status"] == "canary"
    assert canary.json()["promotion_status"] == "canary_required"
    assert active.status_code == 200
    assert active.json()["status"] == "active"
    assert active.json()["promotion_status"] == "active"


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

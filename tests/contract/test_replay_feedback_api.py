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
    diff = replay.json()["diff"]
    assert diff["node_diff"]["added"] == []
    assert diff["edge_diff"]["removed"] == []

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

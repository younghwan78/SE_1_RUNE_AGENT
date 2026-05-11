"""Audit API contract tests."""

from urllib.parse import quote

from fastapi.testclient import TestClient


def test_audit_events_capture_operational_actions(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_audit_1",
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

    feedback = client.post(
        "/api/v1/feedback",
        json={
            "feedback_id": "fb_audit_1",
            "target_type": "edge",
            "target_id": "edge_x",
            "action": "rejected",
            "user_id": "reviewer",
            "user_role": "System Architect",
            "reason_code": "weak_evidence",
        },
    )
    assert feedback.status_code == 200

    summary = client.get("/api/v1/debug/runs/run_audit_1/summary").json()
    artifact_ref = summary["artifact_refs"][0]
    artifact = client.get(f"/api/v1/debug/artifact?artifact_ref={quote(artifact_ref)}")
    assert artifact.status_code == 200

    audit = client.get("/api/v1/audit/events?project_key=RUNE_CAM_ALPHA")
    assert audit.status_code == 200
    actions = {event["action"] for event in audit.json()}
    assert {
        "run_completed",
        "approval_decided",
        "debug_artifact_read",
    } <= actions

    feedback_audit = client.get("/api/v1/audit/events?action=feedback_recorded")
    assert feedback_audit.status_code == 200
    assert feedback_audit.json()[0]["reason_code"] == "weak_evidence"

    retention = client.get("/api/v1/audit/retention")
    assert retention.status_code == 200
    assert retention.json()["policy"]["retention_days"] == 365
    assert retention.json()["total_events"] >= 3

    archive = client.post("/api/v1/audit/retention/archive-prune")
    assert archive.status_code == 200
    assert archive.json()["archived_events"] == 0

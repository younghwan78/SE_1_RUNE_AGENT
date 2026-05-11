"""Run and approval API contract tests."""

from fastapi.testclient import TestClient


def test_analyze_run_and_approve_edge(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_api_1",
        },
    )
    assert response.status_code == 200
    assert response.json()["run"]["input_snapshot_ids"]
    assert response.json()["run"]["trigger_source"] == "api"
    counts = response.json()["counts"]
    assert counts["nodes"] == 10
    assert counts["approvals"] >= 1

    runs = client.get("/api/v1/runs?project_key=RUNE_CAM_ALPHA")
    assert runs.status_code == 200
    assert runs.json()[0]["run_id"] == "run_api_1"
    assert runs.json()[0]["project_key"] == "RUNE_CAM_ALPHA"
    assert runs.json()[0]["trigger_source"] == "api"

    steps = client.get("/api/v1/runs/run_api_1/steps")
    assert steps.status_code == 200
    assert {step["stage_name"] for step in steps.json()} >= {
        "source_fetch",
        "normalize",
        "mask_chunk",
        "extract_nodes",
        "link_edges",
        "llm_assisted_reasoning",
        "detect_findings",
        "stage_approval",
    }

    approvals = client.get("/api/v1/approvals")
    approval = approvals.json()[0]
    decision = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json={
            "approval_id": approval["approval_id"],
            "action": "approve",
            "decided_by": "reviewer",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    graph = client.get("/api/v1/graph/subgraph?project_key=RUNE_CAM_ALPHA")
    assert graph.status_code == 200
    assert len(graph.json()["edges"]) == 1

    projection = client.get("/api/v1/graph/projection?project_key=RUNE_CAM_ALPHA")
    assert projection.status_code == 200
    assert len(projection.json()["nodes"]) == 10
    assert len(projection.json()["approved_edges"]) == 1
    assert len(projection.json()["pending_edges"]) >= 1
    assert projection.json()["pending_edges"][0]["approval_status"] == "pending"
    assert projection.json()["counts"]["orphan_nodes"] >= 1


def test_analyze_run_idempotency_key_returns_original_response(client: TestClient) -> None:
    payload = {
        "project_key": "RUNE_CAM_ALPHA",
        "scenario": "RUNE_CAM_ALPHA",
        "run_id": "run_api_idempotent",
    }
    first = client.post(
        "/api/v1/runs/analyze",
        json=payload,
        headers={"Idempotency-Key": "idem-analyze-1"},
    )
    second = client.post(
        "/api/v1/runs/analyze",
        json=payload,
        headers={"Idempotency-Key": "idem-analyze-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    runs = client.get("/api/v1/runs?project_key=RUNE_CAM_ALPHA")
    assert runs.status_code == 200
    assert [run["run_id"] for run in runs.json()].count("run_api_idempotent") == 1


def test_analyze_run_idempotency_key_rejects_different_payload(client: TestClient) -> None:
    first = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_api_idempotency_conflict",
        },
        headers={"Idempotency-Key": "idem-analyze-conflict"},
    )
    conflict = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA_VARIANT",
            "run_id": "run_api_idempotency_conflict",
        },
        headers={"Idempotency-Key": "idem-analyze-conflict"},
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["message"] == (
        "idempotency key reused with different request"
    )


def test_approval_decision_idempotency_key_avoids_duplicate_side_effects(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_api_approval_idempotent",
        },
    )
    assert response.status_code == 200
    approval = client.get("/api/v1/approvals").json()[0]
    payload = {
        "approval_id": approval["approval_id"],
        "action": "approve",
        "decided_by": "reviewer",
    }

    first = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json=payload,
        headers={"Idempotency-Key": "idem-approval-1"},
    )
    second = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json=payload,
        headers={"Idempotency-Key": "idem-approval-1"},
    )
    conflict = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json={**payload, "action": "reject"},
        headers={"Idempotency-Key": "idem-approval-1"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert conflict.status_code == 409

    audit = client.get("/api/v1/audit/events?project_key=RUNE_CAM_ALPHA")
    assert audit.status_code == 200
    assert [event["action"] for event in audit.json()].count("approval_decided") == 1


def test_modify_approval_commits_corrected_edge_and_feedback(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_api_modify",
        },
    )
    assert response.status_code == 200

    approval = client.get("/api/v1/approvals").json()[0]
    decision = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json={
            "approval_id": approval["approval_id"],
            "action": "modify",
            "decided_by": "reviewer",
            "reason_code": "wrong_relation",
            "correction_payload": {
                "relation": "affects",
                "reasoning": "Reviewer corrected relation.",
            },
        },
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "modified_approved"

    graph = client.get("/api/v1/graph/subgraph?project_key=RUNE_CAM_ALPHA")
    assert graph.status_code == 200
    assert len(graph.json()["edges"]) == 1
    assert graph.json()["edges"][0]["relation"] == "affects"
    assert graph.json()["edges"][0]["approved_by"] == "reviewer"

    feedback = client.get("/api/v1/feedback/summary")
    assert feedback.status_code == 200
    assert feedback.json()["wrong_relation"] == 1


def test_finding_detail_and_status_update_are_idempotent(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_finding_status",
        },
    )
    assert response.status_code == 200
    finding = client.get("/api/v1/findings").json()[0]

    detail = client.get(f"/api/v1/findings/{finding['finding_id']}")
    assert detail.status_code == 200
    assert detail.json()["finding_id"] == finding["finding_id"]
    assert detail.json()["approval_status"] == "open"

    payload = {
        "status": "acknowledged",
        "updated_by": "reviewer",
        "reason_code": "triaged",
        "comment": "Reviewed during traceability triage.",
    }
    first = client.post(
        f"/api/v1/findings/{finding['finding_id']}/status",
        json=payload,
        headers={"Idempotency-Key": "idem-finding-status-1"},
    )
    second = client.post(
        f"/api/v1/findings/{finding['finding_id']}/status",
        json=payload,
        headers={"Idempotency-Key": "idem-finding-status-1"},
    )
    conflict = client.post(
        f"/api/v1/findings/{finding['finding_id']}/status",
        json={**payload, "status": "dismissed"},
        headers={"Idempotency-Key": "idem-finding-status-1"},
    )

    assert first.status_code == 200
    assert first.json()["approval_status"] == "acknowledged"
    assert second.status_code == 200
    assert second.json() == first.json()
    assert conflict.status_code == 409

    audit = client.get("/api/v1/audit/events?project_key=RUNE_CAM_ALPHA")
    assert audit.status_code == 200
    assert [event["action"] for event in audit.json()].count("finding_status_changed") == 1

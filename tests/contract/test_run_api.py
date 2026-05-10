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
    counts = response.json()["counts"]
    assert counts["nodes"] == 10
    assert counts["approvals"] >= 1

    steps = client.get("/api/v1/runs/run_api_1/steps")
    assert steps.status_code == 200
    assert {step["stage_name"] for step in steps.json()} >= {
        "source_fetch",
        "normalize",
        "mask_chunk",
        "extract_nodes",
        "link_edges",
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

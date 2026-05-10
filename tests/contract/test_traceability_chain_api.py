"""Traceability chain API tests."""

from fastapi.testclient import TestClient


def test_traceability_chain_includes_pending_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_chain_1",
        },
    )
    assert response.status_code == 200

    node_id = "node_RUNE_CAM_ALPHA_CAM_REQ_001"
    chain = client.get(f"/api/v1/traceability/chain/{node_id}?depth=2&include_pending=true")
    assert chain.status_code == 200
    payload = chain.json()
    assert payload["center_node_id"] == node_id
    assert any(node["is_center"] for node in payload["nodes"])
    assert len(payload["nodes"]) > 1
    assert payload["edges"]
    assert all(edge["view_status"] in {"approved", "pending"} for edge in payload["edges"])
    assert any(
        edge["view_status"] == "pending" and edge["approval_id"]
        for edge in payload["edges"]
    )


def test_traceability_chain_requires_existing_node(client: TestClient) -> None:
    response = client.get("/api/v1/traceability/chain/missing_node")
    assert response.status_code == 404

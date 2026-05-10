"""Graph projection API contract tests."""

from fastapi.testclient import TestClient


def test_graph_projection_scale_modes(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_SCALE_150",
            "run_id": "run_scale_150",
        },
    )
    assert response.status_code == 200
    assert response.json()["counts"]["nodes"] == 150

    overview = client.get("/api/v1/graph/projection?mode=overview&limit_nodes=120")
    assert overview.status_code == 200
    overview_payload = overview.json()
    assert overview_payload["counts"]["total_nodes"] == 150
    assert overview_payload["counts"]["visible_nodes"] <= 120
    assert overview_payload["counts"]["orphan_nodes"] > 0
    assert overview_payload["counts"]["pending_edges"] > 0
    assert "approved_in_degree" in overview_payload["nodes"][0]

    orphans = client.get("/api/v1/graph/projection?mode=orphans&limit_nodes=200")
    assert orphans.status_code == 200
    orphan_nodes = orphans.json()["nodes"]
    assert orphan_nodes
    assert all(node["is_orphan"] for node in orphan_nodes)

    pending = client.get("/api/v1/graph/projection?mode=pending&limit_nodes=200")
    assert pending.status_code == 200
    pending_payload = pending.json()
    pending_nodes = pending_payload["nodes"]
    assert pending_nodes
    assert all(node["has_pending_edges"] for node in pending_nodes)

    search = client.get(
        "/api/v1/graph/projection?mode=overview&search_query=SCL-DES-011&limit_nodes=200"
    )
    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload["search_query"] == "SCL-DES-011"
    assert len(search_payload["nodes"]) == 1
    assert search_payload["nodes"][0]["node_id"] == "node_RUNE_CAM_ALPHA_SCL_DES_011"

    center_node_id = "node_RUNE_CAM_ALPHA_SCL_REQ_001"
    neighborhood = client.get(
        f"/api/v1/graph/projection?mode=neighborhood&center_node_id={center_node_id}&hops=1"
    )
    assert neighborhood.status_code == 200
    neighborhood_payload = neighborhood.json()
    assert neighborhood_payload["center_node_id"] == center_node_id
    assert any(node["node_id"] == center_node_id for node in neighborhood_payload["nodes"])
    assert len(neighborhood_payload["nodes"]) < overview_payload["counts"]["total_nodes"]

    pending_edges = client.get("/api/v1/graph/projection?mode=pending&edge_filter=pending")
    assert pending_edges.status_code == 200
    pending_edge_payload = pending_edges.json()
    assert pending_edge_payload["edge_filter"] == "pending"
    assert pending_edge_payload["counts"]["visible_approved_edges"] == 0
    assert pending_edge_payload["counts"]["visible_pending_edges"] == len(
        pending_edge_payload["edges"]
    )
    assert pending_edge_payload["edges"]
    assert pending_edge_payload["edges"][0]["approval_id"]
    assert pending_edge_payload["edges"][0]["source_node_name"]
    assert pending_edge_payload["edges"][0]["target_node_name"]

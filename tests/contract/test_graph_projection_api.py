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
    pending_nodes = pending.json()["nodes"]
    assert pending_nodes
    assert all(node["has_pending_edges"] for node in pending_nodes)


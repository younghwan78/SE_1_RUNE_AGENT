"""Health API contract tests."""

from fastapi.testclient import TestClient


def test_health_endpoint_defaults_to_dummy_modes(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"x-correlation-id": "corr_test"})
    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "corr_test"
    body = response.json()
    assert body["status"] == "ok"
    assert body["datasource_mode"] == "dummy"
    assert body["graph_backend"] == "memory"
    assert body["vector_backend"] == "memory"
    assert body["model_gateway_mode"] == "dummy"


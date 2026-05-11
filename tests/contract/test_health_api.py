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


def test_readiness_endpoint_reports_backend_checks(client: TestClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["state_store"]["status"] == "ok"
    assert body["checks"]["state_store"]["mode"] == "memory"
    assert body["checks"]["graph_backend"]["status"] == "ok"
    assert body["checks"]["vector_backend"]["mode"] == "memory"
    assert body["checks"]["artifact_store"]["status"] == "ok"

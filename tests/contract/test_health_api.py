"""Health API contract tests."""

import logging

from fastapi.testclient import TestClient
from pytest import LogCaptureFixture


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


def test_request_log_includes_correlation_and_user_id(
    client: TestClient,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="req_tracker.api.request")

    response = client.get(
        "/api/v1/health",
        headers={
            "x-correlation-id": "corr_log_test",
            "x-rune-user": "engineer@example.com",
        },
    )

    assert response.status_code == 200
    request_records = [
        record
        for record in caplog.records
        if record.name == "req_tracker.api.request" and record.getMessage() == "http_request"
    ]
    assert request_records
    record = request_records[-1]
    assert record.correlation_id == "corr_log_test"
    assert record.user_id == "engineer@example.com"
    assert record.method == "GET"
    assert record.path == "/api/v1/health"
    assert record.status_code == 200
    assert isinstance(record.duration_ms, float)


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

"""API-key RBAC contract tests."""

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def test_api_key_auth_protects_debug_and_audit_routes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            auth_mode="api_key",
            api_key="secret",
        )
    )
    with TestClient(app) as client:
        missing_key = client.get("/api/v1/debug/runs/missing/summary")
        bad_role = client.get(
            "/api/v1/debug/runs/missing/summary",
            headers={"x-rune-api-key": "secret", "x-rune-role": "viewer"},
        )
        allowed = client.get(
            "/api/v1/debug/runs/missing/summary",
            headers={"x-rune-api-key": "secret", "x-rune-role": "developer"},
        )
        audit_forbidden = client.get(
            "/api/v1/audit/events",
            headers={"x-rune-api-key": "secret", "x-rune-role": "developer"},
        )
        audit_allowed = client.get(
            "/api/v1/audit/events",
            headers={"x-rune-api-key": "secret", "x-rune-role": "operator"},
        )

    assert missing_key.status_code == 401
    assert bad_role.status_code == 403
    assert allowed.status_code == 404
    assert audit_forbidden.status_code == 403
    assert audit_allowed.status_code == 200


def test_local_auth_mode_keeps_existing_debug_access(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(Settings(artifact_root=tmp_path / "artifacts", auth_mode="local"))
    with TestClient(app) as client:
        response = client.get("/api/v1/audit/events")

    assert response.status_code == 200

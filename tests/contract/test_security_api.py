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
        diff_bad_role = client.get(
            "/api/v1/debug/runs/missing/diff-view",
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
        retention_forbidden = client.get(
            "/api/v1/audit/retention",
            headers={"x-rune-api-key": "secret", "x-rune-role": "developer"},
        )
        archive_forbidden = client.post(
            "/api/v1/audit/retention/archive-prune",
            headers={"x-rune-api-key": "secret", "x-rune-role": "operator"},
        )
        audit_allowed = client.get(
            "/api/v1/audit/events",
            headers={"x-rune-api-key": "secret", "x-rune-role": "operator"},
        )
        retention_allowed = client.get(
            "/api/v1/audit/retention",
            headers={"x-rune-api-key": "secret", "x-rune-role": "operator"},
        )

    assert missing_key.status_code == 401
    assert bad_role.status_code == 403
    assert diff_bad_role.status_code == 403
    assert allowed.status_code == 404
    assert audit_forbidden.status_code == 403
    assert retention_forbidden.status_code == 403
    assert archive_forbidden.status_code == 403
    assert audit_allowed.status_code == 200
    assert retention_allowed.status_code == 200


def test_local_auth_mode_keeps_existing_debug_access(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(Settings(artifact_root=tmp_path / "artifacts", auth_mode="local"))
    with TestClient(app) as client:
        response = client.get("/api/v1/audit/events")

    assert response.status_code == 200


def test_api_key_auth_enforces_project_scope(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            auth_mode="api_key",
            api_key="secret",
        )
    )
    allowed_headers = {
        "x-rune-api-key": "secret",
        "x-rune-role": "developer",
        "x-rune-projects": "RUNE_CAM_ALPHA",
    }
    denied_headers = {
        "x-rune-api-key": "secret",
        "x-rune-role": "developer",
        "x-rune-projects": "OTHER_PROJECT",
    }
    with TestClient(app) as client:
        run = client.post(
            "/api/v1/runs/analyze",
            headers=allowed_headers,
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_project_auth",
            },
        )
        graph_denied = client.get(
            "/api/v1/graph/projection?project_key=RUNE_CAM_ALPHA",
            headers=denied_headers,
        )
        debug_denied = client.get(
            "/api/v1/debug/runs/run_project_auth/summary",
            headers=denied_headers,
        )
        audit_denied = client.get(
            "/api/v1/audit/events?project_key=RUNE_CAM_ALPHA",
            headers={**denied_headers, "x-rune-role": "operator"},
        )

    assert run.status_code == 200
    assert graph_denied.status_code == 403
    assert debug_denied.status_code == 403
    assert audit_denied.status_code == 403


def test_api_key_auth_protects_approval_review_and_decision(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            auth_mode="api_key",
            api_key="secret",
        )
    )
    developer_headers = {
        "x-rune-api-key": "secret",
        "x-rune-role": "developer",
        "x-rune-projects": "RUNE_CAM_ALPHA",
    }
    operator_headers = {
        **developer_headers,
        "x-rune-role": "operator",
    }
    viewer_headers = {
        **developer_headers,
        "x-rune-role": "viewer",
    }
    wrong_project_headers = {
        **operator_headers,
        "x-rune-projects": "OTHER_PROJECT",
    }
    with TestClient(app) as client:
        run = client.post(
            "/api/v1/runs/analyze",
            headers=developer_headers,
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_approval_auth",
            },
        )
        viewer_list = client.get("/api/v1/approvals", headers=viewer_headers)
        developer_list = client.get(
            "/api/v1/approvals?project_key=RUNE_CAM_ALPHA",
            headers=developer_headers,
        )
        approval = developer_list.json()[0]
        developer_decision = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decision",
            headers=developer_headers,
            json={
                "approval_id": approval["approval_id"],
                "action": "approve",
                "decided_by": "reviewer",
            },
        )
        wrong_project_decision = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decision",
            headers=wrong_project_headers,
            json={
                "approval_id": approval["approval_id"],
                "action": "approve",
                "decided_by": "reviewer",
            },
        )
        operator_decision = client.post(
            f"/api/v1/approvals/{approval['approval_id']}/decision",
            headers=operator_headers,
            json={
                "approval_id": approval["approval_id"],
                "action": "approve",
                "decided_by": "reviewer",
            },
        )

    assert run.status_code == 200
    assert viewer_list.status_code == 403
    assert developer_list.status_code == 200
    assert developer_decision.status_code == 403
    assert wrong_project_decision.status_code == 403
    assert operator_decision.status_code == 200


def test_trusted_proxy_auth_maps_groups_to_roles_and_projects(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            auth_mode="trusted_proxy",
            trusted_proxy_secret="proxy-secret",
        )
    )
    allowed_headers = {
        "x-rune-trusted-secret": "proxy-secret",
        "x-rune-user": "sso.user@example.com",
        "x-rune-groups": "rune-developers,rune-operators",
        "x-rune-projects": "RUNE_CAM_ALPHA",
    }
    denied_headers = {
        **allowed_headers,
        "x-rune-projects": "OTHER_PROJECT",
    }
    with TestClient(app) as client:
        allowed = client.get(
            "/api/v1/audit/events?project_key=RUNE_CAM_ALPHA",
            headers=allowed_headers,
        )
        project_denied = client.get(
            "/api/v1/audit/events?project_key=RUNE_CAM_ALPHA",
            headers=denied_headers,
        )
        bad_secret = client.get(
            "/api/v1/audit/events",
            headers={**allowed_headers, "x-rune-trusted-secret": "wrong"},
        )
        missing_user = client.get(
            "/api/v1/audit/events",
            headers={
                "x-rune-trusted-secret": "proxy-secret",
                "x-rune-groups": "rune-operators",
            },
        )

    assert allowed.status_code == 200
    assert project_denied.status_code == 403
    assert bad_secret.status_code == 401
    assert missing_user.status_code == 401

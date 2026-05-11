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
        metrics_forbidden = client.get(
            "/api/v1/metrics/summary",
            headers={"x-rune-api-key": "secret", "x-rune-role": "developer"},
        )
        metrics_allowed = client.get(
            "/api/v1/metrics/summary",
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
    assert metrics_forbidden.status_code == 403
    assert metrics_allowed.status_code == 200


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


def test_api_key_auth_protects_feedback_eval_and_improvement_activation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            auth_mode="api_key",
            api_key="secret",
        )
    )
    viewer_headers = {"x-rune-api-key": "secret", "x-rune-role": "viewer"}
    developer_headers = {"x-rune-api-key": "secret", "x-rune-role": "developer"}
    admin_headers = {"x-rune-api-key": "secret", "x-rune-role": "admin"}
    feedback_payloads = [
        {
            "feedback_id": f"fb_security_eval_{index}",
            "target_type": "edge",
            "target_id": f"edge_security_eval_{index}",
            "action": "rejected",
            "user_id": "reviewer",
            "user_role": "System Architect",
            "reason_code": "wrong_relation",
        }
        for index in range(2)
    ]
    with TestClient(app) as client:
        viewer_feedback = client.post(
            "/api/v1/feedback",
            headers=viewer_headers,
            json=feedback_payloads[0],
        )
        developer_feedback = [
            client.post("/api/v1/feedback", headers=developer_headers, json=payload)
            for payload in feedback_payloads
        ]
        viewer_summary = client.get("/api/v1/feedback/summary", headers=viewer_headers)
        developer_summary = client.get("/api/v1/feedback/summary", headers=developer_headers)
        improvements = client.get("/api/v1/improvements/candidates", headers=developer_headers)
        candidate_id = improvements.json()[0]["candidate_id"]
        developer_activation = client.post(
            f"/api/v1/improvements/{candidate_id}/activate",
            headers=developer_headers,
            json={"reviewer_approved": True, "canary_passed": True},
        )
        admin_activation = client.post(
            f"/api/v1/improvements/{candidate_id}/activate",
            headers=admin_headers,
            json={"reviewer_approved": True, "canary_passed": True},
        )
        developer_rollback = client.post(
            f"/api/v1/improvements/{candidate_id}/rollback",
            headers=developer_headers,
            json={"reason_code": "canary_regression"},
        )
        admin_rollback = client.post(
            f"/api/v1/improvements/{candidate_id}/rollback",
            headers=admin_headers,
            json={"reason_code": "canary_regression"},
        )
        developer_model_activation = client.post(
            "/api/v1/admin/model-profiles/dummy-local/activate",
            headers=developer_headers,
            json={
                "activated_by": "developer@example.com",
                "eval_passed": True,
                "reviewer_approved": True,
                "canary_passed": True,
            },
        )
        admin_model_activation = client.post(
            "/api/v1/admin/model-profiles/dummy-local/activate",
            headers=admin_headers,
            json={
                "activated_by": "admin@example.com",
                "eval_passed": True,
                "reviewer_approved": True,
                "canary_passed": True,
            },
        )

    assert viewer_feedback.status_code == 403
    assert all(response.status_code == 200 for response in developer_feedback)
    assert viewer_summary.status_code == 403
    assert developer_summary.status_code == 200
    assert improvements.status_code == 200
    assert developer_activation.status_code == 403
    assert admin_activation.status_code == 200
    assert developer_rollback.status_code == 403
    assert admin_rollback.status_code == 200
    assert developer_model_activation.status_code == 403
    assert admin_model_activation.status_code == 200


def test_api_key_auth_protects_findings_schedule_and_debug_run_list(tmp_path) -> None:  # type: ignore[no-untyped-def]
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
        "x-rune-user": "operator@example.com",
    }
    viewer_headers = {
        **developer_headers,
        "x-rune-role": "viewer",
    }
    wrong_project_headers = {
        **developer_headers,
        "x-rune-projects": "OTHER_PROJECT",
    }
    wrong_project_operator_headers = {
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
                "run_id": "run_query_auth",
            },
        )
        viewer_analyze = client.post(
            "/api/v1/runs/analyze",
            headers=viewer_headers,
            json={"project_key": "RUNE_CAM_ALPHA", "run_id": "run_viewer_blocked"},
        )
        viewer_ingest = client.post(
            "/api/v1/runs/ingest",
            headers=viewer_headers,
            json={"project_key": "RUNE_CAM_ALPHA", "run_id": "ingest_viewer_blocked"},
        )
        developer_ingest = client.post(
            "/api/v1/runs/ingest",
            headers=developer_headers,
            json={"project_key": "RUNE_CAM_ALPHA", "run_id": "ingest_developer_allowed"},
        )
        missing_findings_key = client.get("/api/v1/findings")
        missing_runs_key = client.get("/api/v1/runs")
        missing_projects_key = client.get("/api/v1/projects")
        viewer_findings = client.get("/api/v1/findings", headers=viewer_headers)
        viewer_runs = client.get("/api/v1/runs", headers=viewer_headers)
        viewer_projects = client.get("/api/v1/projects", headers=viewer_headers)
        wrong_project_projects = client.get("/api/v1/projects", headers=wrong_project_headers)
        wrong_project_runs = client.get("/api/v1/runs", headers=wrong_project_headers)
        viewer_nodes = client.get(
            "/api/v1/graph/nodes?project_key=RUNE_CAM_ALPHA",
            headers=viewer_headers,
        )
        wrong_project_nodes = client.get(
            "/api/v1/graph/nodes?project_key=RUNE_CAM_ALPHA",
            headers=wrong_project_headers,
        )
        viewer_edges = client.get(
            "/api/v1/graph/edges?project_key=RUNE_CAM_ALPHA",
            headers=viewer_headers,
        )
        wrong_project_edges = client.get(
            "/api/v1/graph/edges?project_key=RUNE_CAM_ALPHA",
            headers=wrong_project_headers,
        )
        developer_findings = client.get("/api/v1/findings", headers=developer_headers)
        wrong_project_findings = client.get("/api/v1/findings", headers=wrong_project_headers)
        finding_id = developer_findings.json()[0]["finding_id"]
        viewer_finding_detail = client.get(
            f"/api/v1/findings/{finding_id}",
            headers=viewer_headers,
        )
        developer_finding_detail = client.get(
            f"/api/v1/findings/{finding_id}",
            headers=developer_headers,
        )
        wrong_project_finding_detail = client.get(
            f"/api/v1/findings/{finding_id}",
            headers=wrong_project_headers,
        )
        viewer_finding_status = client.post(
            f"/api/v1/findings/{finding_id}/status",
            headers=viewer_headers,
            json={"status": "acknowledged"},
        )
        wrong_project_finding_status = client.post(
            f"/api/v1/findings/{finding_id}/status",
            headers=wrong_project_operator_headers,
            json={"status": "acknowledged"},
        )
        operator_finding_status = client.post(
            f"/api/v1/findings/{finding_id}/status",
            headers=operator_headers,
            json={"status": "acknowledged", "updated_by": "operator@example.com"},
        )
        missing_schedule_key = client.get("/api/v1/schedule")
        allowed_schedule = client.get("/api/v1/schedule", headers=developer_headers)
        wrong_project_schedule = client.get("/api/v1/schedule", headers=wrong_project_headers)
        viewer_debug_runs = client.get("/api/v1/debug/runs", headers=viewer_headers)
        developer_debug_runs = client.get("/api/v1/debug/runs", headers=developer_headers)
        wrong_project_debug_runs = client.get(
            "/api/v1/debug/runs",
            headers=wrong_project_headers,
        )
        viewer_steps = client.get(
            "/api/v1/runs/run_query_auth/steps",
            headers=viewer_headers,
        )
        developer_steps = client.get(
            "/api/v1/runs/run_query_auth/steps",
            headers=developer_headers,
        )
        viewer_graph_delta = client.get(
            "/api/v1/runs/run_query_auth/graph-delta",
            headers=viewer_headers,
        )
        developer_graph_delta = client.get(
            "/api/v1/runs/run_query_auth/graph-delta",
            headers=developer_headers,
        )
        viewer_replay = client.post(
            "/api/v1/runs/run_query_auth/replay",
            headers=viewer_headers,
            json={"replay_run_id": "replay_viewer_blocked"},
        )
        developer_replay = client.post(
            "/api/v1/runs/run_query_auth/replay",
            headers=developer_headers,
            json={"replay_run_id": "replay_developer_allowed"},
        )
        configured = client.put(
            "/api/v1/schedule",
            headers=operator_headers,
            json={
                "enabled": False,
                "interval_seconds": 5,
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id_prefix": "auth_sched",
            },
        )
        audit_events = client.get(
            "/api/v1/audit/events?project_key=RUNE_CAM_ALPHA",
            headers=operator_headers,
        )

    assert run.status_code == 200
    assert viewer_analyze.status_code == 403
    assert viewer_ingest.status_code == 403
    assert developer_ingest.status_code == 200
    assert missing_findings_key.status_code == 401
    assert missing_runs_key.status_code == 401
    assert missing_projects_key.status_code == 401
    assert viewer_findings.status_code == 403
    assert viewer_runs.status_code == 200
    assert any(run["run_id"] == "run_query_auth" for run in viewer_runs.json())
    assert viewer_projects.status_code == 200
    assert viewer_projects.json()[0]["project_key"] == "RUNE_CAM_ALPHA"
    assert wrong_project_projects.status_code == 200
    assert wrong_project_projects.json() == []
    assert wrong_project_runs.status_code == 200
    assert wrong_project_runs.json() == []
    assert viewer_nodes.status_code == 200
    assert viewer_edges.status_code == 200
    assert wrong_project_nodes.status_code == 403
    assert wrong_project_edges.status_code == 403
    assert developer_findings.status_code == 200
    assert wrong_project_findings.status_code == 200
    assert wrong_project_findings.json() == []
    assert viewer_finding_detail.status_code == 403
    assert developer_finding_detail.status_code == 200
    assert wrong_project_finding_detail.status_code == 403
    assert viewer_finding_status.status_code == 403
    assert wrong_project_finding_status.status_code == 403
    assert operator_finding_status.status_code == 200
    assert missing_schedule_key.status_code == 401
    assert allowed_schedule.status_code == 200
    assert wrong_project_schedule.status_code == 403
    assert viewer_debug_runs.status_code == 403
    assert developer_debug_runs.status_code == 200
    assert len(developer_debug_runs.json()) == 2
    assert wrong_project_debug_runs.status_code == 200
    assert wrong_project_debug_runs.json() == []
    assert viewer_steps.status_code == 403
    assert developer_steps.status_code == 200
    assert viewer_graph_delta.status_code == 403
    assert developer_graph_delta.status_code == 200
    assert viewer_replay.status_code == 403
    assert developer_replay.status_code == 200
    assert configured.status_code == 200
    assert any(
        event["action"] == "schedule_configured"
        and event["actor_id"] == "operator@example.com"
        for event in audit_events.json()
    )


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

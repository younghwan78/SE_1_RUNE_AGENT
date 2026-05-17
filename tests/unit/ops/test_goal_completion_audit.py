"""Goal completion audit tests."""

from runpy import run_path


def test_goal_completion_audit_separates_local_artifacts_from_readiness() -> None:
    namespace = run_path("ops/rehearsal/check_goal_completion.py")

    report = namespace["build_goal_completion_audit"]({})

    assert report["schema_version"] == "v1"
    assert report["objective"] == (
        "현재 구현된 상태를 상세하게 파악하고 "
        "PRODUCTION_EXECUTION_PLAN.md에 계획한대로 목표한 구현 및 검증을 완료"
    )
    assert report["goal_complete"] is False
    assert report["release_scope"]["passed"] is True
    assert report["release_scope"]["release_ready"] is False
    assert report["production_readiness"]["passed"] is False
    assert report["summary"]["remaining_blocker_count"] > 0
    blocker_ids = {blocker["blocker_id"] for blocker in report["remaining_blockers"]}
    assert "production_readiness:postgres_state_store" in blocker_ids
    assert "release_scope:model_gateway_prompt_registry" in blocker_ids
    assert report["blocker_summary"]["local_action_required"] > 0


def test_goal_completion_audit_lists_concrete_success_criteria() -> None:
    namespace = run_path("ops/rehearsal/check_goal_completion.py")

    report = namespace["build_goal_completion_audit"]({})

    criteria_ids = {criterion["criterion_id"] for criterion in report["success_criteria"]}
    assert criteria_ids == {
        "production_plan_source_of_truth",
        "first_release_scope_artifacts",
        "completion_audit_coverage",
        "local_regression_gates",
        "company_staging_readiness",
        "ci_release_gates",
    }
    checklist_ids = {
        item["criterion_id"] for item in report["prompt_to_artifact_checklist"]
    }
    assert checklist_ids == criteria_ids
    assert report["summary"]["prompt_to_artifact_checklist_count"] == len(criteria_ids)


def test_goal_completion_audit_maps_prompt_requirements_to_artifacts() -> None:
    namespace = run_path("ops/rehearsal/check_goal_completion.py")

    report = namespace["build_goal_completion_audit"]({})
    checklist = {
        item["criterion_id"]: item for item in report["prompt_to_artifact_checklist"]
    }

    scope_item = checklist["first_release_scope_artifacts"]
    assert len(scope_item["scope_items"]) == report["release_scope"]["summary"]["item_count"]
    assert scope_item["first_release_exclusions"] == report["release_scope"][
        "first_release_exclusions"
    ]
    assert "AI의 원본 시스템 write-back" in scope_item["first_release_exclusions"]
    assert "src/req_tracker/adapters/jira_rest.py" in scope_item["artifacts"]
    assert any(
        command.startswith("uv run pytest tests/unit/adapters/test_jira_rest_adapter.py")
        for command in scope_item["commands"]
    )

    company_item = checklist["company_staging_readiness"]
    assert company_item["status"] == "blocked"
    assert ".env.example" in company_item["artifacts"]
    assert "ops/rehearsal/check_goal_completion.py" in company_item["artifacts"]
    assert "ops/rehearsal/build_handoff_bundle.py" in company_item["artifacts"]
    assert "ops/rehearsal/final_validation_commands.py" in company_item["artifacts"]
    assert "ops/rehearsal/validate_handoff_bundle.py" in company_item["artifacts"]
    assert any(
        check["check_id"] == "company_jira_sandbox_rehearsal"
        for check in company_item["checks"]
    )
    assert "production_readiness:postgres_state_store" in company_item["gaps"]
    assert (
        "uv run python ops/rehearsal/check_production_readiness.py "
        "--run-local-gates --env-file <staging.env> "
        "--evidence-file <reviewed-evidence.json>"
        in company_item["commands"]
    )
    assert (
        "uv run python ops/rehearsal/check_goal_completion.py "
        "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
        "--run-local-gates"
        in company_item["commands"]
    )
    assert (
        "uv run python ops/rehearsal/build_handoff_bundle.py "
        "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
        "--run-local-gates --output-dir <handoff-bundle-dir>"
        in company_item["commands"]
    )
    assert (
        "uv run python ops/rehearsal/validate_handoff_bundle.py <handoff-bundle-dir>"
        in company_item["commands"]
    )


def test_goal_completion_audit_applies_manual_evidence() -> None:
    namespace = run_path("ops/rehearsal/check_goal_completion.py")
    evidence = [
        namespace["READINESS_MODULE"].ManualEvidence(
            check_id="company_postgres_rehearsal",
            status="passed",
            summary="Staging PostgreSQL rehearsal passed.",
            evidence=["staging-ci:postgres:run-1"],
        )
    ]

    report = namespace["build_goal_completion_audit"](
        {
            "STATE_STORE": "postgres",
            "POSTGRES_DSN": "postgresql://rune:secret@db/rune_agent",
            "GRAPH_BACKEND": "neo4j",
            "NEO4J_URI": "bolt://neo4j:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "secret",
            "VECTOR_BACKEND": "qdrant",
            "QDRANT_URL": "http://qdrant:6333",
            "QDRANT_COLLECTION": "rune_chunks",
            "MODEL_GATEWAY_MODE": "http_json",
            "MODEL_GATEWAY_ENDPOINT_URL": "https://models.example.test/v1/complete",
            "AUTH_MODE": "trusted_proxy",
            "TRUSTED_PROXY_SECRET": "secret",
            "TRUSTED_GROUP_ROLE_MAP": '{"rune-admins":"admin"}',
            "ARTIFACT_ROOT": "/var/lib/rune-agent/artifacts",
            "OTEL_ENABLED": "true",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel-collector:4317",
        },
        manual_evidence=evidence,
    )

    blocker_ids = {blocker["blocker_id"] for blocker in report["remaining_blockers"]}
    assert "production_readiness:company_postgres_rehearsal" not in blocker_ids
    assert "production_readiness:company_neo4j_rehearsal" in blocker_ids
    assert report["production_readiness"]["manual_evidence_count"] == 1


def test_goal_completion_audit_classifies_local_gate_as_local_action() -> None:
    namespace = run_path("ops/rehearsal/check_goal_completion.py")

    report = namespace["build_goal_completion_audit"](
        _staging_template_env(),
        manual_evidence=[],
        run_local_gates=False,
    )

    assert report["summary"]["remaining_blocker_count"] == 21
    assert report["blocker_summary"] == {
        "company_or_staging_evidence_required": 20,
        "local_action_required": 1,
        "by_status": {
            "company_evidence_required": 4,
            "failed": 6,
            "manual_required": 11,
        },
        "local_action_blockers": ["production_readiness:local_regression_gates"],
    }


def test_goal_completion_audit_can_complete_with_reviewed_company_evidence() -> None:
    namespace = run_path("ops/rehearsal/check_goal_completion.py")

    report = namespace["build_goal_completion_audit"](
        _complete_production_env(),
        manual_evidence=[
            namespace["READINESS_MODULE"].ManualEvidence(
                check_id=check_id,
                status="passed",
                summary=f"{check_id} reviewed and passed.",
                evidence=[f"artifact:{check_id}.json"],
            )
            for check_id in _manual_gate_ids()
        ],
    )

    assert report["goal_complete"] is True
    assert report["summary"]["release_scope_passed"] is True
    assert report["summary"]["release_scope_ready"] is False
    assert report["summary"]["release_scope_goal_ready"] is True
    assert report["release_scope"]["goal_ready"] is True
    assert report["production_readiness"]["passed"] is True
    assert report["remaining_blockers"] == []
    assert report["blocker_summary"] == {
        "company_or_staging_evidence_required": 0,
        "local_action_required": 0,
        "by_status": {},
        "local_action_blockers": [],
    }


def _staging_template_env() -> dict[str, str]:
    return {
        "REQ_TRACKER_ENV": "staging",
        "DATASOURCE_MODE": "jira",
        "STATE_STORE": "postgres",
        "GRAPH_BACKEND": "neo4j",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_DATABASE": "neo4j",
        "VECTOR_BACKEND": "qdrant",
        "QDRANT_COLLECTION": "rune_chunks",
        "QDRANT_VECTOR_SIZE": "64",
        "MODEL_GATEWAY_MODE": "http_json",
        "MODEL_GATEWAY_PROVIDER": "internal",
        "MODEL_GATEWAY_PROFILE_ID": "company-sandbox",
        "MODEL_GATEWAY_MODEL_NAME": "company-sandbox-model",
        "MODEL_GATEWAY_PROMPT_VERSION_ID": "pv_company_probe",
        "AUTH_MODE": "trusted_proxy",
        "TRUSTED_GROUP_ROLE_MAP": '{"rune-admins":"admin"}',
        "ARTIFACT_ROOT": "/var/lib/rune-agent/artifacts",
        "OTEL_ENABLED": "true",
        "DEPLOYMENT_TARGET": "ubuntu",
        "KUBERNETES_DEPLOYMENT": "false",
    }


def _complete_production_env() -> dict[str, str]:
    return {
        "STATE_STORE": "postgres",
        "POSTGRES_DSN": "postgresql://rune:secret-value@db/rune_agent",
        "POSTGRES_TEST_DSN": "postgresql://rune:secret-value@db/rune_agent_test",
        "GRAPH_BACKEND": "neo4j",
        "NEO4J_URI": "bolt://neo4j:7687",
        "NEO4J_TEST_URI": "bolt://neo4j:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "secret-value",
        "VECTOR_BACKEND": "qdrant",
        "QDRANT_URL": "http://qdrant:6333",
        "QDRANT_TEST_URL": "http://qdrant:6333",
        "QDRANT_COLLECTION": "rune_chunks",
        "MODEL_GATEWAY_MODE": "http_json",
        "MODEL_GATEWAY_ENDPOINT_URL": "https://models.example.test/v1/complete",
        "AUTH_MODE": "trusted_proxy",
        "TRUSTED_PROXY_SECRET": "secret-value",
        "TRUSTED_GROUP_ROLE_MAP": '{"rune-admins":"admin"}',
        "OTEL_ENABLED": "true",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel-collector:4317",
        "PROMETHEUS_BASE_URL": "https://prometheus.example.test",
        "GRAFANA_DASHBOARD_UID": "rune-agent-ops",
        "RUNE_API_BASE_URL": "https://rune-agent.example.test",
        "ARTIFACT_ROOT": "/var/lib/rune-agent/artifacts",
        "JIRA_BASE_URL": "https://jira.example.test",
        "CONFLUENCE_BASE_URL": "https://confluence.example.test",
        "RUNE_EMAIL_EXPORT_PATH": "/secure/exports/decision_email.jsonl",
        "BACKUP_ROOT": "/var/backups/rune-agent/20260512T000000Z",
    }


def _manual_gate_ids() -> tuple[str, ...]:
    return (
        "company_postgres_rehearsal",
        "company_neo4j_rehearsal",
        "company_qdrant_rehearsal",
        "company_model_gateway_rehearsal",
        "company_jira_sandbox_rehearsal",
        "company_confluence_sandbox_rehearsal",
        "company_email_policy_rehearsal",
        "backup_restore_load_rehearsal",
        "observability_dashboard_rehearsal",
        "trusted_proxy_rbac_rehearsal",
        "local_regression_gates",
    )

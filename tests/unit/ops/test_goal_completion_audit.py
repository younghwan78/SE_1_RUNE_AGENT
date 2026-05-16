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

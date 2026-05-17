"""Production-readiness checker tests."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def test_readiness_report_flags_unverified_company_gates() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report(
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
        }
    )

    assert report["passed"] is False
    assert report["summary"]["failed"] == 0
    assert report["summary"]["manual_required"] > 0
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["postgres_state_store"]["status"] == "passed"
    assert checks["opentelemetry_export"]["status"] == "passed"
    assert checks["company_postgres_rehearsal"]["status"] == "manual_required"
    assert checks["observability_dashboard_rehearsal"]["status"] == "manual_required"
    assert checks["kubernetes_helm_rehearsal"]["status"] == "passed"
    assert "secret" not in str(report)


def test_local_gate_commands_include_staging_evidence_plan_smoke() -> None:
    checker = _load_checker_module()

    commands = {" ".join(command) for command in checker.LOCAL_GATE_COMMANDS}

    assert (
        "uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown"
        in commands
    )
    assert "uv run python ops/rehearsal/validate_release_scope_artifacts.py" in commands
    assert (
        "uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete"
        in commands
    )
    assert (
        "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
        "--env-file .env.example --output-dir .local_artifacts/handoff-bundle"
        in commands
    )
    assert (
        "uv run python ops/rehearsal/validate_handoff_bundle.py "
        ".local_artifacts/handoff-bundle"
        in commands
    )
    assert (
        "uv run python ops/rehearsal/build_staging_evidence_plan.py "
        "--env-file ops/rehearsal/staging.env.example --format markdown"
        in commands
    )
    assert (
        "uv run python ops/rehearsal/check_goal_completion.py "
        "--allow-incomplete --env-file ops/rehearsal/staging.env.example"
        in commands
    )
    assert (
        "uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete "
        "--env-file ops/rehearsal/staging.env.example "
        "--output-dir .local_artifacts/staging-handoff-bundle"
        in commands
    )
    assert (
        "uv run python ops/rehearsal/validate_handoff_bundle.py "
        ".local_artifacts/staging-handoff-bundle"
        in commands
    )


def test_readiness_report_requires_helm_evidence_for_kubernetes_target() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report(
        {
            "DEPLOYMENT_TARGET": "kubernetes",
        }
    )

    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["kubernetes_helm_rehearsal"]["status"] == "manual_required"

    resolved = checker.build_readiness_report(
        {
            "DEPLOYMENT_TARGET": "kubernetes",
        },
        manual_evidence=[
            checker.ManualEvidence(
                check_id="kubernetes_helm_rehearsal",
                status="passed",
                summary="Helm lint/template passed.",
                evidence=["staging-ci:helm:run-1"],
            )
        ],
    )

    resolved_checks = {check["check_id"]: check for check in resolved["checks"]}
    assert resolved_checks["kubernetes_helm_rehearsal"]["status"] == "passed"


def test_readiness_report_fails_missing_production_env() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report({})

    assert report["passed"] is False
    assert report["summary"]["failed"] >= 6
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["postgres_state_store"]["status"] == "failed"
    assert "POSTGRES_DSN=<unset>" in checks["postgres_state_store"]["evidence"]


def test_manual_evidence_resolves_only_manual_gates() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report(
        {
            "STATE_STORE": "postgres",
            "POSTGRES_DSN": "postgresql://rune:secret@db/rune_agent",
        },
        manual_evidence=[
            checker.ManualEvidence(
                check_id="company_postgres_rehearsal",
                status="passed",
                summary="Staging PostgreSQL rehearsal passed.",
                evidence=["staging-ci:postgres:run-1"],
            ),
            checker.ManualEvidence(
                check_id="postgres_state_store",
                status="failed",
                summary="This should not override a live env check.",
                evidence=["ignored"],
            ),
            checker.ManualEvidence(
                check_id="unknown_gate",
                status="passed",
                summary="Unknown gate.",
                evidence=["unknown"],
            ),
        ],
    )

    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["company_postgres_rehearsal"]["status"] == "passed"
    assert "staging-ci:postgres:run-1" in checks["company_postgres_rehearsal"]["evidence"]
    assert checks["postgres_state_store"]["status"] == "passed"
    assert "manual_evidence_ignored:not_manual_gate" in checks["postgres_state_store"]["evidence"]
    assert checks["unknown_manual_evidence:unknown_gate"]["status"] == "warning"
    assert report["manual_evidence_count"] == 3


def test_load_manual_evidence_from_json(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "release-owner@example.com",
          "reviewed_at": "2026-05-12T00:00:00Z",
          "checks": [
            {
              "check_id": "local_regression_gates",
              "status": "passed",
              "summary": "CI passed.",
              "evidence": ["github-actions:CI:run-1"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    evidence = checker.load_manual_evidence(evidence_path)

    assert len(evidence) == 1
    assert evidence[0].check_id == "local_regression_gates"
    assert evidence[0].status == "passed"


def test_load_env_file_merges_staging_values_without_printing_secrets(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    env_path = tmp_path / "staging.env"
    env_path.write_text(
        "\n".join(
            [
                "# company staging values",
                "STATE_STORE=postgres",
                "POSTGRES_DSN='postgresql://rune:secret@db/rune_agent'",
                'MODEL_GATEWAY_ENDPOINT_URL="https://models.example.test/v1/complete"',
                "export OTEL_ENABLED=true",
                "UNCHANGED=from-file",
            ]
        ),
        encoding="utf-8",
    )

    env = checker.load_env_file(env_path, {"UNCHANGED": "from-base", "BASE_ONLY": "1"})
    report = checker.build_readiness_report(env)

    checks = {check["check_id"]: check for check in report["checks"]}
    assert env["POSTGRES_DSN"] == "postgresql://rune:secret@db/rune_agent"
    assert env["MODEL_GATEWAY_ENDPOINT_URL"] == "https://models.example.test/v1/complete"
    assert env["OTEL_ENABLED"] == "true"
    assert env["UNCHANGED"] == "from-file"
    assert env["BASE_ONLY"] == "1"
    assert checks["postgres_state_store"]["status"] == "passed"
    assert "secret" not in str(report)


def test_load_env_file_rejects_invalid_lines(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    env_path = tmp_path / "staging.env"
    env_path.write_text("NOT_A_KEY_VALUE_LINE\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be KEY=VALUE"):
        checker.load_env_file(env_path)


def test_write_json_output_writes_report_artifact(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    output_path = tmp_path / "readiness-report.json"

    checker.write_json_output(
        {"schema_version": "v1", "passed": False, "summary": {"failed": 1}},
        output_path,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "schema_version": "v1",
        "passed": False,
        "summary": {"failed": 1},
    }


def test_load_manual_evidence_rejects_passed_without_review_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "Reviewed staging run passed.",
              "evidence": ["staging-ci:postgres:run-1"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reviewed_by"):
        checker.load_manual_evidence(evidence_path)


def test_load_manual_evidence_rejects_passed_without_schema_version(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "reviewed_by": "release-owner@example.com",
          "reviewed_at": "2026-05-12T00:00:00Z",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "Reviewed staging run passed.",
              "evidence": ["staging-ci:postgres:run-1"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema_version must be v1"):
        checker.load_manual_evidence(evidence_path)


def test_load_manual_evidence_rejects_passed_empty_evidence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "release-owner@example.com",
          "reviewed_at": "2026-05-12T00:00:00Z",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "Reviewed staging run passed.",
              "evidence": []
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must include non-empty evidence"):
        checker.load_manual_evidence(evidence_path)


def test_load_manual_evidence_rejects_duplicate_check_ids(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "release-owner@example.com",
          "reviewed_at": "2026-05-12T00:00:00Z",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "First staging run passed.",
              "evidence": ["staging-ci:postgres:run-1"]
            },
            {
              "check_id": "company_postgres_rehearsal",
              "status": "failed",
              "summary": "Duplicate entry should be rejected.",
              "evidence": ["staging-ci:postgres:run-2"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicates company_postgres_rehearsal"):
        checker.load_manual_evidence(evidence_path)


def test_load_manual_evidence_rejects_passed_todo_review_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "TODO: release owner email",
          "reviewed_at": "2026-05-12T00:00:00Z",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "Reviewed staging run passed.",
              "evidence": ["staging-ci:postgres:run-1"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reviewed_by cannot contain TODO"):
        checker.load_manual_evidence(evidence_path)


def test_load_manual_evidence_rejects_non_utc_review_timestamp(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "release-owner@example.com",
          "reviewed_at": "2026-05-12 09:00:00",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "Reviewed staging run passed.",
              "evidence": ["staging-ci:postgres:run-1"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reviewed_at must be an ISO-8601 UTC timestamp"):
        checker.load_manual_evidence(evidence_path)


def test_load_manual_evidence_allows_failed_template_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "reviewed_by": "TODO: release owner email",
          "reviewed_at": "TODO: ISO-8601 UTC timestamp",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "failed",
              "summary": "TODO: replace after staging run.",
              "evidence": ["TODO: attach reviewed CI run id"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    evidence = checker.load_manual_evidence(evidence_path)

    assert len(evidence) == 1
    assert evidence[0].status == "failed"


def test_load_manual_evidence_rejects_passed_todo_placeholder(tmp_path) -> None:  # type: ignore[no-untyped-def]
    checker = _load_checker_module()
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        """
        {
          "schema_version": "v1",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "TODO: replace after staging run.",
              "evidence": ["TODO: attach reviewed CI run id"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot be passed"):
        checker.load_manual_evidence(evidence_path)


def test_manual_evidence_template_only_contains_unresolved_manual_gates() -> None:
    checker = _load_checker_module()

    template = checker.build_manual_evidence_template({})

    check_ids = {check["check_id"] for check in template["checks"]}
    assert "postgres_state_store" not in check_ids
    assert "company_postgres_rehearsal" in check_ids
    assert "local_regression_gates" in check_ids
    assert "kubernetes_helm_rehearsal" not in check_ids
    assert {check["status"] for check in template["checks"]} == {"failed"}
    assert "TODO:" in str(template)
    assert "secret" not in str(template)


def test_manual_evidence_template_includes_helm_gate_when_kubernetes_selected() -> None:
    checker = _load_checker_module()

    template = checker.build_manual_evidence_template({"DEPLOYMENT_TARGET": "kubernetes"})

    check_ids = {check["check_id"] for check in template["checks"]}
    assert "kubernetes_helm_rehearsal" in check_ids


def test_example_evidence_file_is_not_passable_without_real_review() -> None:
    checker = _load_checker_module()
    evidence = checker.load_manual_evidence(
        Path("ops/rehearsal/production_readiness_evidence.example.json")
    )

    assert evidence
    assert {record.status for record in evidence} == {"failed"}
    report = checker.build_readiness_report(
        _complete_production_env(),
        manual_evidence=evidence,
    )
    assert report["passed"] is False
    assert report["summary"]["failed"] > 0


def test_readiness_report_passes_with_complete_env_and_reviewed_evidence() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report(
        _complete_production_env(),
        manual_evidence=[
            checker.ManualEvidence(
                check_id=check_id,
                status="passed",
                summary=f"{check_id} passed.",
                evidence=[f"artifact:{check_id}.json"],
            )
            for check_id in _manual_gate_ids()
        ],
    )

    assert report["passed"] is True
    assert report["summary"] == {
        "passed": 19,
        "warning": 0,
        "failed": 0,
        "manual_required": 0,
    }
    assert report["manual_evidence_count"] == len(_manual_gate_ids())
    assert "secret-value" not in str(report)


def test_readiness_report_blocks_unknown_manual_evidence_warning() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report(
        _complete_production_env(),
        manual_evidence=[
            *[
                checker.ManualEvidence(
                    check_id=check_id,
                    status="passed",
                    summary=f"{check_id} passed.",
                    evidence=[f"artifact:{check_id}.json"],
                )
                for check_id in _manual_gate_ids()
            ],
            checker.ManualEvidence(
                check_id="unknown_gate",
                status="passed",
                summary="Unknown gate passed.",
                evidence=["artifact:unknown.json"],
            ),
        ],
    )

    assert report["passed"] is False
    assert report["summary"]["warning"] == 1
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["unknown_manual_evidence:unknown_gate"]["status"] == "warning"


def test_local_gate_summary_treats_docker_unavailable_as_manual_required() -> None:
    checker = _load_checker_module()

    check = checker._local_gate_summary(  # noqa: SLF001
        [
            {
                "command": "uv run ruff check .",
                "returncode": 0,
                "output_tail": "All checks passed!",
            },
            {
                "command": "uv run python ops/integration/run_backend_integration.py",
                "returncode": 1,
                "output_tail": (
                    "failed to connect to the docker API at "
                    "npipe:////./pipe/dockerDesktopLinuxEngine"
                ),
            },
            {
                "command": "uv run python ops/rehearsal/run_full_stack_rehearsal.py",
                "returncode": 1,
                "output_tail": (
                    "Cannot connect to the Docker daemon at "
                    "unix:///var/run/docker.sock"
                ),
            },
        ]
    )

    assert check.status == "manual_required"
    assert "Docker-backed" in check.summary
    assert check.next_action is not None
    assert "Docker" in check.next_action


def test_local_gate_summary_keeps_non_docker_failures_failed() -> None:
    checker = _load_checker_module()

    check = checker._local_gate_summary(  # noqa: SLF001
        [
            {
                "command": "uv run pytest",
                "returncode": 1,
                "output_tail": "FAILED tests/contract/test_models.py",
            },
            {
                "command": "uv run python ops/integration/run_backend_integration.py",
                "returncode": 1,
                "output_tail": "failed to connect to the docker API",
            },
        ]
    )

    assert check.status == "failed"
    assert check.next_action == "Fix failed local gates before release."


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


def _load_checker_module() -> ModuleType:
    module_path = Path("ops/rehearsal/check_production_readiness.py")
    spec = importlib.util.spec_from_file_location("check_production_readiness", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

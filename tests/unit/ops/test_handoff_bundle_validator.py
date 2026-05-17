"""Handoff bundle validator tests."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def test_handoff_bundle_validator_accepts_generated_bundle(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is True
    assert report["summary"]["failed"] == 0
    assert report["artifact_count"] == 4


def test_handoff_bundle_validator_rejects_missing_artifact(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    (bundle_dir / "goal-completion-report.json").unlink()

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "missing_artifact:goal-completion-report.json" in report["failures"]


def test_handoff_bundle_validator_rejects_manifest_summary_drift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["readiness_summary"] = {"failed": 0, "manual_required": 0, "passed": 99}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "readiness_summary_mismatch" in report["failures"]


def test_handoff_bundle_validator_rejects_manifest_blocker_drift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["remaining_blocker_count"] = 0
    manifest["remaining_blockers"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "remaining_blocker_count_mismatch" in report["failures"]
    assert "remaining_blockers_mismatch" in report["failures"]


def test_handoff_bundle_validator_rejects_missing_manual_template_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    template_path = bundle_dir / "manual-evidence-template.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template["checks"] = [
        check
        for check in template["checks"]
        if check["check_id"] != "company_jira_sandbox_rehearsal"
    ]
    template_path.write_text(json.dumps(template), encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert (
        "manual_template_missing_gate:company_jira_sandbox_rehearsal"
        in report["failures"]
    )


def test_handoff_bundle_validator_rejects_missing_final_validation_section(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    plan_path = bundle_dir / "staging-evidence-plan.md"
    content = plan_path.read_text(encoding="utf-8")
    stale_content = (
        content.split("## Final Validation", maxsplit=1)[0] + "## postgres_state_store\n"
    )
    plan_path.write_text(stale_content, encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "staging_evidence_plan_final_validation_missing" in report["failures"]


def test_handoff_bundle_validator_accepts_complete_reviewed_evidence_bundle(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    env_path = tmp_path / "staging.env"
    env_path.write_text("\n".join(_complete_production_env_lines()), encoding="utf-8")
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(_complete_manual_evidence()), encoding="utf-8")
    bundle_dir = tmp_path / "bundle"

    manifest = builder.build_handoff_bundle(
        bundle_dir,
        env_file=env_path,
        evidence_file=evidence_path,
        run_local_gates=False,
    )
    report = validator.validate_handoff_bundle(bundle_dir)
    manual_template = json.loads(
        (bundle_dir / "manual-evidence-template.json").read_text(encoding="utf-8")
    )

    assert manifest["goal_complete"] is True
    assert manifest["remaining_blocker_count"] == 0
    assert manual_template["checks"] == []
    assert report["passed"] is True


def _complete_production_env_lines() -> list[str]:
    return [
        "STATE_STORE=postgres",
        "POSTGRES_DSN=postgresql://rune:secret-value@db/rune_agent",
        "POSTGRES_TEST_DSN=postgresql://rune:secret-value@db/rune_agent_test",
        "GRAPH_BACKEND=neo4j",
        "NEO4J_URI=bolt://neo4j:7687",
        "NEO4J_TEST_URI=bolt://neo4j:7687",
        "NEO4J_USERNAME=neo4j",
        "NEO4J_PASSWORD=secret-value",
        "VECTOR_BACKEND=qdrant",
        "QDRANT_URL=http://qdrant:6333",
        "QDRANT_TEST_URL=http://qdrant:6333",
        "QDRANT_COLLECTION=rune_chunks",
        "MODEL_GATEWAY_MODE=http_json",
        "MODEL_GATEWAY_ENDPOINT_URL=https://models.example.test/v1/complete",
        "AUTH_MODE=trusted_proxy",
        "TRUSTED_PROXY_SECRET=secret-value",
        'TRUSTED_GROUP_ROLE_MAP={"rune-admins":"admin"}',
        "OTEL_ENABLED=true",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
        "PROMETHEUS_BASE_URL=https://prometheus.example.test",
        "GRAFANA_DASHBOARD_UID=rune-agent-ops",
        "RUNE_API_BASE_URL=https://rune-agent.example.test",
        "ARTIFACT_ROOT=/var/lib/rune-agent/artifacts",
        "JIRA_BASE_URL=https://jira.example.test",
        "CONFLUENCE_BASE_URL=https://confluence.example.test",
        "RUNE_EMAIL_EXPORT_PATH=/secure/exports/decision_email.jsonl",
        "BACKUP_ROOT=/var/backups/rune-agent/20260512T000000Z",
    ]


def _complete_manual_evidence() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "reviewed_by": "release-owner@example.com",
        "reviewed_at": "2026-05-12T00:00:00Z",
        "checks": [
            {
                "check_id": check_id,
                "status": "passed",
                "summary": f"{check_id} reviewed and passed.",
                "evidence": [f"artifact:{check_id}.json"],
            }
            for check_id in (
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
        ],
    }


def _load_module(module_name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

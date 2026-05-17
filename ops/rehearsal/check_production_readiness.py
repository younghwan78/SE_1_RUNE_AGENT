"""Check local and company/staging production-readiness gates.

This checker does not prove that company systems are ready by inspecting
environment variables alone. It separates concrete local gates from
company/staging gates that still require a real endpoint rehearsal.
"""

import argparse
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]

CheckStatus = Literal["passed", "warning", "failed", "manual_required"]


@dataclass(frozen=True)
class ReadinessCheck:
    """One production-readiness check item."""

    check_id: str
    status: CheckStatus
    summary: str
    evidence: list[str]
    next_action: str | None = None


@dataclass(frozen=True)
class ManualEvidence:
    """Reviewed evidence for one manual production gate."""

    check_id: str
    status: Literal["passed", "warning", "failed"]
    summary: str
    evidence: list[str]


LOCAL_GATE_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "mypy", "src"),
    ("uv", "run", "pytest"),
    ("uv", "run", "python", "ops/security/rehearse_masking_policy.py"),
    ("uv", "run", "python", "ops/security/check_release_blockers.py"),
    ("uv", "run", "python", "ops/source/validate_source_boundaries.py"),
    ("uv", "run", "python", "ops/integration/run_backend_integration.py"),
    ("uv", "run", "python", "ops/source/smoke_source_adapters.py"),
    ("uv", "run", "python", "ops/source/rehearse_skill_export_sources.py"),
    ("uv", "run", "python", "ops/model_gateway/smoke_model_gateway.py"),
    ("uv", "run", "python", "ops/helm/validate_chart.py"),
    ("uv", "run", "python", "ops/observability/validate_observability_assets.py"),
    ("uv", "run", "python", "ops/rehearsal/validate_postgres_migration_rollbacks.py"),
    ("uv", "run", "python", "ops/rehearsal/validate_postgres_typed_mirrors.py"),
    ("uv", "run", "python", "ops/rehearsal/validate_evidence_example.py"),
    ("uv", "run", "python", "ops/rehearsal/build_staging_evidence_plan.py", "--format", "markdown"),
    ("uv", "run", "python", "ops/rehearsal/validate_release_scope_artifacts.py"),
    ("uv", "run", "python", "ops/rehearsal/check_goal_completion.py", "--allow-incomplete"),
    (
        "uv",
        "run",
        "python",
        "ops/rehearsal/build_handoff_bundle.py",
        "--allow-incomplete",
        "--env-file",
        ".env.example",
        "--output-dir",
        ".local_artifacts/handoff-bundle",
    ),
    ("uv", "run", "python", "ops/rehearsal/validate_ci_gate_coverage.py"),
    ("uv", "run", "python", "ops/ui/smoke_operator_ui.py"),
    ("uv", "run", "python", "ops/rehearsal/run_full_stack_rehearsal.py"),
    ("uv", "run", "python", "ops/evals/run_feedback_eval_rehearsal.py"),
)


def build_readiness_report(
    env: Mapping[str, str],
    *,
    run_local_gates: bool = False,
    command_timeout_seconds: int = 300,
    manual_evidence: Sequence[ManualEvidence] = (),
) -> dict[str, Any]:
    """Build a structured production-readiness report."""
    checks = [
        *_environment_checks(env),
        *_company_rehearsal_checks(env),
    ]
    local_gate_results: list[dict[str, Any]] = []
    if run_local_gates:
        local_gate_results = [
            _run_command(command, timeout_seconds=command_timeout_seconds)
            for command in LOCAL_GATE_COMMANDS
        ]
        checks.append(_local_gate_summary(local_gate_results))
    else:
        checks.append(
            ReadinessCheck(
                check_id="local_regression_gates",
                status="manual_required",
                summary="Local regression and rehearsal gates were not executed by this check.",
                evidence=["Use --run-local-gates to execute the local gate command list."],
                next_action="Run the checker with --run-local-gates before a release decision.",
            )
        )
    checks = _apply_manual_evidence(checks, manual_evidence)
    summary = _summarize_checks(checks)
    return {
        "passed": (
            summary["failed"] == 0
            and summary["manual_required"] == 0
            and summary["warning"] == 0
        ),
        "summary": summary,
        "checks": [asdict(check) for check in checks],
        "local_gate_commands": [" ".join(command) for command in LOCAL_GATE_COMMANDS],
        "local_gate_results": local_gate_results,
        "manual_evidence_count": len(manual_evidence),
        "schema_version": "v1",
    }


def load_manual_evidence(path: Path) -> list[ManualEvidence]:
    """Load reviewed manual-gate evidence from a JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manual evidence file must contain a JSON object")
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("manual evidence file must contain a checks array")
    records: list[ManualEvidence] = []
    seen_check_ids: set[str] = set()
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            raise ValueError(f"checks[{index}] must be an object")
        check_id = item.get("check_id")
        status = item.get("status")
        summary = item.get("summary")
        evidence = item.get("evidence")
        if not isinstance(check_id, str) or not check_id:
            raise ValueError(f"checks[{index}].check_id must be a non-empty string")
        if check_id in seen_check_ids:
            raise ValueError(f"checks[{index}].check_id duplicates {check_id}")
        seen_check_ids.add(check_id)
        if status not in {"passed", "warning", "failed"}:
            raise ValueError(f"checks[{index}].status must be passed, warning, or failed")
        if not isinstance(summary, str) or not summary:
            raise ValueError(f"checks[{index}].summary must be a non-empty string")
        if not isinstance(evidence, list) or not all(isinstance(entry, str) for entry in evidence):
            raise ValueError(f"checks[{index}].evidence must be a string array")
        if status == "passed" and _contains_todo_placeholder([summary, *evidence]):
            raise ValueError(
                f"checks[{index}] cannot be passed while summary or evidence contains TODO"
            )
        records.append(
            ManualEvidence(
                check_id=check_id,
                status=status,
                summary=summary,
                evidence=evidence,
            )
        )
    _validate_review_metadata(payload, records)
    return records


def load_env_file(path: Path, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Load KEY=VALUE lines from an env file without printing secret values."""
    merged = dict(base_env or {})
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped.removeprefix("export ").strip()
        if "=" not in stripped:
            raise ValueError(f"{path}:{line_number} must be KEY=VALUE")
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or any(character.isspace() for character in key):
            raise ValueError(f"{path}:{line_number} has an invalid env key")
        merged[key] = _strip_env_quotes(value.strip())
    return merged


def write_json_output(payload: Mapping[str, Any], output_path: Path) -> None:
    """Write a JSON payload to stdout or an artifact path."""
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if str(output_path) == "-":
        print(rendered)
        return
    output_path.write_text(rendered + "\n", encoding="utf-8")


def _strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _validate_review_metadata(
    payload: Mapping[str, Any],
    records: Sequence[ManualEvidence],
) -> None:
    passed_records = [record for record in records if record.status == "passed"]
    if not passed_records:
        return
    if payload.get("schema_version") != "v1":
        raise ValueError("schema_version must be v1 when passed manual evidence is present")
    for record in passed_records:
        if not record.evidence or any(not entry.strip() for entry in record.evidence):
            raise ValueError(
                f"{record.check_id} passed manual evidence must include non-empty evidence"
            )
    for field_name in ("reviewed_by", "reviewed_at"):
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} must be a non-empty string when passed manual evidence is present"
            )
        if _contains_todo_placeholder([value]):
            raise ValueError(
                f"{field_name} cannot contain TODO when passed manual evidence is present"
            )
    _validate_reviewed_at_utc(payload["reviewed_at"])


def _validate_reviewed_at_utc(value: str) -> None:
    timestamp = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError("reviewed_at must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("reviewed_at must be an ISO-8601 UTC timestamp")


def build_manual_evidence_template(env: Mapping[str, str]) -> dict[str, Any]:
    """Build a review-safe template for unresolved manual production gates."""
    report = build_readiness_report(env)
    checks = [
        {
            "check_id": check["check_id"],
            "status": "failed",
            "summary": (
                "TODO: replace after completing and reviewing this gate. "
                f"Required action: {check.get('next_action') or check['summary']}"
            ),
            "evidence": [
                "TODO: attach reviewed CI run id, artifact reference, or approval record"
            ],
        }
        for check in report["checks"]
        if check["status"] == "manual_required"
    ]
    return {
        "schema_version": "v1",
        "reviewed_by": "TODO: release owner email or approval record",
        "reviewed_at": "TODO: ISO-8601 UTC timestamp",
        "checks": checks,
    }


def _environment_checks(env: Mapping[str, str]) -> list[ReadinessCheck]:
    return [
        _expect_mode(
            env,
            check_id="postgres_state_store",
            mode_key="STATE_STORE",
            expected_mode="postgres",
            required_keys=("POSTGRES_DSN",),
            next_action=(
                "Set STATE_STORE=postgres and POSTGRES_DSN to the company/staging database."
            ),
        ),
        _expect_mode(
            env,
            check_id="neo4j_graph_backend",
            mode_key="GRAPH_BACKEND",
            expected_mode="neo4j",
            required_keys=("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"),
            next_action="Set GRAPH_BACKEND=neo4j and Neo4j connection variables.",
        ),
        _expect_mode(
            env,
            check_id="qdrant_vector_backend",
            mode_key="VECTOR_BACKEND",
            expected_mode="qdrant",
            required_keys=("QDRANT_URL", "QDRANT_COLLECTION"),
            next_action="Set VECTOR_BACKEND=qdrant and Qdrant connection variables.",
        ),
        _expect_mode(
            env,
            check_id="model_gateway_profile",
            mode_key="MODEL_GATEWAY_MODE",
            expected_mode="http_json",
            required_keys=("MODEL_GATEWAY_ENDPOINT_URL",),
            next_action="Configure a non-dummy model gateway profile and endpoint.",
        ),
        _expect_mode(
            env,
            check_id="trusted_proxy_auth",
            mode_key="AUTH_MODE",
            expected_mode="trusted_proxy",
            required_keys=("TRUSTED_PROXY_SECRET", "TRUSTED_GROUP_ROLE_MAP"),
            next_action="Run behind the company SSO/OIDC reverse proxy in trusted_proxy mode.",
        ),
        _expect_keys(
            env,
            check_id="artifact_storage",
            required_keys=("ARTIFACT_ROOT",),
            next_action="Set ARTIFACT_ROOT to a backed-up server path.",
        ),
        _expect_mode(
            env,
            check_id="opentelemetry_export",
            mode_key="OTEL_ENABLED",
            expected_mode="true",
            required_keys=("OTEL_EXPORTER_OTLP_ENDPOINT",),
            next_action=(
                "Set OTEL_ENABLED=true and OTEL_EXPORTER_OTLP_ENDPOINT to the "
                "company-approved collector."
            ),
        ),
    ]


def _company_rehearsal_checks(env: Mapping[str, str]) -> list[ReadinessCheck]:
    checks = [
        _external_rehearsal_check(
            env,
            check_id="company_postgres_rehearsal",
            keys=("POSTGRES_TEST_DSN", "POSTGRES_DSN"),
            next_action=(
                "Run PostgreSQL integration or full-stack rehearsal against "
                "company/staging PostgreSQL."
            ),
        ),
        _external_rehearsal_check(
            env,
            check_id="company_neo4j_rehearsal",
            keys=("NEO4J_TEST_URI", "NEO4J_URI"),
            next_action=(
                "Run Neo4j integration or full-stack rehearsal against company/staging Neo4j."
            ),
        ),
        _external_rehearsal_check(
            env,
            check_id="company_qdrant_rehearsal",
            keys=("QDRANT_TEST_URL", "QDRANT_URL"),
            next_action=(
                "Run Qdrant integration or full-stack rehearsal against company/staging Qdrant."
            ),
        ),
        _external_rehearsal_check(
            env,
            check_id="company_model_gateway_rehearsal",
            keys=("MODEL_GATEWAY_ENDPOINT_URL",),
            next_action=(
                "Run ops/model_gateway/rehearse_model_gateway.py against the "
                "company-approved model provider sandbox."
            ),
        ),
        _external_rehearsal_check(
            env,
            check_id="company_jira_sandbox_rehearsal",
            keys=("RUNE_JIRA_MCP_URL", "JIRA_BASE_URL"),
            next_action=(
                "Run the JIRA source skill and "
                "ops/source/rehearse_company_sources.py --source jira against a sandbox project."
            ),
        ),
        _external_rehearsal_check(
            env,
            check_id="company_confluence_sandbox_rehearsal",
            keys=("RUNE_CONFLUENCE_MCP_URL", "CONFLUENCE_BASE_URL"),
            next_action=(
                "Run the Confluence source skill and "
                "ops/source/rehearse_company_sources.py --source confluence "
                "against a sandbox space."
            ),
        ),
    ]
    checks.append(
        ReadinessCheck(
            check_id="company_email_policy_rehearsal",
            status="manual_required",
            summary=(
                "Email ingestion remains policy-gated and must be validated with "
                "approved exported decision artifacts or a limited mailbox scope."
            ),
            evidence=[
                _presence_evidence(env, "RUNE_EMAIL_EXPORT_PATH"),
                (
                    "AI write-back to Email is intentionally out of scope for the first "
                    "production release."
                ),
            ],
            next_action=(
                "Run ops/source/rehearse_decision_email_export.py against an approved "
                "decision archive or restricted Email export path."
            ),
        )
    )
    checks.append(
        ReadinessCheck(
            check_id="backup_restore_load_rehearsal",
            status="manual_required",
            summary=(
                "Backup/restore/load rehearsals require company/staging infrastructure "
                "and operator approval."
            ),
            evidence=[
                _presence_evidence(env, "BACKUP_ROOT"),
                "Run docs/runbooks/BACKUP_RESTORE.md and ops/load/smoke_load.py in staging.",
            ],
            next_action=(
                "Complete backup, restore, and load rehearsals against company/staging "
                "services, then run ops/backup/verify_backup_set.py on the backup set."
            ),
        )
    )
    checks.append(
        _external_rehearsal_check(
            env,
            check_id="observability_dashboard_rehearsal",
            keys=("PROMETHEUS_BASE_URL", "GRAFANA_DASHBOARD_UID"),
            next_action=(
                "Import ops/observability/grafana-dashboard.json, load "
                "ops/observability/rune-agent-alerts.yml, and verify the "
                "staging Prometheus target scrapes /api/v1/metrics."
            ),
        )
    )
    checks.append(
        _external_rehearsal_check(
            env,
            check_id="trusted_proxy_rbac_rehearsal",
            keys=("RUNE_API_BASE_URL", "TRUSTED_PROXY_SECRET"),
            next_action=(
                "Run ops/security/rehearse_trusted_proxy_auth.py against the "
                "company/staging trusted proxy boundary."
            ),
        )
    )
    checks.append(_kubernetes_helm_rehearsal_check(env))
    return checks


def _expect_mode(
    env: Mapping[str, str],
    *,
    check_id: str,
    mode_key: str,
    expected_mode: str,
    required_keys: Sequence[str],
    next_action: str,
) -> ReadinessCheck:
    actual_mode = env.get(mode_key, "")
    missing = _missing_keys(env, required_keys)
    if actual_mode == expected_mode and not missing:
        return ReadinessCheck(
            check_id=check_id,
            status="passed",
            summary=f"{mode_key} is configured for {expected_mode}.",
            evidence=[
                f"{mode_key}={actual_mode}",
                *[_presence_evidence(env, key) for key in required_keys],
            ],
        )
    evidence = [
        f"{mode_key}={actual_mode or '<unset>'}",
        *[_presence_evidence(env, key) for key in required_keys],
    ]
    return ReadinessCheck(
        check_id=check_id,
        status="failed",
        summary=(
            f"{mode_key} must be {expected_mode}; "
            f"missing keys: {', '.join(missing) or 'none'}."
        ),
        evidence=evidence,
        next_action=next_action,
    )


def _expect_keys(
    env: Mapping[str, str],
    *,
    check_id: str,
    required_keys: Sequence[str],
    next_action: str,
) -> ReadinessCheck:
    missing = _missing_keys(env, required_keys)
    return ReadinessCheck(
        check_id=check_id,
        status="passed" if not missing else "failed",
        summary=(
            "Required environment keys are present."
            if not missing
            else f"Missing keys: {', '.join(missing)}."
        ),
        evidence=[_presence_evidence(env, key) for key in required_keys],
        next_action=None if not missing else next_action,
    )


def _external_rehearsal_check(
    env: Mapping[str, str],
    *,
    check_id: str,
    keys: Sequence[str],
    next_action: str,
) -> ReadinessCheck:
    present = [key for key in keys if env.get(key)]
    if present:
        return ReadinessCheck(
            check_id=check_id,
            status="manual_required",
            summary="Endpoint configuration exists, but a real rehearsal result is still required.",
            evidence=[_presence_evidence(env, key) for key in keys],
            next_action=next_action,
        )
    return ReadinessCheck(
        check_id=check_id,
        status="manual_required",
        summary="No company/staging endpoint configuration was found.",
        evidence=[_presence_evidence(env, key) for key in keys],
        next_action=next_action,
    )


def _kubernetes_helm_rehearsal_check(env: Mapping[str, str]) -> ReadinessCheck:
    deployment_target = env.get("DEPLOYMENT_TARGET", "").lower()
    kubernetes_enabled = env.get("KUBERNETES_DEPLOYMENT", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if deployment_target != "kubernetes" and not kubernetes_enabled:
        return ReadinessCheck(
            check_id="kubernetes_helm_rehearsal",
            status="passed",
            summary="Kubernetes deployment is not selected; Ubuntu runbook remains primary.",
            evidence=[
                f"DEPLOYMENT_TARGET={deployment_target or '<unset>'}",
                _presence_evidence(env, "KUBERNETES_DEPLOYMENT"),
            ],
        )
    return ReadinessCheck(
        check_id="kubernetes_helm_rehearsal",
        status="manual_required",
        summary="Kubernetes deployment is selected, but Helm lint/template evidence is required.",
        evidence=[
            f"DEPLOYMENT_TARGET={deployment_target or '<unset>'}",
            _presence_evidence(env, "KUBERNETES_DEPLOYMENT"),
            _presence_evidence(env, "HELM_RELEASE_EVIDENCE"),
        ],
        next_action=(
            "Run helm lint and helm template against company values, then attach "
            "the reviewed output reference as manual evidence."
        ),
    )


def _local_gate_summary(results: Sequence[dict[str, Any]]) -> ReadinessCheck:
    failures = [result for result in results if result["returncode"] != 0]
    if not failures:
        return ReadinessCheck(
            check_id="local_regression_gates",
            status="passed",
            summary="All local regression and rehearsal gates passed.",
            evidence=[str(result["command"]) for result in results],
        )
    docker_unavailable_failures = [
        result for result in failures if _is_docker_unavailable_failure(result)
    ]
    if len(docker_unavailable_failures) == len(failures):
        return ReadinessCheck(
            check_id="local_regression_gates",
            status="manual_required",
            summary=(
                "Docker-backed local gates could not run because Docker is unavailable; "
                "non-Docker local gates passed."
            ),
            evidence=[
                (
                    f"{result['command']} -> docker_unavailable"
                    if result in docker_unavailable_failures
                    else f"{result['command']} -> {result['returncode']}"
                )
                for result in results
            ],
            next_action=(
                "Start Docker Desktop with the Linux engine, or run these "
                "Docker-backed gates on an Ubuntu/Docker host before release."
            ),
        )
    return ReadinessCheck(
        check_id="local_regression_gates",
        status="failed",
        summary=f"{len(failures)} local gate command(s) failed.",
        evidence=[f"{result['command']} -> {result['returncode']}" for result in results],
        next_action="Fix failed local gates before release.",
    )


def _is_docker_unavailable_failure(result: Mapping[str, Any]) -> bool:
    command = str(result.get("command", ""))
    if not (
        "ops/integration/run_backend_integration.py" in command
        or "ops/rehearsal/run_full_stack_rehearsal.py" in command
    ):
        return False
    output = str(result.get("output_tail", "")).lower()
    docker_unavailable_markers = (
        "failed to connect to the docker api",
        "cannot connect to the docker daemon",
        "dockerdesktoplinuxengine",
        "is the docker daemon running",
    )
    return any(marker in output for marker in docker_unavailable_markers)


def _apply_manual_evidence(
    checks: Sequence[ReadinessCheck],
    manual_evidence: Sequence[ManualEvidence],
) -> list[ReadinessCheck]:
    evidence_by_check = {record.check_id: record for record in manual_evidence}
    updated: list[ReadinessCheck] = []
    for check in checks:
        evidence = evidence_by_check.get(check.check_id)
        if evidence is None:
            updated.append(check)
            continue
        if check.status != "manual_required":
            updated.append(
                ReadinessCheck(
                    check_id=check.check_id,
                    status=check.status,
                    summary=(
                        f"{check.summary} Manual evidence was ignored because this "
                        "is not a manual gate."
                    ),
                    evidence=[
                        *check.evidence,
                        "manual_evidence_ignored:not_manual_gate",
                    ],
                    next_action=check.next_action,
                )
            )
            continue
        updated.append(
            ReadinessCheck(
                check_id=check.check_id,
                status=evidence.status,
                summary=evidence.summary,
                evidence=[*check.evidence, *evidence.evidence],
                next_action=None if evidence.status == "passed" else check.next_action,
            )
        )
    known_ids = {check.check_id for check in checks}
    for evidence in manual_evidence:
        if evidence.check_id in known_ids:
            continue
        updated.append(
            ReadinessCheck(
                check_id=f"unknown_manual_evidence:{evidence.check_id}",
                status="warning",
                summary="Manual evidence references an unknown readiness check id.",
                evidence=evidence.evidence,
                next_action="Remove or rename the unknown evidence check id.",
            )
        )
    return updated


def _run_command(command: Sequence[str], *, timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "output_tail": completed.stdout[-4000:],
    }


def _summarize_checks(checks: Sequence[ReadinessCheck]) -> dict[str, int]:
    summary = {"passed": 0, "warning": 0, "failed": 0, "manual_required": 0}
    for check in checks:
        summary[check.status] += 1
    return summary


def _missing_keys(env: Mapping[str, str], keys: Sequence[str]) -> list[str]:
    return [key for key in keys if not env.get(key)]


def _presence_evidence(env: Mapping[str, str], key: str) -> str:
    value = env.get(key)
    if not value:
        return f"{key}=<unset>"
    return f"{key}=<set>"


def _contains_todo_placeholder(values: Sequence[str]) -> bool:
    return any("TODO:" in value for value in values)


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-local-gates", action="store_true")
    parser.add_argument("--command-timeout-seconds", type=int, default=300)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional KEY=VALUE environment file for company/staging checks.",
    )
    parser.add_argument(
        "--evidence-file",
        type=Path,
        default=None,
        help="Optional reviewed manual-gate evidence JSON file.",
    )
    parser.add_argument(
        "--write-evidence-template",
        type=Path,
        default=None,
        help=(
            "Write a review-safe manual evidence template for unresolved "
            "company/staging gates. Use '-' to print to stdout."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON report output path. Use '-' to print to stdout.",
    )
    args = parser.parse_args()
    env = load_env_file(args.env_file, os.environ) if args.env_file else dict(os.environ)
    if args.write_evidence_template is not None:
        template = build_manual_evidence_template(env)
        write_json_output(template, args.write_evidence_template)
        return 0
    manual_evidence = load_manual_evidence(args.evidence_file) if args.evidence_file else []
    report = build_readiness_report(
        env,
        run_local_gates=args.run_local_gates,
        command_timeout_seconds=args.command_timeout_seconds,
        manual_evidence=manual_evidence,
    )
    if args.output:
        write_json_output(report, args.output)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

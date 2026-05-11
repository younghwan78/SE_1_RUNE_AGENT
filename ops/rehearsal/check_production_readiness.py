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


LOCAL_GATE_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "mypy", "src"),
    ("uv", "run", "pytest"),
    ("uv", "run", "python", "ops/integration/run_backend_integration.py"),
    ("uv", "run", "python", "ops/source/smoke_source_adapters.py"),
    ("uv", "run", "python", "ops/model_gateway/smoke_model_gateway.py"),
    ("uv", "run", "python", "ops/rehearsal/run_full_stack_rehearsal.py"),
    ("uv", "run", "python", "ops/evals/run_feedback_eval_rehearsal.py"),
)


def build_readiness_report(
    env: Mapping[str, str],
    *,
    run_local_gates: bool = False,
    command_timeout_seconds: int = 300,
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
    summary = _summarize_checks(checks)
    return {
        "passed": summary["failed"] == 0 and summary["manual_required"] == 0,
        "summary": summary,
        "checks": [asdict(check) for check in checks],
        "local_gate_commands": [" ".join(command) for command in LOCAL_GATE_COMMANDS],
        "local_gate_results": local_gate_results,
        "schema_version": "v1",
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
                "Run model gateway smoke against the company-approved model provider sandbox."
            ),
        ),
        _external_rehearsal_check(
            env,
            check_id="company_jira_sandbox_rehearsal",
            keys=("RUNE_JIRA_MCP_URL", "JIRA_BASE_URL"),
            next_action="Run the JIRA source skill and adapter smoke against a sandbox project.",
        ),
        _external_rehearsal_check(
            env,
            check_id="company_confluence_sandbox_rehearsal",
            keys=("RUNE_CONFLUENCE_MCP_URL", "CONFLUENCE_BASE_URL"),
            next_action=(
                "Run the Confluence source skill and adapter smoke against a sandbox space."
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
            next_action="Validate only approved decision-archive or restricted Email export paths.",
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
                "Complete backup, restore, and load rehearsals against "
                "company/staging services."
            ),
        )
    )
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


def _local_gate_summary(results: Sequence[dict[str, Any]]) -> ReadinessCheck:
    failures = [result for result in results if result["returncode"] != 0]
    if not failures:
        return ReadinessCheck(
            check_id="local_regression_gates",
            status="passed",
            summary="All local regression and rehearsal gates passed.",
            evidence=[str(result["command"]) for result in results],
        )
    return ReadinessCheck(
        check_id="local_regression_gates",
        status="failed",
        summary=f"{len(failures)} local gate command(s) failed.",
        evidence=[f"{result['command']} -> {result['returncode']}" for result in results],
        next_action="Fix failed local gates before release.",
    )


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


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-local-gates", action="store_true")
    parser.add_argument("--command-timeout-seconds", type=int, default=300)
    args = parser.parse_args()
    report = build_readiness_report(
        os.environ,
        run_local_gates=args.run_local_gates,
        command_timeout_seconds=args.command_timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

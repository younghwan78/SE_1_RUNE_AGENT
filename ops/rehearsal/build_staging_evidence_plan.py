"""Build a concrete company/staging evidence collection plan.

The production-readiness checker tells release owners which gates are still
failed or manual. This helper turns those unresolved gates into an execution
plan with required environment variables, commands, evidence expectations, and
runbook references. It never prints secret values.
"""

import argparse
import importlib.util
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = ROOT / "ops/rehearsal/check_production_readiness.py"

FINAL_VALIDATION_COMMANDS: tuple[str, ...] = (
    (
        "uv run python ops/rehearsal/check_production_readiness.py "
        "--run-local-gates --env-file <staging.env> "
        "--evidence-file <reviewed-evidence.json>"
    ),
    (
        "uv run python ops/rehearsal/check_goal_completion.py "
        "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
        "--run-local-gates"
    ),
    (
        "uv run python ops/rehearsal/build_handoff_bundle.py "
        "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
        "--output-dir <handoff-bundle-dir>"
    ),
    "uv run python ops/rehearsal/validate_handoff_bundle.py <handoff-bundle-dir>",
)


@dataclass(frozen=True)
class GateGuidance:
    """Operator guidance for one readiness check."""

    required_env: tuple[str, ...]
    commands: tuple[str, ...]
    required_evidence: tuple[str, ...]
    docs: tuple[str, ...] = ()


GATE_GUIDANCE: dict[str, GateGuidance] = {
    "postgres_state_store": GateGuidance(
        required_env=("STATE_STORE=postgres", "POSTGRES_DSN"),
        commands=("uv run python ops/rehearsal/check_production_readiness.py",),
        required_evidence=("masked readiness report showing postgres_state_store passed",),
        docs=("README_ubuntu.md#production-readiness",),
    ),
    "neo4j_graph_backend": GateGuidance(
        required_env=("GRAPH_BACKEND=neo4j", "NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"),
        commands=("uv run python ops/rehearsal/check_production_readiness.py",),
        required_evidence=("masked readiness report showing neo4j_graph_backend passed",),
        docs=("README_ubuntu.md#production-readiness",),
    ),
    "qdrant_vector_backend": GateGuidance(
        required_env=("VECTOR_BACKEND=qdrant", "QDRANT_URL", "QDRANT_COLLECTION"),
        commands=("uv run python ops/rehearsal/check_production_readiness.py",),
        required_evidence=("masked readiness report showing qdrant_vector_backend passed",),
        docs=("README_ubuntu.md#production-readiness",),
    ),
    "model_gateway_profile": GateGuidance(
        required_env=("MODEL_GATEWAY_MODE=http_json", "MODEL_GATEWAY_ENDPOINT_URL"),
        commands=("uv run python ops/model_gateway/rehearse_model_gateway.py",),
        required_evidence=("masked model gateway rehearsal JSON",),
        docs=("docs/runbooks/MODEL_POLICY.md",),
    ),
    "trusted_proxy_auth": GateGuidance(
        required_env=("AUTH_MODE=trusted_proxy", "TRUSTED_PROXY_SECRET", "TRUSTED_GROUP_ROLE_MAP"),
        commands=("uv run python ops/security/rehearse_trusted_proxy_auth.py",),
        required_evidence=("masked trusted-proxy rehearsal JSON",),
        docs=("docs/security/RBAC_MATRIX.md", "README_ubuntu.md#production-readiness"),
    ),
    "artifact_storage": GateGuidance(
        required_env=("ARTIFACT_ROOT",),
        commands=("uv run python ops/rehearsal/check_production_readiness.py",),
        required_evidence=("masked readiness report showing artifact_storage passed",),
        docs=("README_ubuntu.md#production-readiness", "docs/runbooks/BACKUP_RESTORE.md"),
    ),
    "opentelemetry_export": GateGuidance(
        required_env=("OTEL_ENABLED=true", "OTEL_EXPORTER_OTLP_ENDPOINT"),
        commands=(
            "uv run python ops/observability/validate_observability_assets.py",
            "uv run python ops/rehearsal/check_production_readiness.py",
        ),
        required_evidence=("collector endpoint proof", "masked readiness report"),
        docs=("README_ubuntu.md#production-readiness",),
    ),
    "company_postgres_rehearsal": GateGuidance(
        required_env=("POSTGRES_TEST_DSN or POSTGRES_DSN",),
        commands=(
            "uv run pytest tests/integration/test_postgres_state_store.py",
            "uv run python ops/rehearsal/run_full_stack_rehearsal.py",
        ),
        required_evidence=("reviewed staging PostgreSQL test run id or JSON artifact",),
        docs=("docs/runbooks/BACKUP_RESTORE.md",),
    ),
    "company_neo4j_rehearsal": GateGuidance(
        required_env=("NEO4J_TEST_URI or NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"),
        commands=(
            "uv run pytest tests/integration/test_neo4j_graph_backend.py",
            "uv run python ops/rehearsal/run_full_stack_rehearsal.py",
        ),
        required_evidence=("reviewed staging Neo4j test run id or JSON artifact",),
        docs=("README_ubuntu.md#production-readiness", "docs/runbooks/BACKUP_RESTORE.md"),
    ),
    "company_qdrant_rehearsal": GateGuidance(
        required_env=("QDRANT_TEST_URL or QDRANT_URL", "QDRANT_COLLECTION"),
        commands=(
            "uv run pytest tests/integration/test_qdrant_vector_backend.py",
            "uv run python ops/rehearsal/run_full_stack_rehearsal.py",
        ),
        required_evidence=("reviewed staging Qdrant test run id or JSON artifact",),
        docs=("README_ubuntu.md#production-readiness", "docs/runbooks/BACKUP_RESTORE.md"),
    ),
    "company_model_gateway_rehearsal": GateGuidance(
        required_env=("MODEL_GATEWAY_ENDPOINT_URL", "MODEL_GATEWAY_API_KEY if required"),
        commands=("uv run python ops/model_gateway/rehearse_model_gateway.py",),
        required_evidence=("masked model gateway rehearsal JSON",),
        docs=("docs/runbooks/MODEL_POLICY.md",),
    ),
    "company_jira_sandbox_rehearsal": GateGuidance(
        required_env=("JIRA_BASE_URL", "JIRA_TOKEN or JIRA_API_TOKEN", "JIRA_PROJECT_KEY"),
        commands=("uv run python ops/source/rehearse_company_sources.py --source jira",),
        required_evidence=("masked JIRA rehearsal JSON with artifact shape summaries",),
        docs=("docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md",),
    ),
    "company_confluence_sandbox_rehearsal": GateGuidance(
        required_env=(
            "CONFLUENCE_BASE_URL",
            "CONFLUENCE_TOKEN or CONFLUENCE_API_TOKEN",
            "CONFLUENCE_SPACE_KEY",
        ),
        commands=("uv run python ops/source/rehearse_company_sources.py --source confluence",),
        required_evidence=("masked Confluence rehearsal JSON with section/table evidence",),
        docs=("docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md",),
    ),
    "company_email_policy_rehearsal": GateGuidance(
        required_env=("RUNE_EMAIL_EXPORT_PATH",),
        commands=("uv run python ops/source/rehearse_decision_email_export.py",),
        required_evidence=("approved decision/email export rehearsal JSON",),
        docs=(
            "docs/security/DATA_POLICY.md",
            "docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md",
        ),
    ),
    "backup_restore_load_rehearsal": GateGuidance(
        required_env=("BACKUP_ROOT", "RUNE_API_BASE_URL for load smoke"),
        commands=(
            "uv run python ops/backup/verify_backup_set.py --backup-root <BACKUP_ROOT>",
            "uv run python ops/load/smoke_load.py --base-url <RUNE_API_BASE_URL>",
        ),
        required_evidence=("backup verification JSON", "restore log reference", "load smoke JSON"),
        docs=("docs/runbooks/BACKUP_RESTORE.md",),
    ),
    "observability_dashboard_rehearsal": GateGuidance(
        required_env=("PROMETHEUS_BASE_URL", "GRAFANA_DASHBOARD_UID"),
        commands=("uv run python ops/observability/validate_observability_assets.py",),
        required_evidence=("Prometheus scrape proof", "Grafana dashboard import proof"),
        docs=("README_ubuntu.md#production-readiness",),
    ),
    "trusted_proxy_rbac_rehearsal": GateGuidance(
        required_env=("RUNE_API_BASE_URL", "TRUSTED_PROXY_SECRET"),
        commands=("uv run python ops/security/rehearse_trusted_proxy_auth.py",),
        required_evidence=("masked trusted-proxy RBAC rehearsal JSON",),
        docs=("docs/security/RBAC_MATRIX.md",),
    ),
    "kubernetes_helm_rehearsal": GateGuidance(
        required_env=("DEPLOYMENT_TARGET=kubernetes", "KUBERNETES_DEPLOYMENT=true"),
        commands=(
            "helm lint ops/helm/rune-agent",
            "helm template rune-agent ops/helm/rune-agent -f <company-values.yaml>",
        ),
        required_evidence=("reviewed helm lint/template output reference",),
        docs=("ops/helm/README.md",),
    ),
    "local_regression_gates": GateGuidance(
        required_env=(),
        commands=("uv run python ops/rehearsal/check_production_readiness.py --run-local-gates",),
        required_evidence=("local gate report showing local_regression_gates passed",),
        docs=("README_ubuntu.md#production-readiness",),
    ),
}


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format. Default: json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. Omit to print to stdout.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional KEY=VALUE environment file for company/staging checks.",
    )
    args = parser.parse_args()
    env = load_plan_env(args.env_file, os.environ) if args.env_file else dict(os.environ)
    plan = build_staging_evidence_plan(env)
    rendered = (
        json.dumps(plan, indent=2, sort_keys=True)
        if args.format == "json"
        else render_markdown(plan)
    )
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


def load_plan_env(path: Path, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Load the staging evidence plan environment through the readiness parser."""
    checker = _load_readiness_checker()
    return checker.load_env_file(path, base_env or {})


def build_staging_evidence_plan(env: Mapping[str, str]) -> dict[str, Any]:
    """Return unresolved readiness gates with concrete collection guidance."""
    checker = _load_readiness_checker()
    report = checker.build_readiness_report(env)
    unresolved = [
        check
        for check in report["checks"]
        if check["status"] in {"failed", "manual_required", "warning"}
    ]
    gates = [_gate_plan(check) for check in unresolved]
    return {
        "schema_version": "v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "unresolved_count": len(gates),
        "summary": report["summary"],
        "final_validation_commands": list(FINAL_VALIDATION_COMMANDS),
        "gates": gates,
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    """Render a human-readable evidence collection plan."""
    lines = [
        "# Staging Evidence Collection Plan",
        "",
        f"- Generated at: `{plan['generated_at']}`",
        f"- Unresolved gates: `{plan['unresolved_count']}`",
        f"- Summary: `{json.dumps(plan['summary'], sort_keys=True)}`",
        "",
        "## Final Validation",
        "",
        "After collecting reviewed evidence, run:",
        "",
        *[f"- `{command}`" for command in plan["final_validation_commands"]],
        "",
    ]
    for gate in plan["gates"]:
        lines.extend(
            [
                f"## {gate['check_id']}",
                "",
                f"- Status: `{gate['status']}`",
                f"- Summary: {gate['summary']}",
                f"- Required env: {_inline_list(gate['required_env'])}",
                "- Commands:",
                *[f"  - `{command}`" for command in gate["commands"]],
                f"- Required evidence: {_inline_list(gate['required_evidence'])}",
                f"- Docs: {_inline_list(gate['docs'])}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _gate_plan(check: Mapping[str, Any]) -> dict[str, Any]:
    guidance = GATE_GUIDANCE.get(
        str(check["check_id"]),
        GateGuidance(
            required_env=(),
            commands=(),
            required_evidence=("reviewed evidence for this readiness check",),
        ),
    )
    return {
        "check_id": check["check_id"],
        "status": check["status"],
        "summary": check["summary"],
        "next_action": check.get("next_action"),
        "current_evidence": _mask_evidence(check.get("evidence", [])),
        "required_env": list(guidance.required_env),
        "commands": list(guidance.commands),
        "required_evidence": list(guidance.required_evidence),
        "docs": list(guidance.docs),
    }


def _mask_evidence(values: object) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, str):
        return []
    masked: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        key, separator, suffix = value.partition("=")
        if separator and suffix not in {"<unset>", "<set>"}:
            masked.append(f"{key}=<set>")
        else:
            masked.append(value)
    return masked


def _inline_list(values: Sequence[str]) -> str:
    if not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)


def _load_readiness_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_production_readiness", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load readiness checker from {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())

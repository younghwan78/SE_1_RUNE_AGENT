"""Validate first-release scope artifacts against the production plan.

This verifier is intentionally not a release approval gate. It checks that each
first-release requirement from PRODUCTION_EXECUTION_PLAN.md has concrete local
artifacts, verification commands, and a current status classification. Real
company/staging evidence is still handled by check_production_readiness.py.
"""

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]

ScopeStatus = Literal["local_complete", "company_evidence_required"]


@dataclass(frozen=True)
class ReleaseScopeItem:
    """One first-release scope item and its concrete local evidence."""

    item_id: str
    requirement: str
    status: ScopeStatus
    evidence_paths: tuple[str, ...]
    verification_commands: tuple[str, ...]
    notes: str


RELEASE_SCOPE_ITEMS: tuple[ReleaseScopeItem, ...] = (
    ReleaseScopeItem(
        item_id="jira_incremental_sync",
        requirement="실제 JIRA incremental sync",
        status="company_evidence_required",
        evidence_paths=(
            "src/req_tracker/adapters/jira_rest.py",
            "ops/source/rehearse_company_sources.py",
            ".claude/skills/rune-source-jira/SKILL.md",
        ),
        verification_commands=(
            "uv run pytest tests/unit/adapters/test_jira_rest_adapter.py",
            "uv run python ops/source/rehearse_company_sources.py --source jira",
        ),
        notes=(
            "Local REST/export adapter and sandbox rehearsal path exist; "
            "real JIRA sandbox evidence is still required."
        ),
    ),
    ReleaseScopeItem(
        item_id="source_snapshot_masking_evidence_chunking",
        requirement="source snapshot, masking, evidence, chunking",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/adapters/base.py",
            "src/req_tracker/ingestion/masking.py",
            "src/req_tracker/ingestion/chunking.py",
            "src/req_tracker/evidence/spans.py",
            "tests/unit/ingestion/test_masking_chunking.py",
        ),
        verification_commands=("uv run pytest tests/unit/ingestion/test_masking_chunking.py",),
        notes="Local deterministic ingestion primitives and masking tests are present.",
    ),
    ReleaseScopeItem(
        item_id="model_gateway_prompt_registry",
        requirement="model gateway와 prompt/model registry",
        status="company_evidence_required",
        evidence_paths=(
            "src/req_tracker/model_gateway/client.py",
            "src/req_tracker/model_gateway/registry.py",
            "config/model_profiles.json",
            "config/prompt_versions.json",
            "ops/model_gateway/rehearse_model_gateway.py",
        ),
        verification_commands=(
            "uv run pytest tests/unit/model_gateway",
            "uv run python ops/model_gateway/rehearse_model_gateway.py",
        ),
        notes=(
            "Local gateway/registry foundation exists; real model sandbox "
            "validation is still required."
        ),
    ),
    ReleaseScopeItem(
        item_id="run_step_llm_trace",
        requirement="run/step/LLM call trace",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/debug/traces.py",
            "src/req_tracker/debug/models.py",
            "src/req_tracker/api/routes/debug.py",
            "tests/contract/test_debug_api.py",
        ),
        verification_commands=("uv run pytest tests/contract/test_debug_api.py",),
        notes="Run, step, artifact, graph-delta, replay, and LLM trace APIs exist locally.",
    ),
    ReleaseScopeItem(
        item_id="deterministic_baseline_rules",
        requirement="deterministic baseline rules",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/findings/rules.py",
            "tests/unit/findings/test_rules.py",
        ),
        verification_commands=("uv run pytest tests/unit/findings/test_rules.py",),
        notes="Deterministic traceability gap/conflict/stale rules are covered by unit tests.",
    ),
    ReleaseScopeItem(
        item_id="llm_assisted_suggestions",
        requirement="LLM-assisted node/edge/finding suggestion",
        status="company_evidence_required",
        evidence_paths=(
            "src/req_tracker/workflows/analysis_graph.py",
            "src/req_tracker/reasoning/extraction.py",
            "src/req_tracker/reasoning/linking.py",
            "tests/integration/test_dummy_analysis_pipeline.py",
        ),
        verification_commands=("uv run pytest tests/integration/test_dummy_analysis_pipeline.py",),
        notes=(
            "Dummy model-gateway path is traceable; live model quality "
            "validation is still required."
        ),
    ),
    ReleaseScopeItem(
        item_id="approval_queue_delta_preview",
        requirement="approval queue와 graph delta preview",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/approvals/service.py",
            "src/req_tracker/api/routes/approvals.py",
            "src/req_tracker/api/routes/runs.py",
            "tests/contract/test_run_api.py",
        ),
        verification_commands=("uv run pytest tests/contract/test_run_api.py",),
        notes="Approval queue, graph delta, stale guard, and decision paths are locally tested.",
    ),
    ReleaseScopeItem(
        item_id="approved_graph_commit",
        requirement="approved graph commit",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/graph/base.py",
            "src/req_tracker/graph/memory_backend.py",
            "src/req_tracker/graph/neo4j_backend.py",
            "tests/integration/test_dummy_analysis_pipeline.py",
        ),
        verification_commands=("uv run pytest tests/integration/test_dummy_analysis_pipeline.py",),
        notes="Approved graph commit paths are separated from pending AI proposals.",
    ),
    ReleaseScopeItem(
        item_id="feedback_event_store",
        requirement="feedback event store",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/feedback/service.py",
            "src/req_tracker/evals/datasets.py",
            "ops/evals/run_feedback_eval_rehearsal.py",
            "tests/contract/test_replay_feedback_api.py",
        ),
        verification_commands=("uv run python ops/evals/run_feedback_eval_rehearsal.py",),
        notes="Feedback, eval candidate, canary, rollback, and gate paths are present locally.",
    ),
    ReleaseScopeItem(
        item_id="debug_workbench",
        requirement="debug workbench",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/ui/debug_workbench.js",
            "src/req_tracker/api/routes/debug.py",
            "tests/contract/test_debug_api.py",
        ),
        verification_commands=("uv run pytest tests/contract/test_debug_api.py",),
        notes="Static debug workbench and debug APIs are present.",
    ),
    ReleaseScopeItem(
        item_id="replay_skeleton",
        requirement="replay skeleton",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/debug/replay.py",
            "src/req_tracker/debug/diff.py",
            "tests/contract/test_replay_feedback_api.py",
        ),
        verification_commands=("uv run pytest tests/contract/test_replay_feedback_api.py",),
        notes="Replay execution and diff contracts are locally covered.",
    ),
    ReleaseScopeItem(
        item_id="graph_chain_finding_read_api",
        requirement="graph/chain/finding read API",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/api/routes/graph.py",
            "src/req_tracker/api/routes/dashboard.py",
            "tests/contract/test_graph_projection_api.py",
            "tests/contract/test_traceability_chain_api.py",
        ),
        verification_commands=(
            "uv run pytest tests/contract/test_graph_projection_api.py "
            "tests/contract/test_traceability_chain_api.py",
        ),
        notes="Graph projection, chain, finding, dashboard read paths exist locally.",
    ),
    ReleaseScopeItem(
        item_id="production_graph_ui",
        requirement="production graph UI with renderer decision gate",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/ui/graph_workbench.js",
            "docs/implementation/07_GRAPH_VIEW_SCALABILITY_PLAN.md",
            "docs/implementation/11_GRAPH_RELATIONSHIP_VIEW_PLAN.md",
            "ops/ui/smoke_operator_ui.py",
        ),
        verification_commands=("uv run python ops/ui/smoke_operator_ui.py",),
        notes=(
            "Deterministic SVG relationship graph is the first-release renderer; "
            "React Flow/Cytoscape remains gated by documented scale and editing needs."
        ),
    ),
    ReleaseScopeItem(
        item_id="sso_rbac_basic",
        requirement="SSO/RBAC 기본 연동",
        status="company_evidence_required",
        evidence_paths=(
            "src/req_tracker/api/security.py",
            "docs/security/RBAC_MATRIX.md",
            "ops/security/rehearse_trusted_proxy_auth.py",
        ),
        verification_commands=("uv run python ops/security/rehearse_trusted_proxy_auth.py",),
        notes=(
            "Trusted-proxy auth foundation exists; company SSO/OIDC boundary "
            "evidence is still required."
        ),
    ),
    ReleaseScopeItem(
        item_id="audit_log",
        requirement="audit log",
        status="local_complete",
        evidence_paths=(
            "src/req_tracker/audit/service.py",
            "src/req_tracker/audit/archive.py",
            "src/req_tracker/api/routes/audit.py",
            "tests/contract/test_audit_api.py",
        ),
        verification_commands=("uv run pytest tests/contract/test_audit_api.py",),
        notes=(
            "Audit event query, retention, archive/prune, and PostgreSQL "
            "archive foundations exist locally."
        ),
    ),
)


def build_release_scope_report(
    *,
    items: Sequence[ReleaseScopeItem] = RELEASE_SCOPE_ITEMS,
) -> dict[str, Any]:
    """Build a first-release scope artifact report."""
    rendered_items = [_render_item(item) for item in items]
    failures: list[str] = []
    for item in rendered_items:
        failures.extend(f"{item['item_id']}:missing_path:{path}" for path in item["missing_paths"])
        if not item["verification_commands"]:
            failures.append(f"{item['item_id']}:missing_verification_command")
        if not item["notes"]:
            failures.append(f"{item['item_id']}:missing_notes")
    status_counts = Counter(item["status"] for item in rendered_items)
    missing_artifacts = sum(len(item["missing_paths"]) for item in rendered_items)
    release_ready = not failures and all(
        item["status"] == "local_complete" for item in rendered_items
    )
    return {
        "schema_version": "v1",
        "passed": not failures,
        "release_ready": release_ready,
        "summary": {
            "item_count": len(rendered_items),
            "missing_artifacts": missing_artifacts,
            "status_counts": dict(sorted(status_counts.items())),
        },
        "items": rendered_items,
        "failures": failures,
    }


def _render_item(item: ReleaseScopeItem) -> dict[str, Any]:
    payload = asdict(item)
    payload["evidence_paths"] = list(item.evidence_paths)
    payload["verification_commands"] = list(item.verification_commands)
    payload["missing_paths"] = [
        path for path in item.evidence_paths if not (ROOT / path).exists()
    ]
    return payload


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = build_release_scope_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

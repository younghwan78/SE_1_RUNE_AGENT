"""Validate release-blocker coverage evidence.

This checker does not replace the referenced tests. It makes the release
blocker map executable so coverage cannot silently disappear from the local
production-readiness gate.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class EvidenceFile:
    """Required snippets for one evidence file."""

    path: str
    snippets: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseBlockerCoverage:
    """One release blocker mapped to concrete repo evidence."""

    blocker_id: str
    summary: str
    evidence_files: tuple[EvidenceFile, ...]


REQUIRED_COVERAGE: tuple[ReleaseBlockerCoverage, ...] = (
    ReleaseBlockerCoverage(
        blocker_id="masking_violation",
        summary="Sensitive inputs must be redacted and violations must fail the gate.",
        evidence_files=(
            EvidenceFile(
                path="ops/security/rehearse_masking_policy.py",
                snippets=("forbidden_patterns", "violation_count", "input_text"),
            ),
            EvidenceFile(
                path="tests/unit/ops/test_masking_policy_rehearsal.py",
                snippets=("violation_count", "custom-secret-value", "not in str(report)"),
            ),
            EvidenceFile(
                path="tests/unit/ingestion/test_masking_chunking.py",
                snippets=("owner@example.com", "SN-IMX789-SECRET", "not in result.text"),
            ),
        ),
    ),
    ReleaseBlockerCoverage(
        blocker_id="approved_graph_mutation_without_approval",
        summary="AI graph proposals must not reach the approved graph without approval.",
        evidence_files=(
            EvidenceFile(
                path="tests/integration/test_dummy_analysis_pipeline.py",
                snippets=("graph.approved_edges() == []", "approvals.decide", "approved_edges()"),
            ),
            EvidenceFile(
                path="tests/contract/test_security_api.py",
                snippets=(
                    "developer_decision.status_code == 403",
                    "wrong_project_decision.status_code == 403",
                    "operator_decision.status_code == 200",
                ),
            ),
        ),
    ),
    ReleaseBlockerCoverage(
        blocker_id="project_authorization_leak",
        summary="Project-scoped nodes, edges, runs, findings, and audit data must not leak.",
        evidence_files=(
            EvidenceFile(
                path="tests/contract/test_security_api.py",
                snippets=(
                    "wrong_project_nodes.status_code == 403",
                    "wrong_project_edges.status_code == 403",
                    "wrong_project_runs.json() == []",
                    "project_denied.status_code == 403",
                ),
            ),
            EvidenceFile(
                path="ops/security/rehearse_trusted_proxy_auth.py",
                snippets=("operator_wrong_project_denied", "expected_status=403"),
            ),
        ),
    ),
    ReleaseBlockerCoverage(
        blocker_id="prompt_model_regression_or_ungated_activation",
        summary="Prompt/model changes must pass eval, review, and canary gates.",
        evidence_files=(
            EvidenceFile(
                path="tests/contract/test_admin_registry_api.py",
                snippets=(
                    "activation gates are not satisfied",
                    "eval_passed",
                    "reviewer_approved",
                    "canary_passed",
                ),
            ),
            EvidenceFile(
                path="tests/contract/test_replay_feedback_api.py",
                snippets=(
                    "eval gate blocked activation",
                    "review_required",
                    "canary_required",
                    "improvement_rolled_back",
                ),
            ),
            EvidenceFile(
                path="tests/unit/ops/test_feedback_eval_rehearsal.py",
                snippets=(
                    "rollback_status",
                    "security_gate_status",
                    "blocked",
                    "security_failures",
                ),
            ),
        ),
    ),
    ReleaseBlockerCoverage(
        blocker_id="graph_migration_without_rollback",
        summary="Graph/state migrations and retention changes need rollback or restore coverage.",
        evidence_files=(
            EvidenceFile(
                path="tests/unit/storage/test_postgres_store.py",
                snippets=("load_postgres_rollbacks", "rollback_migration", "DROP TABLE IF EXISTS"),
            ),
            EvidenceFile(
                path="ops/rehearsal/validate_postgres_migration_rollbacks.py",
                snippets=("missing_rollback", "missing_drop", "orphan_rollback"),
            ),
            EvidenceFile(
                path="ops/migrations/README.md",
                snippets=("rollback path", "staging PostgreSQL rehearsal"),
            ),
            EvidenceFile(
                path="docs/runbooks/BACKUP_RESTORE.md",
                snippets=("Restore", "Rollback"),
            ),
        ),
    ),
    ReleaseBlockerCoverage(
        blocker_id="llm_raw_payload_forbidden_data",
        summary="Unapproved data classes and raw sensitive payloads must not reach model calls.",
        evidence_files=(
            EvidenceFile(
                path="tests/unit/model_gateway/test_dummy_gateway.py",
                snippets=("ModelPolicyError", "no_external_llm", "blocks_disallowed_data_class"),
            ),
            EvidenceFile(
                path="docs/security/DATA_POLICY.md",
                snippets=("no_external_llm", "unmasked confidential content", "Release Blockers"),
            ),
            EvidenceFile(
                path="ops/model_gateway/smoke_model_gateway.py",
                snippets=("raw_response_refs", "schema_version"),
            ),
        ),
    ),
)


def check_release_blockers() -> dict[str, Any]:
    """Return a structured release-blocker coverage report."""
    checks: list[dict[str, Any]] = []
    for coverage in REQUIRED_COVERAGE:
        missing: list[str] = []
        evidence: list[str] = []
        for evidence_file in coverage.evidence_files:
            path = ROOT / evidence_file.path
            if not path.exists():
                missing.append(f"{evidence_file.path}:missing_file")
                continue
            text = path.read_text(encoding="utf-8")
            for snippet in evidence_file.snippets:
                if snippet not in text:
                    missing.append(f"{evidence_file.path}:missing_snippet:{snippet}")
            evidence.append(evidence_file.path)
        checks.append(
            {
                "blocker_id": coverage.blocker_id,
                "summary": coverage.summary,
                "status": "passed" if not missing else "failed",
                "evidence": evidence,
                "missing": missing,
            }
        )
    failed = [check for check in checks if check["status"] != "passed"]
    return {
        "passed": not failed,
        "checks": checks,
        "coverage_count": len(checks),
        "failed_count": len(failed),
        "schema_version": "v1",
    }


def coverage_manifest() -> list[dict[str, Any]]:
    """Return the expected coverage manifest for documentation or tests."""
    return [asdict(item) for item in REQUIRED_COVERAGE]


def main() -> int:
    """CLI entrypoint."""
    import json

    result = check_release_blockers()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

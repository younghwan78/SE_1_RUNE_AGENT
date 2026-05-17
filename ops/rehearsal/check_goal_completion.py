"""Build a top-level completion audit for the active production objective."""

import argparse
import importlib.util
import json
import os
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent


OBJECTIVE = (
    "현재 구현된 상태를 상세하게 파악하고 "
    "PRODUCTION_EXECUTION_PLAN.md에 계획한대로 목표한 구현 및 검증을 완료"
)

SUCCESS_CRITERIA: tuple[dict[str, str], ...] = (
    {
        "criterion_id": "production_plan_source_of_truth",
        "description": "PRODUCTION_EXECUTION_PLAN.md is the source of truth.",
    },
    {
        "criterion_id": "first_release_scope_artifacts",
        "description": "Every first-release scope item has artifacts and verification commands.",
    },
    {
        "criterion_id": "completion_audit_coverage",
        "description": "Every first-release item is covered in the completion audit.",
    },
    {
        "criterion_id": "local_regression_gates",
        "description": "Deterministic local regression and release gates pass.",
    },
    {
        "criterion_id": "company_staging_readiness",
        "description": "Company/staging environment and manual evidence gates pass.",
    },
    {
        "criterion_id": "ci_release_gates",
        "description": "GitHub Actions release gates include the deterministic checks.",
    },
)

RELEASE_SCOPE_READINESS_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "jira_incremental_sync": ("company_jira_sandbox_rehearsal",),
    "model_gateway_prompt_registry": (
        "model_gateway_profile",
        "company_model_gateway_rehearsal",
    ),
    "llm_assisted_suggestions": ("company_model_gateway_rehearsal",),
    "sso_rbac_basic": ("trusted_proxy_auth", "trusted_proxy_rbac_rehearsal"),
}


def _load_script_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


READINESS_MODULE = _load_script_module(
    "check_production_readiness",
    SCRIPT_DIR / "check_production_readiness.py",
)
RELEASE_SCOPE_MODULE = _load_script_module(
    "validate_release_scope_artifacts",
    SCRIPT_DIR / "validate_release_scope_artifacts.py",
)
FINAL_VALIDATION_COMMANDS: tuple[str, ...] = tuple(
    _load_script_module(
        "final_validation_commands",
        SCRIPT_DIR / "final_validation_commands.py",
    ).FINAL_VALIDATION_COMMANDS
)


def build_goal_completion_audit(
    env: Mapping[str, str],
    *,
    run_local_gates: bool = False,
    manual_evidence: Any = (),
) -> dict[str, Any]:
    """Build a concrete goal-completion audit without mutating state."""
    release_scope = RELEASE_SCOPE_MODULE.build_release_scope_report()
    production_readiness = READINESS_MODULE.build_readiness_report(
        env,
        run_local_gates=run_local_gates,
        manual_evidence=manual_evidence,
    )
    release_scope_blockers = _release_scope_blockers(
        release_scope,
        production_readiness,
    )
    remaining_blockers = [
        *release_scope_blockers,
        *_production_readiness_blockers(production_readiness),
    ]
    release_scope_goal_ready = release_scope["passed"] and not release_scope_blockers
    prompt_to_artifact_checklist = _build_prompt_to_artifact_checklist(
        release_scope,
        production_readiness,
        remaining_blockers,
    )
    blocker_summary = _build_blocker_summary(remaining_blockers)
    return {
        "schema_version": "v1",
        "objective": OBJECTIVE,
        "goal_complete": (
            release_scope_goal_ready
            and production_readiness["passed"]
            and not remaining_blockers
        ),
        "summary": {
            "success_criteria_count": len(SUCCESS_CRITERIA),
            "prompt_to_artifact_checklist_count": len(prompt_to_artifact_checklist),
            "remaining_blocker_count": len(remaining_blockers),
            "release_scope_passed": release_scope["passed"],
            "release_scope_ready": release_scope["release_ready"],
            "release_scope_goal_ready": release_scope_goal_ready,
            "production_readiness_passed": production_readiness["passed"],
        },
        "blocker_summary": blocker_summary,
        "success_criteria": list(SUCCESS_CRITERIA),
        "prompt_to_artifact_checklist": prompt_to_artifact_checklist,
        "release_scope": {
            "passed": release_scope["passed"],
            "release_ready": release_scope["release_ready"],
            "goal_ready": release_scope_goal_ready,
            "summary": release_scope["summary"],
            "first_release_exclusions": release_scope["first_release_exclusions"],
        },
        "production_readiness": {
            "passed": production_readiness["passed"],
            "summary": production_readiness["summary"],
            "manual_evidence_count": production_readiness["manual_evidence_count"],
        },
        "remaining_blockers": remaining_blockers,
    }


def _build_prompt_to_artifact_checklist(
    release_scope: Mapping[str, Any],
    production_readiness: Mapping[str, Any],
    remaining_blockers: list[dict[str, str]],
) -> list[dict[str, Any]]:
    blocker_ids = {blocker["blocker_id"] for blocker in remaining_blockers}
    release_items = release_scope["items"]
    readiness_checks = production_readiness["checks"]
    readiness_by_id = {check["check_id"]: check for check in readiness_checks}
    company_check_ids = [
        check["check_id"]
        for check in readiness_checks
        if check["check_id"].startswith("company_")
    ]
    return [
        {
            "criterion_id": "production_plan_source_of_truth",
            "requirement": "Use PRODUCTION_EXECUTION_PLAN.md as the source of truth.",
            "status": "passed" if release_scope["plan_requirements"] else "failed",
            "artifacts": ["PRODUCTION_EXECUTION_PLAN.md"],
            "commands": ["uv run python ops/rehearsal/validate_release_scope_artifacts.py"],
            "evidence": [
                f"plan_requirement_count={len(release_scope['plan_requirements'])}",
                "release-scope verifier parses first-release required-scope bullets",
            ],
            "gaps": [] if release_scope["plan_requirements"] else ["plan_requirements_missing"],
        },
        {
            "criterion_id": "first_release_scope_artifacts",
            "requirement": "Map every first-release scope item to concrete artifacts and commands.",
            "status": "passed" if release_scope["passed"] else "failed",
            "artifacts": sorted(
                {
                    path
                    for item in release_items
                    for path in item.get("artifact_paths", item["evidence_paths"])
                }
            ),
            "commands": sorted(
                {
                    command
                    for item in release_items
                    for command in item["verification_commands"]
                }
            ),
            "scope_items": [
                {
                    "item_id": item["item_id"],
                    "requirement": item["requirement"],
                    "status": item["status"],
                    "audit_covered": item["audit_covered"],
                    "missing_paths": item["missing_paths"],
                    "evidence_paths": item["evidence_paths"],
                    "verification_artifact_paths": item.get(
                        "verification_artifact_paths",
                        [],
                    ),
                    "artifact_paths": item.get("artifact_paths", item["evidence_paths"]),
                    "verification_commands": item["verification_commands"],
                }
                for item in release_items
            ],
            "first_release_exclusions": release_scope["first_release_exclusions"],
            "gaps": [
                blocker_id
                for blocker_id in sorted(blocker_ids)
                if blocker_id.startswith("release_scope:")
            ],
        },
        {
            "criterion_id": "completion_audit_coverage",
            "requirement": "Cover every first-release item in the completion audit.",
            "status": (
                "passed"
                if release_scope["summary"]["audit_coverage_missing"] == 0
                else "failed"
            ),
            "artifacts": ["docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md"],
            "commands": ["uv run python ops/rehearsal/validate_release_scope_artifacts.py"],
            "evidence": [
                f"audit_coverage_missing={release_scope['summary']['audit_coverage_missing']}",
                f"item_count={release_scope['summary']['item_count']}",
            ],
            "gaps": [
                blocker_id
                for blocker_id in sorted(blocker_ids)
                if blocker_id.endswith(":audit_coverage")
            ],
        },
        {
            "criterion_id": "local_regression_gates",
            "requirement": "Run deterministic local regression and release gates.",
            "status": readiness_by_id["local_regression_gates"]["status"],
            "artifacts": _local_regression_gate_artifacts(),
            "commands": production_readiness["local_gate_commands"],
            "evidence": readiness_by_id["local_regression_gates"]["evidence"],
            "gaps": (
                []
                if readiness_by_id["local_regression_gates"]["status"] == "passed"
                else ["production_readiness:local_regression_gates"]
            ),
        },
        {
            "criterion_id": "company_staging_readiness",
            "requirement": "Pass company/staging environment and reviewed manual-evidence gates.",
            "status": "passed" if production_readiness["passed"] else "blocked",
            "artifacts": [
                ".env.example",
                "ops/rehearsal/production_readiness_evidence.example.json",
                "ops/rehearsal/build_staging_evidence_plan.py",
                "ops/rehearsal/check_production_readiness.py",
                "ops/rehearsal/check_goal_completion.py",
                "ops/rehearsal/build_handoff_bundle.py",
                "ops/rehearsal/final_validation_commands.py",
                "ops/rehearsal/validate_handoff_bundle.py",
                "ops/rehearsal/assert_local_handoff_complete.py",
                "README.md",
                "README_ubuntu.md",
                "docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md",
            ],
            "commands": [
                "uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown",
                *FINAL_VALIDATION_COMMANDS,
            ],
            "checks": [
                {
                    "check_id": check["check_id"],
                    "status": check["status"],
                    "summary": check["summary"],
                    "next_action": check.get("next_action"),
                }
                for check in readiness_checks
                if check["check_id"] in company_check_ids
                or check["status"] in {"failed", "manual_required", "warning"}
            ],
            "evidence": [
                f"manual_evidence_count={production_readiness['manual_evidence_count']}",
                f"failed={production_readiness['summary']['failed']}",
                f"manual_required={production_readiness['summary']['manual_required']}",
                f"warning={production_readiness['summary']['warning']}",
            ],
            "gaps": [
                blocker_id
                for blocker_id in sorted(blocker_ids)
                if blocker_id.startswith("production_readiness:")
            ],
        },
        {
            "criterion_id": "ci_release_gates",
            "requirement": "Keep deterministic release gates covered in GitHub Actions.",
            "status": "passed",
            "artifacts": [
                ".github/workflows/ci.yml",
                "ops/rehearsal/validate_ci_gate_coverage.py",
            ],
            "commands": ["uv run python ops/rehearsal/validate_ci_gate_coverage.py"],
            "evidence": [
                "CI workflow runs deterministic local release gates",
                "Docker-backed and company/staging gates remain explicitly documented omissions",
            ],
            "gaps": [],
        },
    ]


def _local_regression_gate_artifacts() -> list[str]:
    artifacts = {
        ".github/workflows/ci.yml",
        "ops/rehearsal/check_production_readiness.py",
    }
    for command in READINESS_MODULE.LOCAL_GATE_COMMANDS:
        artifacts.update(token for token in command if token.endswith(".py"))
    return sorted(artifacts)


def _release_scope_blockers(
    report: Mapping[str, Any],
    production_readiness: Mapping[str, Any],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    readiness_statuses = {
        check["check_id"]: check["status"] for check in production_readiness["checks"]
    }
    for item in report["items"]:
        if item["status"] != "local_complete":
            dependencies = RELEASE_SCOPE_READINESS_DEPENDENCIES.get(item["item_id"], ())
            unresolved_dependencies = [
                check_id
                for check_id in dependencies
                if readiness_statuses.get(check_id) != "passed"
            ]
            if unresolved_dependencies or not dependencies:
                blockers.append(
                    {
                        "blocker_id": f"release_scope:{item['item_id']}",
                        "status": item["status"],
                        "summary": (
                            f"{item['notes']} Required readiness checks: "
                            f"{', '.join(dependencies) or '<unmapped>'}."
                        ),
                        "next_action": (
                            "Collect company/staging evidence for this first-release item."
                        ),
                    }
                )
        for failure in item["missing_paths"]:
            blockers.append(
                {
                    "blocker_id": f"release_scope:{item['item_id']}:missing_path",
                    "status": "failed",
                    "summary": failure,
                    "next_action": "Restore the missing release-scope artifact.",
                }
            )
        if not item["audit_covered"]:
            blockers.append(
                {
                    "blocker_id": f"release_scope:{item['item_id']}:audit_coverage",
                    "status": "failed",
                    "summary": "Completion audit marker is missing.",
                    "next_action": "Update completion audit coverage for this item.",
                }
            )
    return blockers


def _production_readiness_blockers(report: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "blocker_id": f"production_readiness:{check['check_id']}",
            "status": check["status"],
            "summary": check["summary"],
            "next_action": check.get("next_action") or "Review the production readiness gate.",
        }
        for check in report["checks"]
        if check["status"] != "passed"
    ]


def _build_blocker_summary(blockers: list[dict[str, str]]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    local_action_blockers: list[str] = []
    company_or_staging_count = 0
    for blocker in blockers:
        status = blocker["status"]
        by_status[status] = by_status.get(status, 0) + 1
        blocker_id = blocker["blocker_id"]
        if _requires_company_or_staging_evidence(blocker):
            company_or_staging_count += 1
        else:
            local_action_blockers.append(blocker_id)
    return {
        "company_or_staging_evidence_required": company_or_staging_count,
        "local_action_required": len(local_action_blockers),
        "by_status": dict(sorted(by_status.items())),
        "local_action_blockers": sorted(local_action_blockers),
    }


def _requires_company_or_staging_evidence(blocker: Mapping[str, str]) -> bool:
    blocker_id = blocker["blocker_id"]
    if blocker["status"] == "company_evidence_required":
        return True
    if blocker_id.startswith("production_readiness:"):
        return blocker_id != "production_readiness:local_regression_gates"
    return False


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-local-gates",
        action="store_true",
        help="Execute local production-readiness gate commands before auditing.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Return success when the audit is structurally valid but the goal is not complete.",
    )
    parser.add_argument(
        "--evidence-file",
        type=Path,
        default=None,
        help="Optional reviewed manual-gate evidence JSON file.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional KEY=VALUE environment file for company/staging checks.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON report output path. Use '-' to print to stdout.",
    )
    args = parser.parse_args()
    env = (
        READINESS_MODULE.load_env_file(args.env_file, os.environ)
        if args.env_file
        else dict(os.environ)
    )
    manual_evidence = (
        READINESS_MODULE.load_manual_evidence(args.evidence_file)
        if args.evidence_file
        else []
    )
    report = build_goal_completion_audit(
        env,
        run_local_gates=args.run_local_gates,
        manual_evidence=manual_evidence,
    )
    if args.output:
        READINESS_MODULE.write_json_output(report, args.output)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["goal_complete"] or args.allow_incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())

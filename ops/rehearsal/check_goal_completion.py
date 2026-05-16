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


def build_goal_completion_audit(
    env: Mapping[str, str],
    *,
    run_local_gates: bool = False,
) -> dict[str, Any]:
    """Build a concrete goal-completion audit without mutating state."""
    release_scope = RELEASE_SCOPE_MODULE.build_release_scope_report()
    production_readiness = READINESS_MODULE.build_readiness_report(
        env,
        run_local_gates=run_local_gates,
    )
    remaining_blockers = [
        *_release_scope_blockers(release_scope),
        *_production_readiness_blockers(production_readiness),
    ]
    return {
        "schema_version": "v1",
        "objective": OBJECTIVE,
        "goal_complete": (
            release_scope["release_ready"]
            and production_readiness["passed"]
            and not remaining_blockers
        ),
        "summary": {
            "success_criteria_count": len(SUCCESS_CRITERIA),
            "remaining_blocker_count": len(remaining_blockers),
            "release_scope_passed": release_scope["passed"],
            "release_scope_ready": release_scope["release_ready"],
            "production_readiness_passed": production_readiness["passed"],
        },
        "success_criteria": list(SUCCESS_CRITERIA),
        "release_scope": {
            "passed": release_scope["passed"],
            "release_ready": release_scope["release_ready"],
            "summary": release_scope["summary"],
        },
        "production_readiness": {
            "passed": production_readiness["passed"],
            "summary": production_readiness["summary"],
        },
        "remaining_blockers": remaining_blockers,
    }


def _release_scope_blockers(report: Mapping[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for item in report["items"]:
        if item["status"] != "local_complete":
            blockers.append(
                {
                    "blocker_id": f"release_scope:{item['item_id']}",
                    "status": item["status"],
                    "summary": item["notes"],
                    "next_action": "Collect company/staging evidence for this first-release item.",
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
    args = parser.parse_args()
    report = build_goal_completion_audit(dict(os.environ), run_local_gates=args.run_local_gates)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["goal_complete"] or args.allow_incomplete else 1


if __name__ == "__main__":
    raise SystemExit(main())

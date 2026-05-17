"""Validate a generated production handoff bundle."""

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EXPECTED_ARTIFACTS = {
    "goal-completion-report.json",
    "manual-evidence-template.json",
    "production-readiness-report.json",
    "staging-evidence-plan.md",
}

EXPECTED_STAGING_PLAN_SNIPPETS = (
    "ops/rehearsal/check_production_readiness.py",
    "ops/rehearsal/check_goal_completion.py",
    "ops/rehearsal/build_handoff_bundle.py",
    "ops/rehearsal/validate_handoff_bundle.py",
)


def validate_handoff_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Return a structured validation report for a handoff bundle directory."""
    failures: list[str] = []
    manifest_path = bundle_dir / "manifest.json"
    manifest = _load_json(manifest_path, failures, "manifest")
    if not manifest:
        return _report(bundle_dir, failures, artifact_count=0)

    if manifest.get("schema_version") != "v1":
        failures.append("manifest_schema_version_not_v1")

    declared_artifacts = set(_string_list(manifest.get("artifacts")))
    missing_declarations = EXPECTED_ARTIFACTS - declared_artifacts
    extra_declarations = declared_artifacts - EXPECTED_ARTIFACTS
    failures.extend(
        f"missing_manifest_artifact:{artifact}" for artifact in sorted(missing_declarations)
    )
    failures.extend(
        f"unexpected_manifest_artifact:{artifact}" for artifact in sorted(extra_declarations)
    )

    for artifact in sorted(EXPECTED_ARTIFACTS):
        artifact_path = bundle_dir / artifact
        if not artifact_path.exists():
            failures.append(f"missing_artifact:{artifact}")
            continue
        if artifact_path.stat().st_size == 0:
            failures.append(f"empty_artifact:{artifact}")

    readiness_report = _load_json(
        bundle_dir / "production-readiness-report.json",
        failures,
        "production-readiness-report",
    )
    goal_report = _load_json(
        bundle_dir / "goal-completion-report.json",
        failures,
        "goal-completion-report",
    )
    manual_template = _load_json(
        bundle_dir / "manual-evidence-template.json",
        failures,
        "manual-evidence-template",
    )

    if readiness_report:
        _validate_schema(readiness_report, "production-readiness-report", failures)
        if readiness_report.get("passed") != manifest.get("readiness_passed"):
            failures.append("readiness_passed_mismatch")
        if readiness_report.get("summary") != manifest.get("readiness_summary"):
            failures.append("readiness_summary_mismatch")
    if goal_report:
        _validate_schema(goal_report, "goal-completion-report", failures)
        if goal_report.get("goal_complete") != manifest.get("goal_complete"):
            failures.append("goal_complete_mismatch")
        if goal_report.get("summary") != manifest.get("goal_summary"):
            failures.append("goal_summary_mismatch")
        _validate_manifest_blockers(goal_report, manifest, failures)
    if manual_template:
        _validate_schema(manual_template, "manual-evidence-template", failures)
    if readiness_report and manual_template:
        _validate_manual_template_coverage(readiness_report, manual_template, failures)

    staging_plan_path = bundle_dir / "staging-evidence-plan.md"
    if staging_plan_path.exists():
        content = staging_plan_path.read_text(encoding="utf-8")
        if "# Staging Evidence Collection Plan" not in content:
            failures.append("staging_evidence_plan_heading_missing")
        for snippet in EXPECTED_STAGING_PLAN_SNIPPETS:
            if snippet not in content:
                failures.append(f"staging_evidence_plan_missing:{snippet}")
        if "## Final Validation" not in content:
            failures.append("staging_evidence_plan_final_validation_missing")

    return _report(bundle_dir, failures, artifact_count=len(EXPECTED_ARTIFACTS))


def _load_json(path: Path, failures: list[str], label: str) -> dict[str, Any] | None:
    if not path.exists():
        failures.append(f"missing_json:{label}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        failures.append(f"invalid_json:{label}")
        return None
    if not isinstance(payload, dict):
        failures.append(f"json_not_object:{label}")
        return None
    return payload


def _validate_schema(payload: Mapping[str, Any], label: str, failures: list[str]) -> None:
    if payload.get("schema_version") != "v1":
        failures.append(f"schema_version_not_v1:{label}")


def _validate_manual_template_coverage(
    readiness_report: Mapping[str, Any],
    manual_template: Mapping[str, Any],
    failures: list[str],
) -> None:
    expected_gate_ids = {
        str(check["check_id"])
        for check in _object_list(readiness_report.get("checks"))
        if check.get("status") == "manual_required" and isinstance(check.get("check_id"), str)
    }
    template_gate_ids = {
        str(check["check_id"])
        for check in _object_list(manual_template.get("checks"))
        if isinstance(check.get("check_id"), str)
    }
    for check_id in sorted(expected_gate_ids - template_gate_ids):
        failures.append(f"manual_template_missing_gate:{check_id}")
    for check_id in sorted(template_gate_ids - expected_gate_ids):
        failures.append(f"manual_template_unexpected_gate:{check_id}")


def _validate_manifest_blockers(
    goal_report: Mapping[str, Any],
    manifest: Mapping[str, Any],
    failures: list[str],
) -> None:
    expected_count = _summary_remaining_blocker_count(goal_report)
    if manifest.get("remaining_blocker_count") != expected_count:
        failures.append("remaining_blocker_count_mismatch")
    if _manifest_blocker_fingerprint(manifest.get("remaining_blockers")) != (
        _manifest_blocker_fingerprint(goal_report.get("remaining_blockers"))
    ):
        failures.append("remaining_blockers_mismatch")


def _summary_remaining_blocker_count(goal_report: Mapping[str, Any]) -> int | None:
    summary = goal_report.get("summary")
    if not isinstance(summary, Mapping):
        return None
    value = summary.get("remaining_blocker_count")
    return value if isinstance(value, int) else None


def _manifest_blocker_fingerprint(value: object) -> list[tuple[str, str, str]]:
    return sorted(
        (
            str(item["blocker_id"]),
            str(item["status"]),
            str(item["next_action"]),
        )
        for item in _object_list(value)
        if isinstance(item.get("blocker_id"), str)
        and isinstance(item.get("status"), str)
        and isinstance(item.get("next_action"), str)
    )


def _object_list(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _report(bundle_dir: Path, failures: list[str], *, artifact_count: int) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "bundle_dir": str(bundle_dir),
        "artifact_count": artifact_count,
        "failures": failures,
        "summary": {
            "failed": len(failures),
            "passed": 1 if not failures else 0,
        },
        "passed": not failures,
    }


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_dir", type=Path)
    args = parser.parse_args()
    report = validate_handoff_bundle(args.bundle_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

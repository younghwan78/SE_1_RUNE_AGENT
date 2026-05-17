"""Validate a generated production handoff bundle."""

import argparse
import hashlib
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent

EXPECTED_ARTIFACTS = {
    "goal-completion-report.json",
    "manual-evidence-template.json",
    "production-readiness-report.json",
    "staging-evidence-plan.md",
}


def _load_script_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPECTED_STAGING_PLAN_SNIPPETS = tuple(
    _load_script_module(
        "final_validation_commands",
        SCRIPT_DIR / "final_validation_commands.py",
    ).FINAL_VALIDATION_COMMANDS
)


def validate_handoff_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Return a structured validation report for a handoff bundle directory."""
    failures: list[str] = []
    manifest_path = bundle_dir / "manifest.json"
    manifest = _load_json(manifest_path, failures, "manifest")
    if not manifest:
        return _report(
            bundle_dir,
            failures,
            artifact_count=0,
            manifest_summary={},
        )

    if manifest.get("schema_version") != "v1":
        failures.append("manifest_schema_version_not_v1")

    declared_artifacts = set(_string_list(manifest.get("artifacts")))
    artifact_hashes = _string_mapping(manifest.get("artifact_hashes"))
    missing_declarations = EXPECTED_ARTIFACTS - declared_artifacts
    extra_declarations = declared_artifacts - EXPECTED_ARTIFACTS
    failures.extend(
        f"missing_manifest_artifact:{artifact}" for artifact in sorted(missing_declarations)
    )
    failures.extend(
        f"unexpected_manifest_artifact:{artifact}" for artifact in sorted(extra_declarations)
    )
    for artifact in sorted(EXPECTED_ARTIFACTS - set(artifact_hashes)):
        failures.append(f"missing_artifact_hash:{artifact}")
    for artifact in sorted(set(artifact_hashes) - EXPECTED_ARTIFACTS):
        failures.append(f"unexpected_artifact_hash:{artifact}")

    for artifact in sorted(EXPECTED_ARTIFACTS):
        artifact_path = bundle_dir / artifact
        if not artifact_path.exists():
            failures.append(f"missing_artifact:{artifact}")
            continue
        if artifact_path.stat().st_size == 0:
            failures.append(f"empty_artifact:{artifact}")
        expected_hash = artifact_hashes.get(artifact)
        if expected_hash and _sha256_file(artifact_path) != expected_hash:
            failures.append(f"artifact_hash_mismatch:{artifact}")

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
        _validate_manifest_missing_env(content, manifest, failures)

    return _report(
        bundle_dir,
        failures,
        artifact_count=len(EXPECTED_ARTIFACTS),
        manifest_summary=_manifest_summary(manifest),
    )


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
    if manifest.get("blocker_summary") != goal_report.get("blocker_summary"):
        failures.append("blocker_summary_mismatch")
    if _manifest_blocker_fingerprint(manifest.get("remaining_blockers")) != (
        _manifest_blocker_fingerprint(goal_report.get("remaining_blockers"))
    ):
        failures.append("remaining_blockers_mismatch")


def _validate_manifest_missing_env(
    staging_plan_markdown: str,
    manifest: Mapping[str, Any],
    failures: list[str],
) -> None:
    expected = _missing_env_from_staging_plan(staging_plan_markdown)
    if _string_list(manifest.get("missing_env")) != expected:
        failures.append("missing_env_mismatch")
    if manifest.get("missing_env_count") != len(expected):
        failures.append("missing_env_count_mismatch")


def _missing_env_from_staging_plan(content: str) -> list[str]:
    missing: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- Missing env:"):
            continue
        value = stripped.removeprefix("- Missing env:").strip()
        if value == "`none`":
            continue
        for token in value.split(","):
            normalized = token.strip().strip("`")
            if normalized:
                missing.add(normalized)
    return sorted(missing)


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


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {
        key: item
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, str)
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "goal_complete": manifest.get("goal_complete"),
        "remaining_blocker_count": manifest.get("remaining_blocker_count"),
        "blocker_summary": manifest.get("blocker_summary"),
        "missing_env_count": manifest.get("missing_env_count"),
        "missing_env": manifest.get("missing_env"),
    }


def _report(
    bundle_dir: Path,
    failures: list[str],
    *,
    artifact_count: int,
    manifest_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "bundle_dir": str(bundle_dir),
        "artifact_count": artifact_count,
        "goal_complete": manifest_summary.get("goal_complete"),
        "remaining_blocker_count": manifest_summary.get("remaining_blocker_count"),
        "blocker_summary": manifest_summary.get("blocker_summary"),
        "missing_env_count": manifest_summary.get("missing_env_count"),
        "missing_env": manifest_summary.get("missing_env"),
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

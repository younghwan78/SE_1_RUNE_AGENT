"""Assert that a handoff bundle has no workstation-local blockers left."""

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def assert_local_handoff_complete(bundle_dir: Path) -> dict[str, Any]:
    """Validate that the bundle's remaining blockers are external to local work."""
    failures: list[str] = []
    manifest = _load_manifest(bundle_dir, failures)
    blocker_summary = _mapping(manifest.get("blocker_summary"))
    remaining_blocker_count = manifest.get("remaining_blocker_count")
    local_action_required = blocker_summary.get("local_action_required")
    company_required = blocker_summary.get("company_or_staging_evidence_required")
    local_action_blockers = _string_list(blocker_summary.get("local_action_blockers"))
    missing_env = _string_list(manifest.get("missing_env"))
    missing_env_count = manifest.get("missing_env_count")

    if local_action_required != 0:
        failures.append(f"local_action_required:{local_action_required}")
    if local_action_blockers:
        failures.append(
            "local_action_blockers_present:" + ",".join(sorted(local_action_blockers))
        )
    if isinstance(remaining_blocker_count, int) and isinstance(company_required, int):
        if remaining_blocker_count != company_required + int(local_action_required or 0):
            failures.append("remaining_blocker_count_mismatch")
    else:
        failures.append("remaining_blocker_count_or_company_required_missing")

    return {
        "schema_version": "v1",
        "bundle_dir": str(bundle_dir),
        "goal_complete": manifest.get("goal_complete"),
        "remaining_blocker_count": remaining_blocker_count,
        "missing_env_count": missing_env_count,
        "missing_env": missing_env,
        "blocker_summary": blocker_summary,
        "failures": failures,
        "passed": not failures,
    }


def _load_manifest(bundle_dir: Path, failures: list[str]) -> dict[str, Any]:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        failures.append("manifest_missing")
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        failures.append("manifest_invalid_json")
        return {}
    if not isinstance(payload, dict):
        failures.append("manifest_not_object")
        return {}
    if payload.get("schema_version") != "v1":
        failures.append("manifest_schema_version_not_v1")
    return payload


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_dir", type=Path)
    args = parser.parse_args()
    report = assert_local_handoff_complete(args.bundle_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

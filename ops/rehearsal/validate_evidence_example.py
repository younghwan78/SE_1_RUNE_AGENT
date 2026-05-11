"""Validate that the committed readiness evidence example cannot pass release gates."""

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "ops/rehearsal/production_readiness_evidence.example.json"
FAKE_RUN_PATTERN = re.compile(r"\brun-123\d+\b")


def validate_example(path: Path = EXAMPLE_PATH) -> dict[str, Any]:
    """Return a structured validation report for the committed example file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    checks = payload.get("checks", [])
    failures: list[str] = []
    if payload.get("schema_version") != "v1":
        failures.append("schema_version_not_v1")
    for field_name in ("reviewed_by", "reviewed_at"):
        value = payload.get(field_name)
        if not isinstance(value, str) or "TODO:" not in value:
            failures.append(f"{field_name}:missing_todo_placeholder")
    if not isinstance(checks, list) or not checks:
        failures.append("checks_missing_or_empty")
        checks = []
    seen_check_ids: set[str] = set()
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            failures.append(f"checks[{index}]:not_object")
            continue
        check_id = item.get("check_id", f"index_{index}")
        status = item.get("status")
        summary = str(item.get("summary", ""))
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            failures.append(f"{check_id}:evidence_missing_or_empty")
            evidence_values: list[Any] = []
        else:
            evidence_values = evidence
            if not all(isinstance(value, str) and value.strip() for value in evidence):
                failures.append(f"{check_id}:evidence_must_be_non_empty_strings")
        joined = "\n".join([summary, *[str(value) for value in evidence_values]])
        if not isinstance(check_id, str) or not check_id:
            failures.append(f"checks[{index}]:missing_check_id")
            check_id = f"index_{index}"
        if check_id in seen_check_ids:
            failures.append(f"{check_id}:duplicate_check_id")
        seen_check_ids.add(check_id)
        if status != "failed":
            failures.append(f"{check_id}:status_not_failed")
        if status == "passed":
            failures.append(f"{check_id}:status_passed")
        if "TODO:" not in joined:
            failures.append(f"{check_id}:missing_todo_placeholder")
        if FAKE_RUN_PATTERN.search(joined):
            failures.append(f"{check_id}:fake_run_id")
    return {
        "check_count": len(checks),
        "example_path": _display_path(path),
        "failures": failures,
        "passed": not failures,
        "schema_version": "v1",
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    """CLI entrypoint."""
    report = validate_example()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

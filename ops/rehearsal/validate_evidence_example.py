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
    if not isinstance(checks, list) or not checks:
        failures.append("checks_missing_or_empty")
        checks = []
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            failures.append(f"checks[{index}]:not_object")
            continue
        check_id = item.get("check_id", f"index_{index}")
        status = item.get("status")
        summary = str(item.get("summary", ""))
        evidence = item.get("evidence", [])
        evidence_values = evidence if isinstance(evidence, list) else []
        joined = "\n".join([summary, *[str(value) for value in evidence_values]])
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

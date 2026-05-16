"""Validate that GitHub Actions covers the deterministic local release gates."""

from __future__ import annotations

import importlib.util
import json
import re
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github/workflows/ci.yml"
CHECKER_PATH = ROOT / "ops/rehearsal/check_production_readiness.py"

ALLOWED_CI_OMISSIONS = {
    "uv run python ops/integration/run_backend_integration.py",
    "uv run python ops/rehearsal/run_full_stack_rehearsal.py",
}

REQUIRED_CI_EXTRA_COMMANDS = {
    "uv run python ops/rehearsal/check_production_readiness.py --write-evidence-template -",
    "uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown",
}


def validate_ci_gate_coverage(
    workflow_path: Path = WORKFLOW_PATH,
    local_gate_commands: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return a structured report for CI gate coverage."""
    local_commands = (
        list(local_gate_commands)
        if local_gate_commands is not None
        else [" ".join(command) for command in _load_local_gate_commands()]
    )
    workflow_commands = _parse_run_commands(workflow_path)
    expected_commands = [
        command for command in local_commands if command not in ALLOWED_CI_OMISSIONS
    ]
    missing_required = sorted(
        command
        for command in [*expected_commands, *REQUIRED_CI_EXTRA_COMMANDS]
        if command not in workflow_commands
    )
    unexpected_omissions = sorted(
        command
        for command in local_commands
        if command not in workflow_commands and command not in ALLOWED_CI_OMISSIONS
    )
    return {
        "allowed_omissions": sorted(ALLOWED_CI_OMISSIONS),
        "ci_command_count": len(workflow_commands),
        "missing_required": missing_required,
        "passed": not missing_required and not unexpected_omissions,
        "schema_version": "v1",
        "unexpected_omissions": unexpected_omissions,
        "workflow_path": _display_path(workflow_path),
    }


def _parse_run_commands(path: Path) -> set[str]:
    commands: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*run:\s*(.+?)\s*$", line)
        if match:
            commands.add(match.group(1).strip("\"'"))
    return commands


def _load_local_gate_commands() -> tuple[tuple[str, ...], ...]:
    spec = importlib.util.spec_from_file_location("check_production_readiness", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load readiness checker from {_display_path(CHECKER_PATH)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(tuple[tuple[str, ...], ...], _require_attr(module, "LOCAL_GATE_COMMANDS"))


def _require_attr(module: ModuleType, name: str) -> Any:
    value = getattr(module, name, None)
    if value is None:
        raise RuntimeError(f"readiness checker is missing {name}")
    return value


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    """CLI entrypoint."""
    report = validate_ci_gate_coverage()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

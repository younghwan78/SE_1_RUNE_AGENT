"""Tests for Claude Code provider smoke script."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_claude_code_provider_smoke_dry_run_reports_command_and_profile() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/model_gateway/smoke_claude_code_provider.py",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "skipped"
    assert payload["mode"] == "dry_run"
    assert payload["model_profile_id"] == "claude-code-local"
    assert payload["prompt_version_id"] == "pv_soc_slice_planning_v1"
    assert payload["command"][0] in {"claude", "claude-code"}

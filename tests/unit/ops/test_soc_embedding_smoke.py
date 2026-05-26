"""Smoke tests for optional SoC local embedding model loading."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_soc_embedding_smoke_dry_run_reports_model_without_loading() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/smoke_soc_embedding_model.py",
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
    assert payload["model_name"] == "BAAI/bge-m3"
    assert payload["expected_dimensions"] == 1024

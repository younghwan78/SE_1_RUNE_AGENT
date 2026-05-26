"""Tests for SoC cross-encoder reranker smoke script."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_soc_cross_encoder_smoke_dry_run_reports_model_without_loading() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/smoke_soc_cross_encoder_reranker.py",
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
    assert payload["model_name"] == "BAAI/bge-reranker-v2-m3"
    assert payload["reason"] == "pass --live to load and score with the cross-encoder"

"""Tests for the SoC eval-run diff report CLI."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def test_soc_eval_diff_reports_no_regression_for_current_scale_baseline() -> None:
    module = _load_diff_module()

    payload = module.run_soc_eval_diff(coverage_mode="scale")

    assert payload["status"] == "passed"
    assert payload["coverage_mode"] == "scale"
    assert payload["regression_delta"] == 0
    assert payload["regressed_metrics"] == []


def test_soc_eval_diff_cli_reports_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/diff_soc_eval_runs.py",
            "--coverage-mode",
            "scale",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "passed"
    assert payload["coverage_mode"] == "scale"
    assert payload["baseline_run_id"] == "soc_eval_scale_baseline"
    assert payload["candidate_run_id"] == "soc_eval_scale_candidate"


def _load_diff_module() -> ModuleType:
    module_path = ROOT / "ops/evals/diff_soc_eval_runs.py"
    spec = importlib.util.spec_from_file_location(
        "diff_soc_eval_runs",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

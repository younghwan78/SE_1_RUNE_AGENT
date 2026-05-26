"""Tests for the SoC eval persistence rehearsal."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def test_soc_eval_persistence_rehearsal_persists_and_reloads_scale_report() -> None:
    module = _load_rehearsal()

    report = module.run_soc_eval_persistence_rehearsal(coverage_mode="scale")

    assert report["status"] == "passed"
    assert report["coverage_mode"] == "scale"
    assert report["persisted"]["collection"] == "soc_eval_runs"
    assert report["persisted"]["record"]["coverage_mode"] == "scale"
    assert report["persisted"]["record"]["metrics"]["counts"]["queries"] >= 30
    assert report["reloaded"]["run_id"] == report["persisted"]["record"]["run_id"]


def test_soc_eval_persistence_rehearsal_cli_reports_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/run_soc_eval_persistence_rehearsal.py",
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
    assert payload["persisted"]["collection"] == "soc_eval_runs"


def _load_rehearsal() -> ModuleType:
    module_path = ROOT / "ops/evals/run_soc_eval_persistence_rehearsal.py"
    spec = importlib.util.spec_from_file_location(
        "run_soc_eval_persistence_rehearsal",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

"""Tests for the SoC fixture ingestion idempotency rehearsal."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def test_soc_ingestion_idempotency_check_reports_scale_stability() -> None:
    module = _load_rehearsal()

    payload = module.run_soc_ingestion_idempotency_check(coverage_mode="scale")

    assert payload["status"] == "passed"
    assert payload["coverage_mode"] == "scale"
    assert payload["fingerprint_match"] is True
    assert payload["duplicate_candidate_count"] == 0
    assert payload["first"]["counts"]["artifacts"] == 400
    assert payload["second"]["counts"]["artifacts"] == 400


def test_soc_ingestion_idempotency_check_cli_reports_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/rehearsal/run_soc_ingestion_idempotency_check.py",
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
    assert payload["fingerprint_match"] is True
    assert payload["duplicate_candidate_count"] == 0


def _load_rehearsal() -> ModuleType:
    module_path = ROOT / "ops/rehearsal/run_soc_ingestion_idempotency_check.py"
    spec = importlib.util.spec_from_file_location(
        "run_soc_ingestion_idempotency_check",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

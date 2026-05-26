"""Stage F checks for SoC query eval comparison and diagnostics."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_soc_compare_cli_reports_seed_eval_and_no_regressions() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/compare_soc_answer.py",
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
    assert payload["counts"]["queries"] >= 20
    assert payload["recall"] >= 0.85
    assert payload["source_accuracy"] >= 0.95
    assert payload["regression_count"] == 0
    assert payload["diagnostics"]["failed_cases"] == 0


def test_soc_compare_cli_reports_scale_eval_and_no_regressions() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/compare_soc_answer.py",
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
    assert payload["full_stage_f_ready"] is True
    assert payload["counts"]["artifacts"] == 400
    assert payload["counts"]["queries"] >= 30
    assert payload["recall"] >= 0.85
    assert payload["source_accuracy"] >= 0.95
    assert payload["regression_count"] == 0


def test_soc_diagnostics_cli_reports_failure_layers() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/diagnose_soc_failures.py",
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
    assert payload["diagnostics"]["by_layer"] == {}
    assert payload["recommendations"] == []


def test_stage_f_acceptance_yaml_tracks_eval_loop_gap_items() -> None:
    payload = yaml.safe_load((ROOT / "eval/stages/F.yaml").read_text(encoding="utf-8"))

    assert payload["stage"] == "F"
    assert {"F1", "F2", "F3", "F4", "F5", "F6", "F7"} == {
        item["id"] for item in payload["subgoals"]
    }
    assert "ops/evals/run_soc_query_eval.py --format json" in str(payload)
    assert "ops/evals/compare_soc_answer.py --format json" in str(payload)
    assert "ops/evals/compare_soc_answer.py --coverage-mode scale --format json" in str(
        payload
    )
    assert "ops/evals/diagnose_soc_failures.py --format json" in str(payload)
    assert "ops/fixtures/validate_soc_fixtures.py --coverage-mode scale --format json" in str(
        payload
    )
    assert "ops/evals/run_soc_storage_backed_query_eval.py" in str(payload)
    assert "ACC-F-LIVE-01" in str(payload)
    assert "ops/evals/run_soc_eval_persistence_rehearsal.py" in str(payload)
    assert "ACC-F-SEED-05" in str(payload)
    assert "ops/evals/diff_soc_eval_runs.py" in str(payload)
    assert "ACC-F-SEED-06" in str(payload)

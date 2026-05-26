"""Tests for the SoC fixture ingestion workflow rehearsal CLI."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def test_soc_fixture_ingestion_workflow_rehearsal_reports_scale_counts() -> None:
    module = _load_rehearsal()

    payload = module.run_soc_fixture_ingestion_workflow(coverage_mode="scale")

    assert payload["status"] == "passed"
    assert payload["coverage_mode"] == "scale"
    assert payload["counts"]["artifacts"] == 400
    assert payload["counts"]["events"] == 400
    assert payload["counts"]["relations"] > 0
    assert payload["stage_names"] == [
        "soc_fixture_source_snapshot",
        "soc_axis_classification",
        "soc_entity_extraction",
        "soc_lifecycle_events",
        "soc_storage_projection",
    ]


def test_soc_fixture_ingestion_workflow_cli_reports_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/rehearsal/run_soc_fixture_ingestion_workflow.py",
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
    assert payload["counts"]["artifacts"] == 400
    assert payload["storage_projection"]["semantic_relations"] == payload["counts"]["relations"]


def _load_rehearsal() -> ModuleType:
    module_path = ROOT / "ops/rehearsal/run_soc_fixture_ingestion_workflow.py"
    spec = importlib.util.spec_from_file_location(
        "run_soc_fixture_ingestion_workflow",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

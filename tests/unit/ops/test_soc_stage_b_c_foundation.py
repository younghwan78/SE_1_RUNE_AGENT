"""Stage B/C checks for SoC Knowledge seed fixture and classifier foundations."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_soc_fixture_validator_cli_reports_seed_fixture_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/fixtures/validate_soc_fixtures.py",
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
    assert payload["counts"]["artifacts"] == 40
    assert payload["counts"]["jira"] == 20
    assert payload["counts"]["confluence"] == 10
    assert payload["counts"]["email"] == 10
    assert payload["counts"]["queries"] >= 20
    assert payload["classification_recall"] >= 0.85
    assert set(payload["slice_patterns"]) >= {
        "concern_slice",
        "topic_intersection",
        "timeline_slice",
        "lifecycle_trace",
        "unknown",
    }


def test_soc_fixture_validator_cli_reports_scale_fixture_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/fixtures/validate_soc_fixtures.py",
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
    assert payload["counts"]["jira"] == 200
    assert payload["counts"]["confluence"] == 100
    assert payload["counts"]["email"] == 100
    assert payload["classification_recall"] >= 0.85


def test_stage_b_and_c_acceptance_yaml_track_fixture_and_classifier_gap_items() -> None:
    stage_b = yaml.safe_load((ROOT / "eval/stages/B.yaml").read_text(encoding="utf-8"))
    stage_c = yaml.safe_load((ROOT / "eval/stages/C.yaml").read_text(encoding="utf-8"))

    assert stage_b["stage"] == "B"
    assert stage_c["stage"] == "C"
    assert {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"} == {
        item["id"] for item in stage_b["subgoals"]
    }
    assert {"C1", "C2", "C3", "C4", "C5"} <= {
        item["id"] for item in stage_c["subgoals"]
    }
    assert "fixtures/soc_knowledge/artifacts.yaml" in str(stage_b)
    assert "fixtures/soc_knowledge/scale_artifacts.yaml" in str(stage_b)
    assert "ops/fixtures/generate_soc_scale_fixture.py" in str(stage_b)
    assert "coverage-mode scale" in str(stage_b)
    assert "20-30 queries" in str(stage_b)
    assert "src/req_tracker/ingestion/soc_classification.py" in str(stage_c)
    assert "GatewaySocAxisClassifier" in str(stage_c)
    assert "ops/evals/run_soc_classifier_enrichment_gate.py" in str(stage_c)
    assert "pv_soc_axis_classification_v1" in str(stage_c)
    assert "src/req_tracker/ingestion/soc_entity_extraction.py" in str(stage_c)
    c8 = next(item for item in stage_c["subgoals"] if item["id"] == "C8")
    c9 = next(item for item in stage_c["subgoals"] if item["id"] == "C9")
    assert c8["status"] == "implemented_seed"
    assert c9["status"] == "implemented_seed"
    assert "LocalSentenceTransformerEmbedder" in str(stage_c)
    assert "SocPostgresFixtureLoader" in str(stage_c)
    assert "SocAgeGraphLoader" in str(stage_c)
    assert "src/req_tracker/workflows/soc_knowledge.py" in str(stage_c)
    assert "ops/rehearsal/run_soc_fixture_ingestion_workflow.py" in str(stage_c)
    assert "MENTIONS" in str(stage_c)
    assert "AUTHORED_BY" in str(stage_c)
    assert "ACC-C-SEED-03" in str(stage_c)
    assert "ACC-C-SEED-04" in str(stage_c)
    assert "ACC-C-SEED-06" in str(stage_c)
    assert "ACC-C-LIVE-07" in str(stage_c)
    assert "run_soc_ingestion_idempotency_check.py" in str(stage_c)
    assert "ops/fixtures/validate_soc_fixtures.py --format json" in str(stage_b)

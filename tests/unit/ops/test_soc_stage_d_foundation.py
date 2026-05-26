"""Stage D checks for deterministic SoC query baseline."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_soc_query_eval_cli_reports_seed_query_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/run_soc_query_eval.py",
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
    assert payload["counts"]["queries"] >= 8
    assert payload["recall"] >= 0.75
    assert payload["source_accuracy"] >= 0.95
    assert payload["schema_pass_rate"] == 1.0
    assert payload["graceful_unknown_pass_rate"] == 1.0


def test_stage_d_acceptance_yaml_tracks_query_gap_items() -> None:
    payload = yaml.safe_load((ROOT / "eval/stages/D.yaml").read_text(encoding="utf-8"))

    assert payload["stage"] == "D"
    assert {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11"} == {
        item["id"] for item in payload["subgoals"]
    }
    assert "src/req_tracker/query/soc_service.py" in str(payload)
    assert "src/req_tracker/query/soc_planner.py" in str(payload)
    assert "src/req_tracker/query/soc_orchestration.py" in str(payload)
    assert "src/req_tracker/query/reranking.py" in str(payload)
    assert "CrossEncoderSocReranker" in str(payload)
    assert "src/req_tracker/query/retrieval.py" in str(payload)
    assert "src/req_tracker/query/postgres_keyword_backend.py" in str(payload)
    assert "src/req_tracker/vector/pgvector_backend.py" in str(payload)
    assert "src/req_tracker/graph/postgres_age_backend.py" in str(payload)
    assert "src/req_tracker/query/soc_runtime.py" in str(payload)
    assert "tests/unit/query/test_soc_query_planner.py" in str(payload)
    assert "tests/unit/query/test_soc_orchestration.py" in str(payload)
    assert "tests/unit/query/test_soc_reranking.py" in str(payload)
    assert "tests/unit/ops/test_soc_cross_encoder_smoke.py" in str(payload)
    assert "ops/evals/run_soc_local_model_quality_gate.py" in str(payload)
    assert "ops/evals/run_soc_claude_quality_gate.py" in str(payload)
    assert "tests/unit/ops/test_soc_local_model_quality_gate.py" in str(payload)
    assert "tests/unit/ops/test_soc_claude_quality_gate.py" in str(payload)
    assert "tests/unit/query/test_soc_runtime_planner.py" in str(payload)
    assert "tests/unit/query/test_soc_query_service.py" in str(payload)
    assert "src/req_tracker/debug/models.py" in str(payload)
    assert "src/req_tracker/api/routes/soc_query.py" in str(payload)
    assert "ops/evals/run_soc_query_eval.py --format json" in str(payload)
    assert "tests/unit/query/test_soc_storage_retrieval.py" in str(payload)
    assert "ops/rehearsal/validate_soc_postgres_profile.py" in str(payload)
    assert "ops/rehearsal/validate_soc_live_postgres.py" in str(payload)
    assert "src/req_tracker/storage/soc_postgres_loader.py" in str(payload)
    assert "tests/unit/storage/test_soc_postgres_loader.py" in str(payload)
    assert "soc_event_log" in str(payload)
    assert "lifecycle events" in str(payload)
    assert "src/req_tracker/graph/soc_age_loader.py" in str(payload)
    assert "tests/unit/graph/test_soc_age_loader.py" in str(payload)
    assert "ops/rehearsal/run_soc_live_storage_rehearsal.py" in str(payload)
    assert "ACC-D-SEED-11" in str(payload)
    assert "ACC-D-SEED-12" in str(payload)
    assert "ACC-D-SEED-13" in str(payload)
    assert "ACC-D-SEED-14" in str(payload)
    assert "ACC-D-LIVE-15" in str(payload)
    assert "ACC-D-LIVE-16" in str(payload)
    assert "ACC-D-LIVE-17" in str(payload)
    assert "ops/evals/run_soc_storage_backed_query_eval.py" in str(payload)
    assert "ACC-D-LIVE-18" in str(payload)
    assert "age_graph_load.counts.semantic_relations > 0" in str(payload)

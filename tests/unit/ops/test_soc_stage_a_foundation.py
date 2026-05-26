"""Stage A foundation checks for the SoC Knowledge PoC."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_soc_schema_validator_cli_reports_packaged_schema_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/ontology/validate_soc_schema.py",
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
    assert payload["schema_version"] == "soc-v0.1"
    assert payload["counts"]["entities"] >= 13
    assert payload["counts"]["relations"] >= 16
    assert payload["counts"]["concerns"] >= 8
    assert payload["counts"]["components"] >= 20


def test_stage_a_acceptance_yaml_tracks_soc_foundation_gap_items() -> None:
    payload = yaml.safe_load((ROOT / "eval/stages/A.yaml").read_text(encoding="utf-8"))
    payload_text = str(payload)

    assert payload["stage"] == "A"
    assert payload["name"] == "Foundation"
    assert {item["id"] for item in payload["subgoals"]} == {
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
        "A7",
        "A8",
        "A9",
        "A10",
        "A11",
    }
    assert {
        "ACC-A-01",
        "ACC-A-02",
        "ACC-A-03",
        "ACC-A-04",
    } <= {item["id"] for item in payload["acceptance"]}
    assert "docs/ontology/soc/schema/v0.1/entities.yaml" in payload_text
    assert "ops/ontology/validate_soc_schema.py --format json" in payload_text
    assert "src/req_tracker/model_gateway/claude_code_provider.py" in payload_text
    assert "ops/model_gateway/smoke_claude_code_provider.py" in payload_text
    assert "ops/evals/run_soc_claude_quality_gate.py" in payload_text
    assert "ops/evals/smoke_soc_cross_encoder_reranker.py" in payload_text
    assert "ops/evals/smoke_soc_embedding_model.py" in payload_text
    assert "ops/evals/run_soc_local_model_quality_gate.py" in payload_text
    assert "tests/unit/ops/test_claude_code_provider_smoke.py" in payload_text
    assert "tests/unit/ops/test_soc_claude_quality_gate.py" in payload_text
    assert "tests/unit/ops/test_soc_cross_encoder_smoke.py" in payload_text
    assert "tests/unit/ops/test_soc_embedding_smoke.py" in payload_text
    assert "tests/unit/ops/test_soc_local_model_quality_gate.py" in payload_text
    assert "LocalSentenceTransformerEmbedder" in payload_text
    assert (
        "src/req_tracker/storage/migrations/postgres/011_soc_knowledge_tables.sql"
        in payload_text
    )
    assert (
        "src/req_tracker/storage/migrations/postgres/012_soc_pgvector_tables.sql"
        in payload_text
    )
    assert (
        "src/req_tracker/storage/migrations/postgres/013_soc_age_schema.sql"
        in payload_text
    )
    assert "ops/rehearsal/validate_soc_postgres_profile.py" in payload_text
    assert "ops/rehearsal/validate_soc_live_postgres.py" in payload_text
    assert "ACC-A-10" in payload_text
    assert "ACC-A-11" in payload_text
    assert "ACC-A-12" in payload_text
    a11 = next(item for item in payload["subgoals"] if item["id"] == "A11")
    assert a11["status"] == "implemented_seed"
    assert "src/req_tracker/query/" in payload_text
    assert "src/req_tracker/fixtures/" in payload_text
    assert "src/req_tracker/soc_ui/" in payload_text


def test_stage_a_local_model_dependency_is_optional_extra() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "soc-models" in payload["project"]["optional-dependencies"]
    assert any(
        dependency.startswith("sentence-transformers")
        for dependency in payload["project"]["optional-dependencies"]["soc-models"]
    )

"""Tests for the storage-backed SoC query quality gate."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from req_tracker.fixtures.soc_knowledge import (
    load_soc_query_set,
    load_soc_seed_artifacts,
)

ROOT = Path(__file__).resolve().parents[3]


def test_soc_storage_backed_query_eval_skips_without_dsn() -> None:
    module = _load_eval()

    report = module.run_soc_storage_backed_query_eval(dsn="")

    assert report["status"] == "skipped"
    assert report["passed"] is False
    assert report["requires_live"] is True
    assert report["dsn_provided"] is False
    assert report["checks"]["storage_rehearsal"]["status"] == "skipped"
    assert report["checks"]["query_quality"]["status"] == "skipped"


def test_soc_storage_backed_query_eval_runs_quality_with_fake_backend(
    monkeypatch: Any,
) -> None:
    module = _load_eval()
    artifacts = load_soc_seed_artifacts()
    artifacts_by_id = {artifact.external_id: artifact for artifact in artifacts}
    expected_by_query = {
        query.q_id: list(query.expected_artifact_ids) for query in load_soc_query_set()
    }

    def fake_rehearsal(**kwargs: object) -> dict[str, object]:
        assert kwargs["dsn"] == "postgresql://example.invalid/soc"
        assert kwargs["apply_migrations"] is True
        return {"status": "passed", "passed": True, "failure_count": 0}

    class FakeRetrievalBackend:
        backend_name = "postgres_hybrid_fake"

        def __init__(self, *, dsn: str) -> None:
            assert dsn == "postgresql://example.invalid/soc"

        def retrieve(self, **kwargs: object) -> list[object]:
            query_id = str(kwargs["query_id"])
            return [artifacts_by_id[item] for item in expected_by_query[query_id]]

    monkeypatch.setattr(module, "run_soc_live_storage_rehearsal", fake_rehearsal)
    monkeypatch.setattr(module, "PostgresHybridSocRetrievalBackend", FakeRetrievalBackend)

    report = module.run_soc_storage_backed_query_eval(
        dsn="postgresql://example.invalid/soc",
        apply_migrations=True,
        coverage_mode="seed",
    )

    encoded = json.dumps(report, sort_keys=True)
    assert "postgresql://example.invalid/soc" not in encoded
    assert report["status"] == "passed"
    assert report["passed"] is True
    assert report["dsn_provided"] is True
    assert report["checks"]["storage_rehearsal"]["status"] == "passed"
    assert report["checks"]["query_quality"]["status"] == "passed"
    assert report["counts"]["queries"] >= 20
    assert report["recall"] == 1.0
    assert report["source_accuracy"] == 1.0
    assert report["schema_pass_rate"] == 1.0


def test_soc_storage_backed_query_eval_cli_skips_without_dsn() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/run_soc_storage_backed_query_eval.py",
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
    assert payload["requires_live"] is True


def _load_eval() -> ModuleType:
    module_path = ROOT / "ops/evals/run_soc_storage_backed_query_eval.py"
    spec = importlib.util.spec_from_file_location(
        "run_soc_storage_backed_query_eval",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

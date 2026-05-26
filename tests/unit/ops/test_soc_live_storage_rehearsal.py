"""Tests for the live SoC storage-backed retrieval rehearsal."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from req_tracker.fixtures.soc_knowledge import load_soc_seed_artifacts

ROOT = Path(__file__).resolve().parents[3]


def test_soc_live_storage_rehearsal_skips_without_dsn() -> None:
    module = _load_rehearsal()

    report = module.run_soc_live_storage_rehearsal(dsn="")

    assert report["status"] == "skipped"
    assert report["passed"] is False
    assert report["dsn_provided"] is False
    assert report["checks"]["profile"]["status"] == "skipped"
    assert report["checks"]["fixture_load"]["status"] == "skipped"
    assert report["checks"]["hybrid_retrieval"]["status"] == "skipped"


def test_soc_live_storage_rehearsal_runs_profile_load_graph_and_retrieval(
    monkeypatch: Any,
) -> None:
    module = _load_rehearsal()
    seed_artifacts = {artifact.external_id: artifact for artifact in load_soc_seed_artifacts()}
    artifacts = [seed_artifacts["SOC1-JIRA-001"], seed_artifacts["SOC2-JIRA-001"]]

    monkeypatch.setattr(module, "load_soc_seed_artifacts", lambda: artifacts)
    monkeypatch.setattr(
        module,
        "validate_soc_live_postgres",
        lambda **_kwargs: {"status": "passed", "passed": True, "failure_count": 0},
    )

    class FakeFixtureLoader:
        def __init__(self, dsn: str) -> None:
            assert dsn == "postgresql://example.invalid/soc"

        def load_fixture(self, *, artifacts: object, classifications: object) -> dict[str, int]:
            assert len(list(artifacts)) == 2
            assert len(list(classifications)) >= 2
            return {"artifacts": 2, "classifications": 8, "embeddings": 2}

    class FakeGraphLoader:
        def __init__(self, dsn: str) -> None:
            assert dsn == "postgresql://example.invalid/soc"

        def upsert_artifact_graph(
            self,
            *,
            artifacts: object,
            classifications: object,
            semantic_relations: object,
        ) -> dict[str, int]:
            assert len(list(artifacts)) == 2
            assert len(list(classifications)) >= 2
            relations = list(semantic_relations)
            assert len(relations) > 0
            return {
                "artifact_nodes": 2,
                "axis_relations": 8,
                "semantic_relations": len(relations),
            }

    class FakeRetrievalBackend:
        def __init__(self, dsn: str) -> None:
            assert dsn == "postgresql://example.invalid/soc"

        def retrieve(self, **kwargs: object) -> object:
            assert kwargs["query_id"] == "soc_live_storage_rehearsal"
            return [artifacts[0]]

    monkeypatch.setattr(module, "SocPostgresFixtureLoader", FakeFixtureLoader)
    monkeypatch.setattr(module, "SocAgeGraphLoader", FakeGraphLoader)
    monkeypatch.setattr(module, "PostgresHybridSocRetrievalBackend", FakeRetrievalBackend)

    report = module.run_soc_live_storage_rehearsal(
        dsn="postgresql://example.invalid/soc",
        apply_migrations=True,
    )

    assert report["status"] == "passed"
    assert report["passed"] is True
    assert report["checks"]["profile"]["status"] == "passed"
    assert report["checks"]["fixture_load"]["counts"]["artifacts"] == 2
    assert report["checks"]["age_graph_load"]["counts"]["artifact_nodes"] == 2
    assert report["checks"]["age_graph_load"]["counts"]["semantic_relations"] > 0
    assert report["checks"]["hybrid_retrieval"]["artifact_ids"] == [artifacts[0].external_id]
    assert report["checks"]["hybrid_retrieval"]["source_urls"] == [artifacts[0].source_url]


def test_soc_live_storage_rehearsal_cli_skips_without_dsn() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/rehearsal/run_soc_live_storage_rehearsal.py",
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
    assert payload["passed"] is False


def _load_rehearsal() -> ModuleType:
    module_path = ROOT / "ops/rehearsal/run_soc_live_storage_rehearsal.py"
    spec = importlib.util.spec_from_file_location("run_soc_live_storage_rehearsal", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

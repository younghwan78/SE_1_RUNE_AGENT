"""Tests for the SoC local model quality gate."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def test_soc_local_model_quality_gate_dry_run_reports_live_requirements() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/run_soc_local_model_quality_gate.py",
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
    assert payload["mode"] == "dry_run"
    assert payload["requires_live"] is True
    assert payload["checks"]["embedding_quality"]["status"] == "skipped"
    assert payload["checks"]["reranker_quality"]["status"] == "skipped"
    assert payload["models"]["embedding"] == "BAAI/bge-m3"
    assert payload["models"]["reranker"] == "BAAI/bge-reranker-v2-m3"


def test_soc_local_model_quality_gate_scores_embedding_and_reranker_with_fakes(
    monkeypatch: Any,
) -> None:
    module = _load_quality_gate()

    monkeypatch.setattr(module, "LocalSentenceTransformerEmbedder", FakeEmbedder)
    monkeypatch.setattr(module, "CrossEncoderSocReranker", FakeReranker)

    report = module.run_soc_local_model_quality_gate(live=True)

    assert report["status"] == "passed"
    assert report["checks"]["embedding_quality"]["status"] == "passed"
    assert report["checks"]["embedding_quality"]["recall_at_k"] >= 0.6
    assert (
        report["checks"]["embedding_quality"]["top_artifact_ids"][0]
        in report["checks"]["embedding_quality"]["expected_artifact_ids"]
    )
    assert report["checks"]["reranker_quality"]["status"] == "passed"
    assert (
        report["checks"]["reranker_quality"]["top_artifact_ids"][0]
        in report["checks"]["reranker_quality"]["expected_artifact_ids"]
    )


class FakeEmbedder:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def embed_text(self, text: str) -> list[float]:
        return _vector_for_text(text)

    def embed_artifact(self, artifact: Any) -> list[float]:
        return _vector_for_text(f"{artifact.title} {artifact.body_text}")


class FakeReranker:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def rerank(self, *, candidates: list[Any], **_kwargs: object) -> list[Any]:
        return sorted(
            candidates,
            key=lambda artifact: (
                "camera" not in artifact.title.lower(),
                "performance" not in artifact.title.lower(),
                artifact.external_id,
            ),
        )


def _vector_for_text(text: str) -> list[float]:
    lowered = text.lower()
    return [
        1.0 if "camera" in lowered else 0.0,
        1.0 if "performance" in lowered or "성능" in lowered else 0.0,
        1.0 if "memory" in lowered else 0.0,
    ]


def _load_quality_gate() -> ModuleType:
    module_path = ROOT / "ops/evals/run_soc_local_model_quality_gate.py"
    spec = importlib.util.spec_from_file_location("run_soc_local_model_quality_gate", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

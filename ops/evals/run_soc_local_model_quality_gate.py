"""Evaluate optional local embedding and reranker model quality for SoC seed queries."""

from __future__ import annotations

import argparse
import json
import math
from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.config.settings import Settings
from req_tracker.fixtures.soc_knowledge import load_soc_query_set, load_soc_seed_artifacts
from req_tracker.ontology.soc_models import SocGroundTruthQuery
from req_tracker.query.reranking import CrossEncoderSocReranker
from req_tracker.vector.local_embedding import LocalSentenceTransformerEmbedder

DEFAULT_QUERY_ID = "Q2"
DEFAULT_TOP_K = 5
DEFAULT_MIN_RECALL = 0.6


def run_soc_local_model_quality_gate(
    *,
    live: bool,
    query_id: str = DEFAULT_QUERY_ID,
    top_k: int = DEFAULT_TOP_K,
    min_recall_at_k: float = DEFAULT_MIN_RECALL,
    embedding_model_name: str = "",
    reranker_model_name: str = "",
    expected_dimensions: int = 0,
) -> dict[str, Any]:
    """Return local model quality gate results without loading models unless live is true."""
    settings = Settings()
    resolved_embedding_model = embedding_model_name or settings.soc_embedding_model_name
    resolved_reranker_model = reranker_model_name or settings.soc_cross_encoder_model_name
    resolved_dimensions = expected_dimensions or settings.soc_embedding_dimensions
    models = {
        "embedding": resolved_embedding_model,
        "reranker": resolved_reranker_model,
    }
    if not live:
        return {
            "checks": {
                "embedding_quality": {"status": "skipped"},
                "reranker_quality": {"status": "skipped"},
            },
            "mode": "dry_run",
            "models": models,
            "requires_live": True,
            "schema_version": "v1",
            "status": "skipped",
        }

    artifacts = load_soc_seed_artifacts()
    query_case = _query_case(query_id)
    checks: dict[str, Any] = {}
    failures: list[str] = []

    try:
        embedder = LocalSentenceTransformerEmbedder(
            model_name=resolved_embedding_model,
            expected_dimensions=resolved_dimensions,
        )
        checks["embedding_quality"] = _embedding_quality_check(
            embedder=embedder,
            artifacts=artifacts,
            query_case=query_case,
            top_k=top_k,
            min_recall_at_k=min_recall_at_k,
        )
    except Exception as exc:  # noqa: BLE001
        checks["embedding_quality"] = {"error": str(exc), "status": "failed"}
    if checks["embedding_quality"]["status"] != "passed":
        failures.append("embedding_quality_failed")

    try:
        reranker = CrossEncoderSocReranker(model_name=resolved_reranker_model)
        checks["reranker_quality"] = _reranker_quality_check(
            reranker=reranker,
            artifacts=artifacts,
            query_case=query_case,
            top_k=top_k,
            min_recall_at_k=min_recall_at_k,
        )
    except Exception as exc:  # noqa: BLE001
        checks["reranker_quality"] = {"error": str(exc), "status": "failed"}
    if checks["reranker_quality"]["status"] != "passed":
        failures.append("reranker_quality_failed")

    return {
        "checks": checks,
        "expected_query_id": query_case.q_id,
        "failure_count": len(failures),
        "failures": failures,
        "min_recall_at_k": min_recall_at_k,
        "mode": "live",
        "models": models,
        "requires_live": True,
        "schema_version": "v1",
        "status": "passed" if not failures else "failed",
        "top_k": top_k,
    }


def _embedding_quality_check(
    *,
    embedder: LocalSentenceTransformerEmbedder,
    artifacts: list[RawSourceArtifact],
    query_case: SocGroundTruthQuery,
    top_k: int,
    min_recall_at_k: float,
) -> dict[str, Any]:
    query_vector = embedder.embed_text(query_case.question)
    scored = [
        (_cosine_similarity(query_vector, embedder.embed_artifact(artifact)), artifact)
        for artifact in artifacts
    ]
    scored.sort(key=lambda item: (-item[0], item[1].external_id))
    ranked = [artifact for _score, artifact in scored]
    return _quality_payload(
        ranked=ranked,
        query_case=query_case,
        top_k=top_k,
        min_recall_at_k=min_recall_at_k,
    )


def _reranker_quality_check(
    *,
    reranker: CrossEncoderSocReranker,
    artifacts: list[RawSourceArtifact],
    query_case: SocGroundTruthQuery,
    top_k: int,
    min_recall_at_k: float,
) -> dict[str, Any]:
    ranked = reranker.rerank(
        query_id=f"soc_local_model_quality_{query_case.q_id}",
        user_query=query_case.question,
        query_slice=query_case.slice,
        candidates=artifacts,
        run_id="soc_local_model_quality_gate",
        step_id="soc_local_model_rerank_quality",
    )
    return _quality_payload(
        ranked=ranked,
        query_case=query_case,
        top_k=top_k,
        min_recall_at_k=min_recall_at_k,
    )


def _quality_payload(
    *,
    ranked: list[RawSourceArtifact],
    query_case: SocGroundTruthQuery,
    top_k: int,
    min_recall_at_k: float,
) -> dict[str, Any]:
    top_artifacts = ranked[:top_k]
    top_ids = [artifact.external_id for artifact in top_artifacts]
    expected = set(query_case.expected_artifact_ids)
    hits = [artifact_id for artifact_id in top_ids if artifact_id in expected]
    recall = len(hits) / len(expected) if expected else 1.0
    return {
        "expected_artifact_ids": query_case.expected_artifact_ids,
        "hit_artifact_ids": hits,
        "recall_at_k": recall,
        "source_urls": [artifact.source_url for artifact in top_artifacts],
        "status": "passed" if recall >= min_recall_at_k else "failed",
        "top_artifact_ids": top_ids,
    }


def _query_case(query_id: str) -> SocGroundTruthQuery:
    for query_case in load_soc_query_set():
        if query_case.q_id == query_id:
            return query_case
    raise ValueError(f"unknown SoC query id: {query_id}")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not load local models.")
    parser.add_argument("--live", action="store_true", help="Load and score local models.")
    parser.add_argument("--query-id", default=DEFAULT_QUERY_ID)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--min-recall-at-k", type=float, default=DEFAULT_MIN_RECALL)
    parser.add_argument("--embedding-model-name", default="")
    parser.add_argument("--reranker-model-name", default="")
    parser.add_argument("--expected-dimensions", type=int, default=0)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    report = run_soc_local_model_quality_gate(
        live=args.live and not args.dry_run,
        query_id=args.query_id,
        top_k=args.top_k,
        min_recall_at_k=args.min_recall_at_k,
        embedding_model_name=args.embedding_model_name,
        reranker_model_name=args.reranker_model_name,
        expected_dimensions=args.expected_dimensions,
    )
    _emit(report, args.format)
    return 0 if report["status"] in {"passed", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

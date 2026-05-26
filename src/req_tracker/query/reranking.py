"""SoC candidate reranking."""

import importlib
import re
from collections.abc import Callable
from typing import Any, Protocol, cast

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import ModelRequest
from req_tracker.ontology.soc_models import SOC_SCHEMA_VERSION, SocRerankResult, SocSlice

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class SocReranker(Protocol):
    """Order retrieved SoC artifacts by query relevance."""

    def rerank(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        candidates: list[RawSourceArtifact],
        run_id: str,
        step_id: str = "soc_rerank",
    ) -> list[RawSourceArtifact]:
        """Return candidates in preferred answer order."""


class CrossEncoderModel(Protocol):
    """Minimal cross-encoder interface used by the local reranker."""

    def predict(self, pairs: list[tuple[str, str]]) -> object:
        """Return one relevance score per query/candidate pair."""


CrossEncoderModelFactory = Callable[[str], CrossEncoderModel]


class LexicalSocReranker:
    """Deterministic lexical reranker used as the seed/local fallback."""

    def rerank(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        candidates: list[RawSourceArtifact],
        run_id: str,
        step_id: str = "soc_rerank",
    ) -> list[RawSourceArtifact]:
        """Sort candidates by simple selector and keyword overlap."""
        scored = [
            (
                _lexical_score(
                    user_query=user_query,
                    query_slice=query_slice,
                    artifact=artifact,
                ),
                index,
                artifact,
            )
            for index, artifact in enumerate(candidates)
        ]
        scored.sort(key=lambda item: (-item[0], item[1], item[2].external_id))
        return [artifact for _score, _index, artifact in scored]


class CrossEncoderSocReranker:
    """Optional local cross-encoder reranker with lexical fallback."""

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        model_factory: CrossEncoderModelFactory | None = None,
        fallback: SocReranker | None = None,
    ) -> None:
        self.model_name = model_name
        self._model_factory = model_factory or _default_cross_encoder_model_factory
        self._fallback = fallback or LexicalSocReranker()
        self._model: CrossEncoderModel | None = None

    def rerank(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        candidates: list[RawSourceArtifact],
        run_id: str,
        step_id: str = "soc_rerank",
    ) -> list[RawSourceArtifact]:
        """Return cross-encoder-ranked candidates, falling back deterministically."""
        fallback = self._fallback.rerank(
            query_id=query_id,
            user_query=user_query,
            query_slice=query_slice,
            candidates=candidates,
            run_id=run_id,
            step_id=step_id,
        )
        if not candidates:
            return fallback
        pairs = [(user_query, _cross_encoder_candidate_text(artifact)) for artifact in candidates]
        try:
            scores = self._predict_pairs(pairs)
        except Exception:
            return fallback
        if len(scores) != len(candidates):
            return fallback
        scored = [
            (score, index, artifact)
            for index, (score, artifact) in enumerate(zip(scores, candidates, strict=True))
        ]
        scored.sort(key=lambda item: (-item[0], item[1], item[2].external_id))
        return [artifact for _score, _index, artifact in scored]

    def warmup(self) -> list[float]:
        """Load the model and score a sample pair for live smoke checks."""
        return self._predict_pairs([("Camera shot performance?", "Camera shot performance issue.")])

    def _predict_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        if self._model is None:
            self._model = self._model_factory(self.model_name)
        return _coerce_scores(self._model.predict(pairs))


class GatewaySocReranker:
    """Use the model gateway to rerank candidates, with lexical fallback."""

    def __init__(
        self,
        *,
        client: ModelGatewayClient,
        model_profile_id: str,
        prompt_version_id: str,
        fallback: SocReranker | None = None,
    ) -> None:
        self._client = client
        self._model_profile_id = model_profile_id
        self._prompt_version_id = prompt_version_id
        self._fallback = fallback or LexicalSocReranker()

    def rerank(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        candidates: list[RawSourceArtifact],
        run_id: str,
        step_id: str = "soc_rerank",
    ) -> list[RawSourceArtifact]:
        """Return gateway-ranked candidates when validation passes."""
        fallback = self._fallback.rerank(
            query_id=query_id,
            user_query=user_query,
            query_slice=query_slice,
            candidates=candidates,
            run_id=run_id,
            step_id=step_id,
        )
        if not candidates:
            return fallback
        request = ModelRequest(
            model_profile_id=self._model_profile_id,
            prompt_version_id=self._prompt_version_id,
            payload={
                "task": "soc_rerank",
                "schema_version": SOC_SCHEMA_VERSION,
                "query_id": query_id,
                "user_query": user_query,
                "slice": query_slice.model_dump(mode="json"),
                "candidates": [_candidate_payload(artifact) for artifact in candidates],
                "output_contract": "Return SocRerankResult JSON with known artifact IDs only.",
            },
            data_classification="public_internal",
        )
        try:
            _response, parsed, validation = self._client.complete(
                run_id=run_id or f"soc_rerank_{stable_hash(request.payload)[:12]}",
                step_id=step_id,
                request=request,
                response_model=SocRerankResult,
            )
        except Exception:
            return fallback
        if parsed is None or validation.status == "failed":
            return fallback
        ranked = _apply_rerank_result(candidates=candidates, result=parsed)
        return ranked or fallback


def _apply_rerank_result(
    *,
    candidates: list[RawSourceArtifact],
    result: SocRerankResult,
) -> list[RawSourceArtifact]:
    candidates_by_id = {artifact.external_id: artifact for artifact in candidates}
    ranked: list[RawSourceArtifact] = []
    ranked_ids: set[str] = set()
    for item in result.ranked_items:
        artifact = candidates_by_id.get(item.artifact_id)
        if artifact is None:
            continue
        ranked.append(artifact)
        ranked_ids.add(artifact.external_id)
    ranked.extend(artifact for artifact in candidates if artifact.external_id not in ranked_ids)
    return ranked


def _lexical_score(
    *,
    user_query: str,
    query_slice: SocSlice,
    artifact: RawSourceArtifact,
) -> float:
    text = f"{artifact.title} {artifact.body_text}".lower()
    query_tokens = _tokens(user_query)
    selector_tokens = {
        token.lower()
        for value in [
            *query_slice.concerns,
            *query_slice.components,
            *query_slice.keywords,
            *(query_slice.project_keys or []),
        ]
        for token in _tokens(value)
    }
    score = 0.0
    for token in query_tokens:
        if token in text:
            score += 0.08
    for token in selector_tokens:
        if token in text:
            score += 0.18
    for keyword in query_slice.keywords:
        if keyword.lower() in text:
            score += 0.25
    return min(score, 1.0)


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text)}


def _candidate_payload(artifact: RawSourceArtifact) -> dict[str, object]:
    return {
        "artifact_id": artifact.external_id,
        "title": artifact.title,
        "summary": artifact.body_text[:500],
        "source_type": artifact.source_type,
        "source_url": artifact.source_url,
        "project_key": artifact.project_key,
    }


def _cross_encoder_candidate_text(artifact: RawSourceArtifact) -> str:
    return "\n".join(
        [
            f"title: {artifact.title}",
            f"body: {artifact.body_text[:1000]}",
            f"source_type: {artifact.source_type}",
            f"project_key: {artifact.project_key}",
        ]
    )


def _default_cross_encoder_model_factory(model_name: str) -> CrossEncoderModel:
    try:
        module = importlib.import_module("sentence_transformers")
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for SOC_RERANKER_MODE=cross_encoder"
        ) from exc
    cross_encoder_cls = getattr(module, "CrossEncoder", None)
    if cross_encoder_cls is None:
        raise RuntimeError("sentence_transformers.CrossEncoder is not available")
    return cast(CrossEncoderModel, cross_encoder_cls(model_name))


def _coerce_scores(output: object) -> list[float]:
    if hasattr(output, "tolist"):
        output = cast(Any, output).tolist()
    if not isinstance(output, (list, tuple)):
        return []
    scores: list[float] = []
    for item in output:
        try:
            scores.append(float(item))
        except (TypeError, ValueError):
            return []
    return scores

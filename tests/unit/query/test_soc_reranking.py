"""Tests for SoC reranking."""

from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)
from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.reranking import (
    CrossEncoderSocReranker,
    GatewaySocReranker,
    LexicalSocReranker,
)
from req_tracker.query.soc_service import answer_soc_query


class CapturingProvider:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.requests: list[ModelRequest] = []

    def complete(
        self,
        request: ModelRequest,
        active_profile: ModelProfile,
        active_prompt: PromptVersion,
    ) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            model_profile_id=active_profile.model_profile_id,
            prompt_version_id=active_prompt.prompt_version_id,
            output=self.output,
            latency_ms=9,
        )


class ReverseReranker:
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
        return list(reversed(candidates))


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.pairs: list[tuple[str, str]] = []

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        self.pairs = pairs
        return self.scores


class FakeCrossEncoderFactory:
    def __init__(self, scores: list[float]) -> None:
        self._model = FakeCrossEncoder(scores)
        self.model_name = ""

    @property
    def pairs(self) -> list[tuple[str, str]]:
        return self._model.pairs

    def __call__(self, model_name: str) -> FakeCrossEncoder:
        self.model_name = model_name
        return self._model


class FailingCrossEncoderFactory:
    def __call__(self, model_name: str) -> FakeCrossEncoder:
        raise RuntimeError(f"cross-encoder unavailable: {model_name}")


def test_lexical_reranker_promotes_keyword_matches() -> None:
    reranker = LexicalSocReranker()
    candidates = [
        _artifact("A", "Memory cleanup", "Memory usage cleanup."),
        _artifact("B", "Camera shot performance", "Shot-to-shot camera issue."),
    ]

    ranked = reranker.rerank(
        query_id="soc_query_rerank_001",
        user_query="Camera shot 성능 이슈는?",
        query_slice=SocSlice(
            pattern="topic_intersection",
            concerns=["Performance"],
            components=["Camera"],
            keywords=["shot"],
        ),
        candidates=candidates,
        run_id="soc_query_rerank_001",
    )

    assert [artifact.external_id for artifact in ranked] == ["B", "A"]


def test_gateway_reranker_validates_result_and_records_trace() -> None:
    traces = InMemoryTraceRepository()
    provider = CapturingProvider(
        {
            "query_id": "soc_query_rerank_gateway",
            "ranked_items": [
                {
                    "artifact_id": "B",
                    "score": 0.91,
                    "source": "claude",
                    "rationale": "Matches camera shot performance.",
                },
                {
                    "artifact_id": "A",
                    "score": 0.2,
                    "source": "claude",
                    "rationale": "Weaker match.",
                },
            ],
        }
    )
    reranker = GatewaySocReranker(
        client=ModelGatewayClient(
            provider=provider,
            profile=_profile(),
            prompt=_prompt(),
            trace_repo=traces,
        ),
        model_profile_id="dummy-rerank",
        prompt_version_id="pv_soc_rerank_v1",
    )

    ranked = reranker.rerank(
        query_id="soc_query_rerank_gateway",
        user_query="Camera shot 성능 이슈는?",
        query_slice=SocSlice(
            pattern="topic_intersection",
            concerns=["Performance"],
            components=["Camera"],
            keywords=["shot"],
        ),
        candidates=[
            _artifact("A", "Memory cleanup", "Memory usage cleanup."),
            _artifact("B", "Camera shot performance", "Shot-to-shot camera issue."),
        ],
        run_id="soc_query_rerank_gateway",
    )

    assert [artifact.external_id for artifact in ranked] == ["B", "A"]
    trace = list(traces.llm_calls.values())[0]
    assert trace.step_id == "soc_rerank"
    assert trace.validation_status == "passed"


def test_cross_encoder_reranker_promotes_model_scores() -> None:
    factory = FakeCrossEncoderFactory([0.1, 0.97])
    reranker = CrossEncoderSocReranker(
        model_name="BAAI/bge-reranker-v2-m3",
        model_factory=factory,
    )

    ranked = reranker.rerank(
        query_id="soc_query_cross_encoder",
        user_query="Camera shot 성능 이슈는?",
        query_slice=SocSlice(
            pattern="topic_intersection",
            concerns=["Performance"],
            components=["Camera"],
            keywords=["shot"],
        ),
        candidates=[
            _artifact("A", "Memory cleanup", "Memory usage cleanup."),
            _artifact("B", "Camera shot performance", "Shot-to-shot camera issue."),
        ],
        run_id="soc_query_cross_encoder",
    )

    assert factory.model_name == "BAAI/bge-reranker-v2-m3"
    assert factory.pairs[0][0] == "Camera shot 성능 이슈는?"
    assert "Memory cleanup" in factory.pairs[0][1]
    assert [artifact.external_id for artifact in ranked] == ["B", "A"]


def test_cross_encoder_reranker_falls_back_to_lexical_when_model_load_fails() -> None:
    reranker = CrossEncoderSocReranker(
        model_name="missing-cross-encoder",
        model_factory=FailingCrossEncoderFactory(),
    )

    ranked = reranker.rerank(
        query_id="soc_query_cross_encoder_fallback",
        user_query="Camera shot 성능 이슈는?",
        query_slice=SocSlice(
            pattern="topic_intersection",
            concerns=["Performance"],
            components=["Camera"],
            keywords=["shot"],
        ),
        candidates=[
            _artifact("A", "Memory cleanup", "Memory usage cleanup."),
            _artifact("B", "Camera shot performance", "Shot-to-shot camera issue."),
        ],
        run_id="soc_query_cross_encoder_fallback",
    )

    assert [artifact.external_id for artifact in ranked] == ["B", "A"]


def test_answer_soc_query_uses_reranker_before_answer_projection() -> None:
    answer = answer_soc_query(
        user_query="Camera shot 성능 이슈는 무엇이 있었나?",
        user_id="architect_01",
        session_id="session_001",
        query_id="soc_query_rerank_service",
        reranker=ReverseReranker(),
    )

    assert answer.items[0].sources[0].key != "SOC1-JIRA-002"


def _artifact(external_id: str, title: str, body_text: str) -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id=external_id,
        source_type="jira",
        source_url=f"https://jira.example/{external_id}",
        project_key="SOC-N-1",
        title=title,
        body_text=body_text,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="dummy-rerank",
        provider="dummy",
        model_name="dummy-rerank",
        endpoint_alias="dummy",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=30,
    )


def _prompt() -> PromptVersion:
    return PromptVersion(
        prompt_version_id="pv_soc_rerank_v1",
        task_name="soc_rerank",
        template="Return SocRerankResult JSON.",
        schema_version_ref="soc.v0_1.rerank",
        retrieval_policy_id="soc_seed",
        created_by="tester",
        status="active",
    )

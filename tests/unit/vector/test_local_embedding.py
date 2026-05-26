"""Tests for optional local SoC embedding model loading."""

from __future__ import annotations

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.vector.local_embedding import (
    LocalSentenceTransformerEmbedder,
    SocEmbeddingError,
)


class FakeSentenceTransformer:
    """Minimal fake sentence-transformer model."""

    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.encoded_texts: list[str] = []

    def encode(self, texts: list[str], **_kwargs: object) -> object:
        self.encoded_texts.extend(texts)
        return self.vectors


class FakeSentenceTransformerFactory:
    """Capture requested model name and return a fake model."""

    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.model_names: list[str] = []
        self.model = FakeSentenceTransformer(vectors)

    def __call__(self, model_name: str) -> FakeSentenceTransformer:
        self.model_names.append(model_name)
        return self.model


def test_local_sentence_transformer_embedder_encodes_artifact_text() -> None:
    factory = FakeSentenceTransformerFactory([[3.0, 4.0, 0.0]])
    embedder = LocalSentenceTransformerEmbedder(
        model_name="BAAI/bge-m3",
        expected_dimensions=3,
        model_factory=factory,
    )

    vector = embedder.embed_artifact(_artifact())

    assert factory.model_names == ["BAAI/bge-m3"]
    assert factory.model.encoded_texts == [
        "Camera perf regression Camera shot transition drops below target FPS. Camera Performance"
    ]
    assert vector == [0.6, 0.8, 0.0]


def test_local_sentence_transformer_embedder_rejects_wrong_dimensions() -> None:
    embedder = LocalSentenceTransformerEmbedder(
        model_name="BAAI/bge-m3",
        expected_dimensions=3,
        model_factory=FakeSentenceTransformerFactory([[1.0, 2.0]]),
    )

    try:
        embedder.embed_text("dimension mismatch")
    except SocEmbeddingError as exc:
        assert "expected 3 dimensions" in str(exc)
    else:
        raise AssertionError("dimension mismatch should fail")


def _artifact() -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id="SOC1-JIRA-001",
        source_type="jira",
        project_key="SOC-N-1",
        title="Camera perf regression",
        body_text="Camera shot transition drops below target FPS.",
        source_url="https://jira.example/browse/SOC1-JIRA-001",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        labels=["Camera", "Performance"],
        links=[],
        metadata={},
    )

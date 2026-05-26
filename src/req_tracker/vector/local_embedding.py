"""Optional local embedding model support for the SoC Knowledge PoC."""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable, Sequence
from typing import Any, Protocol, cast

from req_tracker.adapters.base import RawSourceArtifact


class SocEmbeddingError(RuntimeError):
    """Raised when a local embedding model cannot produce a valid vector."""


class SentenceTransformerModel(Protocol):
    """Minimal sentence-transformers interface used by the local embedder."""

    def encode(self, texts: list[str], **kwargs: object) -> object:
        """Return one vector per input text."""


SentenceTransformerFactory = Callable[[str], SentenceTransformerModel]


class LocalSentenceTransformerEmbedder:
    """Lazy local sentence-transformers embedder with explicit dimension checks."""

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-m3",
        expected_dimensions: int = 1024,
        model_factory: SentenceTransformerFactory | None = None,
        normalize: bool = True,
    ) -> None:
        self.model_name = model_name
        self.expected_dimensions = expected_dimensions
        self._model_factory = model_factory or _default_sentence_transformer_factory
        self._normalize = normalize
        self._model: SentenceTransformerModel | None = None

    def embed_artifact(self, artifact: RawSourceArtifact) -> list[float]:
        """Embed one source artifact using title, body, and labels."""
        return self.embed_text(_artifact_embedding_text(artifact))

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text and return a validated vector."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed one or more texts and validate model output shape."""
        if not texts:
            return []
        if self._model is None:
            self._model = self._model_factory(self.model_name)
        output = self._model.encode(
            list(texts),
            convert_to_numpy=False,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        vectors = _coerce_vectors(output)
        if len(vectors) != len(texts):
            raise SocEmbeddingError(
                f"embedding model returned {len(vectors)} vectors for {len(texts)} texts"
            )
        return [self._validate_vector(vector) for vector in vectors]

    def warmup(self) -> list[float]:
        """Load the model and embed a sample query for live smoke checks."""
        return self.embed_text("Camera shot performance issue")

    def _validate_vector(self, vector: list[float]) -> list[float]:
        if len(vector) != self.expected_dimensions:
            raise SocEmbeddingError(
                f"embedding model returned {len(vector)} dimensions; "
                f"expected {self.expected_dimensions} dimensions"
            )
        if not self._normalize:
            return vector
        return _normalize_vector(vector)


def _artifact_embedding_text(artifact: RawSourceArtifact) -> str:
    return " ".join([artifact.title, artifact.body_text, *artifact.labels])


def _default_sentence_transformer_factory(model_name: str) -> SentenceTransformerModel:
    try:
        module = importlib.import_module("sentence_transformers")
    except ImportError as exc:
        raise SocEmbeddingError(
            "sentence-transformers is required for local SoC embedding model loading"
        ) from exc
    sentence_transformer_cls = getattr(module, "SentenceTransformer", None)
    if sentence_transformer_cls is None:
        raise SocEmbeddingError("sentence_transformers.SentenceTransformer is not available")
    return cast(SentenceTransformerModel, sentence_transformer_cls(model_name))


def _coerce_vectors(output: object) -> list[list[float]]:
    if hasattr(output, "tolist"):
        output = cast(Any, output).tolist()
    if not isinstance(output, (list, tuple)):
        raise SocEmbeddingError("embedding model output must be a vector list")
    if _is_numeric_sequence(output):
        return [_coerce_vector(output)]
    vectors: list[list[float]] = []
    for item in output:
        if hasattr(item, "tolist"):
            item = cast(Any, item).tolist()
        if not isinstance(item, (list, tuple)):
            raise SocEmbeddingError("embedding model output must contain vector lists")
        vectors.append(_coerce_vector(item))
    return vectors


def _coerce_vector(items: Sequence[object]) -> list[float]:
    vector: list[float] = []
    for item in items:
        try:
            vector.append(float(cast(Any, item)))
        except (TypeError, ValueError) as exc:
            raise SocEmbeddingError("embedding vector contains a non-numeric value") from exc
    return vector


def _is_numeric_sequence(items: Sequence[object]) -> bool:
    if not items:
        return False
    return not isinstance(items[0], (list, tuple))


def _normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]

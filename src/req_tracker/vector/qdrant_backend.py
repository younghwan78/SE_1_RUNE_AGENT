"""Qdrant vector backend foundation."""

import math
from collections import Counter
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import ArtifactChunk


class QdrantVectorBackend:
    """Qdrant-backed retrieval using deterministic local vectors as a foundation."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str | None = None,
        collection_name: str = "rune_chunks",
        vector_size: int = 64,
        client: Any | None = None,
    ) -> None:
        if not url and client is None:
            raise ValueError("qdrant url is required when client is not provided")
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._client = client or QdrantClient(url=url, api_key=api_key)
        self._ensure_collection()

    def upsert(self, chunks: list[ArtifactChunk]) -> None:
        """Insert or replace chunks."""
        if not chunks:
            return
        points = [
            PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=_embed_text(chunk.text, self.vector_size),
                payload={
                    "chunk_id": chunk.chunk_id,
                    "artifact_id": chunk.artifact_id,
                    "project_key": chunk.project_key,
                    "content_hash": chunk.content_hash,
                    "chunk": chunk.model_dump(mode="json"),
                },
            )
            for chunk in chunks
        ]
        self._client.upsert(collection_name=self.collection_name, points=points, wait=True)

    def search(self, query: str, *, project_key: str, limit: int = 5) -> list[ArtifactChunk]:
        """Return matching chunks."""
        response = self._client.query_points(
            collection_name=self.collection_name,
            query=_embed_text(query, self.vector_size),
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="project_key",
                        match=MatchValue(value=project_key),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            ArtifactChunk.model_validate(point.payload["chunk"])
            for point in response.points
            if point.payload and "chunk" in point.payload
        ]

    def _ensure_collection(self) -> None:
        if self._client.collection_exists(self.collection_name):
            return
        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )


def _point_id(chunk_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, chunk_id))


def _embed_text(text: str, vector_size: int) -> list[float]:
    counts: Counter[int] = Counter()
    for raw in text.lower().split():
        token = "".join(char for char in raw if char.isalnum())
        if not token:
            continue
        bucket = int(stable_hash(token)[:8], 16) % vector_size
        counts[bucket] += 1
    vector = [0.0] * vector_size
    for bucket, count in counts.items():
        vector[bucket] = float(count)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]

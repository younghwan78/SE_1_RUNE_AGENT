"""Qdrant vector backend tests."""

from typing import Any

from qdrant_client.models import PointStruct

from req_tracker.ontology.models import ArtifactChunk, EvidenceSpan
from req_tracker.vector.qdrant_backend import QdrantVectorBackend


class FakePoint:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload


class FakeQueryResponse:
    def __init__(self, points: list[FakePoint]) -> None:
        self.points = points


class FakeQdrantClient:
    def __init__(self) -> None:
        self.created_collections: list[str] = []
        self.points: list[PointStruct] = []

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.created_collections

    def create_collection(self, *, collection_name: str, vectors_config: object) -> bool:
        assert vectors_config is not None
        self.created_collections.append(collection_name)
        return True

    def upsert(self, *, collection_name: str, points: list[PointStruct], wait: bool) -> None:
        assert collection_name == "test_chunks"
        assert wait is True
        self.points = points

    def query_points(
        self,
        *,
        collection_name: str,
        query: list[float],
        query_filter: object,
        limit: int,
        with_payload: bool,
    ) -> FakeQueryResponse:
        assert collection_name == "test_chunks"
        assert query
        assert query_filter is not None
        assert with_payload is True
        points = [
            FakePoint(point.payload)
            for point in self.points
            if point.payload and point.payload["project_key"] == "RUNE_CAM_ALPHA"
        ]
        return FakeQueryResponse(points[:limit])


def test_qdrant_backend_creates_collection_upserts_and_searches_chunks() -> None:
    client = FakeQdrantClient()
    backend = QdrantVectorBackend(
        url="",
        collection_name="test_chunks",
        vector_size=16,
        client=client,
    )
    chunk = _chunk("chunk_1", "RUNE_CAM_ALPHA", "camera pipeline latency")
    other = _chunk("chunk_2", "OTHER", "camera pipeline latency")

    backend.upsert([chunk, other])
    results = backend.search("camera latency", project_key="RUNE_CAM_ALPHA", limit=5)

    assert client.created_collections == ["test_chunks"]
    assert len(client.points) == 2
    assert results == [chunk]


def _chunk(chunk_id: str, project_key: str, text: str) -> ArtifactChunk:
    return ArtifactChunk(
        chunk_id=chunk_id,
        artifact_id=f"artifact_{chunk_id}",
        project_key=project_key,
        text=text,
        index=0,
        evidence=EvidenceSpan(
            artifact_id=f"artifact_{chunk_id}",
            source_url=f"dummy://{chunk_id}",
            quote_hash="hash",
            extracted_text_preview=text,
        ),
        content_hash=f"hash_{chunk_id}",
    )

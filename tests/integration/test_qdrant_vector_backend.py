"""Optional real Qdrant vector backend integration tests."""

import os

import pytest
from qdrant_client import QdrantClient

from req_tracker.ontology.models import ArtifactChunk, EvidenceSpan
from req_tracker.vector.qdrant_backend import QdrantVectorBackend

QDRANT_TEST_URL = os.getenv("QDRANT_TEST_URL")
QDRANT_TEST_API_KEY = os.getenv("QDRANT_TEST_API_KEY") or None
QDRANT_TEST_COLLECTION = os.getenv("QDRANT_TEST_COLLECTION", "rune_test_chunks")

pytestmark = pytest.mark.skipif(
    not QDRANT_TEST_URL,
    reason="QDRANT_TEST_URL is not set",
)


def test_qdrant_vector_backend_searches_against_real_collection() -> None:
    assert QDRANT_TEST_URL is not None
    _delete_collection()
    backend = QdrantVectorBackend(
        url=QDRANT_TEST_URL,
        api_key=QDRANT_TEST_API_KEY,
        collection_name=QDRANT_TEST_COLLECTION,
        vector_size=16,
    )
    chunk = _chunk("qdrant_it_chunk_1", "RUNE_CAM_ALPHA", "camera latency budget")
    try:
        backend.upsert([chunk])
        results = backend.search("camera latency", project_key="RUNE_CAM_ALPHA", limit=1)

        assert results == [chunk]
    finally:
        _delete_collection()


def _delete_collection() -> None:
    assert QDRANT_TEST_URL is not None
    client = QdrantClient(url=QDRANT_TEST_URL, api_key=QDRANT_TEST_API_KEY)
    if client.collection_exists(QDRANT_TEST_COLLECTION):
        client.delete_collection(QDRANT_TEST_COLLECTION)


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

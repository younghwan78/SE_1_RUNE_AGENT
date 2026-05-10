"""In-memory lexical retrieval backend."""

import re
from collections import Counter

from req_tracker.ontology.models import ArtifactChunk


class MemoryVectorBackend:
    """Small lexical search backend for dummy validation."""

    def __init__(self) -> None:
        self._chunks: dict[str, ArtifactChunk] = {}

    def upsert(self, chunks: list[ArtifactChunk]) -> None:
        """Insert or replace chunks."""
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def search(self, query: str, *, project_key: str, limit: int = 5) -> list[ArtifactChunk]:
        """Return chunks ranked by lexical overlap."""
        query_terms = _terms(query)
        ranked: list[tuple[int, ArtifactChunk]] = []
        for chunk in self._chunks.values():
            if chunk.project_key != project_key:
                continue
            score = sum((_terms(chunk.text) & query_terms).values())
            if score:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [chunk for _, chunk in ranked[:limit]]


def _terms(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+", text.lower()))


"""Vector backend contract."""

from typing import Protocol, runtime_checkable

from req_tracker.ontology.models import ArtifactChunk


@runtime_checkable
class VectorBackend(Protocol):
    """Retrieval backend interface shared by memory and production stores."""

    def upsert(self, chunks: list[ArtifactChunk]) -> None:
        """Insert or replace chunks."""

    def search(self, query: str, *, project_key: str, limit: int = 5) -> list[ArtifactChunk]:
        """Return matching chunks."""

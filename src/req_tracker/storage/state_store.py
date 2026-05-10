"""Shared state repository contract."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class StateStore(Protocol):
    """Persistence contract shared by local and production repositories."""

    def upsert(
        self,
        *,
        collection: str,
        entity_id: str,
        payload: Any,
        project_key: str | None = None,
    ) -> None:
        """Insert or update a serialized entity."""

    def get(self, collection: str, entity_id: str) -> dict[str, Any] | None:
        """Return one serialized entity payload."""

    def list(
        self,
        collection: str,
        *,
        project_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """List serialized entity payloads."""

    def counts_by_collection(self) -> dict[str, int]:
        """Return stored row counts grouped by collection."""


def jsonable(payload: Any) -> Any:
    """Convert Pydantic contracts and nested values to JSON-compatible objects."""
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, list):
        return [jsonable(item) for item in payload]
    if isinstance(payload, dict):
        return {str(key): jsonable(value) for key, value in payload.items()}
    return payload

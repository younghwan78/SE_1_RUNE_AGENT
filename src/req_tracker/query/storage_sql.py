"""Shared SQL query spec for SoC storage-backed retrieval."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StorageQuery:
    """Parameterized SQL query prepared by a storage-backed retrieval tool."""

    tool: str
    sql: str
    params: tuple[Any, ...]

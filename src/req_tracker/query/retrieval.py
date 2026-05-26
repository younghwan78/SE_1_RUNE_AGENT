"""SoC retrieval backends."""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.graph.postgres_age_backend import PostgresAgeGraphBackend
from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.postgres_keyword_backend import PostgresKeywordSearchBackend
from req_tracker.query.storage_sql import StorageQuery
from req_tracker.vector.pgvector_backend import PgVectorSearchBackend


class SocRetrievalBackend(Protocol):
    """Retrieval backend used by the SoC query service."""

    backend_name: str

    def retrieve(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        limit: int = 50,
    ) -> list[RawSourceArtifact]:
        """Return candidate artifacts for one query slice."""


class PostgresHybridSocRetrievalBackend:
    """Hybrid AGE, pgvector, and Postgres FTS retrieval profile."""

    backend_name = "postgres_hybrid"

    def __init__(
        self,
        *,
        dsn: str = "",
        connection_factory: Callable[[], Any] | None = None,
        vector_provider: Callable[[str], list[float]] | None = None,
        graph_backend: PostgresAgeGraphBackend | None = None,
        keyword_backend: PostgresKeywordSearchBackend | None = None,
        vector_backend: PgVectorSearchBackend | None = None,
    ) -> None:
        if not dsn and connection_factory is None:
            raise ValueError("postgres dsn is required when connection_factory is not provided")
        self._dsn = dsn
        self._connection_factory = connection_factory
        self._vector_provider = vector_provider or _deterministic_query_vector
        self._graph_backend = graph_backend or PostgresAgeGraphBackend()
        self._keyword_backend = keyword_backend or PostgresKeywordSearchBackend()
        self._vector_backend = vector_backend or PgVectorSearchBackend()

    def retrieve(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        limit: int = 50,
    ) -> list[RawSourceArtifact]:
        """Execute graph, keyword, and vector retrieval and dedupe candidates."""
        if query_slice.pattern == "unknown":
            return []
        specs = self._query_specs(user_query=user_query, query_slice=query_slice, limit=limit)
        rows: list[dict[str, Any]] = []
        with self._connect() as connection:
            _prepare_age_session(connection)
            for spec in specs:
                rows.extend(_fetch_rows(connection=connection, spec=spec))
        return _dedupe_artifacts(_artifact_from_row(row) for row in rows)

    def _query_specs(
        self,
        *,
        user_query: str,
        query_slice: SocSlice,
        limit: int,
    ) -> list[StorageQuery]:
        return [
            self._graph_backend.build_slice_query(query_slice=query_slice, limit=limit),
            self._keyword_backend.build_search(
                user_query=user_query,
                query_slice=query_slice,
                limit=limit,
            ),
            self._vector_backend.build_search(
                query_vector=self._vector_provider(user_query),
                query_slice=query_slice,
                limit=limit,
            ),
        ]

    def _connect(self) -> Any:
        if self._connection_factory is not None:
            return self._connection_factory()
        return psycopg.connect(self._dsn, row_factory=dict_row)


def _prepare_age_session(connection: Any) -> None:
    connection.execute("LOAD 'age'")
    connection.execute('SET search_path = ag_catalog, "$user", public')


def _fetch_rows(*, connection: Any, spec: StorageQuery) -> list[dict[str, Any]]:
    cursor = connection.execute(spec.sql, spec.params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def _artifact_from_row(row: dict[str, Any]) -> RawSourceArtifact:
    payload = {
        "external_id": row["external_id"],
        "source_type": row["source_type"],
        "source_url": row["source_url"],
        "project_key": row["project_key"],
        "title": row["title"],
        "body_text": row["body_text"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "labels": _list_value(row.get("labels")),
        "links": _list_value(row.get("links")),
        "metadata": _mapping_value(row.get("metadata")),
    }
    return RawSourceArtifact.model_validate(payload)


def _dedupe_artifacts(artifacts: Iterable[RawSourceArtifact]) -> list[RawSourceArtifact]:
    deduped: dict[str, RawSourceArtifact] = {}
    for artifact in artifacts:
        deduped.setdefault(artifact.external_id, artifact)
    return list(deduped.values())


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        loaded = json.loads(value) if value.startswith("[") else [value]
        if isinstance(loaded, list):
            return [str(item) for item in loaded]
    return []


def _mapping_value(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        loaded = json.loads(value) if value.startswith("{") else {}
        if isinstance(loaded, dict):
            return loaded
    return {}


def _deterministic_query_vector(text: str, vector_size: int = 1024) -> list[float]:
    counts: Counter[int] = Counter()
    for raw in text.lower().split():
        token = "".join(char for char in raw if char.isalnum())
        if not token:
            continue
        counts[int(stable_hash(token)[:8], 16) % vector_size] += 1
    vector = [0.0] * vector_size
    for bucket, count in counts.items():
        vector[bucket] = float(count)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]

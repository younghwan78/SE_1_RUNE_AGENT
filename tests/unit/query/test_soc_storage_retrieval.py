"""Tests for storage-backed SoC retrieval boundaries."""

from typing import Any

from psycopg.rows import dict_row

from req_tracker.graph.postgres_age_backend import PostgresAgeGraphBackend
from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query import retrieval
from req_tracker.query.postgres_keyword_backend import PostgresKeywordSearchBackend
from req_tracker.query.retrieval import PostgresHybridSocRetrievalBackend
from req_tracker.vector.pgvector_backend import PgVectorSearchBackend


class FakeCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def execute(self, sql: str, params: object = None) -> FakeCursor:
        self.executed.append((" ".join(sql.lower().split()), params))
        return FakeCursor([_row("SOC1-JIRA-101")])


def test_postgres_keyword_backend_builds_parameterized_fts_and_trgm_sql() -> None:
    query_slice = SocSlice(
        pattern="topic_intersection",
        project_keys=["SOC-N-1"],
        concerns=["Power"],
        components=["Camera"],
    )
    spec = PostgresKeywordSearchBackend().build_search(
        user_query="camera power'; drop table soc_artifacts; --",
        query_slice=query_slice,
        limit=10,
    )

    assert "drop table" not in spec.sql.lower()
    assert "to_tsvector" in spec.sql
    assert "similarity(" in spec.sql
    assert "project_key = any" in spec.sql.lower()
    assert "soc_artifacts" in spec.sql
    assert "camera power'; drop table soc_artifacts; --" in spec.params


def test_pgvector_backend_builds_parameterized_similarity_sql() -> None:
    query_slice = SocSlice(pattern="concern_slice", project_keys=["SOC-N-1"], concerns=["Power"])
    spec = PgVectorSearchBackend().build_search(
        query_vector=[0.1, 0.2, 0.3],
        query_slice=query_slice,
        limit=5,
    )

    assert "<=>" in spec.sql
    assert "%s::vector" in spec.sql
    assert "[0.1,0.2,0.3]" in spec.params
    assert spec.params[-1] == 5


def test_postgres_age_backend_builds_parameterized_cypher_wrapper() -> None:
    query_slice = SocSlice(pattern="concern_slice", project_keys=["SOC-N-1"], concerns=["Power"])
    spec = PostgresAgeGraphBackend(graph_name="soc_graph").build_slice_query(
        query_slice=query_slice,
        limit=25,
    )

    assert "ag_catalog.cypher(%s" in spec.sql.lower()
    assert "soc_graph" in spec.params
    assert spec.params[-1] == 25
    assert "SOC-N-1" not in spec.sql
    cypher = spec.params[1]
    assert isinstance(cypher, str)
    assert "BELONGS_TO_PROJECT" in cypher
    assert "AT_LEVEL" in cypher
    assert "ADDRESSES" in cypher
    assert "INVOLVES" in cypher
    cypher_params = spec.params[2]
    assert isinstance(cypher_params, str)
    assert '"project_keys": ["SOC-N-1"]' in cypher_params
    assert '"concerns": ["Power"]' in cypher_params


def test_postgres_hybrid_retrieval_executes_storage_tools_and_dedupes_rows() -> None:
    connection = FakeConnection()
    query_slice = SocSlice(pattern="concern_slice", project_keys=["SOC-N-1"], concerns=["Power"])
    backend = PostgresHybridSocRetrievalBackend(
        connection_factory=lambda: connection,
        vector_provider=lambda _text: [0.1, 0.2, 0.3],
    )

    results = backend.retrieve(
        query_id="soc_query_storage_001",
        user_query="camera power",
        query_slice=query_slice,
        limit=5,
    )

    assert [artifact.external_id for artifact in results] == ["SOC1-JIRA-101"]
    executed_sql = " ".join(sql for sql, _ in connection.executed)
    assert "load 'age'" in executed_sql
    assert "set search_path" in executed_sql
    assert "to_tsvector" in executed_sql
    assert "ag_catalog.cypher" in executed_sql
    assert "<=>" in executed_sql


def test_postgres_hybrid_live_connection_uses_dict_row_factory(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    connection = FakeConnection()
    calls: list[dict[str, object]] = []

    def fake_connect(dsn: str, **kwargs: object) -> FakeConnection:
        calls.append({"dsn": dsn, **kwargs})
        return connection

    monkeypatch.setattr(retrieval.psycopg, "connect", fake_connect)
    backend = PostgresHybridSocRetrievalBackend(dsn="postgresql://example.invalid/soc")

    backend.retrieve(
        query_id="soc_query_storage_live_001",
        user_query="camera power",
        query_slice=SocSlice(pattern="concern_slice", project_keys=["SOC-N-1"], concerns=["Power"]),
        limit=5,
    )

    assert calls[0]["row_factory"] is dict_row


def test_postgres_hybrid_default_query_vector_matches_pgvector_schema_dimension() -> None:
    connection = FakeConnection()
    query_slice = SocSlice(pattern="concern_slice", project_keys=["SOC-N-1"], concerns=["Power"])
    backend = PostgresHybridSocRetrievalBackend(connection_factory=lambda: connection)

    backend.retrieve(
        query_id="soc_query_storage_002",
        user_query="camera power",
        query_slice=query_slice,
        limit=5,
    )

    vector_params = connection.executed[-1][1]
    assert isinstance(vector_params, tuple)
    vector_literal = vector_params[-2]
    assert isinstance(vector_literal, str)
    assert vector_literal.count(",") + 1 == 1024


def _row(external_id: str) -> dict[str, Any]:
    return {
        "external_id": external_id,
        "source_type": "jira",
        "source_url": f"https://jira.example/browse/{external_id}",
        "project_key": "SOC-N-1",
        "title": "Camera power scale storage row",
        "body_text": "Storage-backed row for Camera Power query.",
        "created_at": "2026-02-01T00:00:00+00:00",
        "updated_at": "2026-02-02T00:00:00+00:00",
        "labels": ["jira", "level/L2", "concern/power", "component/camera"],
        "links": [],
        "metadata": {
            "soc_axes": {
                "v_level": "L2",
                "concerns": ["Power"],
                "components": ["Camera"],
            }
        },
    }

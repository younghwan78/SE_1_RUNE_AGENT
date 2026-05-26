"""Tests for loading SoC fixtures into PostgreSQL profile tables."""

from req_tracker.fixtures.soc_knowledge import (
    classifications_for_artifacts,
    load_soc_seed_artifacts,
)
from req_tracker.storage.soc_postgres_loader import (
    SocPostgresFixtureLoader,
    lifecycle_events_for_artifacts,
)


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        self.executed.append((" ".join(sql.lower().split()), params))


def test_soc_postgres_loader_upserts_artifacts_classifications_and_embeddings() -> None:
    connection = FakeConnection()
    artifacts = load_soc_seed_artifacts()[:2]
    classifications = classifications_for_artifacts(
        artifacts,
        run_id="fixture_load_run",
        step_id="fixture_load_step",
    )
    loader = SocPostgresFixtureLoader(connection_factory=lambda: connection)

    counts = loader.load_fixture(
        artifacts=artifacts,
        classifications=classifications,
        embedding_model="deterministic-test",
    )

    assert counts == {
        "artifacts": 2,
        "classifications": len(classifications),
        "events": 2,
        "embeddings": 2,
    }
    executed_sql = " ".join(sql for sql, _params in connection.executed)
    assert "insert into soc_artifacts" in executed_sql
    assert "on conflict(external_id)" in executed_sql
    assert "insert into soc_classifications" in executed_sql
    assert "on conflict(artifact_id, axis, value, source)" in executed_sql
    assert "insert into soc_event_log" in executed_sql
    assert "on conflict(event_id)" in executed_sql
    assert "insert into soc_artifact_embeddings" in executed_sql
    assert "%s::vector" in executed_sql


def test_soc_postgres_loader_builds_source_linked_lifecycle_events() -> None:
    artifact = load_soc_seed_artifacts()[0]

    events = lifecycle_events_for_artifacts(
        [artifact],
        run_id="fixture_load_run",
        step_id="fixture_load_step",
    )

    assert len(events) == 1
    assert events[0].entity_id == artifact.external_id
    assert events[0].change_type == "artifact_synced"
    assert events[0].source == artifact.source_type
    assert events[0].source_url == artifact.source_url
    assert events[0].after is not None
    assert events[0].after["raw_hash"]


def test_soc_postgres_loader_upserts_lifecycle_events() -> None:
    connection = FakeConnection()
    artifact = load_soc_seed_artifacts()[0]
    events = lifecycle_events_for_artifacts(
        [artifact],
        run_id="fixture_load_run",
        step_id="fixture_load_step",
    )
    loader = SocPostgresFixtureLoader(connection_factory=lambda: connection)

    count = loader.upsert_lifecycle_events(events)

    assert count == 1
    event_params = _params_for_sql(connection, "insert into soc_event_log")
    assert event_params[0] == events[0].event_id
    assert event_params[1] == artifact.external_id
    assert event_params[2] == "artifact"
    assert event_params[4] == "artifact_synced"
    assert event_params[7] == artifact.source_type
    assert event_params[8] == "fixture_load_run"
    assert event_params[9] == "fixture_load_step"


def test_soc_postgres_loader_default_embedding_matches_pgvector_schema_dimension() -> None:
    connection = FakeConnection()
    artifact = load_soc_seed_artifacts()[0]
    loader = SocPostgresFixtureLoader(connection_factory=lambda: connection)

    loader.upsert_embeddings([artifact])

    embedding_params = _params_for_sql(connection, "insert into soc_artifact_embeddings")
    vector_literal = embedding_params[3]
    assert isinstance(vector_literal, str)
    assert vector_literal.count(",") + 1 == 1024


def _params_for_sql(connection: FakeConnection, pattern: str) -> tuple[object, ...]:
    for sql, params in connection.executed:
        if pattern in sql:
            return params
    raise AssertionError(f"missing SQL pattern: {pattern}")

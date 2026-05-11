"""PostgreSQL-backed state repository and migration runner."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from req_tracker.debug.hash import stable_hash
from req_tracker.storage.state_store import jsonable

MIGRATIONS_PACKAGE = "req_tracker.storage.migrations.postgres"


@dataclass(frozen=True)
class PostgresMigration:
    """A versioned PostgreSQL migration loaded from package resources."""

    version: str
    name: str
    sql: str


@dataclass(frozen=True)
class TypedCollectionSpec:
    """Mapping from a serialized collection payload to a typed PostgreSQL table."""

    table: str
    id_column: str
    columns: tuple[tuple[str, str], ...]


TYPED_COLLECTIONS: dict[str, TypedCollectionSpec] = {
    "agent_runs": TypedCollectionSpec(
        table="agent_runs",
        id_column="run_id",
        columns=(
            ("run_id", "run_id"),
            ("project_key", "project_key"),
            ("run_type", "run_type"),
            ("status", "status"),
            ("triggered_by", "triggered_by"),
            ("trigger_source", "trigger_source"),
            ("model_profile_id", "model_profile_id"),
            ("started_at", "started_at"),
            ("completed_at", "completed_at"),
            ("schema_version", "schema_version"),
        ),
    ),
    "agent_step_traces": TypedCollectionSpec(
        table="agent_step_traces",
        id_column="step_id",
        columns=(
            ("step_id", "step_id"),
            ("run_id", "run_id"),
            ("stage_name", "stage_name"),
            ("status", "status"),
            ("output_ref", "output_ref"),
            ("started_at", "started_at"),
            ("completed_at", "completed_at"),
            ("retry_count", "retry_count"),
            ("schema_version", "schema_version"),
        ),
    ),
    "source_artifacts": TypedCollectionSpec(
        table="source_artifacts",
        id_column="artifact_id",
        columns=(
            ("artifact_id", "artifact_id"),
            ("source_type", "source_type"),
            ("external_id", "external_id"),
            ("project_key", "project_key"),
            ("title", "title"),
            ("content_hash", "content_hash"),
            ("data_classification", "data_classification"),
            ("updated_at", "updated_at"),
            ("ingested_at", "ingested_at"),
            ("schema_version", "schema_version"),
        ),
    ),
    "artifact_chunks": TypedCollectionSpec(
        table="artifact_chunks",
        id_column="chunk_id",
        columns=(
            ("chunk_id", "chunk_id"),
            ("artifact_id", "artifact_id"),
            ("project_key", "project_key"),
            ("chunk_index", "index"),
            ("content_hash", "content_hash"),
            ("schema_version", "schema_version"),
        ),
    ),
    "graph_nodes": TypedCollectionSpec(
        table="graph_nodes",
        id_column="node_id",
        columns=(
            ("node_id", "node_id"),
            ("node_type", "node_type"),
            ("name", "name"),
            ("project_key", "project_key"),
            ("lifecycle_state", "lifecycle_state"),
            ("created_by", "created_by"),
            ("confidence_score", "confidence_score"),
            ("schema_version", "schema_version"),
        ),
    ),
    "candidate_edges": TypedCollectionSpec(
        table="candidate_edges",
        id_column="edge_id",
        columns=(
            ("edge_id", "edge_id"),
            ("source_node_id", "source_node_id"),
            ("target_node_id", "target_node_id"),
            ("relation", "relation"),
            ("approval_status", "approval_status"),
            ("confidence_score", "confidence_score"),
            ("schema_version", "schema_version"),
        ),
    ),
    "graph_edges": TypedCollectionSpec(
        table="graph_edges",
        id_column="edge_id",
        columns=(
            ("edge_id", "edge_id"),
            ("source_node_id", "source_node_id"),
            ("target_node_id", "target_node_id"),
            ("relation", "relation"),
            ("approval_status", "approval_status"),
            ("approved_by", "approved_by"),
            ("approved_at", "approved_at"),
            ("schema_version", "schema_version"),
        ),
    ),
    "graph_deltas": TypedCollectionSpec(
        table="graph_deltas",
        id_column="delta_id",
        columns=(
            ("delta_id", "delta_id"),
            ("project_key", "project_key"),
            ("created_from_run_id", "created_from_run_id"),
            ("created_from_step_id", "created_from_step_id"),
            ("schema_version", "schema_version"),
        ),
    ),
    "approval_items": TypedCollectionSpec(
        table="approval_items",
        id_column="approval_id",
        columns=(
            ("approval_id", "approval_id"),
            ("project_key", "project_key"),
            ("proposal_type", "proposal_type"),
            ("proposal_ref", "proposal_ref"),
            ("graph_delta_ref", "graph_delta_ref"),
            ("status", "status"),
            ("risk_level", "risk_level"),
            ("owner_role", "owner_role"),
            ("created_from_run_id", "created_from_run_id"),
            ("updated_at", "updated_at"),
            ("schema_version", "schema_version"),
        ),
    ),
    "findings": TypedCollectionSpec(
        table="findings",
        id_column="finding_id",
        columns=(
            ("finding_id", "finding_id"),
            ("finding_type", "finding_type"),
            ("severity", "severity"),
            ("detection_method", "detection_method"),
            ("approval_status", "approval_status"),
            ("schema_version", "schema_version"),
        ),
    ),
    "feedback_events": TypedCollectionSpec(
        table="feedback_events",
        id_column="feedback_id",
        columns=(
            ("feedback_id", "feedback_id"),
            ("target_type", "target_type"),
            ("target_id", "target_id"),
            ("action", "action"),
            ("user_id", "user_id"),
            ("user_role", "user_role"),
            ("reason_code", "reason_code"),
            ("created_at", "created_at"),
            ("schema_version", "schema_version"),
        ),
    ),
    "audit_events": TypedCollectionSpec(
        table="audit_events",
        id_column="audit_id",
        columns=(
            ("audit_id", "audit_id"),
            ("action", "action"),
            ("actor_id", "actor_id"),
            ("actor_role", "actor_role"),
            ("project_key", "project_key"),
            ("target_type", "target_type"),
            ("target_id", "target_id"),
            ("outcome", "outcome"),
            ("reason_code", "reason_code"),
            ("created_at", "created_at"),
            ("schema_version", "schema_version"),
        ),
    ),
}


def load_postgres_migrations() -> list[PostgresMigration]:
    """Load PostgreSQL migrations in filename order."""
    root = files(MIGRATIONS_PACKAGE)
    migrations: list[PostgresMigration] = []
    for resource in sorted(root.iterdir(), key=lambda item: item.name):
        if not resource.name.endswith(".sql"):
            continue
        version = resource.name.split("_", maxsplit=1)[0]
        migrations.append(
            PostgresMigration(
                version=version,
                name=resource.name,
                sql=resource.read_text(encoding="utf-8"),
            )
        )
    return migrations


class PostgreSQLStateStore:
    """Persist state contracts into PostgreSQL with migration tracking.

    The first production step keeps the same serialized contract shape as SQLite.
    Typed table repositories can be introduced later behind this same contract.
    """

    def __init__(
        self,
        dsn: str,
        *,
        auto_migrate: bool = True,
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        if not dsn and connection_factory is None:
            raise ValueError("postgres dsn is required when connection_factory is not provided")
        self.dsn = dsn
        self._connection_factory = connection_factory
        if auto_migrate:
            self.apply_migrations()

    def apply_migrations(self) -> None:
        """Apply unapplied package migrations."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            for migration in load_postgres_migrations():
                applied = conn.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s",
                    (migration.version,),
                ).fetchone()
                if applied is not None:
                    continue
                for statement in _split_sql_statements(migration.sql):
                    conn.execute(statement)
                conn.execute(
                    """
                    INSERT INTO schema_migrations(version, name, applied_at)
                    VALUES (%s, %s, %s)
                    """,
                    (migration.version, migration.name, datetime.now(UTC)),
                )

    def upsert(
        self,
        *,
        collection: str,
        entity_id: str,
        payload: Any,
        project_key: str | None = None,
    ) -> None:
        """Insert or update a serialized entity."""
        normalized = jsonable(payload)
        now = datetime.now(UTC)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO state_entities (
                    collection, entity_id, project_key, payload_json,
                    payload_hash, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(collection, entity_id)
                DO UPDATE SET
                    project_key = excluded.project_key,
                    payload_json = excluded.payload_json,
                    payload_hash = excluded.payload_hash,
                    updated_at = excluded.updated_at
                """,
                (
                    collection,
                    entity_id,
                    project_key,
                    Jsonb(normalized),
                    stable_hash(normalized),
                    now,
                    now,
                ),
            )
            _upsert_typed_entity(conn, collection, normalized)

    def get(self, collection: str, entity_id: str) -> dict[str, Any] | None:
        """Return one serialized entity payload."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM state_entities
                WHERE collection = %s AND entity_id = %s
                """,
                (collection, entity_id),
            ).fetchone()
        if row is None:
            return None
        loaded = row["payload_json"]
        if not isinstance(loaded, dict):
            raise TypeError("stored entity payload must be an object")
        return loaded

    def list(
        self,
        collection: str,
        *,
        project_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """List serialized entity payloads in deterministic order."""
        sql = "SELECT payload_json FROM state_entities WHERE collection = %s"
        params: list[str] = [collection]
        if project_key is not None:
            sql += " AND project_key = %s"
            params.append(project_key)
        sql += " ORDER BY entity_id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_payload_from_row(row) for row in rows]

    def counts_by_collection(self) -> dict[str, int]:
        """Return stored row counts grouped by collection."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT collection, COUNT(*) AS count
                FROM state_entities
                GROUP BY collection
                ORDER BY collection
                """
            ).fetchall()
        return {str(row["collection"]): int(row["count"]) for row in rows}

    def _connect(self) -> Any:
        if self._connection_factory is not None:
            return self._connection_factory()
        return psycopg.connect(self.dsn, row_factory=dict_row)


def _payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    loaded = row["payload_json"]
    if not isinstance(loaded, dict):
        raise TypeError("stored entity payload must be an object")
    return loaded


def _split_sql_statements(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def _upsert_typed_entity(conn: Any, collection: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    spec = TYPED_COLLECTIONS.get(collection)
    if spec is None:
        return
    columns = [column for column, _payload_key in spec.columns]
    insert_columns = [*columns, "payload_json"]
    placeholders = ", ".join(["%s"] * len(insert_columns))
    assignments = ", ".join(
        f"{column} = excluded.{column}" for column in insert_columns if column != spec.id_column
    )
    sql = (
        f"INSERT INTO {spec.table} ({', '.join(insert_columns)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT({spec.id_column}) DO UPDATE SET {assignments}"
    )
    values = [payload.get(payload_key) for _column, payload_key in spec.columns]
    conn.execute(sql, (*values, Jsonb(payload)))

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

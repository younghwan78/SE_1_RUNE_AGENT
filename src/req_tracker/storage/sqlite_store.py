"""SQLite-backed state repository for local production-shape validation."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from req_tracker.debug.hash import stable_hash
from req_tracker.storage.state_store import jsonable


class SQLiteStateStore:
    """Persist Pydantic contracts in a compact SQLite key/value repository.

    This is intentionally generic. The production PostgreSQL schema can later split
    each collection into typed tables while keeping the same serialized contracts.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

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
        payload_json = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO state_entities (
                    collection, entity_id, project_key, payload_json,
                    payload_hash, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
                    payload_json,
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
                WHERE collection = ? AND entity_id = ?
                """,
                (collection, entity_id),
            ).fetchone()
        if row is None:
            return None
        loaded = json.loads(str(row["payload_json"]))
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
        sql = "SELECT payload_json FROM state_entities WHERE collection = ?"
        params: list[str] = [collection]
        if project_key is not None:
            sql += " AND project_key = ?"
            params.append(project_key)
        sql += " ORDER BY entity_id"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

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

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS state_entities (
                    collection TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    project_key TEXT,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (collection, entity_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_state_entities_project
                ON state_entities(collection, project_key)
                """
            )

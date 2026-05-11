"""PostgreSQL state repository tests."""

from typing import Any

from psycopg.types.json import Jsonb

from req_tracker.audit.models import AuditRetentionPolicy
from req_tracker.audit.service import AuditService
from req_tracker.debug.models import AgentRun
from req_tracker.storage.postgres_store import (
    PostgreSQLStateStore,
    load_postgres_migrations,
    load_postgres_rollbacks,
)


class FakeCursor:
    def __init__(
        self,
        *,
        one: dict[str, Any] | tuple[int] | None = None,
        many: list[dict[str, Any]] | None = None,
    ) -> None:
        self._one = one
        self._many = many or []

    def fetchone(self) -> dict[str, Any] | tuple[int] | None:
        return self._one

    def fetchall(self) -> list[dict[str, Any]]:
        return self._many


class FakePostgresConnection:
    def __init__(self) -> None:
        self.entities: dict[tuple[str, str], dict[str, Any]] = {}
        self.typed_entities: dict[tuple[str, str], dict[str, Any]] = {}
        self.audit_archives: dict[str, dict[str, Any]] = {}
        self.migrations: set[str] = set()
        self.executed_sql: list[str] = []

    def __enter__(self) -> "FakePostgresConnection":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def execute(self, query: str, params: object = None) -> FakeCursor:
        sql = " ".join(query.lower().split())
        self.executed_sql.append(sql)
        if "select 1 from schema_migrations" in sql:
            version = _params(params)[0]
            return FakeCursor(one=(1,) if version in self.migrations else None)
        if "insert into schema_migrations" in sql:
            version = str(_params(params)[0])
            self.migrations.add(version)
            return FakeCursor()
        if "delete from schema_migrations" in sql:
            version = str(_params(params)[0])
            self.migrations.discard(version)
            return FakeCursor()
        if "insert into state_entities" in sql:
            collection, entity_id, project_key, payload_json, payload_hash, *_ = _params(params)
            assert isinstance(payload_json, Jsonb)
            self.entities[(str(collection), str(entity_id))] = {
                "collection": collection,
                "entity_id": entity_id,
                "project_key": project_key,
                "payload_json": payload_json.obj,
                "payload_hash": payload_hash,
            }
            return FakeCursor()
        if sql.startswith("insert into agent_runs"):
            run_id = str(_params(params)[0])
            payload_json = _params(params)[-1]
            assert isinstance(payload_json, Jsonb)
            self.typed_entities[("agent_runs", run_id)] = {
                "project_key": _params(params)[1],
                "payload_json": payload_json.obj,
            }
            return FakeCursor()
        if sql.startswith("insert into audit_archive_batches"):
            archive_id, archive_ref, policy_json, event_ids, archived_events, *_ = _params(params)
            assert isinstance(policy_json, Jsonb)
            self.audit_archives[str(archive_id)] = {
                "archive_ref": archive_ref,
                "policy_json": policy_json.obj,
                "event_ids": event_ids,
                "archived_events": archived_events,
            }
            return FakeCursor()
        if sql.startswith("delete from audit_events"):
            audit_id = str(_params(params)[0])
            self.typed_entities.pop(("audit_events", audit_id), None)
            return FakeCursor()
        if sql.startswith("delete from state_entities"):
            collection, entity_id = _params(params)
            self.entities.pop((str(collection), str(entity_id)), None)
            return FakeCursor()
        if sql.startswith("select payload_json from agent_runs where run_id"):
            run_id = str(_params(params)[0])
            row = self.typed_entities.get(("agent_runs", run_id))
            return FakeCursor(one=None if row is None else {"payload_json": row["payload_json"]})
        if sql.startswith("select payload_json from agent_runs"):
            rows = [
                {"payload_json": row["payload_json"]}
                for (_table, _entity_id), row in sorted(self.typed_entities.items())
                if row["project_key"] == _params(params)[0]
            ]
            return FakeCursor(many=rows)
        if "select payload_json from state_entities" in sql and "order by entity_id" not in sql:
            collection, entity_id = _params(params)
            row = self.entities.get((str(collection), str(entity_id)))
            return FakeCursor(one=None if row is None else {"payload_json": row["payload_json"]})
        if "select payload_json from state_entities" in sql:
            values = [
                row
                for row in self.entities.values()
                if row["collection"] == _params(params)[0]
                and (len(_params(params)) == 1 or row["project_key"] == _params(params)[1])
            ]
            rows = [
                {"payload_json": row["payload_json"]}
                for row in sorted(values, key=lambda row: row["entity_id"])
            ]
            return FakeCursor(many=rows)
        if "select collection, count(*) as count" in sql:
            counts: dict[str, int] = {}
            for row in self.entities.values():
                counts[str(row["collection"])] = counts.get(str(row["collection"]), 0) + 1
            rows = [
                {"collection": collection, "count": count}
                for collection, count in sorted(counts.items())
            ]
            return FakeCursor(many=rows)
        return FakeCursor()


def test_load_postgres_migrations_returns_ordered_state_schema() -> None:
    migrations = load_postgres_migrations()

    assert [migration.version for migration in migrations] == ["001", "002", "003"]
    assert "CREATE TABLE IF NOT EXISTS state_entities" in migrations[0].sql
    assert "JSONB" in migrations[0].sql
    assert "CREATE TABLE IF NOT EXISTS agent_runs" in migrations[1].sql
    assert "CREATE TABLE IF NOT EXISTS audit_events" in migrations[1].sql
    assert "CREATE TABLE IF NOT EXISTS audit_archive_batches" in migrations[2].sql


def test_load_postgres_rollbacks_returns_versioned_scripts() -> None:
    rollbacks = load_postgres_rollbacks()

    assert sorted(rollbacks) == ["001", "002", "003"]
    assert "DROP TABLE IF EXISTS agent_runs" in rollbacks["002"].sql
    assert "DROP TABLE IF EXISTS audit_archive_batches" in rollbacks["003"].sql


def test_postgres_store_applies_migrations_and_matches_state_contract() -> None:
    fake = FakePostgresConnection()
    store = PostgreSQLStateStore("", connection_factory=lambda: fake)
    run = AgentRun(
        run_id="run_postgres_1",
        run_type="analysis",
        project_key="RUNE_CAM_ALPHA",
        triggered_by="tester",
        trigger_source="manual",
    )

    store.upsert(
        collection="agent_runs",
        entity_id=run.run_id,
        project_key=run.project_key,
        payload=run,
    )

    assert fake.migrations == {"001", "002", "003"}
    assert any("insert into agent_runs" in sql for sql in fake.executed_sql)
    stored = store.get("agent_runs", run.run_id)
    assert stored is not None
    assert stored["run_id"] == "run_postgres_1"
    stored_runs = store.list("agent_runs", project_key="RUNE_CAM_ALPHA")
    assert stored_runs[0]["project_key"] == "RUNE_CAM_ALPHA"
    assert store.counts_by_collection() == {"agent_runs": 1}


def test_postgres_store_rolls_back_one_applied_migration() -> None:
    fake = FakePostgresConnection()
    store = PostgreSQLStateStore("", connection_factory=lambda: fake)

    rolled_back = store.rollback_migration("002")

    assert rolled_back is True
    assert "002" not in fake.migrations
    assert any("drop table if exists agent_runs" in sql for sql in fake.executed_sql)


def test_postgres_store_writes_audit_archive_batches_and_deletes_events() -> None:
    fake = FakePostgresConnection()
    store = PostgreSQLStateStore("", connection_factory=lambda: fake)
    service = AuditService()
    event = service.record(
        action="run_completed",
        actor_id="system",
        target_type="run",
        target_id="run_archive_1",
        project_key="RUNE_CAM_ALPHA",
    )
    store.upsert(
        collection="audit_events",
        entity_id=event.audit_id,
        project_key=event.project_key,
        payload=event,
    )

    archive_ref = store.write_audit_archive(
        events=[event],
        policy=AuditRetentionPolicy(retention_days=30, max_events=1),
    )
    store.delete("audit_events", event.audit_id)

    assert archive_ref is not None
    assert archive_ref.startswith("postgres://audit_archive_batches/")
    assert len(fake.audit_archives) == 1
    archive = next(iter(fake.audit_archives.values()))
    assert archive["event_ids"] == [event.audit_id]
    assert archive["archived_events"] == 1
    assert ("audit_events", event.audit_id) not in fake.entities
    assert any("delete from audit_events" in sql for sql in fake.executed_sql)


def _params(params: object) -> tuple[Any, ...]:
    assert isinstance(params, list | tuple)
    return tuple(params)

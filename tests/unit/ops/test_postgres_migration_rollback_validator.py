"""PostgreSQL migration rollback validator tests."""

import importlib.util
from pathlib import Path
from types import ModuleType

from req_tracker.storage.postgres_store import PostgresMigration


def test_committed_postgres_migrations_have_rollback_coverage() -> None:
    validator = _load_validator_module()

    report = validator.validate_rollbacks()

    assert report["passed"] is True
    assert report["failure_count"] == 0
    assert "001:state_entities" in report["checked_tables"]
    assert "005:scheduler_leases" in report["checked_tables"]


def test_rollback_validator_reports_missing_rollback_and_drop() -> None:
    validator = _load_validator_module()
    migrations = [
        PostgresMigration(
            version="001",
            name="001_a.sql",
            sql="CREATE TABLE IF NOT EXISTS alpha (id TEXT PRIMARY KEY);",
        ),
        PostgresMigration(
            version="002",
            name="002_b.sql",
            sql="CREATE TABLE IF NOT EXISTS beta (id TEXT PRIMARY KEY);",
        ),
    ]
    rollbacks = {
        "001": PostgresMigration(
            version="001",
            name="001_a.sql",
            sql="DROP TABLE IF EXISTS different_table;",
        ),
        "003": PostgresMigration(
            version="003",
            name="003_orphan.sql",
            sql="DROP TABLE IF EXISTS orphan;",
        ),
    }

    report = validator.validate_rollbacks(migrations, rollbacks)

    assert report["passed"] is False
    assert "001:alpha:missing_drop" in report["failures"]
    assert "002:missing_rollback" in report["failures"]
    assert "003:orphan_rollback" in report["failures"]


def _load_validator_module() -> ModuleType:
    module_path = Path("ops/rehearsal/validate_postgres_migration_rollbacks.py")
    spec = importlib.util.spec_from_file_location(
        "validate_postgres_migration_rollbacks",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

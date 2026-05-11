"""Validate PostgreSQL migration rollback coverage."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from req_tracker.storage.postgres_store import (
    PostgresMigration,
    load_postgres_migrations,
    load_postgres_rollbacks,
)

CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(?P<table>\w+)",
    re.IGNORECASE,
)
DROP_TABLE_PATTERN = re.compile(
    r"DROP\s+TABLE\s+IF\s+EXISTS\s+(?P<table>\w+)",
    re.IGNORECASE,
)


def validate_rollbacks(
    migrations: Sequence[PostgresMigration] | None = None,
    rollbacks: Mapping[str, PostgresMigration] | None = None,
) -> dict[str, Any]:
    """Return a structured validation report for migration rollback coverage."""
    loaded_migrations = list(migrations) if migrations is not None else load_postgres_migrations()
    loaded_rollbacks = dict(rollbacks) if rollbacks is not None else load_postgres_rollbacks()
    failures: list[str] = []
    migration_versions = {migration.version for migration in loaded_migrations}
    rollback_versions = set(loaded_rollbacks)
    for version in sorted(migration_versions - rollback_versions):
        failures.append(f"{version}:missing_rollback")
    for version in sorted(rollback_versions - migration_versions):
        failures.append(f"{version}:orphan_rollback")
    checked_tables: list[str] = []
    for migration in loaded_migrations:
        rollback = loaded_rollbacks.get(migration.version)
        if rollback is None:
            continue
        created_tables = _created_tables(migration.sql)
        dropped_tables = _dropped_tables(rollback.sql)
        checked_tables.extend(f"{migration.version}:{table}" for table in sorted(created_tables))
        for table in sorted(created_tables - dropped_tables):
            failures.append(f"{migration.version}:{table}:missing_drop")
    return {
        "checked_tables": checked_tables,
        "failure_count": len(failures),
        "failures": failures,
        "migration_versions": sorted(migration_versions),
        "passed": not failures,
        "rollback_versions": sorted(rollback_versions),
        "schema_version": "v1",
    }


def _created_tables(sql: str) -> set[str]:
    return {match.group("table").lower() for match in CREATE_TABLE_PATTERN.finditer(sql)}


def _dropped_tables(sql: str) -> set[str]:
    return {match.group("table").lower() for match in DROP_TABLE_PATTERN.finditer(sql)}


def main() -> int:
    """CLI entrypoint."""
    report = validate_rollbacks()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

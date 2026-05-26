"""Validate SoC PostgreSQL/AGE/pgvector profile migrations."""

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from req_tracker.storage.postgres_store import (
    PostgresMigration,
    load_postgres_migrations,
    load_postgres_rollbacks,
)


@dataclass(frozen=True)
class MigrationRequirement:
    """Static readiness requirements for one SoC PostgreSQL migration."""

    version: str
    extensions: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    indexes: tuple[str, ...] = ()
    graphs: tuple[str, ...] = ()


REQUIREMENTS: tuple[MigrationRequirement, ...] = (
    MigrationRequirement(
        version="011",
        extensions=("pg_trgm",),
        tables=("soc_artifacts", "soc_classifications", "soc_event_log", "soc_eval_runs"),
        indexes=(
            "idx_soc_artifacts_fts",
            "idx_soc_artifacts_trgm",
            "idx_soc_classifications_axis_value",
            "idx_soc_event_log_entity_ts",
            "idx_soc_eval_runs_mode_started",
        ),
    ),
    MigrationRequirement(
        version="012",
        extensions=("vector",),
        tables=("soc_artifact_embeddings",),
        indexes=("idx_soc_artifact_embeddings_vector",),
    ),
    MigrationRequirement(
        version="013",
        extensions=("age",),
        graphs=("soc_graph",),
    ),
)


def validate_soc_postgres_profile(
    migrations: Sequence[PostgresMigration] | None = None,
    rollbacks: Mapping[str, PostgresMigration] | None = None,
) -> dict[str, Any]:
    """Return a structured static readiness report for the SoC Postgres profile."""
    loaded_migrations = list(migrations) if migrations is not None else load_postgres_migrations()
    loaded_rollbacks = dict(rollbacks) if rollbacks is not None else load_postgres_rollbacks()
    migration_by_version = {migration.version: migration for migration in loaded_migrations}
    failures: list[str] = []
    checked_tables: set[str] = set()
    checked_indexes: set[str] = set()
    checked_graphs: set[str] = set()

    for requirement in REQUIREMENTS:
        migration = migration_by_version.get(requirement.version)
        rollback = loaded_rollbacks.get(requirement.version)
        if migration is None:
            failures.append(f"{requirement.version}:missing_migration")
            _record_missing_requirement_failures(requirement, failures)
            continue

        sql = migration.sql
        _validate_extensions(requirement, sql, failures)
        _validate_tables(requirement, sql, checked_tables, failures)
        _validate_indexes(requirement, sql, checked_indexes, failures)
        _validate_graphs(requirement, sql, checked_graphs, failures)

        if rollback is None:
            failures.append(f"{requirement.version}:missing_rollback")
            continue
        _validate_rollback(requirement, rollback.sql, failures)

    required_extensions = sorted(
        {extension for requirement in REQUIREMENTS for extension in requirement.extensions}
    )
    required_versions = [requirement.version for requirement in REQUIREMENTS]
    return {
        "checked_graphs": sorted(checked_graphs),
        "checked_indexes": sorted(checked_indexes),
        "checked_tables": sorted(checked_tables),
        "failure_count": len(failures),
        "failures": failures,
        "passed": not failures,
        "required_extensions": required_extensions,
        "required_migration_versions": required_versions,
        "schema_version": "v1",
    }


def _record_missing_requirement_failures(
    requirement: MigrationRequirement,
    failures: list[str],
) -> None:
    for extension in requirement.extensions:
        failures.append(f"{requirement.version}:missing_extension:{extension}")
    for table in requirement.tables:
        failures.append(f"{requirement.version}:missing_table:{table}")
    for index in requirement.indexes:
        failures.append(f"{requirement.version}:missing_index:{index}")
    for graph in requirement.graphs:
        failures.append(f"{requirement.version}:missing_graph:{graph}")


def _validate_extensions(
    requirement: MigrationRequirement,
    sql: str,
    failures: list[str],
) -> None:
    for extension in requirement.extensions:
        pattern = rf"CREATE\s+EXTENSION\s+IF\s+NOT\s+EXISTS\s+{re.escape(extension)}\b"
        if re.search(pattern, sql, flags=re.IGNORECASE) is None:
            failures.append(f"{requirement.version}:missing_extension:{extension}")
    if "CREATE EXTENSION" in sql.upper() and "EXCEPTION WHEN" in sql.upper():
        failures.append(f"{requirement.version}:extension_error_swallowed")


def _validate_tables(
    requirement: MigrationRequirement,
    sql: str,
    checked_tables: set[str],
    failures: list[str],
) -> None:
    for table in requirement.tables:
        if _contains_create_table(sql, table):
            checked_tables.add(table)
        else:
            failures.append(f"{requirement.version}:missing_table:{table}")


def _validate_indexes(
    requirement: MigrationRequirement,
    sql: str,
    checked_indexes: set[str],
    failures: list[str],
) -> None:
    for index in requirement.indexes:
        if _contains_create_index(sql, index):
            checked_indexes.add(index)
        else:
            failures.append(f"{requirement.version}:missing_index:{index}")


def _validate_graphs(
    requirement: MigrationRequirement,
    sql: str,
    checked_graphs: set[str],
    failures: list[str],
) -> None:
    for graph in requirement.graphs:
        pattern = rf"create_graph\(\s*'{re.escape(graph)}'\s*\)"
        if re.search(pattern, sql, flags=re.IGNORECASE) is not None:
            checked_graphs.add(graph)
        else:
            failures.append(f"{requirement.version}:missing_graph:{graph}")


def _validate_rollback(
    requirement: MigrationRequirement,
    rollback_sql: str,
    failures: list[str],
) -> None:
    for table in requirement.tables:
        if not _contains_drop_table(rollback_sql, table):
            failures.append(f"{requirement.version}:{table}:missing_rollback_drop")
    for graph in requirement.graphs:
        pattern = rf"drop_graph\(\s*'{re.escape(graph)}'\s*,\s*true\s*\)"
        if re.search(pattern, rollback_sql, flags=re.IGNORECASE) is None:
            failures.append(f"{requirement.version}:{graph}:missing_rollback_drop")


def _contains_create_table(sql: str, table: str) -> bool:
    pattern = rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table)}\b"
    return re.search(pattern, sql, flags=re.IGNORECASE) is not None


def _contains_drop_table(sql: str, table: str) -> bool:
    pattern = rf"DROP\s+TABLE\s+IF\s+EXISTS\s+{re.escape(table)}\b"
    return re.search(pattern, sql, flags=re.IGNORECASE) is not None


def _contains_create_index(sql: str, index: str) -> bool:
    pattern = rf"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+{re.escape(index)}\b"
    return re.search(pattern, sql, flags=re.IGNORECASE) is not None


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json",), default="json")
    parser.parse_args()
    report = validate_soc_postgres_profile()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

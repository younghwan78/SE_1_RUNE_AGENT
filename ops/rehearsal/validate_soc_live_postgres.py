"""Validate a live PostgreSQL database for the SoC Knowledge storage profile."""

import argparse
import json
import os
from collections.abc import Callable
from typing import Any

import psycopg
from psycopg.rows import dict_row

from req_tracker.storage.postgres_store import PostgreSQLStateStore

REQUIRED_EXTENSIONS = ("pg_trgm", "vector", "age")
REQUIRED_TABLES = (
    "soc_artifacts",
    "soc_classifications",
    "soc_event_log",
    "soc_eval_runs",
    "soc_artifact_embeddings",
)
REQUIRED_INDEXES = (
    "idx_soc_artifacts_fts",
    "idx_soc_artifacts_trgm",
    "idx_soc_classifications_axis_value",
    "idx_soc_event_log_entity_ts",
    "idx_soc_eval_runs_mode_started",
    "idx_soc_artifact_embeddings_vector",
)
REQUIRED_GRAPHS = ("soc_graph",)


def validate_soc_live_postgres(
    *,
    dsn: str,
    apply_migrations: bool = False,
    connection_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Return live SoC PostgreSQL profile readiness without leaking the DSN."""
    if not dsn and connection_factory is None:
        return {
            "applied_migrations": False,
            "checked_extensions": [],
            "checked_indexes": [],
            "checked_tables": [],
            "checked_graphs": [],
            "dsn_provided": False,
            "failure_count": 1,
            "failures": ["POSTGRES_DSN or POSTGRES_TEST_DSN is required"],
            "missing_graphs": list(REQUIRED_GRAPHS),
            "missing_indexes": list(REQUIRED_INDEXES),
            "missing_tables": list(REQUIRED_TABLES),
            "passed": False,
            "schema_version": "v1",
            "status": "skipped",
        }

    failures: list[str] = []
    if apply_migrations:
        try:
            PostgreSQLStateStore(dsn, migration_profile="soc")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"migration_apply_failed:{type(exc).__name__}:{exc}")

    try:
        with _connect(dsn, connection_factory) as conn:
            server_version = _server_version(conn)
            checked_extensions, extension_failures = _check_extensions(conn)
            checked_tables, missing_tables = _check_named_objects(
                conn,
                sql="""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = ANY(%s)
                """,
                param_values=REQUIRED_TABLES,
                row_key="table_name",
            )
            checked_indexes, missing_indexes = _check_named_objects(
                conn,
                sql="""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND indexname = ANY(%s)
                """,
                param_values=REQUIRED_INDEXES,
                row_key="indexname",
            )
            checked_graphs, missing_graphs = _check_age_graphs(conn)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"connection_or_introspection_failed:{type(exc).__name__}:{exc}")
        return {
            "applied_migrations": apply_migrations and not failures,
            "checked_extensions": [],
            "checked_indexes": [],
            "checked_tables": [],
            "checked_graphs": [],
            "dsn_provided": bool(dsn),
            "failure_count": len(failures),
            "failures": failures,
            "missing_graphs": list(REQUIRED_GRAPHS),
            "missing_indexes": list(REQUIRED_INDEXES),
            "missing_tables": list(REQUIRED_TABLES),
            "passed": False,
            "schema_version": "v1",
            "server_version": None,
            "status": "failed",
        }

    failures.extend(extension_failures)
    failures.extend(f"missing_table:{name}" for name in missing_tables)
    failures.extend(f"missing_index:{name}" for name in missing_indexes)
    failures.extend(f"missing_graph:{name}" for name in missing_graphs)
    status = "passed" if not failures else "failed"
    return {
        "applied_migrations": apply_migrations and not failures,
        "checked_extensions": checked_extensions,
        "checked_indexes": checked_indexes,
        "checked_tables": checked_tables,
        "checked_graphs": checked_graphs,
        "dsn_provided": bool(dsn),
        "failure_count": len(failures),
        "failures": failures,
        "missing_graphs": missing_graphs,
        "missing_indexes": missing_indexes,
        "missing_tables": missing_tables,
        "passed": status == "passed",
        "schema_version": "v1",
        "server_version": server_version,
        "status": status,
    }


def _connect(dsn: str, connection_factory: Callable[[], Any] | None) -> Any:
    if connection_factory is not None:
        return connection_factory()
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)


def _server_version(conn: Any) -> str:
    row = conn.execute("SELECT version() AS version").fetchone()
    if not isinstance(row, dict):
        return "unknown"
    return str(row.get("version") or "unknown")


def _check_extensions(conn: Any) -> tuple[list[dict[str, Any]], list[str]]:
    rows = conn.execute(
        """
        SELECT
            name,
            true AS available,
            installed_version IS NOT NULL AS installed
        FROM pg_available_extensions
        WHERE name = ANY(%s)
        """,
        (list(REQUIRED_EXTENSIONS),),
    ).fetchall()
    by_name = {str(row["name"]): row for row in rows if isinstance(row, dict)}
    checked: list[dict[str, Any]] = []
    failures: list[str] = []
    for extension in REQUIRED_EXTENSIONS:
        row = by_name.get(extension)
        if row is None:
            checked.append({"available": False, "installed": False, "name": extension})
            failures.append(f"extension_unavailable:{extension}")
            continue
        available = bool(row.get("available"))
        installed = bool(row.get("installed"))
        checked.append({"available": available, "installed": installed, "name": extension})
        if not available:
            failures.append(f"extension_unavailable:{extension}")
        elif not installed:
            failures.append(f"extension_not_installed:{extension}")
    return checked, failures


def _check_named_objects(
    conn: Any,
    *,
    sql: str,
    param_values: tuple[str, ...],
    row_key: str,
) -> tuple[list[str], list[str]]:
    rows = conn.execute(sql, (list(param_values),)).fetchall()
    found = sorted(str(row[row_key]) for row in rows if isinstance(row, dict))
    missing = [name for name in param_values if name not in found]
    return found, missing


def _check_age_graphs(conn: Any) -> tuple[list[str], list[str]]:
    try:
        rows = conn.execute(
            """
            SELECT name
            FROM ag_catalog.ag_graph
            WHERE name = ANY(%s)
            """,
            (list(REQUIRED_GRAPHS),),
        ).fetchall()
    except Exception:  # noqa: BLE001
        return [], list(REQUIRED_GRAPHS)
    found = sorted(str(row["name"]) for row in rows if isinstance(row, dict))
    missing = [name for name in REQUIRED_GRAPHS if name not in found]
    return found, missing


def _env_dsn() -> str:
    return os.getenv("POSTGRES_TEST_DSN") or os.getenv("POSTGRES_DSN") or ""


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default=_env_dsn())
    parser.add_argument("--apply-migrations", action="store_true")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Return non-zero when no DSN is configured.",
    )
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()
    report = validate_soc_live_postgres(
        dsn=args.dsn,
        apply_migrations=args.apply_migrations,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "skipped" and not args.require_live:
        return 0
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

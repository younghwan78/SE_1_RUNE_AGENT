"""Validate PostgreSQL typed mirror specs against packaged migration DDL."""

import json
import re
from collections.abc import Sequence
from typing import Any

from req_tracker.storage.postgres_store import TYPED_COLLECTIONS, load_postgres_migrations

CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(?P<table>\w+)\s*\((?P<body>.*?)\);",
    re.IGNORECASE | re.DOTALL,
)
CONSTRAINT_PREFIXES = ("constraint", "primary", "unique", "foreign", "check")


def validate_typed_mirrors(sql_scripts: Sequence[str] | None = None) -> dict[str, Any]:
    """Return a structured typed-mirror validation report."""
    scripts = sql_scripts
    if scripts is None:
        scripts = [migration.sql for migration in load_postgres_migrations()]
    tables = _parse_tables("\n".join(scripts))
    failures: list[str] = []
    checked_tables: list[str] = []
    for collection, spec in sorted(TYPED_COLLECTIONS.items()):
        checked_tables.append(spec.table)
        table_columns = tables.get(spec.table)
        if table_columns is None:
            failures.append(f"{collection}:{spec.table}:missing_table")
            continue
        required_columns = {column for column, _payload_key in spec.columns}
        required_columns.add("payload_json")
        required_columns.add(spec.id_column)
        missing_columns = sorted(required_columns - table_columns)
        failures.extend(
            f"{collection}:{spec.table}:missing_column:{column}" for column in missing_columns
        )
    return {
        "checked_tables": checked_tables,
        "failure_count": len(failures),
        "failures": failures,
        "passed": not failures,
        "schema_version": "v1",
    }


def _parse_tables(sql: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for match in CREATE_TABLE_PATTERN.finditer(sql):
        table = match.group("table")
        body = match.group("body")
        tables[table] = _parse_columns(body)
    return tables


def _parse_columns(table_body: str) -> set[str]:
    columns: set[str] = set()
    for line in table_body.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped:
            continue
        name = stripped.split(maxsplit=1)[0].strip('"').lower()
        if name in CONSTRAINT_PREFIXES:
            continue
        columns.add(name)
    return columns


def main() -> int:
    """CLI entrypoint."""
    report = validate_typed_mirrors()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

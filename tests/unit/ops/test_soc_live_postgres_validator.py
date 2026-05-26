"""Live SoC PostgreSQL profile validator tests."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


class FakeCursor:
    def __init__(
        self,
        *,
        one: dict[str, Any] | None = None,
        many: list[dict[str, Any]] | None = None,
    ) -> None:
        self._one = one
        self._many = many or []

    def fetchone(self) -> dict[str, Any] | None:
        return self._one

    def fetchall(self) -> list[dict[str, Any]]:
        return self._many


class FakeSocLiveConnection:
    def __init__(
        self,
        *,
        extensions: dict[str, tuple[bool, bool]] | None = None,
        tables: set[str] | None = None,
        indexes: set[str] | None = None,
        graphs: set[str] | None = None,
    ) -> None:
        self.extensions = extensions if extensions is not None else {
            "pg_trgm": (True, True),
            "vector": (True, True),
            "age": (True, True),
        }
        self.tables = tables if tables is not None else {
            "soc_artifacts",
            "soc_classifications",
            "soc_event_log",
            "soc_eval_runs",
            "soc_artifact_embeddings",
        }
        self.indexes = indexes if indexes is not None else {
            "idx_soc_artifacts_fts",
            "idx_soc_artifacts_trgm",
            "idx_soc_classifications_axis_value",
            "idx_soc_event_log_entity_ts",
            "idx_soc_eval_runs_mode_started",
            "idx_soc_artifact_embeddings_vector",
        }
        self.graphs = graphs if graphs is not None else {"soc_graph"}

    def __enter__(self) -> "FakeSocLiveConnection":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def execute(self, query: str, params: object = None) -> FakeCursor:
        sql = " ".join(query.lower().split())
        if "select version()" in sql:
            return FakeCursor(one={"version": "PostgreSQL 16 fake"})
        names = set(_params(params))
        if "from pg_available_extensions" in sql:
            return FakeCursor(
                many=[
                    {
                        "name": name,
                        "available": available,
                        "installed": installed,
                    }
                    for name, (available, installed) in sorted(self.extensions.items())
                    if name in names
                ]
            )
        if "from information_schema.tables" in sql:
            return FakeCursor(
                many=[{"table_name": name} for name in sorted(self.tables & names)]
            )
        if "from pg_indexes" in sql:
            return FakeCursor(
                many=[{"indexname": name} for name in sorted(self.indexes & names)]
            )
        if "from ag_catalog.ag_graph" in sql:
            return FakeCursor(many=[{"name": name} for name in sorted(self.graphs & names)])
        raise AssertionError(f"unexpected SQL: {query}")


def test_soc_live_postgres_validator_skips_without_dsn_or_connection() -> None:
    validator = _load_validator()

    report = validator.validate_soc_live_postgres(dsn="")

    assert report["status"] == "skipped"
    assert report["passed"] is False
    assert "POSTGRES_DSN or POSTGRES_TEST_DSN is required" in report["failures"]


def test_soc_live_postgres_validator_passes_for_complete_profile() -> None:
    validator = _load_validator()

    report = validator.validate_soc_live_postgres(
        dsn="postgresql://example.invalid/rehearsal",
        connection_factory=lambda: FakeSocLiveConnection(),
    )

    assert report["status"] == "passed"
    assert report["passed"] is True
    assert report["missing_tables"] == []
    assert report["missing_indexes"] == []
    assert report["missing_graphs"] == []
    assert {item["name"] for item in report["checked_extensions"]} == {
        "age",
        "pg_trgm",
        "vector",
    }


def test_soc_live_postgres_validator_reports_missing_extension_and_table() -> None:
    validator = _load_validator()
    connection = FakeSocLiveConnection(
        extensions={
            "pg_trgm": (True, True),
            "vector": (False, False),
            "age": (True, False),
        },
        tables={"soc_artifacts"},
        indexes={"idx_soc_artifacts_fts"},
        graphs=set(),
    )

    report = validator.validate_soc_live_postgres(
        dsn="postgresql://example.invalid/rehearsal",
        connection_factory=lambda: connection,
    )

    assert report["status"] == "failed"
    assert report["passed"] is False
    assert "extension_unavailable:vector" in report["failures"]
    assert "extension_not_installed:age" in report["failures"]
    assert "missing_table:soc_classifications" in report["failures"]
    assert "missing_graph:soc_graph" in report["failures"]


def _params(params: object) -> tuple[str, ...]:
    assert isinstance(params, list | tuple)
    if len(params) == 1 and isinstance(params[0], list | tuple | set):
        return tuple(str(item) for item in params[0])
    return tuple(str(item) for item in params)


def _load_validator() -> ModuleType:
    module_path = Path("ops/rehearsal/validate_soc_live_postgres.py")
    spec = importlib.util.spec_from_file_location("validate_soc_live_postgres", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

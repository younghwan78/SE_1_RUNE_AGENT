"""SoC PostgreSQL profile migration/readiness validator tests."""

import importlib.util
from pathlib import Path

from req_tracker.storage.postgres_store import PostgresMigration


def _load_validator():
    module_path = Path("ops/rehearsal/validate_soc_postgres_profile.py")
    spec = importlib.util.spec_from_file_location("validate_soc_postgres_profile", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_soc_postgres_profile_migrations_are_ready() -> None:
    validator = _load_validator()

    report = validator.validate_soc_postgres_profile()

    assert report["passed"] is True
    assert report["required_migration_versions"] == ["011", "012", "013"]
    assert report["required_extensions"] == ["age", "pg_trgm", "vector"]
    assert "soc_artifacts" in report["checked_tables"]
    assert "soc_classifications" in report["checked_tables"]
    assert "soc_event_log" in report["checked_tables"]
    assert "soc_eval_runs" in report["checked_tables"]
    assert "soc_artifact_embeddings" in report["checked_tables"]
    assert "soc_graph" in report["checked_graphs"]
    assert "idx_soc_artifacts_fts" in report["checked_indexes"]
    assert "idx_soc_artifact_embeddings_vector" in report["checked_indexes"]


def test_soc_postgres_profile_validator_reports_missing_extension_and_rollback() -> None:
    validator = _load_validator()
    migrations = [
        PostgresMigration(
            version="011",
            name="011_soc_knowledge_tables.sql",
            sql="CREATE TABLE IF NOT EXISTS soc_artifacts (external_id TEXT PRIMARY KEY);",
        ),
        PostgresMigration(
            version="012",
            name="012_soc_pgvector_tables.sql",
            sql="CREATE TABLE IF NOT EXISTS soc_artifact_embeddings (artifact_id TEXT);",
        ),
    ]
    rollbacks = {
        "011": PostgresMigration(
            version="011",
            name="011_soc_knowledge_tables.sql",
            sql="DROP TABLE IF EXISTS soc_artifacts;",
        )
    }

    report = validator.validate_soc_postgres_profile(migrations, rollbacks)

    assert report["passed"] is False
    assert "012:missing_rollback" in report["failures"]
    assert "013:missing_migration" in report["failures"]
    assert "011:missing_extension:pg_trgm" in report["failures"]
    assert "012:missing_extension:vector" in report["failures"]
    assert "013:missing_extension:age" in report["failures"]

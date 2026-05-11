"""Optional real PostgreSQL state store integration tests.

These tests are skipped by default. Set POSTGRES_TEST_DSN to a disposable
PostgreSQL database when validating production persistence behavior.
"""

import os

import psycopg
import pytest

from req_tracker.debug.models import AgentRun
from req_tracker.storage.postgres_store import PostgreSQLStateStore

POSTGRES_TEST_DSN = os.getenv("POSTGRES_TEST_DSN")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DSN,
    reason="POSTGRES_TEST_DSN is not set",
)


def test_postgres_state_store_persists_contract_payload_against_real_db() -> None:
    assert POSTGRES_TEST_DSN is not None
    store = PostgreSQLStateStore(POSTGRES_TEST_DSN)
    run = AgentRun(
        run_id="run_pg_integration_1",
        run_type="analysis",
        project_key="RUNE_CAM_ALPHA",
        triggered_by="integration",
        trigger_source="manual",
    )

    _delete_test_run(POSTGRES_TEST_DSN, run.run_id)
    try:
        store.upsert(
            collection="agent_runs",
            entity_id=run.run_id,
            project_key=run.project_key,
            payload=run,
        )

        stored = store.get("agent_runs", run.run_id)
        assert stored is not None
        assert stored["run_id"] == run.run_id
        assert store.list("agent_runs", project_key=run.project_key)
    finally:
        _delete_test_run(POSTGRES_TEST_DSN, run.run_id)


def _delete_test_run(dsn: str, run_id: str) -> None:
    with psycopg.connect(dsn) as conn:
        conn.execute("DELETE FROM agent_runs WHERE run_id = %s", (run_id,))
        conn.execute(
            """
            DELETE FROM state_entities
            WHERE collection = 'agent_runs' AND entity_id = %s
            """,
            (run_id,),
        )

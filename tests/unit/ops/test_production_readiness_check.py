"""Production-readiness checker tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_readiness_report_flags_unverified_company_gates() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report(
        {
            "STATE_STORE": "postgres",
            "POSTGRES_DSN": "postgresql://rune:secret@db/rune_agent",
            "GRAPH_BACKEND": "neo4j",
            "NEO4J_URI": "bolt://neo4j:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "secret",
            "VECTOR_BACKEND": "qdrant",
            "QDRANT_URL": "http://qdrant:6333",
            "QDRANT_COLLECTION": "rune_chunks",
            "MODEL_GATEWAY_MODE": "http_json",
            "MODEL_GATEWAY_ENDPOINT_URL": "https://models.example.test/v1/complete",
            "AUTH_MODE": "trusted_proxy",
            "TRUSTED_PROXY_SECRET": "secret",
            "TRUSTED_GROUP_ROLE_MAP": '{"rune-admins":"admin"}',
            "ARTIFACT_ROOT": "/var/lib/rune-agent/artifacts",
        }
    )

    assert report["passed"] is False
    assert report["summary"]["failed"] == 0
    assert report["summary"]["manual_required"] > 0
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["postgres_state_store"]["status"] == "passed"
    assert checks["company_postgres_rehearsal"]["status"] == "manual_required"
    assert "secret" not in str(report)


def test_readiness_report_fails_missing_production_env() -> None:
    checker = _load_checker_module()

    report = checker.build_readiness_report({})

    assert report["passed"] is False
    assert report["summary"]["failed"] >= 6
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["postgres_state_store"]["status"] == "failed"
    assert "POSTGRES_DSN=<unset>" in checks["postgres_state_store"]["evidence"]


def _load_checker_module() -> ModuleType:
    module_path = Path("ops/rehearsal/check_production_readiness.py")
    spec = importlib.util.spec_from_file_location("check_production_readiness", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

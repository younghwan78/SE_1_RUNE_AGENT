"""Run a live SoC PostgreSQL storage-backed retrieval rehearsal."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from req_tracker.fixtures.soc_knowledge import (
    classifications_for_artifacts,
    load_soc_scale_artifacts,
    load_soc_seed_artifacts,
)
from req_tracker.graph.soc_age_loader import SocAgeGraphLoader
from req_tracker.ingestion.soc_entity_extraction import extract_soc_entities_for_artifacts
from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.retrieval import PostgresHybridSocRetrievalBackend
from req_tracker.storage.soc_postgres_loader import SocPostgresFixtureLoader

REHEARSAL_QUERY = "SOC-N-1 Camera Performance storage-backed rehearsal"
REHEARSAL_SLICE = SocSlice(
    pattern="topic_intersection",
    project_keys=["SOC-N-1"],
    concerns=["Performance"],
    components=["Camera"],
)


def run_soc_live_storage_rehearsal(
    *,
    dsn: str,
    apply_migrations: bool = False,
    coverage_mode: str = "seed",
    limit: int = 10,
) -> dict[str, Any]:
    """Validate that a live SoC PostgreSQL profile can load and retrieve fixture data."""
    if not dsn:
        return _skipped_report()

    checks: dict[str, Any] = {}
    failures: list[str] = []

    profile_report = validate_soc_live_postgres(
        dsn=dsn,
        apply_migrations=apply_migrations,
    )
    checks["profile"] = _profile_check(profile_report)
    if not profile_report.get("passed"):
        failures.append("profile_not_ready")
        return _report(
            checks=checks,
            dsn_provided=True,
            failures=failures,
            coverage_mode=coverage_mode,
        )

    artifacts = (
        load_soc_scale_artifacts() if coverage_mode == "scale" else load_soc_seed_artifacts()
    )
    classifications = classifications_for_artifacts(
        artifacts,
        run_id="soc_live_storage_rehearsal",
        step_id="fixture_classification_load",
    )
    entity_extraction = extract_soc_entities_for_artifacts(
        artifacts,
        run_id="soc_live_storage_rehearsal",
        step_id="semantic_relation_extract",
    )

    try:
        loaded_counts = SocPostgresFixtureLoader(dsn=dsn).load_fixture(
            artifacts=artifacts,
            classifications=classifications,
        )
        checks["fixture_load"] = {"counts": loaded_counts, "status": "passed"}
    except Exception as exc:  # noqa: BLE001
        checks["fixture_load"] = {"error": str(exc), "status": "failed"}
        failures.append("fixture_load_failed")
        return _report(
            checks=checks,
            dsn_provided=True,
            failures=failures,
            coverage_mode=coverage_mode,
        )

    try:
        graph_counts = SocAgeGraphLoader(dsn=dsn).upsert_artifact_graph(
            artifacts=artifacts,
            classifications=classifications,
            semantic_relations=entity_extraction.relations,
        )
        checks["age_graph_load"] = {"counts": graph_counts, "status": "passed"}
    except Exception as exc:  # noqa: BLE001
        checks["age_graph_load"] = {"error": str(exc), "status": "failed"}
        failures.append("age_graph_load_failed")
        return _report(
            checks=checks,
            dsn_provided=True,
            failures=failures,
            coverage_mode=coverage_mode,
        )

    try:
        results = PostgresHybridSocRetrievalBackend(dsn=dsn).retrieve(
            query_id="soc_live_storage_rehearsal",
            user_query=REHEARSAL_QUERY,
            query_slice=REHEARSAL_SLICE,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001
        checks["hybrid_retrieval"] = {"error": str(exc), "status": "failed"}
        failures.append("hybrid_retrieval_failed")
        return _report(
            checks=checks,
            dsn_provided=True,
            failures=failures,
            coverage_mode=coverage_mode,
        )

    artifact_ids = [artifact.external_id for artifact in results]
    source_urls = [artifact.source_url for artifact in results]
    retrieval_passed = bool(results) and all(source_urls)
    checks["hybrid_retrieval"] = {
        "artifact_ids": artifact_ids,
        "limit": limit,
        "query_slice": REHEARSAL_SLICE.model_dump(mode="json"),
        "source_urls": source_urls,
        "status": "passed" if retrieval_passed else "failed",
    }
    if not retrieval_passed:
        failures.append("hybrid_retrieval_returned_no_sourced_results")

    return _report(
        checks=checks,
        dsn_provided=True,
        failures=failures,
        coverage_mode=coverage_mode,
    )


def _skipped_report() -> dict[str, Any]:
    return {
        "checks": {
            "profile": {"status": "skipped"},
            "fixture_load": {"status": "skipped"},
            "age_graph_load": {"status": "skipped"},
            "hybrid_retrieval": {"status": "skipped"},
        },
        "coverage_mode": "seed",
        "dsn_provided": False,
        "failure_count": 1,
        "failures": ["POSTGRES_DSN or POSTGRES_TEST_DSN is required"],
        "passed": False,
        "schema_version": "v1",
        "status": "skipped",
    }


def _profile_check(profile_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "failure_count": profile_report.get("failure_count", 0),
        "status": "passed" if profile_report.get("passed") else "failed",
    }


def _report(
    *,
    checks: dict[str, Any],
    dsn_provided: bool,
    failures: list[str],
    coverage_mode: str,
) -> dict[str, Any]:
    status = "passed" if not failures else "failed"
    return {
        "checks": checks,
        "coverage_mode": coverage_mode,
        "dsn_provided": dsn_provided,
        "failure_count": len(failures),
        "failures": failures,
        "passed": status == "passed",
        "schema_version": "v1",
        "status": status,
    }


def _env_dsn() -> str:
    return os.getenv("POSTGRES_TEST_DSN") or os.getenv("POSTGRES_DSN") or ""


def _load_live_validator() -> Callable[..., dict[str, Any]]:
    module_path = Path(__file__).with_name("validate_soc_live_postgres.py")
    spec = importlib.util.spec_from_file_location("validate_soc_live_postgres", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load live validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = module.validate_soc_live_postgres
    if not callable(validator):
        raise RuntimeError("validate_soc_live_postgres must be callable")
    return validator


validate_soc_live_postgres = _load_live_validator()


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default=_env_dsn())
    parser.add_argument("--apply-migrations", action="store_true")
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Return non-zero when no DSN is configured.",
    )
    parser.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args()

    report = run_soc_live_storage_rehearsal(
        dsn=args.dsn,
        apply_migrations=args.apply_migrations,
        coverage_mode=args.coverage_mode,
        limit=args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["status"] == "skipped" and not args.require_live:
        return 0
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

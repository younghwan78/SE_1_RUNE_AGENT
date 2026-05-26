"""Run storage-backed SoC Knowledge query evaluation.

The default CLI path is skip-safe. Use ``--live`` with ``POSTGRES_TEST_DSN`` to
load fixture data through the live storage rehearsal and evaluate the
PostgresHybridSocRetrievalBackend against the seed or scale ground-truth query
set.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.evals.soc_query import (
    SocQueryCaseComparison,
    compare_soc_answer,
    detect_soc_regressions,
)
from req_tracker.fixtures.soc_knowledge import (
    load_soc_query_set,
    load_soc_scale_artifacts,
    load_soc_scale_query_set,
    load_soc_seed_artifacts,
)
from req_tracker.ontology.soc_models import SocAnswer
from req_tracker.query.retrieval import PostgresHybridSocRetrievalBackend
from req_tracker.query.soc_service import answer_soc_query

CoverageMode = Literal["seed", "scale"]
SCHEMA_VERSION = "soc-storage-backed-query-eval-v0.1"


def run_soc_storage_backed_query_eval(
    *,
    dsn: str,
    apply_migrations: bool = False,
    coverage_mode: CoverageMode = "seed",
    limit: int = 50,
    min_recall: float = 0.85,
) -> dict[str, Any]:
    """Evaluate query quality through the live Postgres hybrid retrieval backend."""
    if not dsn:
        return _skipped_report(coverage_mode=coverage_mode)

    rehearsal_report = run_soc_live_storage_rehearsal(
        dsn=dsn,
        apply_migrations=apply_migrations,
        coverage_mode=coverage_mode,
        limit=limit,
    )
    checks = {"storage_rehearsal": _rehearsal_check(rehearsal_report)}
    if not rehearsal_report.get("passed"):
        failures = ["storage_rehearsal_failed"]
        checks["query_quality"] = {"status": "skipped"}
        return _report(
            checks=checks,
            coverage_mode=coverage_mode,
            dsn_provided=True,
            failures=failures,
            query_report=None,
        )

    artifacts, queries = _fixtures_for_mode(coverage_mode)
    artifacts_by_id = {artifact.external_id: artifact for artifact in artifacts}
    backend = PostgresHybridSocRetrievalBackend(dsn=dsn)
    comparisons: list[SocQueryCaseComparison] = []
    schema_passes = 0
    unknown_total = 0
    unknown_passes = 0

    for query in queries:
        answer = answer_soc_query(
            query_id=query.q_id,
            user_query=query.question,
            user_id="soc_storage_eval",
            session_id=f"soc_storage_eval_{coverage_mode}",
            query_slice=query.slice,
            retrieval_backend=backend,
        )
        schema_valid = _schema_valid(answer)
        if schema_valid:
            schema_passes += 1
        comparison = compare_soc_answer(
            query=query,
            answer=answer,
            artifacts_by_id=artifacts_by_id,
            schema_valid=schema_valid,
        )
        comparisons.append(comparison)
        if not query.expected_artifact_ids:
            unknown_total += 1
            if comparison.graceful_unknown_passed:
                unknown_passes += 1

    query_report = _query_report(
        comparisons=comparisons,
        query_count=len(queries),
        artifact_count=len(artifacts),
        schema_passes=schema_passes,
        unknown_total=unknown_total,
        unknown_passes=unknown_passes,
        min_recall=min_recall,
    )
    checks["query_quality"] = {
        "recall": query_report["recall"],
        "source_accuracy": query_report["source_accuracy"],
        "schema_pass_rate": query_report["schema_pass_rate"],
        "status": "passed" if query_report["passed"] else "failed",
    }
    failures = [] if query_report["passed"] else ["query_quality_failed"]
    return _report(
        checks=checks,
        coverage_mode=coverage_mode,
        dsn_provided=True,
        failures=failures,
        query_report=query_report,
    )


def _fixtures_for_mode(
    coverage_mode: CoverageMode,
) -> tuple[list[RawSourceArtifact], list[Any]]:
    if coverage_mode == "scale":
        return load_soc_scale_artifacts(), load_soc_scale_query_set()
    return load_soc_seed_artifacts(), load_soc_query_set()


def _query_report(
    *,
    comparisons: list[SocQueryCaseComparison],
    query_count: int,
    artifact_count: int,
    schema_passes: int,
    unknown_total: int,
    unknown_passes: int,
    min_recall: float,
) -> dict[str, Any]:
    expected_total = sum(len(comparison.expected_artifact_ids) for comparison in comparisons)
    matched_total = sum(len(comparison.matched_artifact_ids) for comparison in comparisons)
    source_checks = sum(comparison.source_checks for comparison in comparisons)
    source_matches = sum(comparison.source_matches for comparison in comparisons)
    recall = _ratio(matched_total, expected_total)
    source_accuracy = _ratio(source_matches, source_checks)
    schema_pass_rate = _ratio(schema_passes, query_count)
    graceful_unknown_pass_rate = _ratio(unknown_passes, unknown_total)
    regressions = detect_soc_regressions(
        comparisons,
        {comparison.q_id for comparison in comparisons},
    )
    diagnostics = _diagnostics(comparisons)
    passed = (
        recall >= min_recall
        and source_accuracy >= 0.95
        and schema_pass_rate == 1.0
        and graceful_unknown_pass_rate == 1.0
        and not regressions
    )
    return {
        "passed": passed,
        "counts": {
            "queries": query_count,
            "artifacts": artifact_count,
            "expected_artifacts": expected_total,
            "source_checks": source_checks,
            "unknown_queries": unknown_total,
        },
        "recall": recall,
        "source_accuracy": source_accuracy,
        "schema_pass_rate": schema_pass_rate,
        "graceful_unknown_pass_rate": graceful_unknown_pass_rate,
        "regression_count": len(regressions),
        "regressions": regressions,
        "diagnostics": diagnostics,
        "cases": [comparison.model_dump(mode="json") for comparison in comparisons],
    }


def _skipped_report(*, coverage_mode: CoverageMode) -> dict[str, Any]:
    return {
        "checks": {
            "storage_rehearsal": {"status": "skipped"},
            "query_quality": {"status": "skipped"},
        },
        "coverage_mode": coverage_mode,
        "dsn_provided": False,
        "failure_count": 1,
        "failures": ["POSTGRES_DSN or POSTGRES_TEST_DSN is required"],
        "passed": False,
        "requires_live": True,
        "schema_version": SCHEMA_VERSION,
        "status": "skipped",
    }


def _report(
    *,
    checks: dict[str, Any],
    coverage_mode: CoverageMode,
    dsn_provided: bool,
    failures: list[str],
    query_report: dict[str, Any] | None,
) -> dict[str, Any]:
    status = "passed" if not failures else "failed"
    payload: dict[str, Any] = {
        "checks": checks,
        "coverage_mode": coverage_mode,
        "dsn_provided": dsn_provided,
        "failure_count": len(failures),
        "failures": failures,
        "passed": status == "passed",
        "requires_live": True,
        "schema_version": SCHEMA_VERSION,
        "status": status,
    }
    if query_report is not None:
        payload.update({key: value for key, value in query_report.items() if key != "passed"})
    return payload


def _rehearsal_check(rehearsal_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "failure_count": rehearsal_report.get("failure_count", 0),
        "status": "passed" if rehearsal_report.get("passed") else "failed",
    }


def _diagnostics(comparisons: list[SocQueryCaseComparison]) -> dict[str, Any]:
    by_layer: Counter[str] = Counter()
    failed_q_ids: list[str] = []
    for comparison in comparisons:
        if comparison.failure_layers:
            failed_q_ids.append(comparison.q_id)
        by_layer.update(comparison.failure_layers)
    return {
        "failed_cases": len(failed_q_ids),
        "failed_q_ids": failed_q_ids,
        "by_layer": dict(sorted(by_layer.items())),
    }


def _schema_valid(answer: SocAnswer) -> bool:
    try:
        SocAnswer.model_validate(answer.model_dump(mode="python"))
    except ValidationError:
        return False
    return True


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def _env_dsn() -> str:
    return os.getenv("POSTGRES_TEST_DSN") or os.getenv("POSTGRES_DSN") or ""


def _load_live_storage_rehearsal() -> Callable[..., dict[str, Any]]:
    module_path = Path(__file__).resolve().parents[1] / "rehearsal" / (
        "run_soc_live_storage_rehearsal.py"
    )
    spec = importlib.util.spec_from_file_location("run_soc_live_storage_rehearsal", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load live storage rehearsal: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rehearsal = module.run_soc_live_storage_rehearsal
    if not callable(rehearsal):
        raise RuntimeError("run_soc_live_storage_rehearsal must be callable")
    return rehearsal


run_soc_live_storage_rehearsal = _load_live_storage_rehearsal()


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default=_env_dsn())
    parser.add_argument("--apply-migrations", action="store_true")
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--live", action="store_true", help="Run against the configured DSN.")
    parser.add_argument("--dry-run", action="store_true", help="Force skip-safe reporting.")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Return non-zero when live execution is not performed.",
    )
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    dsn = args.dsn if args.live and not args.dry_run else ""
    report = run_soc_storage_backed_query_eval(
        dsn=dsn,
        apply_migrations=args.apply_migrations,
        coverage_mode=args.coverage_mode,
        limit=args.limit,
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "SoC storage-backed query eval "
            f"status={report['status']} "
            f"coverage_mode={report['coverage_mode']} "
            f"requires_live={report['requires_live']}"
        )
    if report["status"] == "skipped" and not args.require_live:
        return 0
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

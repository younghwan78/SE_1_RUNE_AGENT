"""SoC Knowledge query eval comparison and diagnostics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.fixtures.soc_knowledge import (
    load_soc_query_set,
    load_soc_scale_artifacts,
    load_soc_scale_query_set,
    load_soc_seed_artifacts,
)
from req_tracker.ontology.soc_models import SocAnswer, SocGroundTruthQuery
from req_tracker.query.soc_service import answer_soc_query
from req_tracker.storage.state_store import StateStore

SOC_QUERY_EVAL_SCHEMA_VERSION = "soc-query-eval-v0.1"
SOC_EVAL_RUN_SCHEMA_VERSION = "soc-v0.1"
SOC_EVAL_RUN_DIFF_SCHEMA_VERSION = "soc-eval-run-diff-v0.1"

FailureLayer = Literal[
    "answer_schema",
    "unknown_handling",
    "retrieval",
    "source_link",
    "precision",
]
CoverageMode = Literal["seed", "scale"]
EvalRunDiffStatus = Literal["passed", "failed"]


class SocQueryCaseComparison(BaseModel):
    """Comparison between one SoC query answer and its ground truth."""

    model_config = ConfigDict(extra="forbid")

    q_id: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    expected_artifact_ids: list[str] = Field(default_factory=list)
    returned_artifact_ids: list[str] = Field(default_factory=list)
    matched_artifact_ids: list[str] = Field(default_factory=list)
    missing_artifact_ids: list[str] = Field(default_factory=list)
    unexpected_artifact_ids: list[str] = Field(default_factory=list)
    missing_source_urls: list[str] = Field(default_factory=list)
    recall: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    source_accuracy: float = Field(ge=0.0, le=1.0)
    source_checks: int = Field(ge=0)
    source_matches: int = Field(ge=0)
    schema_valid: bool
    graceful_unknown_passed: bool
    failure_layers: list[FailureLayer] = Field(default_factory=list)
    passed: bool
    schema_version: str = SOC_QUERY_EVAL_SCHEMA_VERSION


class SocEvalRunRecord(BaseModel):
    """Persistable summary for one SoC query evaluation run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    query_set_id: str = Field(min_length=1)
    coverage_mode: CoverageMode
    status: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    regression_count: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = SOC_EVAL_RUN_SCHEMA_VERSION


class SocEvalRunDiff(BaseModel):
    """Object-level diff between two SoC eval-run records."""

    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str = Field(min_length=1)
    candidate_run_id: str = Field(min_length=1)
    coverage_mode: CoverageMode
    status: EvalRunDiffStatus
    metric_deltas: dict[str, float] = Field(default_factory=dict)
    count_deltas: dict[str, int] = Field(default_factory=dict)
    regression_delta: int
    changed_metrics: list[str] = Field(default_factory=list)
    regressed_metrics: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = SOC_EVAL_RUN_DIFF_SCHEMA_VERSION


def compare_soc_answer(
    *,
    query: SocGroundTruthQuery,
    answer: SocAnswer,
    artifacts_by_id: Mapping[str, RawSourceArtifact],
    schema_valid: bool,
) -> SocQueryCaseComparison:
    """Compare one answer to fixture ground truth with source-link checks."""
    returned_sources = _answer_sources(answer)
    returned_ids = sorted({source["key"] for source in returned_sources if source["key"]})
    expected_ids = sorted(query.expected_artifact_ids)
    expected_set = set(expected_ids)
    returned_set = set(returned_ids)
    matched_ids = sorted(expected_set & returned_set)
    missing_ids = sorted(expected_set - returned_set)
    unexpected_ids = sorted(returned_set - expected_set)
    source_checks = 0
    source_matches = 0
    missing_source_urls: list[str] = []
    for artifact_id in matched_ids:
        expected_url = _expected_source_url(query, artifacts_by_id, artifact_id)
        if expected_url is None:
            continue
        source_checks += 1
        returned_urls = {
            source["url"] for source in returned_sources if source["key"] == artifact_id
        }
        if expected_url in returned_urls:
            source_matches += 1
        else:
            missing_source_urls.append(expected_url)

    graceful_unknown_passed = (
        not expected_ids
        and _answer_item_count(answer) == 0
        and "no_candidates" in answer.quality_signals
    )
    recall = _ratio(len(matched_ids), len(expected_ids))
    precision = _ratio(len(matched_ids), len(returned_ids))
    source_accuracy = _ratio(source_matches, source_checks)
    comparison = SocQueryCaseComparison(
        q_id=query.q_id,
        pattern=query.slice.pattern,
        expected_artifact_ids=expected_ids,
        returned_artifact_ids=returned_ids,
        matched_artifact_ids=matched_ids,
        missing_artifact_ids=missing_ids,
        unexpected_artifact_ids=unexpected_ids,
        missing_source_urls=missing_source_urls,
        recall=recall,
        precision=precision,
        source_accuracy=source_accuracy,
        source_checks=source_checks,
        source_matches=source_matches,
        schema_valid=schema_valid,
        graceful_unknown_passed=graceful_unknown_passed,
        failure_layers=[],
        passed=False,
    )
    failure_layers = diagnose_soc_case(comparison)
    return comparison.model_copy(
        update={
            "failure_layers": failure_layers,
            "passed": not failure_layers,
        }
    )


def diagnose_soc_case(comparison: SocQueryCaseComparison) -> list[FailureLayer]:
    """Return failure layers for one compared query case."""
    failures: list[FailureLayer] = []
    if not comparison.schema_valid:
        failures.append("answer_schema")
    if not comparison.expected_artifact_ids:
        if not comparison.graceful_unknown_passed:
            failures.append("unknown_handling")
        return failures
    if comparison.missing_artifact_ids:
        failures.append("retrieval")
    if comparison.missing_source_urls:
        failures.append("source_link")
    if comparison.unexpected_artifact_ids:
        failures.append("precision")
    return failures


def detect_soc_regressions(
    comparisons: Iterable[SocQueryCaseComparison],
    previous_passed_q_ids: set[str],
) -> list[str]:
    """Return query IDs that were previously passing but now fail."""
    return sorted(
        comparison.q_id
        for comparison in comparisons
        if comparison.q_id in previous_passed_q_ids and not comparison.passed
    )


def build_soc_query_eval_report(
    *,
    coverage_mode: Literal["seed", "scale"] = "seed",
    min_recall: float = 0.85,
    previous_passed_q_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Run packaged seed queries and return Stage F-style comparison diagnostics."""
    if coverage_mode == "scale":
        artifacts = load_soc_scale_artifacts()
        queries = load_soc_scale_query_set()
        session_id = "soc_eval_scale"
    else:
        artifacts = load_soc_seed_artifacts()
        queries = load_soc_query_set()
        session_id = "soc_eval_seed"
    artifacts_by_id = {artifact.external_id: artifact for artifact in artifacts}
    comparisons: list[SocQueryCaseComparison] = []
    schema_passes = 0
    unknown_total = 0
    unknown_passes = 0
    for query in queries:
        answer = answer_soc_query(
            query_id=query.q_id,
            user_query=query.question,
            user_id="soc_eval",
            session_id=session_id,
            query_slice=query.slice,
            artifacts=artifacts,
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

    expected_total = sum(len(comparison.expected_artifact_ids) for comparison in comparisons)
    matched_total = sum(len(comparison.matched_artifact_ids) for comparison in comparisons)
    source_checks = sum(comparison.source_checks for comparison in comparisons)
    source_matches = sum(comparison.source_matches for comparison in comparisons)
    regression_baseline = previous_passed_q_ids or {query.q_id for query in queries}
    regressions = detect_soc_regressions(comparisons, regression_baseline)
    diagnostics = _diagnostics(comparisons)
    recall = _ratio(matched_total, expected_total)
    source_accuracy = _ratio(source_matches, source_checks)
    schema_pass_rate = _ratio(schema_passes, len(queries))
    graceful_unknown_pass_rate = _ratio(unknown_passes, unknown_total)
    status = (
        "passed"
        if recall >= min_recall
        and source_accuracy >= 0.95
        and schema_pass_rate == 1.0
        and graceful_unknown_pass_rate == 1.0
        and not regressions
        else "failed"
    )
    return {
        "status": status,
        "coverage_mode": coverage_mode,
        "full_stage_f_ready": len(queries) >= 20 and len(artifacts) >= 400,
        "counts": {
            "queries": len(queries),
            "artifacts": len(artifacts),
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
        "recommendations": _recommendations(diagnostics["by_layer"]),
        "cases": [comparison.model_dump(mode="json") for comparison in comparisons],
        "schema_version": SOC_QUERY_EVAL_SCHEMA_VERSION,
    }


def build_soc_eval_run_record(
    report: Mapping[str, Any],
    *,
    run_id: str | None = None,
    query_set_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> SocEvalRunRecord:
    """Build a compact, DB-friendly eval-run record from a SoC query eval report."""
    coverage_mode = _coverage_mode(report.get("coverage_mode", "seed"))
    completed = completed_at or datetime.now(UTC)
    started = started_at or completed
    metrics = _eval_metrics(report)
    metadata = {
        "case_count": len(report.get("cases", [])) if isinstance(report.get("cases"), list) else 0,
        "diagnostics": report.get("diagnostics", {}),
        "full_stage_f_ready": bool(report.get("full_stage_f_ready", False)),
        "recommendations": report.get("recommendations", []),
        "report_hash": stable_hash(report),
        "report_schema_version": str(report.get("schema_version", "unknown")),
    }
    resolved_query_set_id = query_set_id or f"soc_knowledge_{coverage_mode}_v0.1"
    resolved_run_id = run_id or f"soc_eval_{stable_hash([resolved_query_set_id, metrics])[:16]}"
    return SocEvalRunRecord(
        run_id=resolved_run_id,
        query_set_id=resolved_query_set_id,
        coverage_mode=coverage_mode,
        status=str(report.get("status", "unknown")),
        started_at=started,
        completed_at=completed,
        metrics=metrics,
        regression_count=int(report.get("regression_count", 0)),
        metadata=metadata,
    )


def persist_soc_eval_run(
    report: Mapping[str, Any],
    *,
    state_store: StateStore,
    run_id: str | None = None,
    query_set_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    project_key: str = "soc_knowledge",
) -> SocEvalRunRecord:
    """Persist a SoC eval report into the shared state-store contract."""
    record = build_soc_eval_run_record(
        report,
        run_id=run_id,
        query_set_id=query_set_id,
        started_at=started_at,
        completed_at=completed_at,
    )
    state_store.upsert(
        collection="soc_eval_runs",
        entity_id=record.run_id,
        project_key=project_key,
        payload=record,
    )
    return record


def diff_soc_eval_run_records(
    baseline: SocEvalRunRecord | Mapping[str, Any],
    candidate: SocEvalRunRecord | Mapping[str, Any],
    *,
    tolerance: float = 0.0,
) -> SocEvalRunDiff:
    """Compare two eval-run summaries and flag metric or regression drift."""
    baseline_record = _coerce_eval_run_record(baseline)
    candidate_record = _coerce_eval_run_record(candidate)
    metric_keys = (
        "recall",
        "source_accuracy",
        "schema_pass_rate",
        "graceful_unknown_pass_rate",
    )
    metric_deltas: dict[str, float] = {}
    changed_metrics: set[str] = set()
    regressed_metrics: set[str] = set()
    for key in metric_keys:
        delta = _metric_delta(
            candidate_record.metrics.get(key),
            baseline_record.metrics.get(key),
        )
        metric_deltas[key] = delta
        if delta != 0:
            changed_metrics.add(key)
        if delta < -tolerance:
            regressed_metrics.add(key)

    regression_delta = candidate_record.regression_count - baseline_record.regression_count
    if regression_delta != 0:
        changed_metrics.add("regression_count")
    if regression_delta > 0:
        regressed_metrics.add("regression_count")

    count_deltas = _count_deltas(
        baseline_record.metrics.get("counts", {}),
        candidate_record.metrics.get("counts", {}),
    )
    status: EvalRunDiffStatus = (
        "failed"
        if candidate_record.status != "passed" or regressed_metrics
        else "passed"
    )
    return SocEvalRunDiff(
        baseline_run_id=baseline_record.run_id,
        candidate_run_id=candidate_record.run_id,
        coverage_mode=candidate_record.coverage_mode,
        status=status,
        metric_deltas=metric_deltas,
        count_deltas=count_deltas,
        regression_delta=regression_delta,
        changed_metrics=sorted(changed_metrics),
        regressed_metrics=sorted(regressed_metrics),
        summary={
            "baseline_status": baseline_record.status,
            "candidate_status": candidate_record.status,
            "changed_metric_count": len(changed_metrics),
            "regressed_metric_count": len(regressed_metrics),
            "report_only": True,
        },
    )


def _diagnostics(comparisons: list[SocQueryCaseComparison]) -> dict[str, Any]:
    by_layer: Counter[str] = Counter()
    failed_cases: list[str] = []
    for comparison in comparisons:
        if comparison.failure_layers:
            failed_cases.append(comparison.q_id)
        by_layer.update(comparison.failure_layers)
    return {
        "failed_cases": len(failed_cases),
        "failed_q_ids": failed_cases,
        "by_layer": dict(sorted(by_layer.items())),
    }


def _recommendations(by_layer: Mapping[str, int]) -> list[str]:
    recommendations: list[str] = []
    if by_layer.get("answer_schema"):
        recommendations.append("Check SocAnswer schema validation and answer assembly.")
    if by_layer.get("unknown_handling"):
        recommendations.append("Check unknown-slice routing and no-candidates response.")
    if by_layer.get("retrieval"):
        recommendations.append("Check slice classification, axis filters, and retrieval recall.")
    if by_layer.get("source_link"):
        recommendations.append("Check source URL preservation in answer projection.")
    if by_layer.get("precision"):
        recommendations.append("Check reranking and candidate pruning precision.")
    return recommendations


def _eval_metrics(report: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "counts",
        "recall",
        "source_accuracy",
        "schema_pass_rate",
        "graceful_unknown_pass_rate",
        "regression_count",
    )
    return {key: report[key] for key in keys if key in report}


def _coverage_mode(value: object) -> CoverageMode:
    if value == "scale":
        return "scale"
    return "seed"


def _coerce_eval_run_record(
    record: SocEvalRunRecord | Mapping[str, Any],
) -> SocEvalRunRecord:
    if isinstance(record, SocEvalRunRecord):
        return record
    return SocEvalRunRecord.model_validate(record)


def _metric_delta(candidate_value: object, baseline_value: object) -> float:
    candidate = float(candidate_value) if isinstance(candidate_value, int | float) else 0.0
    baseline = float(baseline_value) if isinstance(baseline_value, int | float) else 0.0
    return round(candidate - baseline, 6)


def _count_deltas(baseline_counts: object, candidate_counts: object) -> dict[str, int]:
    if not isinstance(baseline_counts, Mapping) or not isinstance(candidate_counts, Mapping):
        return {}
    keys = sorted(set(baseline_counts) | set(candidate_counts))
    deltas: dict[str, int] = {}
    for key in keys:
        baseline = baseline_counts.get(key, 0)
        candidate = candidate_counts.get(key, 0)
        if isinstance(baseline, int) and isinstance(candidate, int):
            delta = candidate - baseline
            if delta != 0:
                deltas[str(key)] = delta
    return deltas


def _schema_valid(answer: SocAnswer) -> bool:
    try:
        SocAnswer.model_validate(answer.model_dump(mode="python"))
    except ValidationError:
        return False
    return True


def _expected_source_url(
    query: SocGroundTruthQuery,
    artifacts_by_id: Mapping[str, RawSourceArtifact],
    artifact_id: str,
) -> str | None:
    artifact = artifacts_by_id.get(artifact_id)
    if artifact is not None:
        return artifact.source_url
    if query.expected_source_urls:
        return next((url for url in query.expected_source_urls if artifact_id in url), None)
    return None


def _answer_sources(answer: SocAnswer) -> list[dict[str, str | None]]:
    sources: list[dict[str, str | None]] = []
    for item in answer.items:
        raw_item = item if isinstance(item, dict) else item.model_dump(mode="python")
        raw_sources = raw_item.get("sources", [])
        if not isinstance(raw_sources, list):
            continue
        for source in raw_sources:
            raw_source = source if isinstance(source, dict) else source.model_dump(mode="python")
            key = raw_source.get("key")
            url = raw_source.get("url")
            sources.append(
                {
                    "key": str(key) if key is not None else None,
                    "url": str(url) if url is not None else None,
                }
            )
    return sources


def _answer_item_count(answer: SocAnswer) -> int:
    return len(answer.items)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator

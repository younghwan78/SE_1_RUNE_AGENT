"""Validate SoC Knowledge seed fixtures and rule-classifier recall."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from req_tracker.fixtures.soc_knowledge import (
    SOC_FIXTURE_ROOT,
    classifications_for_artifacts,
    load_soc_ground_truth_classifications,
    load_soc_query_set,
    load_soc_scale_artifacts,
    load_soc_scale_query_set,
    load_soc_seed_artifacts,
)
from req_tracker.ingestion.soc_classification import classify_soc_axes

OutputFormat = Literal["json", "text"]
CoverageMode = Literal["seed", "scale"]
REQUIRED_PATTERNS = {
    "concern_slice",
    "topic_intersection",
    "timeline_slice",
    "lifecycle_trace",
    "unknown",
}
MIN_QUERY_COUNT = 20
SCALE_EXPECTED_COUNTS = {
    "artifacts": 400,
    "jira": 200,
    "confluence": 100,
    "email": 100,
}


def validate_soc_fixtures(
    fixture_root: Path = SOC_FIXTURE_ROOT,
    *,
    coverage_mode: CoverageMode = "seed",
) -> dict[str, Any]:
    """Return a structured validation report for seed or scale fixtures."""
    if coverage_mode == "seed":
        artifacts = load_soc_seed_artifacts(fixture_root)
        ground_truth = load_soc_ground_truth_classifications(fixture_root)
        queries = load_soc_query_set(fixture_root)
    else:
        artifacts = load_soc_scale_artifacts(fixture_root)
        ground_truth = classifications_for_artifacts(
            artifacts,
            run_id="fixture_scale",
            step_id="fixture_scale_ground_truth",
        )
        queries = load_soc_scale_query_set(fixture_root)
    artifact_ids = [artifact.external_id for artifact in artifacts]
    duplicate_ids = sorted(
        item for item, count in Counter(artifact_ids).items() if count > 1
    )
    artifact_id_set = set(artifact_ids)
    missing_query_refs = _missing_query_refs(queries=queries, artifact_id_set=artifact_id_set)
    source_counts = Counter(artifact.source_type for artifact in artifacts)
    patterns = sorted({query.slice.pattern for query in queries})
    classification_recall = _classification_recall(
        artifacts=artifacts,
        ground_truth=ground_truth,
    )
    errors: list[str] = []
    if duplicate_ids:
        errors.append(f"duplicate artifact ids: {duplicate_ids}")
    if missing_query_refs:
        errors.append(f"query expected_artifact_ids missing artifacts: {missing_query_refs}")
    if coverage_mode == "seed" and REQUIRED_PATTERNS - set(patterns):
        errors.append(f"missing query patterns: {sorted(REQUIRED_PATTERNS - set(patterns))}")
    if coverage_mode == "seed" and len(queries) < MIN_QUERY_COUNT:
        errors.append(f"query count below {MIN_QUERY_COUNT}: {len(queries)}")
    if coverage_mode == "scale":
        _append_scale_count_errors(errors=errors, source_counts=source_counts, total=len(artifacts))
        if len(queries) < 30:
            errors.append(f"scale query count below 30: {len(queries)}")
    if classification_recall < 0.85:
        errors.append(f"classification recall below 0.85: {classification_recall:.3f}")
    if any(not artifact.source_url for artifact in artifacts):
        errors.append("all artifacts must have source_url")
    return {
        "status": "passed" if not errors else "failed",
        "coverage_mode": coverage_mode,
        "fixture_root": str(fixture_root),
        "counts": {
            "artifacts": len(artifacts),
            "jira": source_counts["jira"],
            "confluence": source_counts["confluence"],
            "email": source_counts["email"],
            "classifications": len(ground_truth),
            "queries": len(queries),
        },
        "classification_recall": classification_recall,
        "slice_patterns": patterns,
        "errors": errors,
        "schema_version": "soc-fixture-v0.1",
    }


def _classification_recall(
    *,
    artifacts: list[Any],
    ground_truth: list[Any],
) -> float:
    expected = {
        (classification.entity_id, classification.axis, classification.value)
        for classification in ground_truth
    }
    if not expected:
        return 0.0
    actual = {
        (classification.entity_id, classification.axis, classification.value)
        for artifact in artifacts
        for classification in classify_soc_axes(
            artifact,
            run_id="fixture_validation",
            step_id="rule_classification",
        )
    }
    return len(expected & actual) / len(expected)


def _missing_query_refs(
    *,
    queries: list[Any],
    artifact_id_set: set[str],
) -> list[str]:
    return sorted(
        {
            expected_id
            for query in queries
            for expected_id in query.expected_artifact_ids
            if expected_id not in artifact_id_set
        }
    )


def _append_scale_count_errors(
    *,
    errors: list[str],
    source_counts: Counter[str],
    total: int,
) -> None:
    actual_counts = {
        "artifacts": total,
        "jira": source_counts["jira"],
        "confluence": source_counts["confluence"],
        "email": source_counts["email"],
    }
    for key, expected in SCALE_EXPECTED_COUNTS.items():
        actual = actual_counts[key]
        if actual != expected:
            errors.append(f"scale {key} count expected {expected}, got {actual}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=SOC_FIXTURE_ROOT,
        help="Path to fixtures/soc_knowledge.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--coverage-mode",
        choices=("seed", "scale"),
        default="seed",
        help="Validate the 40-artifact seed fixture or generated 400-artifact scale fixture.",
    )
    return parser.parse_args()


def _print_report(report: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(
        "SoC fixture validation "
        f"{report['status']}: "
        f"{report['counts']['artifacts']} artifacts, "
        f"{report['counts']['queries']} queries, "
        f"recall={report['classification_recall']:.3f}"
    )


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    report = validate_soc_fixtures(args.fixture_root, coverage_mode=args.coverage_mode)
    _print_report(report, args.format)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

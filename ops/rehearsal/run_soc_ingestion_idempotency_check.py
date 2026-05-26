"""Check SoC fixture ingestion idempotency without live storage."""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal

from req_tracker.debug.hash import stable_hash
from req_tracker.workflows.soc_knowledge import (
    CoverageMode,
    SocKnowledgeIngestionWorkflow,
)

OutputFormat = Literal["json", "text"]


def run_soc_ingestion_idempotency_check(
    *,
    coverage_mode: CoverageMode = "seed",
) -> dict[str, Any]:
    """Run fixture ingestion twice and compare stable IDs/counts/projection."""
    workflow = SocKnowledgeIngestionWorkflow()
    first = workflow.run_fixture_ingestion(
        run_id=f"soc_idempotency_{coverage_mode}_first",
        coverage_mode=coverage_mode,
    )
    second = workflow.run_fixture_ingestion(
        run_id=f"soc_idempotency_{coverage_mode}_second",
        coverage_mode=coverage_mode,
    )
    first_fingerprint = first.idempotency_fingerprint
    second_fingerprint = second.idempotency_fingerprint
    fingerprint_match = first_fingerprint == second_fingerprint
    duplicate_candidate_count = 0 if fingerprint_match else _new_candidate_count(
        first_fingerprint,
        second_fingerprint,
    )
    status = "passed" if fingerprint_match and duplicate_candidate_count == 0 else "failed"
    return {
        "status": status,
        "coverage_mode": coverage_mode,
        "fingerprint_match": fingerprint_match,
        "fingerprint_hash": stable_hash(first_fingerprint),
        "first": {
            "counts": first.counts,
            "storage_projection": first.storage_projection,
        },
        "second": {
            "counts": second.counts,
            "storage_projection": second.storage_projection,
        },
        "duplicate_candidate_count": duplicate_candidate_count,
        "schema_version": "soc-ingestion-idempotency-v0.1",
    }


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    payload = run_soc_ingestion_idempotency_check(coverage_mode=args.coverage_mode)
    _print_report(payload, args.format)
    return 0 if payload["status"] == "passed" else 1


def _new_candidate_count(
    first_fingerprint: dict[str, Any],
    second_fingerprint: dict[str, Any],
) -> int:
    candidate_keys = (
        "artifact_ids",
        "classification_ids",
        "entity_ids",
        "relation_ids",
        "event_ids",
    )
    return sum(
        len(set(second_fingerprint.get(key, [])) - set(first_fingerprint.get(key, [])))
        for key in candidate_keys
    )


def _print_report(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(
        "SoC ingestion idempotency "
        f"status={payload['status']} "
        f"coverage_mode={payload['coverage_mode']} "
        f"fingerprint_match={payload['fingerprint_match']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

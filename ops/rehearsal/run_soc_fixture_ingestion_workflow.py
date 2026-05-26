"""Run the skip-safe SoC fixture ingestion workflow rehearsal."""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal

from req_tracker.workflows.soc_knowledge import (
    CoverageMode,
    SocKnowledgeIngestionWorkflow,
)

OutputFormat = Literal["json", "text"]


def run_soc_fixture_ingestion_workflow(
    *,
    coverage_mode: CoverageMode = "seed",
) -> dict[str, Any]:
    """Run packaged fixtures through the local SoC ingestion workflow."""
    result = SocKnowledgeIngestionWorkflow().run_fixture_ingestion(
        run_id=f"soc_fixture_ingestion_{coverage_mode}",
        coverage_mode=coverage_mode,
    )
    payload = result.model_dump(mode="json")
    return {
        "status": "passed" if result.run.status == "succeeded" else "failed",
        "coverage_mode": coverage_mode,
        "counts": payload["counts"],
        "source_counts": payload["source_counts"],
        "storage_projection": payload["storage_projection"],
        "stage_names": [step["stage_name"] for step in payload["steps"]],
        "run": payload["run"],
        "schema_version": payload["schema_version"],
    }


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    payload = run_soc_fixture_ingestion_workflow(coverage_mode=args.coverage_mode)
    _print_report(payload, args.format)
    return 0 if payload["status"] == "passed" else 1


def _print_report(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(
        "SoC fixture ingestion workflow "
        f"status={payload['status']} "
        f"coverage_mode={payload['coverage_mode']} "
        f"artifacts={payload['counts']['artifacts']} "
        f"events={payload['counts']['events']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

"""Compare two SoC eval-run reports for metric drift and regressions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from req_tracker.evals.soc_query import (
    SocEvalRunRecord,
    build_soc_eval_run_record,
    build_soc_query_eval_report,
    diff_soc_eval_run_records,
)

CoverageMode = Literal["seed", "scale"]
OutputFormat = Literal["json", "text"]


def run_soc_eval_diff(
    *,
    coverage_mode: CoverageMode = "seed",
    baseline_report: Path | None = None,
    candidate_report: Path | None = None,
) -> dict[str, Any]:
    """Return a report-only diff for two eval-run records or reports."""
    baseline_payload = _load_report_or_current(
        coverage_mode=coverage_mode,
        path=baseline_report,
    )
    candidate_payload = _load_report_or_current(
        coverage_mode=coverage_mode,
        path=candidate_report,
    )
    baseline = _eval_record_from_payload(
        baseline_payload,
        run_id=f"soc_eval_{coverage_mode}_baseline",
    )
    candidate = _eval_record_from_payload(
        candidate_payload,
        run_id=f"soc_eval_{coverage_mode}_candidate",
    )
    return diff_soc_eval_run_records(baseline, candidate).model_dump(mode="json")


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument("--baseline-report", type=Path, default=None)
    parser.add_argument("--candidate-report", type=Path, default=None)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    payload = run_soc_eval_diff(
        coverage_mode=args.coverage_mode,
        baseline_report=args.baseline_report,
        candidate_report=args.candidate_report,
    )
    _print_report(payload, args.format)
    return 0 if payload["status"] == "passed" else 1


def _load_report_or_current(*, coverage_mode: CoverageMode, path: Path | None) -> dict[str, Any]:
    if path is None:
        return build_soc_query_eval_report(coverage_mode=coverage_mode, min_recall=0.85)
    return json.loads(path.read_text(encoding="utf-8"))


def _eval_record_from_payload(payload: dict[str, Any], *, run_id: str) -> SocEvalRunRecord:
    if "metrics" in payload and "query_set_id" in payload:
        return SocEvalRunRecord.model_validate(payload)
    return build_soc_eval_run_record(payload, run_id=run_id)


def _print_report(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(
        "SoC eval diff "
        f"status={payload['status']} "
        f"coverage_mode={payload['coverage_mode']} "
        f"regressions={payload['regression_delta']} "
        f"regressed_metrics={','.join(payload['regressed_metrics']) or 'none'}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

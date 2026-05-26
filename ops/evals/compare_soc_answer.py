"""Compare SoC query answers against packaged ground truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from req_tracker.evals.soc_query import build_soc_query_eval_report

OutputFormat = Literal["json", "text"]


def run_compare(*, coverage_mode: str = "seed") -> dict[str, Any]:
    """Run the seed Stage F comparison report."""
    return build_soc_query_eval_report(coverage_mode=coverage_mode, min_recall=0.85)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON comparison report.",
    )
    args = parser.parse_args()

    payload = run_compare(coverage_mode=args.coverage_mode)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    _print_report(payload, args.format)
    return 0 if payload["status"] == "passed" else 1


def _print_report(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print(
        "SoC answer comparison "
        f"status={payload['status']} "
        f"queries={payload['counts']['queries']} "
        f"recall={payload['recall']:.3f} "
        f"source_accuracy={payload['source_accuracy']:.3f} "
        f"regressions={payload['regression_count']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

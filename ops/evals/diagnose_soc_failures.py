"""Diagnose SoC query eval failures by pipeline layer."""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal

from req_tracker.evals.soc_query import build_soc_query_eval_report

OutputFormat = Literal["json", "text"]


def run_diagnostics(*, coverage_mode: str = "seed") -> dict[str, Any]:
    """Run the seed comparison report and return its diagnostics section."""
    return build_soc_query_eval_report(coverage_mode=coverage_mode, min_recall=0.85)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    args = parser.parse_args()

    payload = run_diagnostics(coverage_mode=args.coverage_mode)
    _print_report(payload, args.format)
    return 0 if payload["status"] == "passed" else 1


def _print_report(payload: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    diagnostics = payload["diagnostics"]
    print(
        "SoC failure diagnostics "
        f"status={payload['status']} "
        f"failed_cases={diagnostics['failed_cases']} "
        f"by_layer={diagnostics['by_layer']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

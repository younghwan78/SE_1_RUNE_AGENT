"""Run seed SoC Knowledge query evaluation.

The Stage D baseline evaluates the deterministic fixture-backed query service
against the packaged ground-truth query set. It intentionally stays behind the
typed service contract so Claude Code reranking and storage-backed retrieval can
replace the internals without changing the acceptance runner.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from req_tracker.evals.soc_query import build_soc_query_eval_report


def run_eval(*, coverage_mode: str = "seed") -> dict[str, Any]:
    """Evaluate query recall, source accuracy, schema validity, and unknown handling."""
    return build_soc_query_eval_report(coverage_mode=coverage_mode, min_recall=0.75)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    args = parser.parse_args()

    payload = run_eval(coverage_mode=args.coverage_mode)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "SoC query eval "
            f"status={payload['status']} "
            f"queries={payload['counts']['queries']} "
            f"recall={payload['recall']:.3f} "
            f"source_accuracy={payload['source_accuracy']:.3f}"
        )
    return 0 if payload["status"] == "passed" else 1

if __name__ == "__main__":
    raise SystemExit(main())

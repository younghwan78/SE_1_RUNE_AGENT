"""Run a local SoC query eval and persist its eval-run summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from req_tracker.evals.soc_query import (
    build_soc_query_eval_report,
    persist_soc_eval_run,
)
from req_tracker.storage.sqlite_store import SQLiteStateStore

CoverageMode = Literal["seed", "scale"]
DEFAULT_SQLITE_PATH = Path(".local_artifacts/soc_eval_persistence_rehearsal/state.sqlite3")


def run_soc_eval_persistence_rehearsal(
    *,
    coverage_mode: CoverageMode = "seed",
    sqlite_path: Path | None = None,
) -> dict[str, Any]:
    """Persist a SoC eval report into a local state store and read it back."""
    return _run_with_store(
        coverage_mode=coverage_mode,
        sqlite_path=sqlite_path or DEFAULT_SQLITE_PATH,
    )


def _run_with_store(*, coverage_mode: CoverageMode, sqlite_path: Path) -> dict[str, Any]:
    report = build_soc_query_eval_report(coverage_mode=coverage_mode, min_recall=0.85)
    store = SQLiteStateStore(sqlite_path)
    record = persist_soc_eval_run(
        report,
        state_store=store,
        run_id=f"soc_eval_{coverage_mode}_persistence_rehearsal",
    )
    reloaded = store.get("soc_eval_runs", record.run_id)
    record_payload = record.model_dump(mode="json")
    passed = report["status"] == "passed" and reloaded == record_payload
    return {
        "coverage_mode": coverage_mode,
        "persisted": {
            "collection": "soc_eval_runs",
            "record": record_payload,
        },
        "reloaded": reloaded,
        "schema_version": "v1",
        "status": "passed" if passed else "failed",
    }


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-mode", choices=("seed", "scale"), default="seed")
    parser.add_argument("--sqlite-path", type=Path, default=None)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    report = run_soc_eval_persistence_rehearsal(
        coverage_mode=args.coverage_mode,
        sqlite_path=args.sqlite_path,
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "SoC eval persistence rehearsal "
            f"status={report['status']} "
            f"coverage_mode={report['coverage_mode']}"
        )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

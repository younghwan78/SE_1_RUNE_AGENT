"""Generate the SoC Knowledge 400-artifact scale fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from req_tracker.fixtures.soc_knowledge import (
    SOC_FIXTURE_ROOT,
    SOC_SCALE_ARTIFACTS_FILENAME,
    SOC_SCALE_QUERIES_FILENAME,
)
from req_tracker.fixtures.soc_scale import (
    generate_soc_scale_artifacts,
    generate_soc_scale_queries,
    write_soc_scale_fixture,
    write_soc_scale_queries,
)

OutputFormat = Literal["json", "text"]


def generate_report(output_path: Path, queries_output_path: Path) -> dict[str, Any]:
    """Write the scale fixture and return a compact generation report."""
    artifacts = generate_soc_scale_artifacts()
    write_soc_scale_fixture(output_path)
    queries = generate_soc_scale_queries(artifacts)
    write_soc_scale_queries(queries_output_path)
    source_counts: dict[str, int] = {"jira": 0, "confluence": 0, "email": 0}
    for artifact in artifacts:
        source_counts[artifact.source_type] = source_counts.get(artifact.source_type, 0) + 1
    return {
        "status": "generated",
        "output_path": str(output_path),
        "queries_output_path": str(queries_output_path),
        "counts": {"artifacts": len(artifacts), **source_counts},
        "query_count": len(queries),
        "schema_version": "soc-fixture-scale-v0.1",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=SOC_FIXTURE_ROOT / SOC_SCALE_ARTIFACTS_FILENAME,
        help="Path for generated scale_artifacts.yaml.",
    )
    parser.add_argument(
        "--queries-output",
        type=Path,
        default=SOC_FIXTURE_ROOT / SOC_SCALE_QUERIES_FILENAME,
        help="Path for generated scale_queries.yaml.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def _print_report(report: dict[str, Any], output_format: OutputFormat) -> None:
    if output_format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    counts = report["counts"]
    print(
        "Generated SoC scale fixture: "
        f"{counts['artifacts']} artifacts "
        f"({counts['jira']} JIRA, {counts['confluence']} Confluence, "
        f"{counts['email']} Email), "
        f"{report['query_count']} queries"
    )


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    report = generate_report(args.output, args.queries_output)
    _print_report(report, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

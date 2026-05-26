"""Validate packaged SoC ontology schema assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from req_tracker.ontology.soc_models import SOC_SCHEMA_VERSION
from req_tracker.ontology.soc_schema import (
    SOC_SCHEMA_ROOT,
    SocSchema,
    SocSchemaValidationError,
    load_soc_schema,
    validate_soc_schema,
)

OutputFormat = Literal["json", "text"]


def validate_packaged_soc_schema(schema_root: Path = SOC_SCHEMA_ROOT) -> dict[str, Any]:
    """Return a structured SoC schema validation report."""
    schema = load_soc_schema(schema_root)
    validate_soc_schema(schema)
    return _report(schema=schema, schema_root=schema_root, status="passed")


def _report(*, schema: SocSchema, schema_root: Path, status: str) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SOC_SCHEMA_VERSION,
        "schema_root": str(schema_root),
        "counts": {
            "entities": len(schema.entities),
            "relations": len(schema.relations),
            "v_levels": len(schema.v_levels),
            "concerns": len(schema.concerns),
            "components": len(schema.components),
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema-root",
        type=Path,
        default=SOC_SCHEMA_ROOT,
        help="Path to docs/ontology/soc/schema/v0.1.",
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
    print(
        "SoC schema validation "
        f"{report['status']}: "
        f"{report['counts']['entities']} entities, "
        f"{report['counts']['relations']} relations, "
        f"{report['counts']['concerns']} concerns, "
        f"{report['counts']['components']} components"
    )


def main() -> int:
    """CLI entrypoint."""
    args = _parse_args()
    try:
        report = validate_packaged_soc_schema(args.schema_root)
    except SocSchemaValidationError as exc:
        failure = {
            "status": "failed",
            "schema_version": SOC_SCHEMA_VERSION,
            "schema_root": str(args.schema_root),
            "error": str(exc),
        }
        _print_report(failure, args.format)
        return 1
    _print_report(report, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

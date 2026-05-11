"""Run a local masking-policy rehearsal for release gating.

The rehearsal verifies that representative sensitive inputs are redacted before
model-gateway payload construction. It prints pattern labels and pass/fail
metadata only.
"""

import argparse
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from req_tracker.adapters.dummy.fixtures import fixture_by_name
from req_tracker.ingestion.masking import mask_text


@dataclass(frozen=True)
class MaskingCase:
    """One masking rehearsal case."""

    case_id: str
    input_text: str
    forbidden_patterns: list[str]
    expected_labels: list[str]


DEFAULT_CASES = (
    MaskingCase(
        case_id="email_serial_token",
        input_text=(
            "owner@example.com reports serial SN-IMX789-SECRET with "
            "api_key=super-secret-value"
        ),
        forbidden_patterns=[
            r"owner@example\.com",
            r"SN-IMX789-SECRET",
            r"super-secret-value",
        ],
        expected_labels=["email", "device_serial", "secret"],
    ),
    MaskingCase(
        case_id="security_fixture",
        input_text=fixture_by_name("RUNE_SECURITY")[0].body_text,
        forbidden_patterns=[
            r"owner@example\.com",
            r"SN-IMX789-SECRET",
        ],
        expected_labels=["email", "device_serial"],
    ),
)


def main() -> int:
    """CLI entrypoint."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    report = run_masking_rehearsal()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def run_masking_rehearsal(cases: tuple[MaskingCase, ...] = DEFAULT_CASES) -> dict[str, Any]:
    """Run masking checks and return a release-gate report."""
    results = [_run_case(case) for case in cases]
    return {
        "passed": all(result["passed"] for result in results),
        "case_count": len(results),
        "results": results,
        "schema_version": "v1",
    }


def _run_case(case: MaskingCase) -> dict[str, Any]:
    masked = mask_text(case.input_text)
    violation_indexes = [
        index
        for index, pattern in enumerate(case.forbidden_patterns)
        if re.search(pattern, masked.text)
    ]
    missing_labels = [
        label
        for label in case.expected_labels
        if label not in masked.labels
    ]
    return {
        "case_id": case.case_id,
        "passed": not violation_indexes and not missing_labels,
        "redaction_count": masked.redaction_count,
        "labels": masked.labels,
        "missing_labels": missing_labels,
        "violation_count": len(violation_indexes),
        "violation_indexes": violation_indexes,
        "config": _safe_case_config(case),
    }


def _safe_case_config(case: MaskingCase) -> dict[str, Any]:
    payload = asdict(case)
    payload["input_text"] = "<masked>"
    payload["forbidden_patterns"] = f"<{len(case.forbidden_patterns)} patterns>"
    return payload


if __name__ == "__main__":
    raise SystemExit(main())

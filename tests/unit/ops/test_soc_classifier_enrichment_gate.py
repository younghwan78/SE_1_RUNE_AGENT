"""Tests for the skip-safe SoC classifier enrichment quality gate."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def test_soc_classifier_enrichment_gate_dry_run_is_skip_safe() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/run_soc_classifier_enrichment_gate.py",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "skipped"
    assert payload["requires_live"] is True
    assert payload["checks"]["classifier_enrichment"]["prompt_version_id"] == (
        "pv_soc_axis_classification_v1"
    )


def test_soc_classifier_enrichment_gate_scores_injected_live_client() -> None:
    module = _load_gate()
    requests: list[Any] = []

    class FakeClient:
        def complete(self, **kwargs: Any) -> tuple[object, object, object]:
            from req_tracker.model_gateway.models import StructuredValidationResult
            from req_tracker.ontology.soc_models import SocAxisClassificationBatch

            requests.append(kwargs["request"])
            assert kwargs["request"].payload["artifact"]["external_id"] == (
                "SOC-CLAUDE-ENRICH-001"
            )
            baseline_axes = {
                item["axis"] for item in kwargs["request"].payload["baseline_classifications"]
            }
            assert "concern" not in baseline_axes
            parsed = SocAxisClassificationBatch.model_validate(
                {
                    "classifications": [
                        {
                            "entity_id": "SOC-CLAUDE-ENRICH-001",
                            "axis": "concern",
                            "value": "Performance",
                            "confidence": 0.74,
                            "evidence_ref": "body:latency",
                        }
                    ]
                }
            )
            return object(), parsed, StructuredValidationResult(status="passed")

    report = module.run_soc_classifier_enrichment_gate(
        live=True,
        client_factory=lambda _task_name: FakeClient(),
    )

    assert report["status"] == "passed"
    assert report["checks"]["classifier_enrichment"]["status"] == "passed"
    assert report["checks"]["classifier_enrichment"]["proposal_count"] == 1
    assert report["checks"]["classifier_enrichment"]["pending_count"] == 1
    assert requests[0].payload["output_contract"].startswith("Return ONLY raw JSON")
    assert "example_output" in requests[0].payload


def _load_gate() -> ModuleType:
    module_path = ROOT / "ops/evals/run_soc_classifier_enrichment_gate.py"
    spec = importlib.util.spec_from_file_location("run_soc_classifier_enrichment_gate", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

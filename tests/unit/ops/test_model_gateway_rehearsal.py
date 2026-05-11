"""Company model gateway rehearsal tests."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from req_tracker.model_gateway.models import ModelResponse


def test_model_gateway_rehearsal_reports_missing_endpoint_without_secret() -> None:
    module = _load_module()

    report = module.run_model_gateway_rehearsal({"MODEL_GATEWAY_API_KEY": "secret"})

    assert report["passed"] is False
    assert report["status"] == "missing_config"
    assert "MODEL_GATEWAY_ENDPOINT_URL" in report["missing"]
    assert "secret" not in str(report)
    assert report["config"]["api_key"] == "<set>"


def test_model_gateway_rehearsal_validates_probe_and_traces(monkeypatch: Any) -> None:
    module = _load_module()

    class FakeProvider:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["endpoint_url"] == "https://models.example.test/v1/complete"
            assert kwargs["api_key"] == "model-secret"

        def complete(self, request: Any, profile: Any, prompt: Any) -> ModelResponse:
            assert request.payload["probe_id"] == "MODEL-GATEWAY-PROBE-001"
            return ModelResponse(
                model_profile_id=profile.model_profile_id,
                prompt_version_id=prompt.prompt_version_id,
                output={
                    "probe_id": "MODEL-GATEWAY-PROBE-001",
                    "confidence_score": 0.9,
                },
                latency_ms=12,
            )

    monkeypatch.setattr(module, "HttpJsonModelProvider", FakeProvider)

    report = module.run_model_gateway_rehearsal(
        {
            "MODEL_GATEWAY_ENDPOINT_URL": "https://models.example.test/v1/complete",
            "MODEL_GATEWAY_API_KEY": "model-secret",
            "MODEL_GATEWAY_PROFILE_ID": "sandbox-profile",
        }
    )

    assert report["passed"] is True
    assert report["output"]["probe_id"] == "MODEL-GATEWAY-PROBE-001"
    assert report["trace_count"] == 1
    assert report["traces"][0]["validation_status"] == "passed"
    assert report["config"]["endpoint_url"] == "<set>"
    assert "model-secret" not in str(report)


def _load_module() -> ModuleType:
    module_path = Path("ops/model_gateway/rehearse_model_gateway.py")
    spec = importlib.util.spec_from_file_location("rehearse_model_gateway", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

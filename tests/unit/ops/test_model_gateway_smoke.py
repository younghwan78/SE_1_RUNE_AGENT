"""Model gateway smoke harness tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_model_gateway_smoke_exercises_http_fallback(tmp_path) -> None:  # type: ignore[no-untyped-def]
    smoke = _load_smoke_module()

    result = smoke.run_model_gateway_smoke(artifact_root=tmp_path / "artifacts")

    assert result["passed"] is True
    assert result["fallback_used"] is True
    assert result["model_profile_id"] == "smoke-fallback"
    assert result["trace_count"] == 2
    assert result["trace_statuses"] == ["failed", "passed"]
    assert result["input_tokens_total"] == 18
    assert result["output_tokens_total"] == 6
    assert result["cost_usd_total"] == 0.0009
    assert result["output"]["node_id"] == "SMOKE-NODE-001"
    assert result["raw_response_refs"][0] is None
    assert result["raw_response_refs"][1] is not None


def _load_smoke_module() -> ModuleType:
    module_path = Path("ops/model_gateway/smoke_model_gateway.py")
    spec = importlib.util.spec_from_file_location("smoke_model_gateway", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

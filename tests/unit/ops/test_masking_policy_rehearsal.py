"""Masking policy rehearsal tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_masking_policy_rehearsal_passes_default_cases() -> None:
    module = _load_module()

    report = module.run_masking_rehearsal()

    assert report["passed"] is True
    assert report["case_count"] >= 2
    assert all(result["violation_count"] == 0 for result in report["results"])
    assert "owner@example.com" not in str(report)
    assert "SN-IMX789-SECRET" not in str(report)
    assert "super-secret-value" not in str(report)


def test_masking_policy_rehearsal_reports_violation() -> None:
    module = _load_module()

    report = module.run_masking_rehearsal(
        (
            module.MaskingCase(
                case_id="unmasked_custom_secret",
                input_text="custom-secret-value",
                forbidden_patterns=[r"custom-secret-value"],
                expected_labels=["secret"],
            ),
        )
    )

    assert report["passed"] is False
    result = report["results"][0]
    assert result["violation_count"] == 1
    assert result["violation_indexes"] == [0]
    assert result["missing_labels"] == ["secret"]
    assert "custom-secret-value" not in str(report)


def _load_module() -> ModuleType:
    module_path = Path("ops/security/rehearse_masking_policy.py")
    spec = importlib.util.spec_from_file_location("rehearse_masking_policy", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

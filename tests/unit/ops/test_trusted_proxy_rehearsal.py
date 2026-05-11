"""Trusted proxy rehearsal tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_trusted_proxy_rehearsal_reports_missing_config_without_secret() -> None:
    module = _load_module()

    report = module.run_trusted_proxy_rehearsal({"TRUSTED_PROXY_SECRET": "secret-value"})

    assert report["passed"] is False
    assert report["status"] == "missing_config"
    assert "RUNE_API_BASE_URL" in report["missing"]
    assert "secret-value" not in str(report)
    assert report["config"]["trusted_secret"] == "<set>"


def test_trusted_proxy_rehearsal_checks_expected_statuses() -> None:
    module = _load_module()
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_get(url: str, headers: dict[str, str]) -> tuple[int, object]:
        calls.append((url, headers))
        if url.endswith("/api/v1/health"):
            return 200, {"status": "ok"}
        if url.endswith("/api/v1/schedule"):
            return 200, {"enabled": False}
        if "audit/events" in url and headers.get("x-rune-groups") == "rune-developers":
            return 403, {"detail": "insufficient role"}
        if headers.get("x-rune-projects") == "OTHER_PROJECT":
            return 403, {"detail": "project access denied"}
        return 200, []

    report = module.run_trusted_proxy_rehearsal(
        {
            "RUNE_API_BASE_URL": "http://127.0.0.1:8000",
            "TRUSTED_PROXY_SECRET": "proxy-secret",
            "RUNE_PROJECT_KEY": "RUNE_CAM_ALPHA",
        },
        http_get=fake_get,
    )

    assert report["passed"] is True
    assert len(report["checks"]) == 5
    assert all(check["passed"] for check in report["checks"])
    assert "proxy-secret" not in str(report)
    assert any(headers.get("x-rune-groups") == "rune-operators" for _, headers in calls)


def _load_module() -> ModuleType:
    module_path = Path("ops/security/rehearse_trusted_proxy_auth.py")
    spec = importlib.util.spec_from_file_location("rehearse_trusted_proxy_auth", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

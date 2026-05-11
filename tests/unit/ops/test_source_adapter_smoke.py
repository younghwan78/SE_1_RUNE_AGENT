"""Source adapter smoke harness tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_source_adapter_smoke_exercises_rest_pagination_and_permission_warnings() -> None:
    smoke = _load_smoke_module()

    result = smoke.run_source_adapter_smoke()

    assert result["passed"] is True
    assert result["jira_artifacts"] == ["CAM-REQ-001", "CAM-VER-001"]
    assert result["jira_links"] == ["CAM-REQ-001", "CAM-VER-001"]
    assert result["jira_permission_warnings"] == ["jira_permission_denied:403"]
    assert result["confluence_artifacts"] == ["1001", "1002"]
    assert result["confluence_links"] == ["CAM-REQ-001", "CAM-VER-001"]
    assert result["confluence_permission_warnings"] == ["confluence_permission_denied:401"]


def _load_smoke_module() -> ModuleType:
    module_path = Path("ops/source/smoke_source_adapters.py")
    spec = importlib.util.spec_from_file_location("smoke_source_adapters", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

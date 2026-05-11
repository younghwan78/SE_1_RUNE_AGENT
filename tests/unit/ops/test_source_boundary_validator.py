"""Source boundary validator tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_current_source_boundaries_pass() -> None:
    validator = _load_validator_module()

    report = validator.validate_source_boundaries()

    assert report["passed"] is True
    assert report["forbidden_core_hits"] == []
    assert report["forbidden_adapter_hits"] == []


def test_source_boundary_validator_reports_mcp_and_writeback_hits(tmp_path) -> None:  # type: ignore[no-untyped-def]
    validator = _load_validator_module()
    core_root = tmp_path / "src" / "req_tracker"
    adapter_root = core_root / "adapters"
    adapter_root.mkdir(parents=True)
    (core_root / "core.py").write_text('MCP_NAME = "RUNE_JIRA_MCP_URL"\n', encoding="utf-8")
    (adapter_root / "jira.py").write_text('method = "DELETE"\n', encoding="utf-8")

    report = validator.validate_source_boundaries(
        core_root=core_root,
        adapter_root=adapter_root,
    )

    assert report["passed"] is False
    assert any("RUNE_JIRA_MCP_URL" in hit for hit in report["forbidden_core_hits"])
    assert any('"DELETE"' in hit for hit in report["forbidden_adapter_hits"])


def _load_validator_module() -> ModuleType:
    module_path = Path("ops/source/validate_source_boundaries.py")
    spec = importlib.util.spec_from_file_location("validate_source_boundaries", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

"""Smoke load script tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_percentile_handles_empty_single_and_bounds() -> None:
    smoke_load = _load_smoke_module()

    assert smoke_load.percentile([], 95) == 0.0
    assert smoke_load.percentile([12.0], 95) == 12.0
    assert smoke_load.percentile([1.0, 2.0, 3.0], 0) == 1.0
    assert smoke_load.percentile([1.0, 2.0, 3.0], 100) == 3.0
    assert smoke_load.percentile([1.0, 2.0, 3.0], 50) == 2.0


def _load_smoke_module() -> ModuleType:
    module_path = Path("ops/load/smoke_load.py")
    spec = importlib.util.spec_from_file_location("smoke_load", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

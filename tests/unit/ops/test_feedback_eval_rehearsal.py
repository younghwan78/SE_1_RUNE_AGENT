"""Feedback eval rehearsal runner tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_feedback_eval_rehearsal_exercises_review_canary_and_security_blocker() -> None:
    rehearsal = _load_rehearsal_module()

    result = rehearsal.run_feedback_eval_rehearsal()

    assert result["passed"] is True
    assert result["initial_gate_status"] == "passed"
    assert result["review_status"] == "review_ready"
    assert result["canary_status"] == "canary"
    assert result["active_status"] == "active"
    assert result["rollback_status"] == "rolled_back"
    assert result["restored_version_id"] == "local_active"
    assert result["security_gate_status"] == "blocked"
    assert any("security_failures" in blocker for blocker in result["security_blockers"])


def _load_rehearsal_module() -> ModuleType:
    module_path = Path("ops/evals/run_feedback_eval_rehearsal.py")
    spec = importlib.util.spec_from_file_location("run_feedback_eval_rehearsal", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

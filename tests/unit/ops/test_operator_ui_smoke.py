"""Operator UI smoke tests."""

from runpy import run_path


def test_operator_ui_smoke_exercises_scaled_graph_projection() -> None:
    namespace = run_path("ops/ui/smoke_operator_ui.py")

    result = namespace["run_operator_ui_smoke"]()

    assert result["passed"] is True
    assert result["graph_counts"]["total_nodes"] >= 150
    assert result["graph_counts"]["visible_nodes"] <= 120
    assert all(result["checks"].values())

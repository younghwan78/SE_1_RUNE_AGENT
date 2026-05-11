"""Release-blocker checker tests."""

from runpy import run_path


def test_release_blocker_checker_maps_all_plan_blockers() -> None:
    namespace = run_path("ops/security/check_release_blockers.py")

    manifest = namespace["coverage_manifest"]()
    blocker_ids = {item["blocker_id"] for item in manifest}

    assert blocker_ids == {
        "masking_violation",
        "approved_graph_mutation_without_approval",
        "project_authorization_leak",
        "prompt_model_regression_or_ungated_activation",
        "graph_migration_without_rollback",
        "llm_raw_payload_forbidden_data",
    }


def test_release_blocker_checker_passes_current_evidence() -> None:
    namespace = run_path("ops/security/check_release_blockers.py")

    result = namespace["check_release_blockers"]()

    assert result["passed"] is True
    assert result["coverage_count"] == 6
    assert result["failed_count"] == 0
    assert all(check["missing"] == [] for check in result["checks"])

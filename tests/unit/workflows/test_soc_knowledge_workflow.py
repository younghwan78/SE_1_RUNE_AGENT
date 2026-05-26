"""Tests for the SoC Knowledge fixture ingestion workflow."""

from req_tracker.workflows.soc_knowledge import SocKnowledgeIngestionWorkflow


def test_soc_fixture_ingestion_workflow_builds_traceable_seed_projection() -> None:
    workflow = SocKnowledgeIngestionWorkflow()

    result = workflow.run_fixture_ingestion(
        run_id="soc_fixture_ingest_seed",
        coverage_mode="seed",
    )

    assert result.run.run_id == "soc_fixture_ingest_seed"
    assert result.run.run_type == "ingestion"
    assert result.run.status == "succeeded"
    assert result.coverage_mode == "seed"
    assert result.counts["artifacts"] == 40
    assert result.counts["events"] == 40
    assert result.counts["relations"] > 0
    assert result.storage_projection["events"] == 40
    assert result.storage_projection["embeddings"] == 40
    assert result.storage_projection["semantic_relations"] == result.counts["relations"]
    assert [step.stage_name for step in result.steps] == [
        "soc_fixture_source_snapshot",
        "soc_axis_classification",
        "soc_entity_extraction",
        "soc_lifecycle_events",
        "soc_storage_projection",
    ]
    assert all(step.validation_status == "passed" for step in result.steps)
    assert all(step.output_hash for step in result.steps)


def test_soc_fixture_ingestion_workflow_scales_without_live_storage() -> None:
    workflow = SocKnowledgeIngestionWorkflow()

    result = workflow.run_fixture_ingestion(
        run_id="soc_fixture_ingest_scale",
        coverage_mode="scale",
    )

    assert result.run.status == "succeeded"
    assert result.coverage_mode == "scale"
    assert result.counts["artifacts"] == 400
    assert result.counts["events"] == 400
    assert result.counts["relations"] > 0
    assert result.storage_projection["artifacts"] == 400
    assert result.storage_projection["classifications"] >= 400
    assert result.storage_projection["semantic_relations"] == result.counts["relations"]
    assert result.storage_projection["live_storage_required"] == 0


def test_soc_fixture_ingestion_workflow_has_stable_idempotency_fingerprint() -> None:
    workflow = SocKnowledgeIngestionWorkflow()

    first = workflow.run_fixture_ingestion(
        run_id="soc_fixture_ingest_scale_first",
        coverage_mode="scale",
    )
    second = workflow.run_fixture_ingestion(
        run_id="soc_fixture_ingest_scale_second",
        coverage_mode="scale",
    )

    assert first.idempotency_fingerprint == second.idempotency_fingerprint
    assert first.idempotency_fingerprint["counts"]["artifacts"] == 400
    assert first.idempotency_fingerprint["storage_projection"]["semantic_relations"] == (
        first.counts["relations"]
    )

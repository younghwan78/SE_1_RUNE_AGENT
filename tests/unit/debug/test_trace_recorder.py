"""Trace recorder tests."""

from req_tracker.debug.models import LLMCallTrace
from req_tracker.debug.traces import InMemoryTraceRepository


def test_trace_repository_records_successful_step() -> None:
    repo = InMemoryTraceRepository()
    run = repo.create_run(
        run_id="run_001",
        run_type="analysis",
        project_key="RUNE_CAM_ALPHA",
        triggered_by="tester",
        trigger_source="manual",
    )
    repo.mark_run_running(run.run_id)
    step = repo.start_step(
        step_id="step_001",
        run_id=run.run_id,
        stage_name="extract_nodes",
        input_payload={"artifact_ids": ["src_001"]},
    )
    finished = repo.finish_step(
        step_id=step.step_id,
        output_payload={"nodes": ["node_001"]},
        output_ref="artifact://nodes",
    )

    assert finished.status == "succeeded"
    assert finished.output_hash is not None
    assert finished.output_ref == "artifact://nodes"
    assert len(repo.list_steps(run.run_id)) == 1


def test_trace_repository_records_failed_step_and_llm_call() -> None:
    repo = InMemoryTraceRepository()
    repo.create_run(
        run_id="run_001",
        run_type="analysis",
        project_key="RUNE_CAM_ALPHA",
        triggered_by="tester",
        trigger_source="manual",
    )
    step = repo.start_step(
        step_id="step_001",
        run_id="run_001",
        stage_name="enrich_reasoning",
        input_payload={"edges": ["edge_001"]},
    )
    failed = repo.fail_step(
        step_id=step.step_id,
        error_class="STRUCTURED_OUTPUT_INVALID",
        error_message="missing evidence",
    )
    call = LLMCallTrace(
        llm_call_id="llm_001",
        run_id="run_001",
        step_id=step.step_id,
        model_profile_id="dummy",
        prompt_version_id="pv_reasoning_v1",
        request_hash="hash_req",
        masked_payload_ref="artifact://masked",
        latency_ms=5,
        validation_status="failed",
        error_message="missing evidence",
    )
    repo.record_llm_call(call)

    assert failed.status == "failed"
    assert failed.error_class == "STRUCTURED_OUTPUT_INVALID"
    assert repo.llm_calls[call.llm_call_id].validation_status == "failed"


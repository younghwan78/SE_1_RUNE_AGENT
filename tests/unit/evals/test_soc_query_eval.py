"""SoC query eval comparison and diagnostics tests."""

from req_tracker.evals.soc_query import (
    build_soc_eval_run_record,
    build_soc_query_eval_report,
    compare_soc_answer,
    detect_soc_regressions,
    diagnose_soc_case,
    diff_soc_eval_run_records,
    persist_soc_eval_run,
)
from req_tracker.fixtures.soc_knowledge import load_soc_query_set, load_soc_seed_artifacts
from req_tracker.ontology.soc_models import SocAnswerSource
from req_tracker.query.soc_service import answer_soc_query


def test_compare_soc_answer_identifies_missing_result_and_source_error() -> None:
    artifacts_by_id = {
        artifact.external_id: artifact for artifact in load_soc_seed_artifacts()
    }
    query = next(query for query in load_soc_query_set() if query.q_id == "Q2")
    answer = answer_soc_query(
        query_id=query.q_id,
        user_query=query.question,
        user_id="soc_eval",
        session_id="soc_eval",
        query_slice=query.slice,
    )
    degraded_items = answer.items[:-1]
    wrong_source = degraded_items[0].sources[0].model_copy(
        update={"url": "https://wrong.example/source"}
    )
    degraded_items[0] = degraded_items[0].model_copy(update={"sources": [wrong_source]})
    degraded_answer = answer.model_copy(update={"items": degraded_items})

    comparison = compare_soc_answer(
        query=query,
        answer=degraded_answer,
        artifacts_by_id=artifacts_by_id,
        schema_valid=True,
    )

    assert comparison.recall < 1.0
    assert comparison.missing_artifact_ids == ["SOC2-MAIL-002"]
    assert comparison.missing_source_urls == [
        artifacts_by_id["SOC1-JIRA-002"].source_url
    ]
    assert diagnose_soc_case(comparison) == ["retrieval", "source_link"]


def test_diagnose_soc_case_covers_schema_and_unknown_handling_failures() -> None:
    query = next(query for query in load_soc_query_set() if query.q_id == "Q5")
    source = SocAnswerSource(
        type="jira",
        key="SOC1-JIRA-001",
        url="https://jira.example/browse/SOC1-JIRA-001",
    )
    bad_answer = answer_soc_query(
        query_id=query.q_id,
        user_query=query.question,
        user_id="soc_eval",
        session_id="soc_eval",
        query_slice=query.slice,
    ).model_copy(
        update={
            "items": [
                {
                    "title": "Unexpected Bluetooth hit",
                    "summary": "Should not have matched.",
                    "sources": [source],
                    "level": "L2",
                    "concern": ["Performance"],
                    "component": ["Camera"],
                }
            ],
            "quality_signals": [],
        }
    )

    comparison = compare_soc_answer(
        query=query,
        answer=bad_answer,
        artifacts_by_id={},
        schema_valid=False,
    )

    assert diagnose_soc_case(comparison) == ["answer_schema", "unknown_handling"]


def test_detect_soc_regressions_flags_previously_passing_failed_cases() -> None:
    artifacts_by_id = {
        artifact.external_id: artifact for artifact in load_soc_seed_artifacts()
    }
    query = next(query for query in load_soc_query_set() if query.q_id == "Q1")
    answer = answer_soc_query(
        query_id=query.q_id,
        user_query=query.question,
        user_id="soc_eval",
        session_id="soc_eval",
        query_slice=query.slice,
    ).model_copy(update={"items": []})
    comparison = compare_soc_answer(
        query=query,
        answer=answer,
        artifacts_by_id=artifacts_by_id,
        schema_valid=True,
    )

    assert detect_soc_regressions([comparison], {"Q1"}) == ["Q1"]


def test_scale_query_eval_report_uses_400_fixture_recall_loop() -> None:
    report = build_soc_query_eval_report(coverage_mode="scale", min_recall=0.85)

    assert report["status"] == "passed"
    assert report["coverage_mode"] == "scale"
    assert report["full_stage_f_ready"] is True
    assert report["counts"]["artifacts"] == 400
    assert report["counts"]["queries"] >= 30
    assert report["recall"] >= 0.85
    assert report["source_accuracy"] >= 0.95
    assert report["regression_count"] == 0


def test_soc_query_eval_report_builds_persistable_eval_run_record() -> None:
    report = {
        "status": "passed",
        "coverage_mode": "scale",
        "counts": {"queries": 30, "artifacts": 400},
        "recall": 0.9,
        "source_accuracy": 0.97,
        "schema_pass_rate": 1.0,
        "graceful_unknown_pass_rate": 1.0,
        "regression_count": 0,
        "diagnostics": {"failed_cases": 0},
        "schema_version": "soc-query-eval-v0.1",
    }

    record = build_soc_eval_run_record(
        report,
        run_id="soc_eval_scale_001",
        query_set_id="soc_knowledge_scale_v0.1",
    )

    assert record.run_id == "soc_eval_scale_001"
    assert record.query_set_id == "soc_knowledge_scale_v0.1"
    assert record.coverage_mode == "scale"
    assert record.status == "passed"
    assert record.metrics["recall"] == 0.9
    assert record.metrics["counts"]["queries"] == 30
    assert record.regression_count == 0
    assert record.metadata["report_schema_version"] == "soc-query-eval-v0.1"


def test_soc_query_eval_report_persists_to_state_store() -> None:
    class FakeStateStore:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def upsert(self, **kwargs: object) -> None:
            self.calls.append(kwargs)

    store = FakeStateStore()
    report = {
        "status": "passed",
        "coverage_mode": "seed",
        "counts": {"queries": 20, "artifacts": 40},
        "recall": 1.0,
        "source_accuracy": 1.0,
        "schema_pass_rate": 1.0,
        "graceful_unknown_pass_rate": 1.0,
        "regression_count": 0,
        "diagnostics": {"failed_cases": 0},
        "schema_version": "soc-query-eval-v0.1",
    }

    record = persist_soc_eval_run(
        report,
        state_store=store,  # type: ignore[arg-type]
        run_id="soc_eval_seed_001",
    )

    assert record.run_id == "soc_eval_seed_001"
    assert store.calls == [
        {
            "collection": "soc_eval_runs",
            "entity_id": "soc_eval_seed_001",
            "project_key": "soc_knowledge",
            "payload": record,
        }
    ]


def test_soc_eval_run_diff_flags_metric_and_regression_changes() -> None:
    baseline = build_soc_eval_run_record(
        {
            "status": "passed",
            "coverage_mode": "scale",
            "counts": {"queries": 30, "artifacts": 400},
            "recall": 0.9,
            "source_accuracy": 0.97,
            "schema_pass_rate": 1.0,
            "graceful_unknown_pass_rate": 1.0,
            "regression_count": 0,
            "diagnostics": {"failed_cases": 0},
            "schema_version": "soc-query-eval-v0.1",
        },
        run_id="soc_eval_baseline",
    )
    candidate = build_soc_eval_run_record(
        {
            "status": "failed",
            "coverage_mode": "scale",
            "counts": {"queries": 30, "artifacts": 400},
            "recall": 0.82,
            "source_accuracy": 0.94,
            "schema_pass_rate": 1.0,
            "graceful_unknown_pass_rate": 1.0,
            "regression_count": 2,
            "diagnostics": {"failed_cases": 2},
            "schema_version": "soc-query-eval-v0.1",
        },
        run_id="soc_eval_candidate",
    )

    diff = diff_soc_eval_run_records(baseline, candidate)

    assert diff.status == "failed"
    assert diff.baseline_run_id == "soc_eval_baseline"
    assert diff.candidate_run_id == "soc_eval_candidate"
    assert diff.metric_deltas["recall"] == -0.08
    assert diff.metric_deltas["source_accuracy"] == -0.03
    assert diff.regression_delta == 2
    assert diff.changed_metrics == ["recall", "regression_count", "source_accuracy"]
    assert diff.regressed_metrics == ["recall", "regression_count", "source_accuracy"]

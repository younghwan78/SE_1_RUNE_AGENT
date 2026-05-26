"""Contract tests for SoC Knowledge PoC data models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from req_tracker.ontology.soc_models import (
    SocAnswer,
    SocAnswerItem,
    SocAnswerSource,
    SocAxisClassification,
    SocLifecycleEvent,
    SocQueryRequest,
    SocSlice,
)


def test_soc_axis_classification_round_trip() -> None:
    classification = SocAxisClassification(
        classification_id="soc_cls_jira_soc1_001_concern_power",
        entity_id="jira:SOC1-001",
        axis="concern",
        value="Power",
        confidence=0.91,
        source="rule",
        status="baseline",
        evidence_ref="artifact://run_001/classification/SOC1-001",
        run_id="run_001",
        step_id="step_run_001_classify_axes",
    )

    dumped = classification.model_dump(mode="json")

    assert dumped["axis"] == "concern"
    assert SocAxisClassification.model_validate(dumped).value == "Power"


def test_soc_axis_classification_rejects_empty_value_and_bad_confidence() -> None:
    with pytest.raises(ValidationError):
        SocAxisClassification(
            classification_id="soc_cls_bad",
            entity_id="jira:SOC1-001",
            axis="component",
            value="",
            confidence=1.2,
            source="claude",
            status="pending",
            run_id="run_001",
            step_id="step_run_001_classify_axes",
        )


def test_soc_lifecycle_event_preserves_source_lineage() -> None:
    event = SocLifecycleEvent(
        event_id="soc_evt_jira_soc1_001_status_001",
        entity_id="jira:SOC1-001",
        timestamp=datetime(2026, 1, 2, tzinfo=UTC),
        change_type="status_transition",
        before={"status": "Open"},
        after={"status": "Resolved"},
        source="jira_changelog",
        source_url="https://jira.example/browse/SOC1-001",
        run_id="run_001",
        step_id="step_run_001_extract_events",
    )

    assert event.before == {"status": "Open"}
    assert event.after == {"status": "Resolved"}
    assert event.source_url == "https://jira.example/browse/SOC1-001"


def test_soc_query_and_answer_contracts_cover_slice_response() -> None:
    request = SocQueryRequest(
        query_id="soc_query_001",
        user_query="이전 과제 power 관련 활동은?",
        user_id="architect_01",
        session_id="session_001",
        current_project="SOC-N",
        slice=SocSlice(
            pattern="concern_slice",
            project_keys=["SOC-N-1"],
            concerns=["Power"],
        ),
    )
    answer = SocAnswer(
        query_id=request.query_id,
        summary="SOC-N-1에서 power 관련 활동 1건을 찾았습니다.",
        items=[
            SocAnswerItem(
                title="DVFS governor power reduction",
                summary="Camera DVFS 설계가 power 절감을 목표로 검토되었습니다.",
                sources=[
                    SocAnswerSource(
                        type="jira",
                        key="SOC1-123",
                        url="https://jira.example/browse/SOC1-123",
                    )
                ],
                level="L2",
                concern=["Power"],
                component=["Camera"],
            )
        ],
        timeline=[],
        confidence="high",
        reasoning_log_ref="artifact://run_001/soc_query_reasoning",
        quality_signals=[],
    )

    assert answer.items[0].sources[0].url.endswith("SOC1-123")
    assert answer.items[0].concern == ["Power"]


def test_soc_answer_item_requires_source_link() -> None:
    with pytest.raises(ValidationError):
        SocAnswerItem(
            title="No source",
            summary="This item is invalid because PoC answers require provenance.",
            sources=[],
            level="L1",
            concern=["Power"],
            component=["Camera"],
        )


def test_soc_slice_requires_at_least_one_selector() -> None:
    with pytest.raises(ValidationError):
        SocSlice(pattern="concern_slice")

"""Tests for the SoC Knowledge Streamlit UI support layer."""

from __future__ import annotations

from typing import Any

import pytest

from req_tracker.ontology.soc_models import SocAnswer
from req_tracker.soc_ui.api_client import SocKnowledgeApiClient, SocUiApiError
from req_tracker.soc_ui.render_answer import build_answer_view


class CapturingTransport:
    """Capture API calls and return canned payloads."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "payload": payload,
                "headers": headers,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.responses.pop(0)


def test_soc_ui_client_posts_query_through_fastapi_contract_only() -> None:
    transport = CapturingTransport([_answer_payload()])
    client = SocKnowledgeApiClient(
        api_base_url="http://127.0.0.1:18000",
        user_id="architect_01",
        user_role="developer",
        api_key="local-secret",
        transport=transport,
    )

    answer = client.query(
        user_query="Camera shot 성능 이슈는?",
        session_id="session_001",
        conversation_history=[{"role": "user", "content": "이전 질문"}],
        current_project="SOC-N-1",
        query_id="soc_ui_query_001",
    )

    assert isinstance(answer, SocAnswer)
    assert answer.query_id.startswith("soc_ui_query_")
    assert transport.calls == [
        {
            "method": "POST",
            "path": "/api/v1/soc/query",
            "payload": {
                "query_id": answer.query_id,
                "user_query": "Camera shot 성능 이슈는?",
                "user_id": "architect_01",
                "session_id": "session_001",
                "current_project": "SOC-N-1",
                "conversation_history": [{"role": "user", "content": "이전 질문"}],
                "schema_version": "soc-v0.1",
            },
            "headers": {
                "content-type": "application/json",
                "x-rune-user": "architect_01",
                "x-rune-role": "developer",
                "x-rune-api-key": "local-secret",
            },
            "timeout_seconds": 30.0,
        }
    ]


def test_soc_ui_client_records_answer_feedback_with_reason_code() -> None:
    transport = CapturingTransport([_answer_payload(), _feedback_payload()])
    client = SocKnowledgeApiClient(
        api_base_url="http://127.0.0.1:18000",
        user_id="architect_01",
        user_role="developer",
        transport=transport,
    )
    answer = client.query(user_query="Power 이슈는?", session_id="session_001")

    result = client.record_answer_feedback(
        answer=answer,
        action="marked_low_quality",
        reason_code="weak_evidence",
        comment="근거가 부족함",
    )

    assert result["target_type"] == "answer"
    assert result["target_id"] == answer.query_id
    feedback_call = transport.calls[1]
    assert feedback_call["path"] == "/api/v1/feedback"
    assert feedback_call["payload"]["target_type"] == "answer"
    assert feedback_call["payload"]["target_id"] == answer.query_id
    assert feedback_call["payload"]["reason_code"] == "weak_evidence"
    assert feedback_call["payload"]["correction_text"] == "근거가 부족함"
    assert feedback_call["headers"]["x-rune-role"] == "developer"


def test_soc_ui_client_surfaces_api_failures_as_ui_errors() -> None:
    def failing_transport(**_kwargs: Any) -> dict[str, Any]:
        raise SocUiApiError("request timed out")

    client = SocKnowledgeApiClient(
        api_base_url="http://127.0.0.1:18000",
        user_id="architect_01",
        transport=failing_transport,
    )

    with pytest.raises(SocUiApiError, match="request timed out"):
        client.query(user_query="timeout test", session_id="session_001")


def test_answer_view_contains_source_links_timeline_feedback_and_reasoning() -> None:
    view = build_answer_view(SocAnswer.model_validate(_answer_payload()))

    assert view.summary == "Camera shot performance risk found."
    assert view.items[0].source_links == [
        {
            "label": "jira SOC-101",
            "url": "https://jira.example/browse/SOC-101",
        }
    ]
    assert view.timeline[0].timestamp == "2026-01-01T00:00:00Z"
    assert view.reasoning_log_ref == "artifact://soc_query_reasoning.json"
    assert view.feedback_target_id == "soc_ui_query_001"


def _answer_payload() -> dict[str, Any]:
    return {
        "query_id": "soc_ui_query_001",
        "summary": "Camera shot performance risk found.",
        "items": [
            {
                "title": "Camera shot FPS drop",
                "summary": "GPU load regressed during shot transition.",
                "sources": [
                    {
                        "type": "jira",
                        "key": "SOC-101",
                        "url": "https://jira.example/browse/SOC-101",
                    }
                ],
                "level": "L3",
                "concern": ["Performance"],
                "component": ["Camera", "GPU"],
            }
        ],
        "timeline": [
            {
                "event_id": "event_001",
                "entity_id": "SOC-101",
                "timestamp": "2026-01-01T00:00:00Z",
                "change_type": "created",
                "source": "jira",
                "source_url": "https://jira.example/browse/SOC-101",
                "run_id": "run_001",
                "step_id": "step_001",
            }
        ],
        "confidence": "high",
        "reasoning_log_ref": "artifact://soc_query_reasoning.json",
        "quality_signals": ["source_backed"],
        "schema_version": "soc-v0.1",
    }


def _feedback_payload() -> dict[str, Any]:
    return {
        "feedback_id": "fb_soc_ui_001",
        "target_type": "answer",
        "target_id": "soc_ui_query_001",
        "action": "marked_low_quality",
        "user_id": "architect_01",
        "user_role": "developer",
        "reason_code": "weak_evidence",
        "correction_text": "근거가 부족함",
        "schema_version": "v1",
    }

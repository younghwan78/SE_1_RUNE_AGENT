"""Pure answer view helpers for the SoC Knowledge Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass

from req_tracker.ontology.soc_models import SocAnswer


@dataclass(frozen=True)
class SocAnswerItemView:
    """Display-ready answer item."""

    title: str
    summary: str
    level: str | None
    concerns: list[str]
    components: list[str]
    source_links: list[dict[str, str]]


@dataclass(frozen=True)
class SocTimelineEventView:
    """Display-ready lifecycle event."""

    timestamp: str
    label: str
    source_url: str | None


@dataclass(frozen=True)
class SocAnswerView:
    """Display-ready answer data for Streamlit rendering."""

    query_id: str
    summary: str
    confidence: str
    items: list[SocAnswerItemView]
    timeline: list[SocTimelineEventView]
    reasoning_log_ref: str
    quality_signals: list[str]
    feedback_target_id: str


def build_answer_view(answer: SocAnswer) -> SocAnswerView:
    """Convert a strict SocAnswer into UI-friendly display data."""
    return SocAnswerView(
        query_id=answer.query_id,
        summary=answer.summary,
        confidence=answer.confidence,
        items=[
            SocAnswerItemView(
                title=item.title,
                summary=item.summary,
                level=item.level,
                concerns=item.concern,
                components=item.component,
                source_links=[
                    {
                        "label": _source_label(source_type=source.type, key=source.key),
                        "url": source.url,
                    }
                    for source in item.sources
                ],
            )
            for item in answer.items
        ],
        timeline=[
            SocTimelineEventView(
                timestamp=_isoformat_z(event.timestamp),
                label=f"{event.change_type}: {event.entity_id}",
                source_url=event.source_url,
            )
            for event in sorted(answer.timeline, key=lambda item: item.timestamp)
        ],
        reasoning_log_ref=answer.reasoning_log_ref,
        quality_signals=answer.quality_signals,
        feedback_target_id=answer.query_id,
    )


def _source_label(*, source_type: str, key: str | None) -> str:
    if key:
        return f"{source_type} {key}"
    return source_type


def _isoformat_z(value: object) -> str:
    if hasattr(value, "isoformat"):
        return str(value.isoformat()).replace("+00:00", "Z")
    return str(value)

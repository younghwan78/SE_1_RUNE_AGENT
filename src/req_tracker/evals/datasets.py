"""Feedback to eval dataset mapping."""

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.feedback.models import FeedbackEvent

_REASON_TO_DATASET = {
    "wrong_relation": "edge_linking/rejected_edges.jsonl",
    "weak_evidence": "retrieval/evidence_sufficiency.jsonl",
    "wrong_node_type": "node_extraction/corrections.jsonl",
    "duplicate": "entity_resolution/duplicates.jsonl",
    "missing_context": "retrieval/missed_context.jsonl",
    "wrong_severity": "findings/severity_corrections.jsonl",
    "security_concern": "security/blockers.jsonl",
    "other": "manual_triage/unclassified.jsonl",
}


class EvalDatasetCandidate(BaseModel):
    """Feedback grouped into a candidate eval dataset file."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: str
    reason_code: str
    feedback_ids: list[str] = Field(default_factory=list)
    target_ids: list[str] = Field(default_factory=list)


def build_eval_candidates(feedback: list[FeedbackEvent]) -> list[EvalDatasetCandidate]:
    """Group feedback into eval dataset candidates."""
    grouped: dict[str, EvalDatasetCandidate] = {}
    for event in feedback:
        reason = event.reason_code or "other"
        dataset_path = _REASON_TO_DATASET.get(reason, _REASON_TO_DATASET["other"])
        candidate = grouped.setdefault(
            dataset_path,
            EvalDatasetCandidate(dataset_path=dataset_path, reason_code=reason),
        )
        candidate.feedback_ids.append(event.feedback_id)
        candidate.target_ids.append(event.target_id)
    return list(grouped.values())


def feedback_counts_by_reason(feedback: list[FeedbackEvent]) -> dict[str, int]:
    """Return counts by reason code for dashboard/eval summaries."""
    counts: defaultdict[str, int] = defaultdict(int)
    for event in feedback:
        counts[event.reason_code or "other"] += 1
    return dict(counts)

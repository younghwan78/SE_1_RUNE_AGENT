"""Feedback-driven improvement candidate service."""

from collections import defaultdict

from req_tracker.debug.hash import stable_hash
from req_tracker.feedback.models import FeedbackEvent, ImprovementCandidate, ImprovementType

_REASON_TO_IMPROVEMENT: dict[str, ImprovementType] = {
    "wrong_relation": "rule",
    "weak_evidence": "retrieval_policy",
    "wrong_node_type": "prompt",
    "duplicate": "rule",
    "missing_context": "retrieval_policy",
    "wrong_severity": "scoring_threshold",
    "security_concern": "model_profile",
    "other": "prompt",
}


def build_improvement_candidates(
    feedback: list[FeedbackEvent],
    before_version_id: str = "local_active",
) -> list[ImprovementCandidate]:
    """Group feedback into controlled improvement candidates."""
    grouped: defaultdict[str, list[FeedbackEvent]] = defaultdict(list)
    for event in feedback:
        grouped[event.reason_code or "other"].append(event)

    candidates: list[ImprovementCandidate] = []
    for reason_code, events in sorted(grouped.items()):
        candidate_type = _REASON_TO_IMPROVEMENT.get(reason_code, "prompt")
        feedback_ids = [event.feedback_id for event in events]
        digest = stable_hash(
            {
                "reason_code": reason_code,
                "candidate_type": candidate_type,
                "feedback_ids": feedback_ids,
            }
        )[:16]
        candidates.append(
            ImprovementCandidate(
                candidate_id=f"imp_{digest}",
                candidate_type=candidate_type,
                source_feedback_ids=feedback_ids,
                proposed_change_summary=_summary(reason_code, candidate_type, len(events)),
                before_version_id=before_version_id,
                after_version_ref=f"draft://{candidate_type}/{reason_code}/{digest}",
                status="draft",
            )
        )
    return candidates


def _summary(reason_code: str, candidate_type: ImprovementType, count: int) -> str:
    return (
        f"Review {count} feedback events tagged {reason_code} and prepare a "
        f"{candidate_type} change for eval."
    )

"""Feedback to eval dataset tests."""

from req_tracker.evals.datasets import build_eval_candidates, feedback_counts_by_reason
from req_tracker.feedback.models import FeedbackEvent


def test_feedback_groups_into_eval_candidates() -> None:
    feedback = [
        FeedbackEvent(
            feedback_id="fb_1",
            target_type="edge",
            target_id="edge_1",
            action="rejected",
            user_id="reviewer",
            user_role="System Architect",
            reason_code="wrong_relation",
        ),
        FeedbackEvent(
            feedback_id="fb_2",
            target_type="edge",
            target_id="edge_2",
            action="modified",
            user_id="reviewer",
            user_role="System Architect",
            reason_code="weak_evidence",
        ),
    ]
    candidates = build_eval_candidates(feedback)
    paths = {candidate.dataset_path for candidate in candidates}
    assert "edge_linking/rejected_edges.jsonl" in paths
    assert "retrieval/evidence_sufficiency.jsonl" in paths
    assert feedback_counts_by_reason(feedback) == {"wrong_relation": 1, "weak_evidence": 1}


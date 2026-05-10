"""Feedback to eval dataset tests."""

from req_tracker.evals.datasets import build_eval_candidates, feedback_counts_by_reason
from req_tracker.evals.runner import run_local_eval_gate
from req_tracker.feedback.models import FeedbackEvent
from req_tracker.feedback.service import build_improvement_candidates


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


def test_feedback_builds_improvement_candidates_and_gate_blocks_single_case() -> None:
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
    ]

    improvements = build_improvement_candidates(feedback)
    assert improvements[0].candidate_type == "rule"
    assert improvements[0].status == "draft"

    gate = run_local_eval_gate(build_eval_candidates(feedback), "eval_1")
    assert gate.status == "blocked"
    assert "edge_linking/rejected_edges.jsonl:not_enough_cases" in gate.blockers

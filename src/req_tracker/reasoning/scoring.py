"""Deterministic confidence and approval-risk scoring."""

from req_tracker.approvals.models import RiskLevel
from req_tracker.ontology.models import TraceabilityEdge


def approval_risk_for_edge(edge: TraceabilityEdge) -> RiskLevel:
    """Route candidate edges by deterministic confidence and relation risk."""
    if edge.confidence_score < 0.5:
        return "high"
    if edge.relation in {"conflicts_with", "supersedes"}:
        return "high"
    if edge.is_inferred or edge.confidence_score < 0.85:
        return "medium"
    return "low"

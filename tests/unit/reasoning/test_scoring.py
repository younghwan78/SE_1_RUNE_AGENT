"""Deterministic scoring tests."""

from req_tracker.ontology.models import EvidenceSpan, TraceabilityEdge
from req_tracker.reasoning.scoring import approval_risk_for_edge


def _edge(
    *,
    confidence_score: float,
    relation: str = "satisfies",
    is_inferred: bool = False,
) -> TraceabilityEdge:
    return TraceabilityEdge(
        edge_id=f"edge_{relation}_{confidence_score}_{is_inferred}",
        source_node_id="node_src",
        target_node_id="node_dst",
        relation=relation,  # type: ignore[arg-type]
        reasoning="Scoring test edge.",
        evidence=[
            EvidenceSpan(
                artifact_id="src_1",
                source_url="dummy://src/1",
                quote_hash="hash_quote",
                extracted_text_preview="Relevant source evidence.",
            )
        ],
        is_inferred=is_inferred,
        confidence_score=confidence_score,
    )


def test_edge_approval_risk_uses_confidence_and_relation() -> None:
    assert approval_risk_for_edge(_edge(confidence_score=0.95)) == "low"
    assert approval_risk_for_edge(_edge(confidence_score=0.8)) == "medium"
    assert approval_risk_for_edge(_edge(confidence_score=0.9, is_inferred=True)) == "medium"
    assert approval_risk_for_edge(_edge(confidence_score=0.4)) == "high"
    assert (
        approval_risk_for_edge(_edge(confidence_score=0.95, relation="conflicts_with"))
        == "high"
    )

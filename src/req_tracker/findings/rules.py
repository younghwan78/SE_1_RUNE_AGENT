"""Deterministic graph finding rules."""

from collections import defaultdict
from typing import cast

from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import Finding, FindingType, OntologyNode, TraceabilityEdge


def analyze_findings(nodes: list[OntologyNode], edges: list[TraceabilityEdge]) -> list[Finding]:
    """Run deterministic finding rules over candidate graph projection."""
    findings: list[Finding] = []
    incoming_by_target: dict[str, list[TraceabilityEdge]] = defaultdict(list)
    outgoing_by_source: dict[str, list[TraceabilityEdge]] = defaultdict(list)
    for edge in edges:
        incoming_by_target[edge.target_node_id].append(edge)
        outgoing_by_source[edge.source_node_id].append(edge)

    for node in nodes:
        if node.node_type == "Requirement":
            has_impl = any(
                edge.relation in {"satisfies", "implements"}
                for edge in incoming_by_target[node.node_id]
            )
            has_ver = any(edge.relation == "verifies" for edge in incoming_by_target[node.node_id])
            if not has_impl:
                findings.append(
                    _finding("REQ_WITHOUT_IMPLEMENTATION", node, "missing_implementation")
                )
            if not has_ver:
                findings.append(_finding("REQ_WITHOUT_VERIFICATION", node, "missing_verification"))
        if node.node_type == "Design_Spec":
            has_parent = any(
                edge.relation in {"implements", "satisfies", "derives"}
                for edge in outgoing_by_source[node.node_id]
            )
            if not has_parent:
                findings.append(_finding("DESIGN_WITHOUT_PARENT", node, "orphan_node"))

    impl_by_target: dict[str, list[TraceabilityEdge]] = defaultdict(list)
    for edge in edges:
        if edge.relation == "implements":
            impl_by_target[edge.target_node_id].append(edge)
    for target_id, impl_edges in impl_by_target.items():
        if len(impl_edges) > 1:
            affected = [target_id, *(edge.source_node_id for edge in impl_edges)]
            finding_hash = stable_hash(
                {"rule": "CONFLICTING_ALTERNATIVES", "ids": affected}
            )
            findings.append(
                Finding(
                    finding_id=f"fdg_{finding_hash[:16]}",
                    finding_type="conflict",
                    severity="high",
                    affected_node_ids=affected,
                    affected_edge_ids=[edge.edge_id for edge in impl_edges],
                    description=(
                        "Multiple implementation alternatives target the same architecture."
                    ),
                    suggested_action=(
                        "Select one implementation or mark alternatives as superseded."
                    ),
                    evidence=impl_edges[0].evidence,
                    detection_method="rule",
                    rule_id="CONFLICTING_ALTERNATIVES",
                )
            )
    return findings


def _finding(rule_id: str, node: OntologyNode, finding_type: str) -> Finding:
    typed_finding_type = cast(FindingType, finding_type)
    return Finding(
        finding_id=f"fdg_{stable_hash({'rule': rule_id, 'node': node.node_id})[:16]}",
        finding_type=typed_finding_type,
        severity="high" if finding_type == "missing_implementation" else "medium",
        affected_node_ids=[node.node_id],
        affected_edge_ids=[],
        description=f"{node.node_id} triggered {rule_id}.",
        suggested_action="Review traceability links and add missing relation or verification.",
        evidence=node.evidence,
        detection_method="rule",
        rule_id=rule_id,
    )


"""Deterministic relation linking."""

from typing import cast, get_args

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.ontology.id_factory import edge_id
from req_tracker.ontology.models import EdgeRelation, EvidenceSpan, OntologyNode, TraceabilityEdge

_VALID_RELATIONS = set(get_args(EdgeRelation))


def link_edges(
    raws: list[RawSourceArtifact],
    nodes: list[OntologyNode],
    evidence_by_external_id: dict[str, EvidenceSpan],
) -> list[TraceabilityEdge]:
    """Create candidate edges from source links and relation metadata."""
    node_by_external = {_external_id_from_node(node): node for node in nodes}
    edges: dict[str, TraceabilityEdge] = {}
    for raw in raws:
        source_node = node_by_external.get(raw.external_id)
        if source_node is None:
            continue
        relations = raw.metadata.get("relations", {})
        if not isinstance(relations, dict):
            relations = {}
        for target_external_id in raw.links:
            target_node = node_by_external.get(target_external_id)
            if target_node is None:
                continue
            relation_value = relations.get(
                target_external_id,
                _default_relation(source_node, target_node),
            )
            if relation_value not in _VALID_RELATIONS:
                continue
            relation = cast(EdgeRelation, relation_value)
            evidence = evidence_by_external_id.get(raw.external_id)
            if evidence is None:
                continue
            eid = edge_id(source_node.node_id, relation, target_node.node_id)
            edges[eid] = TraceabilityEdge(
                edge_id=eid,
                source_node_id=source_node.node_id,
                target_node_id=target_node.node_id,
                relation=relation,
                reasoning=f"Source link from {raw.external_id} to {target_external_id}.",
                evidence=[evidence],
                is_inferred=relation in {"affects", "conflicts_with"},
                confidence_score=0.8,
                approval_status="pending",
            )
    return list(edges.values())


def _default_relation(source: OntologyNode, target: OntologyNode) -> EdgeRelation:
    if source.node_type == "Verification":
        return "verifies"
    if source.node_type in {"Design_Spec", "Architecture_Block"}:
        return "implements" if target.node_type != "Requirement" else "satisfies"
    if source.node_type in {"Issue", "Risk"}:
        return "affects"
    return "derives"


def _external_id_from_node(node: OntologyNode) -> str:
    prefix = f"node_{node.project_key}_"
    if node.node_id.startswith(prefix):
        return node.node_id.removeprefix(prefix).replace("_", "-")
    return node.node_id

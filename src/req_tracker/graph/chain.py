"""Traceability chain projection."""

from collections import defaultdict, deque
from typing import Literal

from pydantic import BaseModel, ConfigDict

from req_tracker.ontology.models import OntologyNode, TraceabilityEdge

GraphChainDirection = Literal["upstream", "downstream", "both"]
GraphChainEdgeStatus = Literal["approved", "pending"]


class TraceabilityChainNode(BaseModel):
    """Node displayed in a traceability chain."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: str
    name: str
    description: str
    project_key: str
    depth: int
    is_center: bool


class TraceabilityChainEdge(BaseModel):
    """Edge displayed in a traceability chain."""

    model_config = ConfigDict(extra="forbid")

    edge_id: str
    source_node_id: str
    source_node_name: str | None = None
    target_node_id: str
    target_node_name: str | None = None
    relation: str
    reasoning: str
    confidence_score: float
    view_status: GraphChainEdgeStatus
    approval_status: str
    approval_id: str | None = None


class TraceabilityChain(BaseModel):
    """Hop-limited traceability chain around a node."""

    model_config = ConfigDict(extra="forbid")

    project_key: str
    center_node_id: str
    direction: GraphChainDirection
    depth: int
    include_pending: bool
    nodes: list[TraceabilityChainNode]
    edges: list[TraceabilityChainEdge]
    truncated: bool


def build_traceability_chain(
    *,
    project_key: str,
    center_node_id: str,
    nodes: list[OntologyNode],
    approved_edges: list[TraceabilityEdge],
    pending_edges: list[TraceabilityEdge],
    pending_approval_by_edge_id: dict[str, str] | None = None,
    direction: GraphChainDirection = "both",
    depth: int = 3,
    include_pending: bool = True,
    limit_nodes: int = 200,
) -> TraceabilityChain:
    """Build a deterministic traceability chain for UI/API consumers."""
    capped_depth = min(max(depth, 1), 6)
    capped_limit = min(max(limit_nodes, 1), 500)
    node_map = {node.node_id: node for node in nodes if node.project_key == project_key}
    edge_records: list[tuple[TraceabilityEdge, GraphChainEdgeStatus]] = [
        (edge, "approved")
        for edge in approved_edges
        if _edge_in_project(edge, node_map)
    ]
    if include_pending:
        edge_records.extend(
            (edge, "pending")
            for edge in pending_edges
            if _edge_in_project(edge, node_map)
        )

    adjacency = _adjacency(edge_records, direction)
    selected_depths = _walk_chain(
        center_node_id=center_node_id,
        adjacency=adjacency,
        depth=capped_depth,
        limit_nodes=capped_limit,
    )
    selected_ids = set(selected_depths)
    approvals = pending_approval_by_edge_id or {}
    visible_edges = [
        _edge_view(edge, status, node_map, approvals)
        for edge, status in edge_records
        if edge.source_node_id in selected_ids and edge.target_node_id in selected_ids
    ]
    visible_nodes = [
        _node_view(node_map[node_id], selected_depths[node_id], center_node_id)
        for node_id in sorted(selected_ids, key=lambda item: (selected_depths[item], item))
        if node_id in node_map
    ]
    return TraceabilityChain(
        project_key=project_key,
        center_node_id=center_node_id,
        direction=direction,
        depth=capped_depth,
        include_pending=include_pending,
        nodes=visible_nodes,
        edges=sorted(visible_edges, key=lambda edge: (edge.relation, edge.edge_id)),
        truncated=len(selected_depths) >= capped_limit,
    )


def _edge_in_project(edge: TraceabilityEdge, node_map: dict[str, OntologyNode]) -> bool:
    return edge.source_node_id in node_map and edge.target_node_id in node_map


def _adjacency(
    edges: list[tuple[TraceabilityEdge, GraphChainEdgeStatus]],
    direction: GraphChainDirection,
) -> dict[str, set[str]]:
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    for edge, _status in edges:
        if direction in {"downstream", "both"}:
            adjacency[edge.source_node_id].add(edge.target_node_id)
        if direction in {"upstream", "both"}:
            adjacency[edge.target_node_id].add(edge.source_node_id)
    return adjacency


def _walk_chain(
    *,
    center_node_id: str,
    adjacency: dict[str, set[str]],
    depth: int,
    limit_nodes: int,
) -> dict[str, int]:
    selected = {center_node_id: 0}
    queue: deque[tuple[str, int]] = deque([(center_node_id, 0)])
    while queue and len(selected) < limit_nodes:
        node_id, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for neighbor_id in sorted(adjacency.get(node_id, set())):
            if neighbor_id in selected:
                continue
            selected[neighbor_id] = current_depth + 1
            queue.append((neighbor_id, current_depth + 1))
            if len(selected) >= limit_nodes:
                break
    return selected


def _node_view(
    node: OntologyNode,
    depth: int,
    center_node_id: str,
) -> TraceabilityChainNode:
    return TraceabilityChainNode(
        node_id=node.node_id,
        node_type=node.node_type,
        name=node.name,
        description=node.description,
        project_key=node.project_key,
        depth=depth,
        is_center=node.node_id == center_node_id,
    )


def _edge_view(
    edge: TraceabilityEdge,
    status: GraphChainEdgeStatus,
    node_map: dict[str, OntologyNode],
    pending_approval_by_edge_id: dict[str, str],
) -> TraceabilityChainEdge:
    return TraceabilityChainEdge(
        edge_id=edge.edge_id,
        source_node_id=edge.source_node_id,
        source_node_name=node_map[edge.source_node_id].name,
        target_node_id=edge.target_node_id,
        target_node_name=node_map[edge.target_node_id].name,
        relation=edge.relation,
        reasoning=edge.reasoning,
        confidence_score=edge.confidence_score,
        view_status=status,
        approval_status="pending" if status == "pending" else edge.approval_status,
        approval_id=pending_approval_by_edge_id.get(edge.edge_id),
    )

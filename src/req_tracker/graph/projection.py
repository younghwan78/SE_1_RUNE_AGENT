"""Graph view projection for scalable UI rendering."""

from collections import defaultdict, deque
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.ontology.models import Finding, OntologyNode, Severity, TraceabilityEdge

GraphViewMode = Literal["overview", "neighborhood", "orphans", "pending", "full"]

_SEVERITY_RANK: dict[Severity, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class GraphNodeView(BaseModel):
    """Node plus graph-view metadata."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: str
    name: str
    description: str
    project_key: str
    domain: str | None = None
    lifecycle_state: str
    source_artifact_ids: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str
    confidence_score: float
    version: int
    schema_version: str
    approved_in_degree: int = 0
    approved_out_degree: int = 0
    pending_in_degree: int = 0
    pending_out_degree: int = 0
    finding_count: int = 0
    risk_level: str = "none"
    is_orphan: bool = False
    has_pending_edges: bool = False


class GraphEdgeView(BaseModel):
    """Edge plus graph-view metadata."""

    model_config = ConfigDict(extra="forbid")

    edge_id: str
    source_node_id: str
    target_node_id: str
    relation: str
    reasoning: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    is_inferred: bool
    confidence_score: float
    approval_status: str
    approved_by: str | None = None
    approved_at: str | None = None
    version: int
    schema_version: str
    view_status: Literal["approved", "pending"]


class GraphGroupView(BaseModel):
    """Aggregated graph count for overview/navigation."""

    model_config = ConfigDict(extra="forbid")

    group_id: str
    label: str
    node_type: str | None = None
    count: int
    orphan_count: int = 0
    pending_count: int = 0
    finding_count: int = 0


class GraphProjectionCounts(BaseModel):
    """Graph projection count summary."""

    model_config = ConfigDict(extra="forbid")

    total_nodes: int
    visible_nodes: int
    approved_edges: int
    pending_edges: int
    visible_approved_edges: int
    visible_pending_edges: int
    orphan_nodes: int
    findings: int
    truncated: bool


class GraphProjection(BaseModel):
    """UI-ready graph projection."""

    model_config = ConfigDict(extra="forbid")

    mode: GraphViewMode
    nodes: list[GraphNodeView]
    approved_edges: list[GraphEdgeView]
    pending_edges: list[GraphEdgeView]
    edges: list[GraphEdgeView]
    groups: list[GraphGroupView]
    counts: GraphProjectionCounts


def build_graph_projection(
    *,
    nodes: list[OntologyNode],
    approved_edges: list[TraceabilityEdge],
    pending_edges: list[TraceabilityEdge],
    findings: list[Finding],
    mode: GraphViewMode = "overview",
    center_node_id: str | None = None,
    hops: int = 1,
    limit_nodes: int = 120,
) -> GraphProjection:
    """Build a graph view projection with node status metadata."""
    capped_hops = min(max(hops, 1), 3)
    capped_limit = min(max(limit_nodes, 1), 500)
    node_map = {node.node_id: node for node in nodes}
    approved = [edge for edge in approved_edges if _edge_nodes_exist(edge, node_map)]
    pending = [edge for edge in pending_edges if _edge_nodes_exist(edge, node_map)]
    finding_by_node = _finding_by_node(findings)
    risk_by_node = _risk_by_node(findings)
    degree = _degree_by_node(approved, pending)

    node_views = [
        _node_view(
            node,
            degree[node.node_id],
            finding_by_node[node.node_id],
            risk_by_node[node.node_id],
        )
        for node in nodes
    ]
    selected = _select_nodes(
        node_views,
        approved,
        pending,
        mode=mode,
        center_node_id=center_node_id,
        hops=capped_hops,
        limit_nodes=capped_limit,
    )
    selected_ids = {node.node_id for node in selected}
    visible_approved = [
        _edge_view(edge, "approved")
        for edge in approved
        if edge.source_node_id in selected_ids and edge.target_node_id in selected_ids
    ]
    visible_pending = [
        _edge_view(edge, "pending")
        for edge in pending
        if edge.source_node_id in selected_ids and edge.target_node_id in selected_ids
    ]
    groups = _groups(node_views)
    return GraphProjection(
        mode=mode,
        nodes=selected,
        approved_edges=visible_approved,
        pending_edges=visible_pending,
        edges=[*visible_approved, *visible_pending],
        groups=groups,
        counts=GraphProjectionCounts(
            total_nodes=len(node_views),
            visible_nodes=len(selected),
            approved_edges=len(approved),
            pending_edges=len(pending),
            visible_approved_edges=len(visible_approved),
            visible_pending_edges=len(visible_pending),
            orphan_nodes=sum(1 for node in node_views if node.is_orphan),
            findings=len(findings),
            truncated=len(selected) < len(node_views),
        ),
    )


def _edge_nodes_exist(edge: TraceabilityEdge, node_map: dict[str, OntologyNode]) -> bool:
    return edge.source_node_id in node_map and edge.target_node_id in node_map


def _degree_by_node(
    approved_edges: list[TraceabilityEdge],
    pending_edges: list[TraceabilityEdge],
) -> dict[str, dict[str, int]]:
    degree: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {
            "approved_in": 0,
            "approved_out": 0,
            "pending_in": 0,
            "pending_out": 0,
        }
    )
    for edge in approved_edges:
        degree[edge.source_node_id]["approved_out"] += 1
        degree[edge.target_node_id]["approved_in"] += 1
    for edge in pending_edges:
        degree[edge.source_node_id]["pending_out"] += 1
        degree[edge.target_node_id]["pending_in"] += 1
    return degree


def _finding_by_node(findings: list[Finding]) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for finding in findings:
        for node_id in finding.affected_node_ids:
            counts[node_id] += 1
    return counts


def _risk_by_node(findings: list[Finding]) -> dict[str, str]:
    risk: defaultdict[str, str] = defaultdict(lambda: "none")
    rank_by_node: defaultdict[str, int] = defaultdict(int)
    for finding in findings:
        rank = _SEVERITY_RANK[finding.severity]
        for node_id in finding.affected_node_ids:
            if rank > rank_by_node[node_id]:
                rank_by_node[node_id] = rank
                risk[node_id] = finding.severity
    return risk


def _node_view(
    node: OntologyNode,
    degree: dict[str, int],
    finding_count: int,
    risk_level: str,
) -> GraphNodeView:
    total_degree = sum(degree.values())
    pending_degree = degree["pending_in"] + degree["pending_out"]
    return GraphNodeView(
        **node.model_dump(mode="json"),
        approved_in_degree=degree["approved_in"],
        approved_out_degree=degree["approved_out"],
        pending_in_degree=degree["pending_in"],
        pending_out_degree=degree["pending_out"],
        finding_count=finding_count,
        risk_level=risk_level,
        is_orphan=total_degree == 0,
        has_pending_edges=pending_degree > 0,
    )


def _edge_view(
    edge: TraceabilityEdge,
    view_status: Literal["approved", "pending"],
) -> GraphEdgeView:
    payload = edge.model_dump(mode="json")
    if view_status == "pending":
        payload["approval_status"] = "pending"
        payload["approved_by"] = None
        payload["approved_at"] = None
    return GraphEdgeView(**payload, view_status=view_status)


def _select_nodes(
    nodes: list[GraphNodeView],
    approved_edges: list[TraceabilityEdge],
    pending_edges: list[TraceabilityEdge],
    *,
    mode: GraphViewMode,
    center_node_id: str | None,
    hops: int,
    limit_nodes: int,
) -> list[GraphNodeView]:
    if mode == "full":
        return _sort_nodes(nodes)[:limit_nodes]
    if mode == "orphans":
        return _sort_nodes([node for node in nodes if node.is_orphan])[:limit_nodes]
    if mode == "pending":
        return _sort_nodes([node for node in nodes if node.has_pending_edges])[:limit_nodes]
    if mode == "neighborhood" and center_node_id:
        neighbor_ids = _neighborhood_ids(center_node_id, [*approved_edges, *pending_edges], hops)
        return _sort_nodes([node for node in nodes if node.node_id in neighbor_ids])[:limit_nodes]
    return _sort_nodes(nodes)[:limit_nodes]


def _neighborhood_ids(
    center_node_id: str,
    edges: list[TraceabilityEdge],
    hops: int,
) -> set[str]:
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.source_node_id].add(edge.target_node_id)
        adjacency[edge.target_node_id].add(edge.source_node_id)

    seen = {center_node_id}
    queue: deque[tuple[str, int]] = deque([(center_node_id, 0)])
    while queue:
        node_id, depth = queue.popleft()
        if depth >= hops:
            continue
        for neighbor_id in adjacency[node_id]:
            if neighbor_id in seen:
                continue
            seen.add(neighbor_id)
            queue.append((neighbor_id, depth + 1))
    return seen


def _sort_nodes(nodes: list[GraphNodeView]) -> list[GraphNodeView]:
    return sorted(
        nodes,
        key=lambda node: (
            0 if node.is_orphan else 1,
            0 if node.risk_level in {"critical", "high"} else 1,
            0 if node.has_pending_edges else 1,
            node.node_type,
            node.node_id,
        ),
    )


def _groups(nodes: list[GraphNodeView]) -> list[GraphGroupView]:
    grouped: defaultdict[str, list[GraphNodeView]] = defaultdict(list)
    for node in nodes:
        grouped[node.node_type].append(node)
    return [
        GraphGroupView(
            group_id=f"group_{node_type}",
            label=node_type,
            node_type=node_type,
            count=len(group_nodes),
            orphan_count=sum(1 for node in group_nodes if node.is_orphan),
            pending_count=sum(1 for node in group_nodes if node.has_pending_edges),
            finding_count=sum(node.finding_count for node in group_nodes),
        )
        for node_type, group_nodes in sorted(grouped.items())
    ]

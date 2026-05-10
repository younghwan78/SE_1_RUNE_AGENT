"""Graph APIs."""

from typing import Any

from fastapi import APIRouter, Request

from req_tracker.graph.projection import GraphViewMode, build_graph_projection
from req_tracker.ontology.models import TraceabilityEdge

router = APIRouter(tags=["graph"])


@router.get("/graph/subgraph")
def subgraph(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, list[dict[str, Any]]]:
    """Return approved local graph subgraph."""
    runtime = request.app.state.runtime
    result: dict[str, list[dict[str, Any]]] = runtime.graph.subgraph(project_key)
    return result


@router.get("/graph/projection")
def graph_projection(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    mode: GraphViewMode = "overview",
    center_node_id: str | None = None,
    hops: int = 1,
    limit_nodes: int = 120,
) -> dict[str, Any]:
    """Return approved nodes plus approved and pending edge projection."""
    runtime = request.app.state.runtime
    nodes = [node for node in runtime.graph.nodes.values() if node.project_key == project_key]
    approved_edges = [
        edge
        for edge in runtime.graph.edges.values()
        if edge.source_node_id in runtime.graph.nodes and edge.target_node_id in runtime.graph.nodes
    ]
    pending_edges: list[TraceabilityEdge] = []
    pending_delta_ids = {
        item.graph_delta_ref
        for item in runtime.approvals.items.values()
        if item.project_key == project_key and item.status == "pending" and item.graph_delta_ref
    }
    for delta in runtime.approvals.deltas.values():
        if delta.project_key != project_key or delta.delta_id not in pending_delta_ids:
            continue
        for operation in delta.operations:
            if operation.operation == "create_edge":
                edge = dict(operation.payload)
                edge["approval_status"] = "pending"
                edge["approved_by"] = None
                edge["approved_at"] = None
                pending_edges.append(TraceabilityEdge.model_validate(edge))
    findings = [
        finding
        for analysis in runtime.analyses.values()
        if analysis.run.project_key == project_key
        for finding in analysis.findings
    ]
    projection = build_graph_projection(
        nodes=nodes,
        approved_edges=approved_edges,
        pending_edges=pending_edges,
        findings=findings,
        mode=mode,
        center_node_id=center_node_id,
        hops=hops,
        limit_nodes=limit_nodes,
    )
    result: dict[str, Any] = projection.model_dump(mode="json")
    return result

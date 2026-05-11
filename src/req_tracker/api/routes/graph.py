"""Graph APIs."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from req_tracker.api.security import require_project, require_role
from req_tracker.graph.chain import GraphChainDirection, build_traceability_chain
from req_tracker.graph.projection import GraphEdgeFilter, GraphViewMode, build_graph_projection
from req_tracker.ontology.models import TraceabilityEdge

router = APIRouter(tags=["graph"])


@router.get("/projects")
def list_projects(request: Request) -> list[dict[str, Any]]:
    """Return projects visible to the current user."""
    user = require_role(request, "viewer")
    runtime = request.app.state.runtime
    project_keys = {
        run.project_key
        for run in runtime.traces.runs.values()
    }
    project_keys.update(node.project_key for node in runtime.graph.nodes.values())
    project_keys.add(runtime.scheduler.config.project_key)
    visible_projects = [
        project_key
        for project_key in sorted(project_keys)
        if "*" in user.project_keys or project_key in user.project_keys
    ]
    return [
        {
            "project_key": project_key,
            "run_count": sum(
                1 for run in runtime.traces.runs.values() if run.project_key == project_key
            ),
            "node_count": sum(
                1 for node in runtime.graph.nodes.values() if node.project_key == project_key
            ),
            "approved_edge_count": _approved_edge_count(runtime, project_key),
        }
        for project_key in visible_projects
    ]


@router.get("/graph/nodes")
def list_graph_nodes(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return graph nodes for a project."""
    require_project(request, project_key)
    runtime = request.app.state.runtime
    capped_limit = min(max(limit, 1), 1000)
    nodes = [
        node
        for node in runtime.graph.nodes.values()
        if node.project_key == project_key
    ]
    nodes.sort(key=lambda node: node.node_id)
    return [node.model_dump(mode="json") for node in nodes[:capped_limit]]


@router.get("/graph/edges")
def list_graph_edges(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    include_pending: bool = True,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return approved and optionally pending graph edges for a project."""
    require_project(request, project_key)
    runtime = request.app.state.runtime
    capped_limit = min(max(limit, 1), 1000)
    approved_edges = [
        edge.model_dump(mode="json")
        for edge in runtime.graph.edges.values()
        if _edge_project_key(runtime, edge) == project_key
    ]
    if include_pending:
        pending_edges, pending_approval_by_edge_id = _pending_edges(runtime, project_key)
        for edge in pending_edges:
            payload = edge.model_dump(mode="json")
            payload["approval_id"] = pending_approval_by_edge_id.get(edge.edge_id)
            approved_edges.append(payload)
    approved_edges.sort(key=lambda edge: str(edge["edge_id"]))
    return approved_edges[:capped_limit]


@router.get("/graph/subgraph")
def subgraph(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, list[dict[str, Any]]]:
    """Return approved local graph subgraph."""
    require_project(request, project_key)
    runtime = request.app.state.runtime
    result: dict[str, list[dict[str, Any]]] = runtime.graph.subgraph(project_key)
    return result


def _approved_edge_count(runtime: Any, project_key: str) -> int:
    return sum(
        1
        for edge in runtime.graph.edges.values()
        if _edge_project_key(runtime, edge) == project_key
    )


def _edge_project_key(runtime: Any, edge: TraceabilityEdge) -> str | None:
    source_node = runtime.graph.nodes.get(edge.source_node_id)
    if source_node is None:
        return None
    project_key = getattr(source_node, "project_key", None)
    return project_key if isinstance(project_key, str) else None


@router.get("/graph/projection")
def graph_projection(
    request: Request,
    project_key: str = "RUNE_CAM_ALPHA",
    mode: GraphViewMode = "overview",
    center_node_id: str | None = None,
    hops: int = 1,
    limit_nodes: int = 120,
    search_query: str | None = None,
    edge_filter: GraphEdgeFilter = "all",
) -> dict[str, Any]:
    """Return approved nodes plus approved and pending edge projection."""
    require_project(request, project_key)
    runtime = request.app.state.runtime
    nodes = [node for node in runtime.graph.nodes.values() if node.project_key == project_key]
    approved_edges = [
        edge
        for edge in runtime.graph.edges.values()
        if edge.source_node_id in runtime.graph.nodes and edge.target_node_id in runtime.graph.nodes
    ]
    pending_edges, pending_approval_by_edge_id = _pending_edges(runtime, project_key)
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
        search_query=search_query,
        edge_filter=edge_filter,
        pending_approval_by_edge_id=pending_approval_by_edge_id,
    )
    result: dict[str, Any] = projection.model_dump(mode="json")
    return result


@router.get("/traceability/chain/{node_id}")
def traceability_chain(
    request: Request,
    node_id: str,
    project_key: str = "RUNE_CAM_ALPHA",
    direction: GraphChainDirection = "both",
    depth: int = 3,
    include_pending: bool = True,
    limit_nodes: int = 200,
) -> dict[str, Any]:
    """Return a hop-limited traceability chain around a node."""
    runtime = request.app.state.runtime
    require_project(request, project_key)
    nodes = [node for node in runtime.graph.nodes.values() if node.project_key == project_key]
    if node_id not in {node.node_id for node in nodes}:
        raise HTTPException(status_code=404, detail="node not found")
    approved_edges = [
        edge
        for edge in runtime.graph.edges.values()
        if edge.source_node_id in runtime.graph.nodes and edge.target_node_id in runtime.graph.nodes
    ]
    pending_edges, pending_approval_by_edge_id = _pending_edges(runtime, project_key)
    chain = build_traceability_chain(
        project_key=project_key,
        center_node_id=node_id,
        nodes=nodes,
        approved_edges=approved_edges,
        pending_edges=pending_edges,
        pending_approval_by_edge_id=pending_approval_by_edge_id,
        direction=direction,
        depth=depth,
        include_pending=include_pending,
        limit_nodes=limit_nodes,
    )
    result: dict[str, Any] = chain.model_dump(mode="json")
    return result


def _pending_edges(
    runtime: Any,
    project_key: str,
) -> tuple[list[TraceabilityEdge], dict[str, str]]:
    pending_edges: list[TraceabilityEdge] = []
    pending_approval_by_edge_id: dict[str, str] = {}
    approval_by_delta = {
        item.graph_delta_ref: item.approval_id
        for item in runtime.approvals.items.values()
        if item.project_key == project_key and item.status == "pending" and item.graph_delta_ref
    }
    for delta in runtime.approvals.deltas.values():
        if delta.project_key != project_key or delta.delta_id not in approval_by_delta:
            continue
        for operation in delta.operations:
            if operation.operation != "create_edge":
                continue
            edge = dict(operation.payload)
            edge["approval_status"] = "pending"
            edge["approved_by"] = None
            edge["approved_at"] = None
            pending_edge = TraceabilityEdge.model_validate(edge)
            pending_edges.append(pending_edge)
            pending_approval_by_edge_id[pending_edge.edge_id] = approval_by_delta[
                delta.delta_id
            ]
    return pending_edges, pending_approval_by_edge_id

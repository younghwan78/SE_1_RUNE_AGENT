"""Graph APIs."""

from typing import Any

from fastapi import APIRouter, Request

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
) -> dict[str, list[dict[str, Any]]]:
    """Return approved nodes plus approved and pending edge projection."""
    runtime = request.app.state.runtime
    graph: dict[str, list[dict[str, Any]]] = runtime.graph.subgraph(project_key)
    pending_edges: list[dict[str, Any]] = []
    for delta in runtime.approvals.deltas.values():
        if delta.project_key != project_key:
            continue
        for operation in delta.operations:
            if operation.operation == "create_edge":
                pending_edges.append(operation.payload)
    return {
        "nodes": graph["nodes"],
        "approved_edges": graph["edges"],
        "pending_edges": pending_edges,
    }

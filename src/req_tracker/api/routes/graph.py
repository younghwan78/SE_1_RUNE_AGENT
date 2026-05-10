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

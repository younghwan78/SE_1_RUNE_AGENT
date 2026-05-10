"""Health and runtime mode endpoints."""

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    """Return API health and local backend modes."""
    settings = request.app.state.settings
    return {
        "status": "ok",
        "environment": settings.environment,
        "datasource_mode": settings.datasource_mode,
        "graph_backend": settings.graph_backend,
        "vector_backend": settings.vector_backend,
        "model_gateway_mode": settings.model_gateway_mode,
        "artifact_store": settings.artifact_store,
    }


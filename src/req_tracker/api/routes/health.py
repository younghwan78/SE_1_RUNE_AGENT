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
        "state_store": settings.state_store,
    }


@router.get("/ready")
def readiness(request: Request) -> dict[str, Any]:
    """Return non-destructive readiness checks for configured runtime backends."""
    settings = request.app.state.settings
    runtime = request.app.state.runtime
    checks = {
        "state_store": _state_store_check(runtime),
        "graph_backend": _graph_backend_check(runtime),
        "vector_backend": _vector_backend_check(settings),
        "artifact_store": _artifact_store_check(runtime),
    }
    status = "ok" if all(check["status"] == "ok" for check in checks.values()) else "degraded"
    return {
        "status": status,
        "environment": settings.environment,
        "checks": checks,
        "schema_version": "v1",
    }


def _state_store_check(runtime: Any) -> dict[str, Any]:
    if runtime.state_store is None:
        return {"status": "ok", "mode": "memory", "collections": {}}
    try:
        return {
            "status": "ok",
            "mode": "persistent",
            "collections": runtime.state_store.counts_by_collection(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": exc.__class__.__name__}


def _graph_backend_check(runtime: Any) -> dict[str, Any]:
    try:
        return {
            "status": "ok",
            "nodes": len(runtime.graph.nodes),
            "approved_edges": len(runtime.graph.edges),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": exc.__class__.__name__}


def _vector_backend_check(settings: Any) -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": settings.vector_backend,
    }


def _artifact_store_check(runtime: Any) -> dict[str, Any]:
    try:
        runtime.artifact_store.root.mkdir(parents=True, exist_ok=True)
        return {
            "status": "ok",
            "root": str(runtime.artifact_store.root),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": exc.__class__.__name__}

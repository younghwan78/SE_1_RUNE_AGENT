"""FastAPI application factory."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from req_tracker.api.routes.approvals import router as approvals_router
from req_tracker.api.routes.feedback import router as feedback_router
from req_tracker.api.routes.graph import router as graph_router
from req_tracker.api.routes.health import router as health_router
from req_tracker.api.routes.runs import router as runs_router
from req_tracker.api.routes.ui import UI_ASSET_DIR
from req_tracker.api.routes.ui import router as ui_router
from req_tracker.api.state import RuntimeState
from req_tracker.config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application."""
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="SE 1 RUNE Agent API",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.enable_docs else None,
        redoc_url="/redoc" if resolved_settings.enable_docs else None,
    )
    app.state.settings = resolved_settings
    app.state.runtime = RuntimeState.create(resolved_settings.artifact_root)

    @app.middleware("http")
    async def add_correlation_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or resolved_settings.new_id(
            "corr"
        )
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        return response

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(approvals_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(ui_router)
    app.mount("/ui", StaticFiles(directory=UI_ASSET_DIR), name="ui")
    return app


app = create_app()

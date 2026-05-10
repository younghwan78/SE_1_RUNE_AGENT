"""FastAPI application factory."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from req_tracker.api.routes.approvals import router as approvals_router
from req_tracker.api.routes.audit import router as audit_router
from req_tracker.api.routes.debug import router as debug_router
from req_tracker.api.routes.feedback import router as feedback_router
from req_tracker.api.routes.graph import router as graph_router
from req_tracker.api.routes.health import router as health_router
from req_tracker.api.routes.runs import router as runs_router
from req_tracker.api.routes.ui import UI_ASSET_DIR
from req_tracker.api.routes.ui import router as ui_router
from req_tracker.api.state import RuntimeState
from req_tracker.config.settings import Settings, get_settings
from req_tracker.scheduler.models import ScheduleConfig
from req_tracker.storage.sqlite_store import SQLiteStateStore


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application."""
    resolved_settings = settings or get_settings()
    state_store = None
    if resolved_settings.state_store == "sqlite":
        state_store = SQLiteStateStore(resolved_settings.sqlite_state_path)
    runtime = RuntimeState.create(
        resolved_settings.artifact_root,
        ScheduleConfig(
            enabled=resolved_settings.scheduler_enabled,
            interval_seconds=resolved_settings.scheduler_interval_seconds,
            project_key=resolved_settings.scheduler_project_key,
            scenario=resolved_settings.scheduler_scenario,
        ),
        state_store=state_store,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.runtime = runtime
        if runtime.scheduler.config.enabled:
            await runtime.scheduler.start(
                runner=lambda run_id, project_key, scenario: runtime.run_analysis(
                    run_id=run_id,
                    project_key=project_key,
                    scenario=scenario,
                ),
                new_id=resolved_settings.new_id,
            )
        yield
        await runtime.scheduler.stop()

    app = FastAPI(
        title="SE 1 RUNE Agent API",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.enable_docs else None,
        redoc_url="/redoc" if resolved_settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.runtime = runtime

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
    app.include_router(debug_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(ui_router)
    app.mount("/ui", StaticFiles(directory=UI_ASSET_DIR), name="ui")
    return app


app = create_app()

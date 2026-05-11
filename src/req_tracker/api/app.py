"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from req_tracker.api.routes.admin import router as admin_router
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
from req_tracker.audit.archive import PostgresAuditArchiveStore
from req_tracker.audit.models import AuditRetentionPolicy
from req_tracker.config.logging import configure_logging
from req_tracker.config.settings import Settings, get_settings
from req_tracker.graph.base import GraphBackend
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.graph.neo4j_backend import Neo4jGraphBackend
from req_tracker.observability.metrics import InMemoryMetrics
from req_tracker.scheduler.models import ScheduleConfig
from req_tracker.storage.postgres_store import PostgreSQLStateStore
from req_tracker.storage.sqlite_store import SQLiteStateStore
from req_tracker.storage.state_store import StateStore
from req_tracker.vector.base import VectorBackend
from req_tracker.vector.memory_backend import MemoryVectorBackend
from req_tracker.vector.qdrant_backend import QdrantVectorBackend

REQUEST_LOGGER = logging.getLogger("req_tracker.api.request")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    graph = _create_graph_backend(resolved_settings)
    vector = _create_vector_backend(resolved_settings)
    state_store: StateStore | None = None
    if resolved_settings.state_store == "sqlite":
        state_store = SQLiteStateStore(resolved_settings.sqlite_state_path)
    elif resolved_settings.state_store == "postgres":
        state_store = PostgreSQLStateStore(resolved_settings.postgres_dsn)
    elif resolved_settings.state_store != "memory":
        raise ValueError(f"unsupported STATE_STORE: {resolved_settings.state_store}")
    metrics = InMemoryMetrics()
    runtime = RuntimeState.create(
        resolved_settings.artifact_root,
        ScheduleConfig(
            enabled=resolved_settings.scheduler_enabled,
            interval_seconds=resolved_settings.scheduler_interval_seconds,
            project_key=resolved_settings.scheduler_project_key,
            scenario=resolved_settings.scheduler_scenario,
            lease_name=resolved_settings.scheduler_lease_name,
            lease_ttl_seconds=resolved_settings.scheduler_lease_ttl_seconds,
        ),
        state_store=state_store,
        graph=graph,
        vector=vector,
        audit_policy=AuditRetentionPolicy(
            retention_days=resolved_settings.audit_retention_days,
            max_events=resolved_settings.audit_max_events,
        ),
        audit_archive_store=PostgresAuditArchiveStore(state_store)
        if isinstance(state_store, PostgreSQLStateStore)
        else None,
        scheduler_lease_manager=state_store
        if isinstance(state_store, PostgreSQLStateStore)
        else None,
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
                    triggered_by="scheduler",
                    trigger_source="schedule",
                ),
                new_id=resolved_settings.new_id,
            )
        yield
        await runtime.scheduler.stop()
        close_graph = getattr(runtime.graph, "close", None)
        if callable(close_graph):
            close_graph()

    app = FastAPI(
        title="SE 1 RUNE Agent API",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.enable_docs else None,
        redoc_url="/redoc" if resolved_settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.runtime = runtime
    app.state.metrics = metrics

    @app.middleware("http")
    async def add_correlation_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or resolved_settings.new_id(
            "corr"
        )
        request.state.correlation_id = correlation_id
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started) * 1000, 3)
            _record_request_metrics(
                metrics=metrics,
                request=request,
                correlation_id=correlation_id,
                user_id=_request_user_id(request, resolved_settings),
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
        duration_ms = round((perf_counter() - started) * 1000, 3)
        response.headers["x-correlation-id"] = correlation_id
        _record_request_metrics(
            metrics=metrics,
            request=request,
            correlation_id=correlation_id,
            user_id=_request_user_id(request, resolved_settings),
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(approvals_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(debug_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(ui_router)
    app.mount("/ui", StaticFiles(directory=UI_ASSET_DIR), name="ui")
    return app


def _request_user_id(request: Request, settings: Settings) -> str:
    """Resolve a non-authoritative user id for request logs without auth side effects."""
    user_id = request.headers.get("x-rune-user")
    if user_id:
        return user_id
    if settings.auth_mode == "local":
        return "local"
    return "anonymous"


def _record_request_metrics(
    *,
    metrics: InMemoryMetrics,
    request: Request,
    correlation_id: str,
    user_id: str,
    status_code: int,
    duration_ms: float,
) -> None:
    metrics.observe_http_request(
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        duration_ms=duration_ms,
    )
    REQUEST_LOGGER.info(
        "http_request",
        extra={
            "correlation_id": correlation_id,
            "user_id": user_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        },
    )


def _create_graph_backend(settings: Settings) -> GraphBackend:
    if settings.graph_backend == "memory":
        return MemoryGraphBackend()
    if settings.graph_backend == "neo4j":
        if not settings.neo4j_uri or not settings.neo4j_password:
            raise ValueError("NEO4J_URI and NEO4J_PASSWORD are required for GRAPH_BACKEND=neo4j")
        return Neo4jGraphBackend(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
    raise ValueError(f"unsupported GRAPH_BACKEND: {settings.graph_backend}")


def _create_vector_backend(settings: Settings) -> VectorBackend:
    if settings.vector_backend == "memory":
        return MemoryVectorBackend()
    if settings.vector_backend == "qdrant":
        if not settings.qdrant_url:
            raise ValueError("QDRANT_URL is required for VECTOR_BACKEND=qdrant")
        return QdrantVectorBackend(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            collection_name=settings.qdrant_collection,
            vector_size=settings.qdrant_vector_size,
        )
    raise ValueError(f"unsupported VECTOR_BACKEND: {settings.vector_backend}")


app = create_app()

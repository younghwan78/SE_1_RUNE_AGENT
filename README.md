# SE 1 RUNE Agent

Production-oriented MBSE traceability agent system.

The single source of truth is `PRODUCTION_EXECUTION_PLAN.md`. Detailed implementation design lives under `docs/implementation/`.

## Local Setup

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

Run the API locally:

```powershell
uv run uvicorn req_tracker.api.app:create_app --factory --reload
```

Open the local operator UI:

```text
http://127.0.0.1:8000/
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

## Current Implementation Stage

Current local implementation:

- Pydantic core contracts
- dummy/local runtime settings and FastAPI endpoints
- local artifact store
- in-memory trace recorder
- dummy source adapter and fixture-backed analysis workflow
- in-memory graph/vector backends
- approval queue, graph commit, feedback capture
- replay diff and eval candidate grouping
- static local operator UI

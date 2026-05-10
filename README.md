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

Configure periodic runs:

```powershell
Invoke-RestMethod -Method Put http://127.0.0.1:8000/api/v1/schedule `
  -ContentType "application/json" `
  -Body '{"enabled":true,"interval_seconds":3600,"project_key":"RUNE_CAM_ALPHA","scenario":"RUNE_MULTI_SOURCE","run_id_prefix":"sched"}'
```

Ubuntu server deployment details are in `README_ubuntu.md`.

## Current Implementation Stage

Current local implementation:

- Pydantic core contracts
- dummy/local runtime settings and FastAPI endpoints
- local artifact store
- optional SQLite state store for production-shaped persistence validation
- PostgreSQL state repository with package migrations for production persistence foundation
- in-memory trace recorder
- dummy source adapter and fixture-backed analysis workflow
- JIRA, Confluence, and restricted decision/email export-file adapters
- in-memory graph/vector backends
- approval queue, graph commit, feedback capture
- audit event capture for approval, feedback, debug artifact, scheduler, and run completion
- replay diff and eval candidate grouping
- static local operator UI
- ontology graph view with pending/approved edge projection
- traceability chain, run debug workbench, and audit events panel
- periodic analysis scheduler for server operation

Enable local SQLite persistence:

```powershell
$env:STATE_STORE="sqlite"
$env:SQLITE_STATE_PATH=".local_state/rune_state.sqlite3"
uv run uvicorn req_tracker.api.app:app --host 127.0.0.1 --port 8000
```

Enable PostgreSQL persistence:

```powershell
$env:STATE_STORE="postgres"
$env:POSTGRES_DSN="postgresql://rune:rune@127.0.0.1:5432/rune_agent"
uv run uvicorn req_tracker.api.app:app --host 127.0.0.1 --port 8000
```

Debug APIs:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/debug/runs
Invoke-RestMethod http://127.0.0.1:8000/api/v1/debug/runs/{run_id}/summary
```

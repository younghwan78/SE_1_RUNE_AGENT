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

The same `ruff`, `mypy`, and `pytest` gates run in GitHub Actions on pushes to
`main` and on pull requests.

Optional real PostgreSQL integration tests are skipped unless
`POSTGRES_TEST_DSN` points to a disposable PostgreSQL database:

```powershell
$env:POSTGRES_TEST_DSN="postgresql://rune:rune@127.0.0.1:5432/rune_agent_test"
uv run pytest tests/integration/test_postgres_state_store.py
```

Optional real Neo4j integration tests are skipped unless `NEO4J_TEST_URI` and
`NEO4J_TEST_PASSWORD` point to a disposable Neo4j database:

```powershell
$env:NEO4J_TEST_URI="bolt://127.0.0.1:7687"
$env:NEO4J_TEST_USERNAME="neo4j"
$env:NEO4J_TEST_PASSWORD="password"
uv run pytest tests/integration/test_neo4j_graph_backend.py
```

Optional real Qdrant integration tests are skipped unless `QDRANT_TEST_URL`
points to a disposable Qdrant collection:

```powershell
$env:QDRANT_TEST_URL="http://127.0.0.1:6333"
uv run pytest tests/integration/test_qdrant_vector_backend.py
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

Enable API-key RBAC for protected debug/audit routes:

```powershell
$env:AUTH_MODE="api_key"
$env:API_KEY="change-me"
$env:AUDIT_RETENTION_DAYS="365"
$env:AUDIT_MAX_EVENTS="100000"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/audit/events `
  -Headers @{"x-rune-api-key"="change-me";"x-rune-role"="operator"}
Invoke-RestMethod http://127.0.0.1:8000/api/v1/audit/retention `
  -Headers @{"x-rune-api-key"="change-me";"x-rune-role"="operator"}
```

Configure periodic runs:

```powershell
Invoke-RestMethod -Method Put http://127.0.0.1:8000/api/v1/schedule `
  -ContentType "application/json" `
  -Body '{"enabled":true,"interval_seconds":3600,"project_key":"RUNE_CAM_ALPHA","scenario":"RUNE_MULTI_SOURCE","run_id_prefix":"sched"}'
```

Configure a company-approved model gateway profile:

```powershell
$env:MODEL_GATEWAY_MODE="http_json"
$env:MODEL_GATEWAY_ENDPOINT_URL="https://models.example.com/v1/complete"
$env:MODEL_GATEWAY_API_KEY="<from-secret-store>"
$env:MODEL_PROFILES_PATH="config/model_profiles.example.json"
$env:PROMPT_VERSIONS_PATH="config/prompt_versions.example.json"
```

The built-in `HttpJsonModelProvider` posts a provider-neutral JSON envelope to
the configured endpoint and keeps provider SDK calls outside application code.
Model profile and prompt files are registry inputs only; do not place secrets in
those files.

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
- generic HTTP JSON model provider with file-backed model/prompt registry
- in-memory graph/vector backends
- approval queue, graph commit, feedback capture
- audit event capture for approval, feedback, debug artifact, scheduler, and run completion
- replay diff and eval candidate grouping
- static local operator UI
- ontology graph view with pending/approved edge projection
- traceability chain, run debug workbench, and audit events panel
- debug side-by-side panes for LLM payloads and graph delta previews
- debug artifact store root access policy with blocked-read audit events
- audit retention policy status API
- backup/restore rehearsal runbook and smoke load runner
- periodic analysis scheduler for server operation

Enable local SQLite persistence:

```powershell
$env:STATE_STORE="sqlite"
$env:SQLITE_STATE_PATH=".local_state/rune_state.sqlite3"
uv run uvicorn req_tracker.api.app:app --host 127.0.0.1 --port 8000
```

Enable Neo4j graph persistence:

```powershell
$env:GRAPH_BACKEND="neo4j"
$env:NEO4J_URI="bolt://127.0.0.1:7687"
$env:NEO4J_USERNAME="neo4j"
$env:NEO4J_PASSWORD="password"
uv run uvicorn req_tracker.api.app:app --host 127.0.0.1 --port 8000
```

Enable Qdrant retrieval persistence:

```powershell
$env:VECTOR_BACKEND="qdrant"
$env:QDRANT_URL="http://127.0.0.1:6333"
$env:QDRANT_COLLECTION="rune_chunks"
uv run uvicorn req_tracker.api.app:app --host 127.0.0.1 --port 8000
```

JIRA and Confluence source access remain behind `.claude/skills/rune-source-*`.
The application provides `JiraRestSourceAdapter` and `ConfluenceRestSourceAdapter`
for company-approved REST transport, while MCP tool names and credentials stay
outside core code. These REST adapters normalize rate-limit, retry, permission
denial, and partial-failure warnings into the shared `SourceFetchResult`
contract.

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

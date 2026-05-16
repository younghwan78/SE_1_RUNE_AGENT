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

Run disposable Docker-backed PostgreSQL, Neo4j, and Qdrant integration tests:

```powershell
uv run python ops/integration/run_backend_integration.py
```

The runner starts `ops/integration/docker-compose.integration.yml`, waits for
real client readiness, executes the env-gated integration tests, and tears the
stack down. Override host ports with `RUNE_IT_POSTGRES_PORT`,
`RUNE_IT_NEO4J_BOLT_PORT`, and `RUNE_IT_QDRANT_HTTP_PORT` when local ports are
already in use.

Run a production-shaped full-stack rehearsal:

```powershell
uv run python ops/rehearsal/run_full_stack_rehearsal.py
```

This starts the disposable backends, launches the API with
`STATE_STORE=postgres`, `GRAPH_BACKEND=neo4j`, and `VECTOR_BACKEND=qdrant`, then
runs readiness, analyze, approval commit, graph projection, audit retention, and
API restart-restore checks. It also runs a small `ops/load/smoke_load.py` pass
against the live rehearsal API.

Run feedback/eval/canary rehearsal:

```powershell
uv run python ops/evals/run_feedback_eval_rehearsal.py
```

This validates that feedback-derived improvements pass through eval,
review-ready, canary, and active states, while security feedback remains blocked.

Run masking policy rehearsal:

```powershell
uv run python ops/security/rehearse_masking_policy.py
```

This verifies representative sensitive inputs are redacted without printing the
raw sensitive strings or forbidden patterns.

Check production-readiness gates before a release decision:

```powershell
uv run python ops/rehearsal/check_production_readiness.py
```

The checker reports required production environment variables, company/staging
rehearsal gates, and the local regression command list without printing secret
values. Add `--run-local-gates` to execute the local regression and rehearsal
commands from the report. After a staging rehearsal, pass a reviewed evidence
file to resolve manual gates. The release gate passes only when there are no
failed, warning, or manual-required checks:

```powershell
uv run python ops/rehearsal/check_production_readiness.py `
  --evidence-file ops/rehearsal/production_readiness_evidence.example.json
```

Run the API locally:

```powershell
uv run uvicorn req_tracker.api.app:create_app --factory --reload
```

Open the local operator UI:

```text
http://127.0.0.1:8000/
```

The first screen is a dashboard-first command center backed by
`/api/v1/dashboard/*` read models. It summarizes traceability health, pending
approvals, high findings, source health, run health, eval gate state, a compact
graph preview, and a prioritized work queue before the full traceability
workbench.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
```

Enable API-key RBAC for protected debug/audit routes:

```powershell
$env:AUTH_MODE="api_key"
$env:API_KEY="change-me"
$env:AUDIT_RETENTION_DAYS="365"
$env:AUDIT_MAX_EVENTS="100000"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/audit/events `
  -Headers @{"x-rune-api-key"="change-me";"x-rune-role"="operator";"x-rune-projects"="RUNE_CAM_ALPHA"}
Invoke-RestMethod http://127.0.0.1:8000/api/v1/audit/retention `
  -Headers @{"x-rune-api-key"="change-me";"x-rune-role"="operator"}
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/audit/retention/archive-prune `
  -Headers @{"x-rune-api-key"="change-me";"x-rune-role"="admin"}
```

Enable trusted SSO/OIDC proxy headers behind a company-controlled reverse proxy:

```powershell
$env:AUTH_MODE="trusted_proxy"
$env:TRUSTED_PROXY_SECRET="<from-secret-store>"
$env:TRUSTED_GROUP_ROLE_MAP='{"rune-viewers":"viewer","rune-developers":"developer","rune-operators":"operator","rune-admins":"admin"}'
Invoke-RestMethod http://127.0.0.1:8000/api/v1/audit/events `
  -Headers @{"x-rune-trusted-secret"="<from-secret-store>";"x-rune-user"="user@example.com";"x-rune-groups"="rune-operators";"x-rune-projects"="RUNE_CAM_ALPHA"}
```

Rehearse trusted-proxy RBAC against a running staging API:

```powershell
$env:RUNE_API_BASE_URL="https://rune-agent.example.com"
$env:TRUSTED_PROXY_SECRET="<from-secret-store>"
$env:RUNE_PROJECT_KEY="RUNE_CAM_ALPHA"
uv run python ops/security/rehearse_trusted_proxy_auth.py
```

The rehearsal checks health, viewer schedule read, developer audit denial,
operator audit read, and wrong-project denial while masking the shared secret.

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

Run a local model-gateway smoke without a real model endpoint:

```powershell
uv run python ops/model_gateway/smoke_model_gateway.py
```

This starts a disposable localhost JSON gateway and verifies that the production
HTTP provider records a failed primary call and succeeds through fallback.

Run a model gateway rehearsal against a company-approved sandbox endpoint:

```powershell
$env:MODEL_GATEWAY_ENDPOINT_URL="https://models.example.com/v1/complete"
$env:MODEL_GATEWAY_API_KEY="<from-secret-store>"
$env:MODEL_GATEWAY_PROFILE_ID="company-sandbox"
uv run python ops/model_gateway/rehearse_model_gateway.py
```

The rehearsal sends only a public internal probe payload and reports trace
hashes, validation status, and artifact-reference presence with secrets masked.

Run local JIRA and Confluence REST adapter smoke without company systems:

```powershell
uv run python ops/source/smoke_source_adapters.py
```

This starts a disposable localhost source server and validates HTTP pagination,
normalized artifacts, links, and permission-denied warnings through the real
REST adapters.

Run source rehearsals against company-approved sandbox systems after setting
source environment variables:

```powershell
$env:JIRA_BASE_URL="https://jira.example.com"
$env:JIRA_TOKEN="<from-secret-store>"
$env:JIRA_PROJECT_KEY="CAM"
$env:CONFLUENCE_BASE_URL="https://confluence.example.com"
$env:CONFLUENCE_TOKEN="<from-secret-store>"
$env:CONFLUENCE_SPACE_KEY="CAM"
uv run python ops/source/rehearse_company_sources.py --source all
```

The rehearsal prints artifact counts, warnings, and shape checks only; token
values are masked.

Run the restricted decision/email export rehearsal for approved decision
archives or limited mailbox exports:

```powershell
$env:RUNE_EMAIL_EXPORT_PATH="E:\secure_exports\decision_email.jsonl"
$env:RUNE_PROJECT_KEY="RUNE_CAM_ALPHA"
uv run python ops/source/rehearse_decision_email_export.py
```

The rehearsal accepts only `decision_archive` artifacts or email artifacts with
`decision_source_approved=true` and decision metadata; broad mailbox items are
reported as skipped warnings.

Ubuntu server deployment details are in `README_ubuntu.md`.

## Current Implementation Stage

Current local implementation:

- Pydantic core contracts
- dummy/local runtime settings and FastAPI endpoints
- local artifact store
- optional SQLite state store for production-shaped persistence validation
- PostgreSQL state repository with package migrations and audit archive batches
- in-memory trace recorder
- dummy source adapter and fixture-backed analysis workflow
- JIRA, Confluence, and restricted decision/email export-file adapters
- JIRA REST link, comment, and changelog metadata preservation
- Confluence REST section-path and table-cell metadata extraction
- Confluence previous-version metadata and stale trace finding generation
- local JIRA/Confluence REST source smoke harness
- restricted decision/email export policy that skips unapproved mailbox artifacts,
  routes sensitive threads to manual review, and masks email thread metadata
- generic HTTP JSON model provider with file-backed model/prompt registry
- local model-gateway smoke harness for HTTP fallback and trace validation
- model-gateway comparison helper for same-input model/prompt candidate diffs
- traceable dummy model-gateway calls for node extraction, edge linking, and finding reasoning
- in-memory graph/vector backends
- deterministic critical-impact rule for issues affecting P0/critical requirements
- deterministic architecture verification-path rule for architecture blocks with no direct
  or linked verification coverage
- masking policy violation block that stops analysis and records a security review
  reference when source-specific forbidden patterns remain visible
- approval queue, graph commit, feedback capture
- audit event capture for approval, feedback, debug artifact, scheduler, and run completion
- replay diff and eval candidate grouping
- controlled feedback improvement promotion through eval, review, canary, and active states
- static local operator UI with dashboard-first command center
- dashboard read APIs for summary, work queue, source health, run health, risk summary, and recent activity
- ontology graph view with pending/approved edge projection
- traceability chain, run debug workbench, and audit events panel
- debug side-by-side panes for LLM payloads and graph delta previews
- debug artifact store root access policy with blocked-read audit events
- audit retention policy status API
- admin-only audit archive/prune API with local JSONL or PostgreSQL archive writer
- API-key project-scope authorization foundation with `x-rune-projects`
- trusted SSO/OIDC proxy header auth foundation with group-to-role mapping
- backup/restore rehearsal runbook and smoke load runner
- incident response runbook for triage, rollback, evidence, and review
- Docker Compose backend integration runner for PostgreSQL, Neo4j, and Qdrant
- full-stack API rehearsal against PostgreSQL, Neo4j, and Qdrant
- runtime state restore from persisted state after API restart
- readiness API for non-destructive backend checks
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

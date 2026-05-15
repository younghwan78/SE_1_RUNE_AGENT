# API Surface

This directory anchors the API documentation track from
`PRODUCTION_EXECUTION_PLAN.md`.

The current source of truth for implemented routes is:

- `src/req_tracker/api/app.py`
- `src/req_tracker/api/routes/`
- `tests/contract/`

Runtime OpenAPI can be exposed in non-production environments by setting
`ENABLE_DOCS=true` and opening `/docs` or `/openapi.json`.

Production default is `ENABLE_DOCS=false`. Any externally published API
contract must be generated from the FastAPI app and reviewed with the matching
contract tests before release.

Requests may pass a W3C `traceparent` header. The API returns a server-span
`traceparent`, `x-rune-trace-id`, and `x-correlation-id` so logs, metrics, and
debug traces can be correlated before a full OpenTelemetry collector is wired in
the target environment.

Set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` to a company-approved
collector to export FastAPI spans through OTLP. The default local mode keeps
OpenTelemetry export disabled while preserving trace-context headers.

Implemented route groups:

- health, readiness, and runtime metrics
- run ingestion, analysis execution, and replay
- finding list, detail, and status triage
- project list, graph node/edge lists, graph projection, and traceability chain
- dashboard summary, work queue, source health, run health, risk summary, and recent activity read models
- approvals and graph commit
- feedback, eval candidates, improvement candidates, and improvement rollback
- admin model profile and prompt version activation/rollback records
- debug traces and diff views
- source sync cursor snapshots for ingestion debugging
- audit events and retention
- scheduler controls
- static UI route

Run execution records both `run_started` and `run_completed` audit events.
The start event carries `scenario`, `run_type`, and `trigger_source` metadata
so operators can distinguish API, manual, scheduled, and system-originated
runs even when a later stage needs failure triage.
If a run raises during execution, the runtime marks the run as `failed`, stores
`failure_code` and `failure_message`, and records a failed `run_completed`
audit event before re-raising the error to the API layer.
Replay executions are stored as `run_type="replay"` with their own audit
boundary events and restart-safe run/step/LLM traces. Replay trace persistence
does not overwrite reviewed operational findings or graph state.
Replay idempotency responses are also restart-safe: a repeated request with the
same idempotency key can return the persisted response even after the source
analysis object has aged out of in-memory runtime state.

Run step responses include step-level `retrieval_context_ref`,
`validation_status`, and `validation_result` fields so debug screens can show
the stage retrieval context and structured validation result without requiring a
separate LLM-call lookup.
The source-fetch step records `source_sync_cursor_id`, page count, completed
cursor, next cursor, warning, and partial-failure metadata. Developers can query
the latest persisted cursor snapshots through `GET /api/v1/debug/source-cursors`
without exposing company-specific JIRA, Confluence, Email, or MCP details in the
application layer.

Replay responses include `compared_model_profile_ids` and
`compared_prompt_version_ids` so model/prompt comparison reports keep the exact
version set used for object-level diffs.

Do not document MCP tool names or company-specific source credentials here.
JIRA, Confluence, and Email access procedures belong in `.claude/skills/` and
company-local MCP configuration.

Feedback API inputs accept command-style aliases such as `approve`, `reject`,
`modify`, `comment`, and `mark low quality`, then store canonical contract values
such as `approved`, `rejected`, `modified`, `commented`, and
`marked_low_quality`. Reason codes are stored with underscores, while
human-readable aliases such as `wrong relation` are accepted at the API boundary.

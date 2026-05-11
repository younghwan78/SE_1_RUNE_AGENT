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
- approvals and graph commit
- feedback, eval candidates, and improvement candidates
- admin model profile and prompt version activation records
- debug traces and diff views
- audit events and retention
- scheduler controls
- static UI route

Do not document MCP tool names or company-specific source credentials here.
JIRA, Confluence, and Email access procedures belong in `.claude/skills/` and
company-local MCP configuration.

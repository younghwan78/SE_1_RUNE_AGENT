# MEMORY

## 2026-05-12 Progress Snapshot

This project builds an internal, production-grade MBSE traceability agent system.

Primary source of truth:

- `PRODUCTION_EXECUTION_PLAN.md`

Do not use or recreate removed planning files:

- `PRD.md`
- `PRD_ref.md`

## Baseline Repository State Before Final Local Handoff Pass

- Working directory: `E:\51_Codex_MBSE_Agent`
- Key pushed commits before this handoff pass:
  - `edce126 Add project memory snapshot`
  - `fee8aad Inject configured source adapters`
  - `f88eab1 Persist source sync cursors`
- Latest confirmed GitHub Actions CI before this handoff pass: `25702699010`, success

## Completed Foundation

- FastAPI API skeleton and OpenAPI surface guard.
- Pydantic contracts for ontology, debug traces, approvals, feedback, audit, source adapter contracts, and source sync cursor snapshots.
- Local deterministic analysis workflow with ingestion, masking, chunking, evidence spans, node extraction, edge linking, findings, approval staging, LLM-assisted reasoning trace, and replay diff.
- Model gateway abstraction with dummy provider, HTTP JSON provider foundation, registry activation/rollback records, structured validation, retry/fallback traces, and token/cost metadata.
- Approval workflow with pending graph proposals separated from approved graph state.
- Approval actions: approve, reject, hold, modify.
- Approval safety: idempotency, version/proposal-hash stale checks, RBAC, audit.
- Feedback/eval/improvement loop with feedback taxonomy, eval candidates, improvement candidates, review/canary/active/rollback flow, and security-blocked eval path.
- SQLite persistence and restore.
- PostgreSQL state store, typed core/operation mirrors, migrations, rollback validation, audit archive/prune, idempotency restore, replay restore, failed run persistence.
- Neo4j graph backend and Qdrant vector backend foundations.
- Docker-backed backend integration runner and full-stack rehearsal.
- Scheduler API/UI/runbook path plus PostgreSQL scheduler lease support for Ubuntu multi-worker deployments.
- Graph view scalability plan and implementation: larger graph view, zoom/pan/reset, projection modes, 150-node dummy graph smoke validation.
- Debug workbench: run summaries, artifact read, LLM payload diff panes, graph delta preview, approval lineage, replay diff, source cursor debug API.
- Audit trail: run_started/run_completed boundaries for analysis/ingestion/replay, failed completion audit, blocked debug read audit, finding status audit, improvement/model/prompt activation and rollback audit, archive/prune idempotency.
- Claude Code source skill boundary: source skills remain the company access layer; core app code uses stable adapters and does not leak MCP tool names.
- JIRA/Confluence/Email foundations:
  - JIRA REST adapter
  - Confluence REST adapter
  - export-file adapters for JIRA, Confluence, restricted decision/email
  - restricted decision/email export policy
  - source boundary validator
  - source adapter smoke harness
- Latest source integration work:
  - `SourceSyncCursorState`
  - persisted `source_sync_cursors`
  - `GET /api/v1/debug/source-cursors`
  - datasource factory
  - runtime workflow injection for `dummy`, `jira_export`, `confluence_export`, `decision_email_export`, `jira_rest`, and `confluence_rest`
- Local handoff work:
  - `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`
  - `ops/source/rehearse_skill_export_sources.py`
  - `tests/unit/ops/test_skill_export_rehearsal.py`
  - CI/local gate coverage for source-skill export dry-run
- Ubuntu/server docs, backup/restore/load rehearsal assets, observability assets, Prometheus/Grafana starter files, readiness evidence template, and validators are present.

## Latest Validation Evidence

- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `209 passed, 3 skipped`
- `uv run pytest tests/unit/ops/test_skill_export_rehearsal.py tests/unit/ops/test_production_readiness_check.py`: `19 passed`
- `uv run pytest tests/contract/test_backend_settings_api.py tests/contract/test_health_api.py tests/contract/test_run_api.py tests/contract/test_debug_api.py tests/contract/test_persistence_api.py`: `33 passed`
- `uv run pytest tests/contract/test_debug_api.py tests/contract/test_security_api.py tests/contract/test_openapi_surface.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py tests/unit/storage/test_postgres_store.py tests/contract/test_models.py`: `44 passed`
- `uv run python ops/source/smoke_source_adapters.py`: passed
- `uv run python ops/source/rehearse_skill_export_sources.py`: passed
- `uv run python ops/source/validate_source_boundaries.py`: passed
- `uv run python ops/security/check_release_blockers.py`: passed
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed
- GitHub Actions CI for `fee8aad`: success

## Current Status

The local/dummy production-shaped foundation and non-company handoff package are implemented and validated.

The overall production objective is not fully complete yet because company/staging evidence is still required.

Do not mark the overall production goal complete until a completion audit verifies company/staging readiness evidence.

## Remaining Production Gates

- Company/staging PostgreSQL rehearsal.
- Company/staging Neo4j rehearsal.
- Company/staging Qdrant rehearsal.
- Real JIRA sandbox incremental sync rehearsal.
- Real Confluence sandbox rehearsal.
- Real model provider sandbox rehearsal.
- Trusted proxy / SSO-OIDC staging rehearsal.
- OpenTelemetry collector, Prometheus scrape, and Grafana import validation.
- Backup/restore/load rehearsal against staging infrastructure.
- Optional Kubernetes/Helm target-cluster validation if Kubernetes becomes the deployment target.
- Restricted decision/email export validation with approved company data.
- Broad Email ingestion remains out of first-release scope.

## Recommended Continuation Prompt

```text
E:\51_Codex_MBSE_Agent에서 PRODUCTION_EXECUTION_PLAN.md와 docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md 기준으로 이어서 진행해줘.
먼저 git status, 최신 CI, readiness gate를 확인하고 company/staging evidence가 필요한 항목과 로컬에서 더 보강 가능한 항목을 분리해줘.
```

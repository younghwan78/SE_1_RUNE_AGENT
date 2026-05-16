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
- PostgreSQL state store, typed core/operation mirrors, migrations, rollback validation, audit archive/prune, idempotency restore, replay restore, improvement decision restore, failed run persistence.
- Neo4j graph backend and Qdrant vector backend foundations.
- Docker-backed backend integration runner and full-stack rehearsal.
- Scheduler API/UI/runbook path plus PostgreSQL scheduler lease support for Ubuntu multi-worker deployments.
- Graph view scalability plan and implementation: larger graph view, zoom/pan/reset, projection modes, 150-node dummy graph smoke validation.
- Dashboard production uplift:
  - `docs/implementation/10_DASHBOARD_PRODUCTION_PLAN.md`
  - `/api/v1/dashboard/summary`
  - `/api/v1/dashboard/work-queue`
  - `/api/v1/dashboard/source-health`
  - `/api/v1/dashboard/run-health`
  - `/api/v1/dashboard/risk-summary`
  - `/api/v1/dashboard/recent-activity`
  - dashboard-first local operator UI command center
  - work queue, source health, run health, risk snapshot, recent activity, and compact graph preview panels
  - contract/unit/UI smoke coverage for empty state, `RUNE_CAM_ALPHA`, `RUNE_SCALE_150`, approval count update, source export health, RBAC, and dashboard UI hooks
- Debug workbench: run summaries, artifact read, LLM payload diff panes, graph delta preview, approval lineage, replay diff, source cursor debug API.
- Audit trail: run_started/run_completed boundaries for analysis/ingestion/replay, failed completion audit, blocked debug read audit, finding status audit, improvement/model/prompt activation and rollback audit, archive/prune idempotency.
- Claude Code source skill boundary: source skills remain the company access layer; core app code uses stable adapters and does not leak MCP tool names.
- JIRA/Confluence/Email foundations:
  - JIRA REST adapter
  - Confluence REST adapter
  - Confluence section-path and table-cell metadata extraction
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
- Incident response runbook is present for severity, first response, run/source/model/approval/security triage, rollback, evidence preservation, and post-incident review.

## Latest Validation Evidence

- `uv run ruff check .`: passed
- `uv run mypy src`: passed

- `uv run pytest`: `217 passed, 3 skipped`
- `uv run pytest tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_openapi_surface.py`: `10 passed`
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

## 2026-05-13 Dashboard UI Phase Handoff

Current local focus:

- The dashboard-first API and static operator UI foundation is implemented, but the UI is not yet complete at commercial/operator quality.
- The next implementation step requested by the user is the second dashboard UI phase based on `docs/implementation/10_DASHBOARD_PRODUCTION_PLAN.md`.
- The immediate target is to move from one long scrolling page to a production-shaped operator workspace with clear views:
  - Dashboard
  - Work Queue
  - Traceability Workbench
  - Run Debug
  - Source Health
  - Eval and Improvement
  - Admin or Operations
- Work Queue needs an actionable detail panel/drawer so an operator can click an item and see:
  - item type, severity, status, and summary
  - related node, run, approval, finding, or eval candidate identifiers
  - evidence and trace references where available
  - actions to open the graph context, open the debug context, or route to approval handling where applicable
- Source Health and Run Health should have fuller operational views, not only dashboard summary cards.
- Existing graph, approval, scheduler, findings, replay, debug, audit, improvement, and eval functionality must be preserved while reorganizing the UI.

Implementation constraints for the next pass:

- Keep the static FastAPI-served UI unless there is a concrete reason to introduce another frontend framework.
- Do not add Streamlit; the project intentionally uses the production app surface rather than carrying forward POC Streamlit UI.
- Keep dashboard data contracts under `/api/v1/dashboard/*`.
- Update `ops/ui/smoke_operator_ui.py`, `tests/contract/test_ui_route.py`, and related unit/contract tests together with the UI changes.
- After each meaningful step, run focused tests first, then full regression:
  - `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py`
  - `uv run python ops/ui/smoke_operator_ui.py`
  - `uv run ruff check .`
  - `uv run mypy src`
  - `uv run pytest`

Latest verified baseline before this handoff:

- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `217 passed, 3 skipped`
- `uv run python ops/ui/smoke_operator_ui.py`: passed
- Dashboard smoke data included `RUNE_SCALE_150` with 150 graph nodes, 103 pending approvals, 47 open findings, 40 high findings, and 9 orphan nodes.

Continuation prompt:

```text
E:\51_Codex_MBSE_Agent에서 docs/implementation/10_DASHBOARD_PRODUCTION_PLAN.md를 기준으로 dashboard UI 2단계를 구현해줘.
먼저 현재 uncommitted 변경을 보존하면서 git status와 src/req_tracker/ui/index.html, app.js, styles.css, ops/ui/smoke_operator_ui.py, tests/contract/test_ui_route.py를 확인해.
그 다음 view split, work queue detail panel, source/run health detail view를 구현하고 focused test -> UI smoke -> ruff -> mypy -> full pytest 순서로 검증해.
```

## 2026-05-15 Dashboard Production Uplift Completion Snapshot

Current dashboard status:

- Dashboard read-model APIs and local operator UI production uplift are implemented and locally validated.
- The static UI now has separate workspace views:
  - Dashboard
  - Work Queue
  - Traceability
  - Run Debug
  - Source Health
  - Eval
  - Admin
- Work Queue now has:
  - item detail panel
  - graph/debug/source/eval deep-link actions
  - approval approve/reject routing where applicable
  - type, priority, owner, and search filters
  - saved filter presets through backend preference API with browser
    `localStorage` fallback
  - assignment state through backend assignment API with browser `localStorage`
    fallback
  - `Assign to me` and `Clear assignment`
- Static JS has been split into focused browser modules:
  - `core.js`
  - `dashboard.js`
  - `work_queue.js`
  - `graph_workbench.js`
  - `debug_workbench.js`
  - `source_health.js`
- Hash routes/deep links are supported:
  - `#dashboard`
  - `#work-queue?item=...`
  - `#traceability?node=...&mode=neighborhood`
  - `#debug?run=...`
  - `#source-health?source=...`

Latest validation evidence:

- `node --check` for all UI JS modules: passed
- `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py`: `13 passed`
- `uv run python ops/ui/smoke_operator_ui.py`: passed
- `uv run ruff check .`: passed
- `uv run mypy src`: passed

## 2026-05-16 Dashboard PostgreSQL State and RBAC Snapshot

Implemented and verified the remaining local dashboard backend state hardening.

Changed:

- Added PostgreSQL migration/rollback `006_dashboard_state_tables` for
  `dashboard_preferences` and `dashboard_assignments`.
- Added PostgreSQL typed mirror coverage for dashboard preference/assignment
  state.
- Updated dashboard state API RBAC documentation in
  `docs/security/RBAC_MATRIX.md`.
- Added regression coverage that dashboard work queue preference/assignment
  routes require developer role and project access.
- Added a documentation guard ensuring the RBAC matrix lists the dashboard state
  routes.

Validation evidence:

- `uv run pytest tests/unit/storage/test_postgres_store.py -q`: `9 passed`
- `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
  passed for versions `001` through `006`
- `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
- `uv run pytest tests/contract/test_dashboard_api.py tests/contract/test_security_api.py tests/contract/test_openapi_surface.py -q`:
  `17 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `git diff --check`: passed
- `uv run pytest`: `227 passed, 3 skipped`
- GitHub Actions `CI` run `25965051096` for commit
  `6418677 Document dashboard state RBAC`: success

Current status:

- Local/dashboard production-shaped implementation remains complete for the
  current non-company scope.
- Overall production readiness is still not complete until company/staging
  evidence is provided for PostgreSQL, Neo4j, Qdrant, JIRA/Confluence,
  trusted proxy SSO/OIDC, real model gateway, observability,
  backup/restore/load, and approved decision/email export validation.

## 2026-05-17 Local Readiness Refresh

Fresh local readiness check:

- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`
  was executed with Docker Desktop Linux engine available.
- All local regression and rehearsal gates passed, including disposable
  PostgreSQL/Neo4j/Qdrant integration and Docker-backed full-stack rehearsal.
- Full-stack rehearsal evidence included `passed=true`, `restart_restored=true`,
  `audit_total_events=3`, and smoke-load p95 under the 5 second local threshold.
- Overall readiness remains incomplete by design in this workstation shell:
  summary `failed=7`, `manual_required=10`, `passed=2`, `warning=0`.
- The remaining failed/manual gates require company/staging configuration and
  reviewed evidence for PostgreSQL, Neo4j, Qdrant, model gateway, trusted proxy
  SSO/OIDC, artifact storage, OpenTelemetry, JIRA/Confluence, approved
  decision/email export, Prometheus/Grafana, backup/restore/load, and staging
  endpoint rehearsals.
- Latest pushed GitHub Actions `CI` run `25965768329` for commit `c2004f2`
  passed.

Follow-up production persistence hardening:

- Added PostgreSQL migration `006_dashboard_state_tables.sql` and rollback for
  backend dashboard preferences and assignments.
- Added typed PostgreSQL mirror specs for `dashboard_preferences` and
  `dashboard_assignments`.
- Added PostgreSQL migration `007_source_cursor_state_tables.sql` and rollback
  for `source_sync_cursors`.
- Added typed PostgreSQL mirror spec for `source_sync_cursors`, keeping the
  full payload JSON and promoting source type, project key, scenario, run id,
  cursor counters, failure state, and update metadata into typed columns.
- Added PostgreSQL migration `008_debug_replay_state_tables.sql` and rollback
  for `llm_call_traces` and `replay_results`.
- Added typed PostgreSQL mirror specs for `llm_call_traces` and
  `replay_results`, keeping full payload JSON and promoting debug/replay lookup
  fields into typed columns.
- Added PostgreSQL migration `009_improvement_decision_state_tables.sql` and
  rollback for `improvement_decisions`.
- Added typed PostgreSQL mirror spec for controlled improvement activation and
  rollback decisions, keeping full payload JSON and promoting candidate id,
  status, decision type, eval run, reviewer, and version fields into typed
  columns.
- Validation:
  - `uv run pytest tests/unit/storage/test_postgres_store.py -q`: `11 passed`
  - `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
    passed with versions `001` through `009`
  - `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
    including dashboard preference/assignment, source sync cursor, LLM call
    trace, replay result, and improvement decision mirrors
  - `uv run pytest`: `231 passed, 3 skipped`
- Playwright CLI screenshot smoke was run manually for dashboard/work-queue rendering and deep-link behavior, but it is intentionally not added to CI per user direction.

Remaining dashboard-specific items:

- CI browser screenshot smoke: intentionally skipped for now.
- Backend user preference and assignment APIs are now implemented; keep
  localStorage only as a browser fallback.
- Reassess React + React Flow only after real graph shape and reviewer workflow complexity justify it.
- Optional future UX backlog: SLA/age thresholds, dashboard trend history, source drill-down pages, graph clustering/grouping API, accessibility pass, keyboard navigation, and bulk review.

Recommended continuation prompt:

```text
E:\51_Codex_MBSE_Agent에서 dashboard local implementation은 완료된 기준으로 보고,
먼저 git status와 최신 CI를 확인한 뒤 전체 production readiness 기준으로
company/staging evidence가 필요한 항목과 로컬에서 추가 보강 가능한 항목을 분리해줘.
CI browser screenshot smoke는 계속 skip하고, React/React Flow는 아직 결정하지 마.
```

## 2026-05-16 Relationship Graph and Completion Audit Snapshot

Latest pushed commits:

- `0e438b0 Add relationship graph workbench interactions`
- `67eeb22 Refresh production completion audit`
- `4f96977 Classify unavailable Docker readiness gates`

GitHub verification:

- GitHub Actions `CI` run `25929814655`: success for
  `0e438b05d8b26daf6cec37836563fc39ff631a5a`
- GitHub Actions `CI` run `25964404814`: success for
  `4f96977b654a95b2e931d575ce6f46ae2a70221d`

Graph UI status:

- `docs/implementation/11_GRAPH_RELATIONSHIP_VIEW_PLAN.md` is added.
- `Traceability Workbench` now separates projection mode from layout mode:
  - `Ontology Lane`
  - `Relationship Graph`
- `Relationship Graph` uses component-aware layout for large graphs.
- Dense 100+ node view reduces labels to representative component labels.
- Relationship nodes can be dragged to temporary pinned positions.
- Dragging rerenders related edges.
- `Reset View` clears zoom/pan and pinned node positions.

Latest validation evidence:

- `node --check src/req_tracker/ui/graph_workbench.js`: passed
- `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py`: `6 passed`
- `uv run python ops/ui/smoke_operator_ui.py`: passed
- Playwright CLI verified `Relationship Graph` with 120 relationship nodes,
  73 edges, 26 dense-mode labels, node drag/pin, edge preservation, and reset
  restoring the auto layout.
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `222 passed, 3 skipped`

Production readiness audit update:

- `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md` and
  `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md` are updated to reflect
  the latest graph UI work, CI success, and current gate status.
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`
  was executed on 2026-05-16. After starting Docker Desktop Linux engine, all
  local regression gates passed. The overall readiness report still fails
  because production/staging env vars and manual evidence are unset.
- The checker now classifies Docker-backed gate failures caused by Docker daemon
  unavailability as `manual_required` with `docker_unavailable` evidence instead
  of treating them as application failures, while mixed non-Docker local gate
  failures still fail the local gate summary.
- Docker-backed gates passed locally after Docker Desktop Linux engine was
  started:
  - `uv run python ops/integration/run_backend_integration.py`
  - `uv run python ops/rehearsal/run_full_stack_rehearsal.py`
- Remaining production gates still require company/staging evidence:
  PostgreSQL, Neo4j, Qdrant, JIRA/Confluence sandbox, trusted proxy SSO/OIDC,
  real model gateway sandbox, OpenTelemetry collector, Prometheus/Grafana,
  backup/restore/load, and approved decision/email export validation.

## 2026-05-16 Dashboard Backend Preference and Assignment Snapshot

Implemented local production-quality dashboard backend state for work queue
operator controls.

Changed:

- Added backend-backed work queue preference contracts and routes:
  - `GET /api/v1/dashboard/work-queue/preferences`
  - `PUT /api/v1/dashboard/work-queue/preferences`
- Added backend-backed work queue assignment contracts and routes:
  - `GET /api/v1/dashboard/work-queue/assignments`
  - `POST /api/v1/dashboard/work-queue/assignments/{queue_id}`
- Work queue assignment writes use existing command idempotency helpers.
- Preference and assignment state persist through the configured state store and
  restore through SQLite restart tests.
- Dashboard UI now hydrates saved filters and assignments from backend APIs and
  keeps localStorage as a fallback.
- Operator UI smoke now validates backend preference/assignment routes.

Validation evidence:

- `uv run pytest tests/contract/test_dashboard_api.py tests/contract/test_persistence_api.py tests/contract/test_openapi_surface.py`: passed
- `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_dashboard_api.py tests/contract/test_persistence_api.py tests/contract/test_openapi_surface.py -q`: `21 passed`
- `node --check src/req_tracker/ui/app.js`: passed
- `node --check src/req_tracker/ui/work_queue.js`: passed
- `uv run python ops/ui/smoke_operator_ui.py`: passed
- `uv run ruff check .`: passed
- `uv run mypy src`: passed

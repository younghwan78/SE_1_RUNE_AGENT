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
- The local workflow records dummy model-gateway traces for node extraction,
  edge linking, and finding reasoning using `pv_node_extraction_v1`,
  `pv_edge_linking_v1`, and `pv_finding_reasoning_v1`.
- Edge-linking LLM reasoning uses a vector-backed retrieval context artifact
  (`edge_retrieval_context.json`) with retrieved chunk and source artifact ids.
- Masking policy violations stop analysis before node extraction/LLM reasoning,
  mark the mask/chunk step failed, persist a security-review debug artifact
  reference, and fail the run with `MASKING_POLICY_VIOLATION`.
- Deterministic finding rules include missing implementation, missing verification, orphan design, conflicting alternatives, Confluence stale trace, issue-affects-critical-requirement, and architecture-without-verification-path.
- Model gateway abstraction with dummy provider, HTTP JSON provider foundation, registry activation/rollback records, structured validation, retry/fallback traces, and token/cost metadata.
- Model gateway same-input comparison helper can run model/prompt candidates and
  report profile ids, prompt ids, validation statuses, and output diffs.
- Approval workflow with pending graph proposals separated from approved graph state.
- Approval actions: approve, reject, hold, modify.
- Approval safety: idempotency, version/proposal-hash stale checks, RBAC, audit.
- Feedback/eval/improvement loop with feedback taxonomy, eval candidates, improvement candidates, review/canary/active/rollback flow, and security-blocked eval path.
- SQLite persistence and restore.
- PostgreSQL state store, typed core/operation mirrors, migrations, rollback validation, audit archive/prune, idempotency restore, replay restore, improvement decision restore, failed run persistence.
- Neo4j graph backend and Qdrant vector backend foundations.
- Docker-backed backend integration runner and full-stack rehearsal.
- Scheduler API/UI/runbook path, restart-safe schedule configuration persistence,
  and PostgreSQL scheduler lease support for Ubuntu multi-worker deployments.
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
  - approval feedback reason-code controls in work queue detail
  - contract/unit/UI smoke coverage for empty state, `RUNE_CAM_ALPHA`, `RUNE_SCALE_150`, approval count update, source export health, RBAC, and dashboard UI hooks
- Debug workbench: run summaries, artifact read, LLM payload diff panes, graph delta preview, approval lineage, replay diff, source cursor debug API.
- Audit trail: run_started/run_completed boundaries for analysis/ingestion/replay, failed completion audit, blocked debug read audit, finding status audit, improvement/model/prompt activation and rollback audit, archive/prune idempotency.
- Claude Code source skill boundary: source skills remain the company access layer; core app code uses stable adapters and does not leak MCP tool names.
- JIRA/Confluence/Email foundations:
  - JIRA REST adapter
  - JIRA link, comment, and changelog metadata preservation
  - Confluence REST adapter
  - Confluence section-path and table-cell metadata extraction
  - Confluence previous-version metadata and deterministic stale trace findings
  - export-file adapters for JIRA, Confluence, restricted decision/email
  - restricted decision/email export policy with sensitive-thread manual-review routing and email thread metadata masking
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
- `uv run pytest`: `242 passed, 3 skipped`
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
  local regression gates passed; overall readiness remains incomplete with
  `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because
  company/staging variables and reviewed evidence are unset.
- `uv run pytest tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_openapi_surface.py`: `10 passed`
- `uv run pytest tests/unit/ops/test_skill_export_rehearsal.py tests/unit/ops/test_production_readiness_check.py`: `19 passed`
- `uv run pytest tests/contract/test_backend_settings_api.py tests/contract/test_health_api.py tests/contract/test_run_api.py tests/contract/test_debug_api.py tests/contract/test_persistence_api.py`: `33 passed`
- `uv run pytest tests/contract/test_debug_api.py tests/contract/test_security_api.py tests/contract/test_openapi_surface.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py tests/unit/storage/test_postgres_store.py tests/contract/test_models.py`: `44 passed`
- `uv run python ops/source/smoke_source_adapters.py`: passed
- `uv run python ops/source/rehearse_skill_export_sources.py`: passed
- `uv run python ops/source/validate_source_boundaries.py`: passed
- `uv run python ops/security/check_release_blockers.py`: passed
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown`: passed
- Latest GitHub Actions CI for `ee3dea2`: success (`25968150339`)

## Current Status

The local/dummy production-shaped foundation and non-company handoff package are implemented and validated.

The overall production objective is not fully complete yet because company/staging evidence is still required.

Do not mark the overall production goal complete until a completion audit verifies company/staging readiness evidence.

## 2026-05-17 Staging Evidence Plan Generator

Added a masked company/staging evidence collection planner:

- New script: `ops/rehearsal/build_staging_evidence_plan.py`
- New tests: `tests/unit/ops/test_staging_evidence_plan.py`
- Docs updated: `README_ubuntu.md`,
  `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`, and
  `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md`

Purpose:

- Convert unresolved readiness gates into concrete required env vars,
  commands, expected evidence artifacts, and runbook references.
- Print JSON or Markdown without exposing secret values.
- Help the company/staging phase collect reviewed evidence for PostgreSQL,
  Neo4j, Qdrant, model gateway, JIRA, Confluence, decision/email export,
  trusted proxy RBAC, observability, backup/restore/load, and optional Helm.
- The same Markdown smoke command is now required by
  `ops/rehearsal/validate_ci_gate_coverage.py`, runs in GitHub Actions `CI`,
  and is included in `check_production_readiness.py --run-local-gates`.

Validation:

- `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`: `3 passed`
- `uv run ruff check ops/rehearsal/build_staging_evidence_plan.py tests/unit/ops/test_staging_evidence_plan.py`: passed
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown`: passed
- RED/GREEN: `uv run pytest tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q` failed before adding the CI requirement and passed after adding it.
- RED/GREEN: `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q` failed before adding the local gate command and passed after adding it.
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local gates passed with staging evidence plan smoke included; overall readiness remains blocked by company/staging evidence.
- RED/GREEN: `uv run pytest tests/unit/ops/test_staging_evidence_plan.py::test_staging_evidence_plan_guides_every_unresolved_gate -q` failed before Neo4j/Qdrant staging docs guidance was added and passed after adding it.

## 2026-05-17 Confluence Stale Trace Local Hardening

- Added deterministic stale trace finding generation for Confluence source
  artifacts that provide `metadata.previous_version_number` and a newer
  `metadata.version_number`.
- Updated `ConfluenceRestSourceAdapter` to preserve
  `history.previousVersion.number` or `version.previousVersion.number` as
  `metadata.previous_version_number` when the REST payload provides it.
- Routed source artifact metadata into the workflow finding stage so document
  version changes can create reviewable stale trace candidates without LLM
  ownership of graph commits.
- Updated `.claude/skills/rune-source-confluence/SKILL.md` and
  `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` so company
  MCP/REST/export procedures preserve the same version metadata contract.
- Validation:
  - `uv run pytest tests/unit/adapters/test_confluence_rest_adapter.py::test_confluence_rest_adapter_preserves_previous_version_metadata tests/unit/findings/test_rules.py::test_confluence_version_change_creates_stale_trace_finding tests/integration/test_dummy_analysis_pipeline.py::test_confluence_version_change_is_routed_to_stale_finding -q`: `3 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `236 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

## 2026-05-17 Masking Policy Violation Workflow Block

- Added workflow-level masking policy enforcement for source-specific
  `metadata.forbidden_patterns`.
- If forbidden text remains after masking, `LocalAnalysisWorkflow` now writes a
  `masking_policy_violation` debug artifact, fails the `mask_chunk` step with
  `validation_status=failed`, marks `security_review_required=true`, completes
  the run as failed with `MASKING_POLICY_VIOLATION`, and raises
  `MaskingPolicyViolationError` before graph extraction or LLM reasoning.
- Runtime failure recording now preserves explicit exception `failure_code`
  values, so API/audit state can distinguish masking policy violations from
  generic runtime errors.
- Focused verification:
  - `uv run pytest tests/integration/test_dummy_analysis_pipeline.py::test_masking_policy_violation_blocks_analysis_and_routes_security_review -q`: passed
  - `uv run pytest tests/unit/ingestion/test_masking_chunking.py tests/integration/test_dummy_analysis_pipeline.py tests/unit/api/test_runtime_state.py tests/contract/test_run_api.py tests/unit/debug/test_trace_recorder.py -q`: `20 passed`
  - `uv run pytest tests/unit/ops/test_release_blocker_checker.py tests/integration/test_dummy_analysis_pipeline.py::test_masking_policy_violation_blocks_analysis_and_routes_security_review -q`: `3 passed`
  - `uv run python ops/security/check_release_blockers.py`: passed, now including the workflow-level masking block integration evidence
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `239 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

## 2026-05-17 Traceable Node/Finding LLM Stage Coverage

- Extended `LocalAnalysisWorkflow` so the local deterministic analysis run now
  records model-gateway traces for node extraction and finding reasoning in
  addition to edge-linking reasoning.
- Prompt trace coverage now includes:
  - `pv_node_extraction_v1`
  - `pv_edge_linking_v1`
  - `pv_finding_reasoning_v1`
- Updated debug, replay, persistence, integration, and metrics contracts to
  expect three LLM call traces per local analysis run.
- Changed `ModelGatewayClient` artifact names to include `step_id`, preventing
  multi-stage calls in the same run from overwriting `masked_payload`,
  `raw_response`, or `parsed_output` debug artifacts.
- Verification:
  - `uv run pytest tests/contract/test_health_api.py::test_metrics_summary_reports_http_and_runtime_counts tests/unit/model_gateway tests/contract/test_debug_api.py tests/contract/test_replay_feedback_api.py tests/contract/test_persistence_api.py tests/integration/test_dummy_analysis_pipeline.py -q`: `40 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `239 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.
- Commit/CI:
  - `360b68e Trace node and finding LLM stages`
  - GitHub Actions `CI` run `25967338344`: success

## 2026-05-17 Model Gateway Comparison Coverage

- Added `src/req_tracker/model_gateway/comparison.py`.
- The new comparison helper runs the same `ModelRequest.payload` through two
  or more model/prompt candidates and reports:
  - compared model profile ids
  - compared prompt version ids
  - per-profile validation status
  - output hashes
  - top-level added/removed/changed output fields
- This closes the local Step 3 gap for comparing the same request across two
  dummy model profiles without a live provider.
- Verification:
  - `uv run pytest tests/unit/model_gateway -q`: `16 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `240 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

## 2026-05-17 Vector-Backed Edge Retrieval Context

- Edge-linking LLM reasoning now calls the configured vector backend before
  model-gateway execution.
- The workflow writes `edge_retrieval_context.json` and uses it as the
  `llm_assisted_reasoning` step `retrieval_context_ref`.
- The model payload includes the retrieval context, including query,
  `ret_dummy_v1`, retrieved chunk ids, source artifact ids, and candidate edge
  ids.
- Verification:
  - `uv run pytest tests/integration/test_dummy_analysis_pipeline.py::test_dummy_analysis_creates_findings_and_approvals -q`: passed
  - `uv run pytest tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_debug_api.py tests/contract/test_run_api.py tests/contract/test_persistence_api.py tests/contract/test_replay_feedback_api.py -q`: `33 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `240 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

## 2026-05-17 Decision/Email Manual Review Local Hardening

- Added restricted decision/email export policy that blocks email artifacts with
  `metadata.manual_review_required=true` or `metadata.sensitive_thread=true`
  from automatic ingestion even when they are otherwise approved decision
  artifacts.
- Added source warning
  `decision_email_manual_review_required:<external_id>` so sensitive threads
  are distinguishable from ordinary skipped mailbox artifacts.
- Updated `ops/source/rehearse_decision_email_export.py` to report
  `manual_review_count` separately from `skipped_count`.
- Validation:
  - `uv run pytest tests/unit/adapters/test_export_file_adapter.py tests/unit/ops/test_decision_email_rehearsal.py -q`: `8 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `236 passed, 3 skipped`

## 2026-05-17 JIRA Comment and Changelog Local Hardening

- Updated `JiraRestSourceAdapter` to request `comment` fields and `changelog`
  expansion from the REST search payload.
- Preserved comment summaries in `metadata.comment_refs` and
  `metadata.comment_count`, including comment id, author id, created/updated
  timestamps, and a bounded body preview.
- Preserved changelog summaries in `metadata.history_refs` and
  `metadata.history_count`, including history id, author id, timestamp, field,
  from/to ids, and from/to display strings.
- Updated `.claude/skills/rune-source-jira/SKILL.md` and
  `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` so
  MCP/REST/export source procedures preserve the same debug/replay metadata
  contract.
- Validation:
  - `uv run pytest tests/unit/adapters/test_jira_rest_adapter.py -q`: `6 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `236 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

## 2026-05-17 Deterministic Critical Impact Rule

- Added deterministic `ISSUE_AFFECTS_CRITICAL_REQUIREMENT` finding rule.
- The rule creates a `cross_domain_hidden` critical finding when an Issue/Risk
  node has an `affects` edge to a Requirement whose source artifact priority or
  labels indicate `P0`, `critical`, or `blocker`.
- The compact dummy dashboard now reports `blocked` health with one critical
  finding for `CAM-ISS-060 -> CAM-REQ-001`, matching
  `PRODUCTION_EXECUTION_PLAN.md` Step 7's `issue affects critical requirement`
  rule.
- Validation:
  - `uv run pytest tests/unit/findings/test_rules.py tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_dashboard_api.py::test_dashboard_summary_after_compact_analysis -q`: `6 passed`
  - `uv run ruff check src/req_tracker/findings/rules.py tests/unit/findings/test_rules.py tests/contract/test_dashboard_api.py`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `237 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

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
- Dashboard smoke data included `RUNE_SCALE_150` with 150 graph nodes, 103 pending approvals, 48 open findings, 41 high findings, and 9 orphan nodes after architecture verification-path coverage was added.

## 2026-05-17 Deterministic Architecture Verification-Path Rule

- Added deterministic `ARCHITECTURE_WITHOUT_VERIFICATION_PATH` finding rule.
- The rule creates a high `missing_verification` finding when an
  `Architecture_Block` has neither a direct incoming `verifies` edge nor an
  indirect verification path through linked requirement/design targets.
- The rule addresses `PRODUCTION_EXECUTION_PLAN.md` Step 7's `architecture
  without verification path` baseline rule.
- `RUNE_SCALE_150` now reports 48 open findings, including one
  architecture verification-path gap, while compact `RUNE_CAM_ALPHA` remains at
  6 open findings because `CAM-ARCH-010` is covered through verified
  `CAM-REQ-001`.
- Fresh verification:
  - `uv run pytest tests/unit/findings/test_rules.py tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py -q`: `17 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `238 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

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

## 2026-05-17 Work Queue Feedback Reason Controls

Implemented approval feedback controls in the dashboard work queue detail view.

Changed:

- Added canonical feedback reason-code selection for approval-related work queue
  items.
- Routed work queue approve/reject/hold actions through the shared approval
  decision handler with the selected reason code.
- Kept reject fallback behavior as `wrong_relation` when a reason is not
  supplied.
- Extended operator UI smoke coverage for the feedback selector, key canonical
  reason codes, and hold action wiring.
- Updated `README.md` and
  `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md`.

Validation evidence:

- `node --check src/req_tracker/ui/work_queue.js`: passed
- `node --check src/req_tracker/ui/app.js`: passed
- `uv run pytest tests/contract/test_run_api.py::test_analyze_run_and_approve_edge tests/contract/test_run_api.py::test_modify_approval_commits_corrected_edge_and_feedback tests/contract/test_replay_feedback_api.py::test_feedback_api_normalizes_command_style_actions tests/unit/ops/test_operator_ui_smoke.py -q`: `4 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `240 passed, 3 skipped`
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.

## 2026-05-17 Persisted Schedule Configuration

Implemented restart-safe scheduler configuration persistence for Ubuntu/server
operation.

Changed:

- Added `RuntimeState.record_schedule_config()` and call it from
  `PUT /api/v1/schedule`.
- Restored saved `ScheduleConfig` from the configured state store during
  runtime startup before the scheduler lifespan starts.
- Added PostgreSQL typed mirror migration/rollback
  `010_schedule_config_state_tables` for `schedule_configs`.
- Added `schedule_configs` to the PostgreSQL typed collection specs and drift
  validators.
- Updated `README.md` and
  `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md`.

Validation evidence:

- RED: `uv run pytest tests/contract/test_persistence_api.py::test_sqlite_state_store_restores_schedule_configuration -q` failed with restored `interval_seconds` still `3600`.
- GREEN: same test passed after persisting/restoring schedule config.
- `uv run pytest tests/unit/storage/test_postgres_store.py::test_postgres_store_typed_schedule_config_table tests/unit/storage/test_postgres_store.py::test_load_postgres_migrations_returns_ordered_state_schema tests/unit/storage/test_postgres_store.py::test_load_postgres_rollbacks_returns_versioned_scripts -q`: `3 passed`
- `uv run pytest tests/contract/test_schedule_api.py tests/contract/test_persistence_api.py tests/unit/storage/test_postgres_store.py tests/unit/ops/test_postgres_migration_rollback_validator.py tests/unit/ops/test_postgres_typed_mirror_validator.py -q`: `26 passed`
- `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`: passed with `010:schedule_configs`
- `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed with `schedule_configs`
- `uv run ruff check src/req_tracker/api/state.py src/req_tracker/api/routes/runs.py src/req_tracker/storage/postgres_store.py tests/contract/test_persistence_api.py tests/unit/storage/test_postgres_store.py`: passed
- `uv run mypy src`: passed
- `uv run ruff check .`: passed
- `uv run pytest`: `242 passed, 3 skipped`
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness still fails as expected with `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.
- Commit/CI:
  - `c52572d Persist scheduler configuration state`
  - GitHub Actions `CI` run `25967994338`: success
  - `ee3dea2 Document schedule configuration persistence`
  - GitHub Actions `CI` run `25968150339`: success

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
  - `uv run pytest`: `235 passed, 3 skipped`
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

## 2026-05-17 Release Scope Artifact Verifier

Added a machine-readable first-release scope verifier based on
`PRODUCTION_EXECUTION_PLAN.md`.

Implemented:

- Added `ops/rehearsal/validate_release_scope_artifacts.py`.
- Added `tests/unit/ops/test_release_scope_artifacts.py`.
- Added the verifier to GitHub Actions `CI`.
- Added the verifier to
  `ops/rehearsal/validate_ci_gate_coverage.py` required extra commands.
- Added the verifier to
  `ops/rehearsal/check_production_readiness.py` `LOCAL_GATE_COMMANDS`.

Verifier behavior:

- Checks that each first-release scope item has concrete repo artifacts.
- Checks that each item has at least one verification command.
- Checks that each item has guidance notes.
- Parses the first-release required-scope bullets from
  `PRODUCTION_EXECUTION_PLAN.md` and fails on plan/verifier requirement drift.
- Checks that each first-release scope item has a marker in
  `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md`.
- Reports `release_ready=false` separately from structural pass/fail so local
  artifact coverage can pass while company/staging evidence remains unresolved.
- Current status counts:
  - `local_complete=11`
  - `company_evidence_required=4`
  - `missing_artifacts=0`
  - `audit_coverage_missing=0`
- Graph UI scope decision:
  - `PRODUCTION_EXECUTION_PLAN.md` now treats the first-release graph UI as
    `production graph UI with renderer decision gate`.
  - The deterministic SVG relationship graph is the first-release renderer.
  - React Flow/Cytoscape remains a future renderer-decision gate after real
    graph shape and editing workflow validation.

Validation evidence:

- RED/GREEN: `uv run pytest tests/unit/ops/test_release_scope_artifacts.py -q`
  failed while the verifier still reported `decision_pending=1`, then passed
  after moving the graph UI item to `local_complete`.
- RED/GREEN:
  `uv run pytest tests/unit/ops/test_release_scope_artifacts.py::test_release_scope_requirements_match_production_plan -q`
  failed before the plan parser existed, then passed after adding it.
- RED/GREEN:
  `uv run pytest tests/unit/ops/test_release_scope_artifacts.py::test_release_scope_items_have_completion_audit_coverage -q`
  failed before audit coverage was reported, then passed after adding
  `audit_markers`, `audit_covered`, and `audit_coverage_missing`.
- `uv run pytest tests/unit/ops/test_release_scope_artifacts.py tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q`:
  `6 passed`
- `uv run python ops/rehearsal/validate_release_scope_artifacts.py`: passed
  with `release_ready=false`, `audit_coverage_missing=0`, and
  `plan_requirements` aligned to the production plan
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
  `ci_command_count=23`
- Added `ops/rehearsal/check_goal_completion.py`, a top-level completion audit
  that combines release-scope artifact status and production-readiness status.
  It reports `goal_complete=false` with concrete remaining blockers instead of
  relying on manual interpretation.
- Added the goal completion audit to local readiness gates and GitHub Actions
  as `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete`.
- `uv run pytest tests/unit/ops/test_goal_completion_audit.py tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q`:
  `4 passed`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete`:
  passed, reporting `goal_complete=false`, `remaining_blocker_count=22`,
  `release_scope_passed=true`, `release_scope_ready=false`, and
  `production_readiness_passed=false`
- Added `--evidence-file` support to `ops/rehearsal/check_goal_completion.py`
  so the top-level goal audit can apply the same reviewed manual evidence file
  used by `check_production_readiness.py`.
- `uv run pytest tests/unit/ops/test_goal_completion_audit.py -q`: `3 passed`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --evidence-file ops/rehearsal/production_readiness_evidence.example.json`:
  passed, reporting `goal_complete=false` while applying 11 example manual
  evidence entries that remain failed TODO placeholders by design
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `256 passed, 3 skipped`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --run-local-gates`:
  passed, reporting `goal_complete=false`, `remaining_blocker_count=21`,
  `release_scope_passed=true`, `release_scope_ready=false`, and local
  regression gates passed; remaining blockers are company/staging environment
  configuration and manual evidence.
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
  local regression gates passed with release-scope and goal-completion audits included;
  overall readiness failed as expected with summary `failed=7`,
  `manual_required=10`, `passed=2`, `warning=0`
- Committed and pushed `f16b991 Accept manual evidence in goal audit`.
  GitHub Actions CI run `25969313834` passed all deterministic release gates.
- Updated GitHub Actions JavaScript actions from `actions/checkout@v4` and
  `actions/setup-python@v5` to their `v6` Node 24-backed tags, removing the
  temporary `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` compatibility env.
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
  `ci_command_count=23`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `256 passed, 3 skipped`
- Expanded `.env.example` with company/staging rehearsal variables for
  PostgreSQL, Neo4j, Qdrant, model gateway, trusted proxy, observability, JIRA,
  Confluence, and restricted decision/email export handoff.
- Added `tests/unit/config/test_env_example.py` to keep `.env.example` aligned
  with production-readiness inputs.
- `uv run pytest tests/unit/config/test_env_example.py -q`: `1 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `257 passed, 3 skipped`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --run-local-gates`:
  passed, still reporting `goal_complete=false` and `remaining_blocker_count=21`
  because company/staging env values and reviewed manual evidence are unset.
- Added a `prompt_to_artifact_checklist` section to
  `ops/rehearsal/check_goal_completion.py` so the top-level audit maps each
  success criterion to concrete artifacts, commands, checks, evidence, and gaps
  instead of relying only on summary/proxy green signals.
- Added unit coverage in `tests/unit/ops/test_goal_completion_audit.py` for
  checklist criterion alignment and release/company evidence mapping.
- `uv run pytest tests/unit/ops/test_goal_completion_audit.py -q`: `4 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `258 passed, 3 skipped`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --run-local-gates`:
  rerun after the checklist change and passed structurally with
  `goal_complete=false`, `remaining_blocker_count=22`,
  `prompt_to_artifact_checklist_count=6`, `failed=7`,
  `manual_required=11`, `passed=1`, `warning=0`. Non-Docker local gates passed,
  but Docker-backed local gates were classified as `manual_required` because
  Docker is unavailable in this workstation shell.
- Docker Desktop Linux engine later became available. Rerunning
  `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --run-local-gates`
  passed structurally with `goal_complete=false`, `remaining_blocker_count=21`,
  `prompt_to_artifact_checklist_count=6`, readiness summary `failed=7`,
  `manual_required=10`, `passed=2`, `warning=0`; local regression gates are now
  passed, leaving company/staging environment configuration and reviewed manual
  evidence as the remaining blockers.
- Added `--env-file` support to `ops/rehearsal/check_production_readiness.py`
  and `ops/rehearsal/check_goal_completion.py` so company/staging operators can
  pass a secure KEY=VALUE env file alongside reviewed manual evidence without
  exporting every variable in the shell.
- Added env-file parser coverage in
  `tests/unit/ops/test_production_readiness_check.py`, including quote/export
  handling, base-env merge behavior, invalid-line rejection, and secret masking
  in readiness reports.
- Updated `README.md` and `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`
  with `--env-file` examples for readiness and goal-completion audits.
- `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_load_env_file_merges_staging_values_without_printing_secrets tests/unit/ops/test_production_readiness_check.py::test_load_env_file_rejects_invalid_lines -q`:
  `2 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `260 passed, 3 skipped`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example`:
  passed structurally with `goal_complete=false`, proving the new env-file input
  path works; local gates were not run in this smoke, so the local regression
  gate remains `manual_required` in that specific report.
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
  passed structurally with `goal_complete=false`, `remaining_blocker_count=20`,
  `prompt_to_artifact_checklist_count=6`, readiness summary `failed=6`,
  `manual_required=10`, `passed=3`, `warning=0`. This validates the intended
  release-style env-file plus local-gates execution path; remaining blockers
  still require real company/staging values and reviewed manual evidence.
- Added `--env-file` support to `ops/rehearsal/build_staging_evidence_plan.py`
  so the evidence collection plan can be generated from the same secure staging
  env file used by readiness and goal-completion audits.
- Updated `README.md` and `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`
  with `build_staging_evidence_plan.py --env-file` examples.
- `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`: `5 passed`
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file .env.example --format markdown`:
  passed, reporting `Unresolved gates: 17` and summary `failed=6`,
  `manual_required=11`, `passed=2`, `warning=0`.
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `261 passed, 3 skipped`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
  passed structurally with `goal_complete=false`, `remaining_blocker_count=20`,
  `prompt_to_artifact_checklist_count=6`, readiness summary `failed=6`,
  `manual_required=10`, `passed=3`, `warning=0`.
- Added env-file CLI smoke gates to GitHub Actions `CI`:
  `check_production_readiness.py --env-file .env.example --write-evidence-template -`,
  `build_staging_evidence_plan.py --env-file .env.example --format markdown`,
  and `check_goal_completion.py --allow-incomplete --env-file .env.example`.
- Updated `ops/rehearsal/validate_ci_gate_coverage.py` so those env-file smoke
  commands are required CI coverage.
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
  `ci_command_count=26`
- `uv run pytest tests/unit/ops/test_ci_gate_coverage.py -q`: `2 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `261 passed, 3 skipped`
- Fixed the top-level goal-completion semantics so `company_evidence_required`
  release-scope items are resolved through mapped production-readiness checks
  instead of permanently blocking `goal_complete` through the local-only
  `release_ready=false` flag. This preserves `release_scope.release_ready=false`
  as the local artifact verifier's status, while adding
  `release_scope_goal_ready` / `release_scope.goal_ready` for the actual
  completion decision.
- Added `test_goal_completion_audit_can_complete_with_reviewed_company_evidence`
  to prove that complete company/staging env values plus reviewed manual
  evidence can drive the top-level audit to `goal_complete=true`.
- `uv run pytest tests/unit/ops/test_goal_completion_audit.py -q`: `5 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `262 passed, 3 skipped`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
  passed structurally with `goal_complete=false`, `remaining_blocker_count=20`,
  `release_scope_goal_ready=false`, and `production_readiness_passed=false`.
- Added `--output` support to `ops/rehearsal/check_production_readiness.py` and
  `ops/rehearsal/check_goal_completion.py` so staging readiness and final
  goal-completion reports can be written as JSON artifacts for review/retention
  instead of being copied from stdout.
- Reused `write_json_output` for readiness evidence-template writing and added
  unit coverage for JSON artifact output.
- Updated `README.md` and `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`
  with `--output` examples for readiness and goal-completion reports.
- `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_write_json_output_writes_report_artifact -q`:
  `1 passed`
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `263 passed, 3 skipped`

Remaining production gap is unchanged:

- Real/company staging evidence is still required for company JIRA/Confluence
  source sync, real model gateway execution, live model quality validation,
  company SSO/OIDC proxy, PostgreSQL, Neo4j, Qdrant, observability,
  backup/restore/load, and approved decision/email export validation.

## 2026-05-17 Handoff Bundle Generation

- Added `ops/rehearsal/build_handoff_bundle.py` to generate a single staging
  review bundle containing:
  - `manifest.json`
  - `staging-evidence-plan.md`
  - `manual-evidence-template.json`
  - `production-readiness-report.json`
  - `goal-completion-report.json`
- The bundle accepts the same `--env-file` and `--evidence-file` inputs as the
  readiness and goal-completion audits, without copying secret env values into
  generated reports.
- Added `--allow-incomplete` for pre-review/dry-run bundles. Without that flag,
  the CLI exits non-zero until the top-level goal completion audit is actually
  complete.
- Added unit coverage in `tests/unit/ops/test_handoff_bundle.py` for artifact
  generation, manifest contents, reviewed evidence input, incomplete CLI smoke,
  and secret non-leakage.
- Added GitHub Actions smoke coverage:
  `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file .env.example --output-dir .local_artifacts/handoff-bundle`
  and updated `ops/rehearsal/validate_ci_gate_coverage.py`.
- Updated `README.md`,
  `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`, and
  `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md` with the
  bundle command and handoff evidence role.
- Verification so far:
  - `uv run pytest tests/unit/ops/test_handoff_bundle.py`: `3 passed`
  - `uv run pytest tests/unit/ops/test_ci_gate_coverage.py tests/unit/ops/test_handoff_bundle.py`:
    `5 passed`
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file .env.example --output-dir .local_artifacts/handoff-bundle`:
    passed, reporting `goal_complete=false`, readiness summary `failed=6`,
    `manual_required=11`, `passed=2`, `warning=0`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=27`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `266 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`
  - Commit `c3f9a36 Add staging handoff bundle generator` pushed to
    `origin/main`
  - GitHub Actions `CI` run `25979725389`: success, including the new
    `Handoff bundle env-file smoke` step

## 2026-05-17 Handoff Bundle Local Gate Coverage

- Added the handoff bundle smoke command to
  `ops/rehearsal/check_production_readiness.py` `LOCAL_GATE_COMMANDS`:
  `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file .env.example --output-dir .local_artifacts/handoff-bundle`
- This aligns release-style local gate runs with GitHub Actions coverage, so
  `check_goal_completion.py --run-local-gates` also executes the handoff bundle
  generator.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q`
    failed before the command was added and passed after updating
    `LOCAL_GATE_COMMANDS`.
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke tests/unit/ops/test_ci_gate_coverage.py tests/unit/ops/test_handoff_bundle.py -q`:
    `6 passed`
- Verification after adding the local gate command:
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `266 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=27`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`; the local regression gate
    evidence now includes
    `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file .env.example --output-dir .local_artifacts/handoff-bundle`

## 2026-05-17 Handoff Bundle Validator

- Added `ops/rehearsal/validate_handoff_bundle.py` to validate generated
  staging handoff bundles before release-owner review.
- The validator checks:
  - `manifest.json` schema version
  - required artifact declarations and file presence
  - non-empty artifact files
  - JSON parse/object shape for readiness, goal, and manual-evidence template
    artifacts
  - manifest `readiness_passed`, `goal_complete`, readiness summary, and goal
    summary consistency with generated report files
  - manual-evidence-template coverage for every `manual_required` readiness
    gate
  - staging evidence plan Markdown heading
- Wired the validator into:
  - GitHub Actions `CI` after `Handoff bundle env-file smoke`
  - `ops/rehearsal/check_production_readiness.py` `LOCAL_GATE_COMMANDS`
  - `ops/rehearsal/validate_ci_gate_coverage.py`
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py -q`
    failed before `validate_handoff_bundle.py` existed and passed after
    implementation.
- Verification so far:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke tests/unit/ops/test_ci_gate_coverage.py -q`:
    `10 passed`
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file .env.example --output-dir .local_artifacts/handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/handoff-bundle`:
    passed with `artifact_count=4`, `failed=0`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=28`
- Full verification after manual-template coverage validation:
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `270 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=28`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`

## 2026-05-17 Ubuntu Handoff Bundle Runbook Update

- Updated `README_ubuntu.md` production-readiness instructions with the
  staging handoff bundle workflow:
  - `ops/rehearsal/build_handoff_bundle.py`
  - `ops/rehearsal/validate_handoff_bundle.py`
  - guidance for using `--allow-incomplete` before final release decision
  - manual-evidence-template coverage validation description
- Added `test_ubuntu_runbook_covers_handoff_bundle_workflow` to
  `tests/unit/ops/test_runbook_docs.py`.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_runbook_docs.py::test_ubuntu_runbook_covers_handoff_bundle_workflow -q`
    failed before the Ubuntu runbook mentioned the handoff bundle workflow and
    passed after the runbook update.
- Verification:
  - `uv run pytest tests/unit/ops/test_runbook_docs.py -q`: `2 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `271 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=28`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`

## 2026-05-17 Staging Env Template

- Added `ops/rehearsal/staging.env.example` as a staging/release rehearsal
  environment template separate from the local `.env.example`.
- The template sets production-oriented modes while leaving endpoint/secret
  values empty for secure injection:
  - `STATE_STORE=postgres`
  - `GRAPH_BACKEND=neo4j`
  - `VECTOR_BACKEND=qdrant`
  - `MODEL_GATEWAY_MODE=http_json`
  - `AUTH_MODE=trusted_proxy`
  - `OTEL_ENABLED=true`
  - `ARTIFACT_ROOT=/var/lib/rune-agent/artifacts`
- The template explicitly targets the intended Ubuntu server handoff path with
  `DEPLOYMENT_TARGET=ubuntu` and `KUBERNETES_DEPLOYMENT=false`; change those
  only for a future Kubernetes/Helm evidence pass.
- Added config test coverage to ensure required staging modes are set and fake
  secret values are not committed in the template.
- Added GitHub Actions smoke coverage:
  `uv run python ops/rehearsal/check_production_readiness.py --env-file ops/rehearsal/staging.env.example --write-evidence-template -`
  and updated `ops/rehearsal/validate_ci_gate_coverage.py`.
- Updated `README.md`, `README_ubuntu.md`, and
  `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md` to direct operators to
  copy `ops/rehearsal/staging.env.example` to a secure untracked path before
  filling company endpoint/secret values.
- RED/GREEN:
  - `uv run pytest tests/unit/config/test_env_example.py::test_staging_env_example_sets_production_modes_without_fake_secrets -q`
    failed before the template existed and passed after adding it.
- Verification:
  - `uv run pytest tests/unit/config/test_env_example.py tests/unit/ops/test_runbook_docs.py tests/unit/ops/test_ci_gate_coverage.py -q`:
    `6 passed`
  - `uv run python ops/rehearsal/check_production_readiness.py --env-file ops/rehearsal/staging.env.example --write-evidence-template -`:
    passed
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`:
    passed with unresolved gate plan output
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed with `artifact_count=4`, `failed=0`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `272 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=29`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`
- Added RED/GREEN coverage for stale manual-evidence templates:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py::test_handoff_bundle_validator_rejects_missing_manual_template_gate -q`
    failed before the template/readiness comparison existed and passed after
    `validate_handoff_bundle.py` compared template check ids with
    `manual_required` readiness checks.
- Full verification after wiring validator into local gates:
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `269 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`; local regression evidence
    includes both handoff bundle generation and validation commands.
- Verification after making the staging template explicitly Ubuntu-targeted:
  - `uv run pytest tests/unit/config/test_env_example.py`: `2 passed`
  - `uv run python ops/rehearsal/check_production_readiness.py --env-file ops/rehearsal/staging.env.example --write-evidence-template -`:
    passed
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`:
    passed with unresolved gate output
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `272 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=29`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.
- Commit `5cc4c20 Guard readiness evidence example against gate drift` was pushed
  to `origin/main`; GitHub Actions `CI` run `25980477607` completed
  successfully.

## 2026-05-17 Staging Template Handoff Gate Coverage

- Strengthened local gate and GitHub Actions coverage so the release handoff
  path is exercised with `ops/rehearsal/staging.env.example`, not only the
  generic `.env.example`.
- Added staging-template commands to `LOCAL_GATE_COMMANDS`:
  - `build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example`
  - `check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example`
  - `build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`
  - `validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`
- Added matching GitHub Actions steps and updated
  `ops/rehearsal/validate_ci_gate_coverage.py`; CI command coverage now reports
  `ci_command_count=33`.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q`
    failed before staging-template handoff commands were added to local gates and
    passed after implementation.
  - `uv run pytest tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q`
    failed before staging-template CI requirements were added and passed after
    implementation.
- Verification so far:
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`:
    passed with unresolved gate output
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example`:
    passed structurally with `goal_complete=false`
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `273 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=33`.
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with the expanded local gate list,
    `goal_complete=false`, `remaining_blocker_count=20`, readiness summary
    `failed=6`, `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Handoff Bundle Blocker Manifest

- Enhanced `ops/rehearsal/build_handoff_bundle.py` so `manifest.json` carries
  a review-friendly remaining blocker summary:
  - `remaining_blocker_count`
  - `remaining_blockers[]` with `blocker_id`, `status`, and `next_action`
- Enhanced `ops/rehearsal/validate_handoff_bundle.py` to compare manifest
  blocker count/list against `goal-completion-report.json` and fail on drift.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_handoff_bundle.py::test_handoff_bundle_writes_required_artifacts_without_secrets -q`
    failed before the manifest blocker fields existed and passed after
    implementation.
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py::test_handoff_bundle_validator_rejects_manifest_blocker_drift -q`
    failed before validator blocker drift checks existed and passed after
    implementation.
- Verification:
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed and printed `remaining_blocker_count=21` without `--run-local-gates`.
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed after sequential bundle generation.
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `274 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=33`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Final Reviewed Evidence Bundle Fix

- Fixed `ops/rehearsal/build_handoff_bundle.py` so
  `manual-evidence-template.json` is generated from the readiness report after
  applying reviewed `--evidence-file` entries, rather than from env-only
  readiness.
- This matters for final release bundles: when all manual gates are resolved by
  reviewed evidence, the generated manual evidence template now has no stale
  TODO gate entries and `validate_handoff_bundle.py` can pass.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py::test_handoff_bundle_validator_accepts_complete_reviewed_evidence_bundle -q`
    failed while the template still included 11 stale manual gates and passed
    after generating the template from the evidence-applied readiness report.
- Verification:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py::test_handoff_bundle_validator_accepts_complete_reviewed_evidence_bundle tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_handoff_bundle_validator.py -q`:
    `9 passed`
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `275 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=33`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Staging Evidence Plan Doc Reference Guard

- Added a regression guard in
  `tests/unit/ops/test_staging_evidence_plan.py` so every documentation
  reference emitted by `ops/rehearsal/build_staging_evidence_plan.py` must
  point to an existing Markdown file and, when a fragment is present, an
  existing heading anchor.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py::test_staging_evidence_plan_doc_refs_exist -q`
    failed because `README_ubuntu.md#production-readiness` did not exist.
  - Added `### Production Readiness` to `README_ubuntu.md`.
  - The same focused test passed after the runbook anchor existed.
- Verification:
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`:
    `6 passed`
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`:
    passed and rendered company/staging gate guidance with the now-valid
    `README_ubuntu.md#production-readiness` references.
  - `uv run ruff check tests/unit/ops/test_staging_evidence_plan.py`: passed
  - `uv run python ops/rehearsal/validate_release_scope_artifacts.py`: passed
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.
  - `git diff --check`: passed

## 2026-05-17 Staging Evidence Final Validation Commands

- Added `final_validation_commands` to
  `ops/rehearsal/build_staging_evidence_plan.py` so the company/staging
  evidence collection plan explicitly tells release owners how to validate
  reviewed evidence, run the goal completion audit, build the final handoff
  bundle, and validate that bundle after gate evidence is collected.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py::test_staging_evidence_plan_includes_final_validation_commands tests/unit/ops/test_staging_evidence_plan.py::test_staging_evidence_plan_markdown_is_operator_readable -q`
    failed while the plan had no `final_validation_commands` and no
    `## Final Validation` Markdown section.
  - The same focused tests passed after adding the structured command list and
    Markdown section.
- Verification:
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`:
    `7 passed`
  - `uv run ruff check ops/rehearsal/build_staging_evidence_plan.py tests/unit/ops/test_staging_evidence_plan.py`:
    passed
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`:
    passed and rendered the final validation command sequence.
  - `uv run python ops/rehearsal/validate_release_scope_artifacts.py`: passed
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.
  - `git diff --check`: passed

## 2026-05-17 Handoff Bundle Final Validation Guard

- Strengthened `ops/rehearsal/validate_handoff_bundle.py` so generated handoff
  bundles must include the staging evidence plan `## Final Validation` section
  and the final readiness, goal-completion, handoff build, and bundle validation
  command references.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py::test_handoff_bundle_validator_rejects_missing_final_validation_section -q`
    failed while a stale `staging-evidence-plan.md` without the final validation
    section still passed bundle validation.
  - The focused test passed after the validator checked the final validation
    section and command snippets.
- Verification:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_staging_evidence_plan.py -q`:
    `17 passed`
  - `uv run ruff check ops/rehearsal/validate_handoff_bundle.py tests/unit/ops/test_handoff_bundle_validator.py`:
    passed
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Traceable Manual Evidence References

- Strengthened `ops/rehearsal/check_production_readiness.py` so file-loaded
  `passed` manual evidence must include at least one traceable evidence
  reference prefix such as `artifact:`, `github-actions:`, `staging-ci:`,
  `run:`, or `approval:`. Free-text confirmations no longer satisfy a final
  production-readiness evidence file.
- Updated `README_ubuntu.md` and
  `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md` to document the
  traceable evidence reference requirement.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_load_manual_evidence_rejects_passed_without_traceable_reference -q`
    failed while `"operator confirmed this passed"` was accepted for a passed
    manual gate.
  - The focused test passed after the loader required a traceable reference.
- Verification:
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_readiness_evidence_example.py -q`:
    `41 passed`
  - `uv run ruff check ops/rehearsal/check_production_readiness.py tests/unit/ops/test_production_readiness_check.py`:
    passed
  - `uv run python ops/rehearsal/validate_evidence_example.py`: passed with
    `check_count=11`, `expected_check_count=11`, and no failures.
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Readiness Evidence Example Drift Guard

- Strengthened `ops/rehearsal/validate_evidence_example.py` so the committed
  `production_readiness_evidence.example.json` must stay synchronized with the
  current manual gates generated by `build_manual_evidence_template({})`.
- The validator now reports `missing_current_manual_gate:<check_id>` or
  `unknown_current_manual_gate:<check_id>` if readiness checks change without
  updating the example.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_readiness_evidence_example.py::test_validator_rejects_example_missing_current_manual_gate -q`
    failed before the drift guard existed and passed after implementation.
- Verification:
  - `uv run pytest tests/unit/ops/test_readiness_evidence_example.py -q`:
    `6 passed`
  - `uv run ruff check ops/rehearsal/validate_evidence_example.py tests/unit/ops/test_readiness_evidence_example.py`:
    passed
  - `uv run python ops/rehearsal/validate_evidence_example.py`: passed with
    `check_count=11`, `expected_check_count=11`, and no failures.
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `273 passed, 3 skipped`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=29`
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Handoff Bundle Artifact Hash Guard

- Strengthened `ops/rehearsal/build_handoff_bundle.py` so each handoff
  artifact listed in `manifest.json` is recorded with a SHA-256 artifact hash.
- Strengthened `ops/rehearsal/validate_handoff_bundle.py` so stale or tampered
  bundle artifacts fail validation with `artifact_hash_mismatch:<artifact>`.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py::test_handoff_bundle_validator_rejects_artifact_hash_drift -q`
    failed while a modified `staging-evidence-plan.md` still passed validation
    after bundle generation.
  - The focused test passed after the validator compared the current artifact
    hash against the manifest hash.
- Verification:
  - `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_handoff_bundle.py -q`:
    `11 passed`
  - `uv run ruff check ops/rehearsal/build_handoff_bundle.py ops/rehearsal/validate_handoff_bundle.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_handoff_bundle_validator.py`:
    passed
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed and emitted hashes for all four bundle artifacts.
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed with no failures.
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Staging Evidence Plan Reviewed Evidence Alignment

- Fixed `ops/rehearsal/build_staging_evidence_plan.py` so the staging evidence
  collection plan can apply the same reviewed manual evidence and optional
  local-gate execution inputs as the production-readiness and goal-completion
  reports.
- Updated `ops/rehearsal/build_handoff_bundle.py` so `--evidence-file` and
  `--run-local-gates` influence `staging-evidence-plan.md`, not only
  `production-readiness-report.json` and `goal-completion-report.json`.
- This prevents a final or partial handoff bundle from asking release owners to
  recollect a gate that is already passed by reviewed evidence.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py::test_staging_evidence_plan_applies_reviewed_manual_evidence -q`
    first failed because `build_staging_evidence_plan()` had no
    `manual_evidence` input.
  - The focused test passed after the plan builder passed reviewed evidence
    through to `check_production_readiness.build_readiness_report()`.
- Verification:
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py tests/unit/ops/test_handoff_bundle.py -q`:
    `11 passed`
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_production_readiness_check.py -q`:
    `44 passed`
  - `uv run ruff check ops/rehearsal/build_staging_evidence_plan.py ops/rehearsal/build_handoff_bundle.py tests/unit/ops/test_staging_evidence_plan.py tests/unit/ops/test_handoff_bundle.py`:
    passed
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown --evidence-file ops/rehearsal/production_readiness_evidence.example.json`:
    passed.
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --evidence-file ops/rehearsal/production_readiness_evidence.example.json --output-dir .local_artifacts/staging-handoff-bundle`:
    passed.
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed with no failures.
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Reviewed Evidence CI Smoke Coverage

- Added GitHub Actions smoke coverage for reviewed-evidence handoff paths:
  - `build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --evidence-file ops/rehearsal/production_readiness_evidence.example.json --format markdown`
  - `build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --evidence-file ops/rehearsal/production_readiness_evidence.example.json --output-dir .local_artifacts/staging-handoff-bundle-reviewed`
  - `validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle-reviewed`
- Strengthened `ops/rehearsal/validate_ci_gate_coverage.py` so those reviewed
  evidence smoke commands remain required in CI.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_requires_reviewed_evidence_handoff_smokes -q`
    failed while the reviewed-evidence smoke commands were not required.
  - The CI gate coverage tests passed after adding the required commands and
    matching workflow steps.
- Verification:
  - `uv run pytest tests/unit/ops/test_ci_gate_coverage.py -q`: `3 passed`
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=36`
  - `uv run ruff check ops/rehearsal/validate_ci_gate_coverage.py tests/unit/ops/test_ci_gate_coverage.py`:
    passed

## 2026-05-17 Reviewed Evidence Local Gate Coverage

- Added the reviewed-evidence staging evidence plan and handoff bundle smoke
  commands to `ops/rehearsal/check_production_readiness.py`
  `LOCAL_GATE_COMMANDS`.
- This keeps local `--run-local-gates`, goal completion audit evidence, and CI
  coverage aligned for the reviewed-evidence handoff path.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q`
    failed while `LOCAL_GATE_COMMANDS` lacked the reviewed-evidence plan and
    handoff bundle commands.
  - The focused test passed after adding those commands and the reviewed bundle
    validation command.
- Verification:
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q`:
    passed
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=36`
  - `uv run ruff check ops/rehearsal/check_production_readiness.py tests/unit/ops/test_production_readiness_check.py`:
    passed
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest -q`: passed with the expected skipped tests.
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with reviewed-evidence smoke commands included in
    `local_regression_gates`; `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

## 2026-05-17 Local Handoff Document Refresh

- Refreshed `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md` so the local
  gate command set includes staging evidence plan, release scope validation,
  goal completion audit, staging-template handoff bundle validation, and
  reviewed-evidence handoff bundle validation.
- Updated the latest readiness evidence in that document to the fresh
  `ops/rehearsal/staging.env.example --run-local-gates` result:
  `failed=6`, `manual_required=10`, `passed=3`, `warning=0`, with local gates
  passed and company/staging evidence still external.
- Verification:
  - `uv run python ops/rehearsal/check_production_readiness.py --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    returned non-zero as expected because production readiness is still blocked,
    but `local_regression_gates` passed and the summary matched the updated
    document.

## 2026-05-17 Goal Completion Final Validation Checklist

- Strengthened `ops/rehearsal/check_goal_completion.py` so the
  `company_staging_readiness` prompt-to-artifact checklist includes the final
  goal-completion audit, handoff bundle build, and handoff bundle validation
  commands in addition to readiness and evidence-plan generation commands.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_goal_completion_audit.py::test_goal_completion_audit_maps_prompt_requirements_to_artifacts -q`
    failed while those final validation commands were absent from the
    checklist.
  - The focused test passed after adding the final commands.
- Verification:
  - `uv run pytest tests/unit/ops/test_goal_completion_audit.py -q`:
    `5 passed`
  - `uv run ruff check ops/rehearsal/check_goal_completion.py tests/unit/ops/test_goal_completion_audit.py`:
    passed
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with the final validation commands present in the
    checklist; `goal_complete=false`, `remaining_blocker_count=20`, readiness
    summary `failed=6`, `manual_required=10`, `passed=3`, `warning=0`.
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed.
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed with no failures.
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=36`.

## 2026-05-17 Goal Completion Final Validation Artifact Mapping

- Strengthened the `company_staging_readiness` prompt-to-artifact checklist so
  the artifacts list now names the scripts that own the final staging
  validation commands:
  - `ops/rehearsal/check_goal_completion.py`
  - `ops/rehearsal/build_handoff_bundle.py`
  - `ops/rehearsal/validate_handoff_bundle.py`
- This closes a traceability gap where final validation commands were present
  but their owning executable artifacts were not listed in the checklist.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_goal_completion_audit.py::test_goal_completion_audit_maps_prompt_requirements_to_artifacts -q`
    failed while those artifacts were absent from
    `company_staging_readiness`.
  - The focused test passed after adding the final validation scripts to the
    artifact list.
- Verification:
  - `uv run pytest tests/unit/ops/test_goal_completion_audit.py -q`:
    `5 passed`
  - `uv run ruff check ops/rehearsal/check_goal_completion.py tests/unit/ops/test_goal_completion_audit.py`:
    passed
  - `uv run python ops/rehearsal/validate_release_scope_artifacts.py`:
    passed with no failures and `audit_coverage_missing=0`.
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=36`.
  - `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`:
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.
  - `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle`:
    passed and generated artifact hashes for the staging handoff bundle.
  - `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`:
    passed with no failures.
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest -q`: passed with the expected skipped tests.
  - `git diff --check`: passed

## 2026-05-17 Goal Completion Handoff Local Gate Alignment

- Updated the final `company_staging_readiness` handoff bundle command in
  `ops/rehearsal/check_goal_completion.py` to include `--run-local-gates`.
- This keeps the final goal-completion command and final handoff bundle command
  aligned so the bundle can carry local gate evidence instead of reporting
  `local_regression_gates` as a manual follow-up.
- RED/GREEN:
  - `uv run pytest tests/unit/ops/test_goal_completion_audit.py::test_goal_completion_audit_maps_prompt_requirements_to_artifacts -q`
    failed while the final handoff bundle command lacked
    `--run-local-gates`.
  - The focused test passed after adding `--run-local-gates` to that command.

## 2026-05-17 Korean Model Gateway UTF-8 Compatibility

- Investigated a Korean chat/non-ASCII compatibility issue at the
  model-gateway HTTP boundary.
- Root cause found locally: `HttpJsonModelProvider` sent
  `content-type: application/json` without an explicit charset, and
  `_urllib_transport()` used Python's default `json.dumps()` behavior, escaping
  Korean text as `\u....` sequences before UTF-8 encoding.
- Updated `src/req_tracker/model_gateway/http_provider.py` to send
  `content-type: application/json; charset=utf-8` and serialize HTTP payloads
  with `ensure_ascii=False`.
- RED/GREEN:
  - `uv run pytest tests/unit/model_gateway/test_http_provider_and_registry.py::test_http_json_model_provider_sends_provider_neutral_payload tests/unit/model_gateway/test_http_provider_and_registry.py::test_http_json_transport_preserves_korean_text_as_utf8 -q`
    failed while Korean text was escaped and charset was missing.
  - The focused tests passed after preserving Korean text as UTF-8 bytes.
- Verification:
  - `uv run pytest tests/unit/model_gateway -q`: `17 passed`
  - `uv run pytest tests/unit/model_gateway/test_http_provider_and_registry.py tests/unit/model_gateway/test_dummy_gateway.py tests/unit/ops/test_model_gateway_smoke.py -q`:
    `18 passed`
  - `uv run ruff check src/req_tracker/model_gateway/http_provider.py tests/unit/model_gateway/test_http_provider_and_registry.py`:
    passed
  - `uv run mypy src`: passed
  - GitHub Actions `CI` run `25986199459` for commit `b8cbb20`: passed.
  - Post-fix goal audit:
    `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`
    passed structurally with `goal_complete=false`,
    `remaining_blocker_count=20`, readiness summary `failed=6`,
    `manual_required=10`, `passed=3`, `warning=0`.

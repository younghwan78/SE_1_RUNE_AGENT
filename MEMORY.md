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
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `255 passed, 3 skipped`
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
  local regression gates passed with release-scope and goal-completion audits included;
  overall readiness failed as expected with summary `failed=7`,
  `manual_required=10`, `passed=2`, `warning=0`

Remaining production gap is unchanged:

- Real/company staging evidence is still required for company JIRA/Confluence
  source sync, real model gateway execution, live model quality validation,
  company SSO/OIDC proxy, PostgreSQL, Neo4j, Qdrant, observability,
  backup/restore/load, and approved decision/email export validation.

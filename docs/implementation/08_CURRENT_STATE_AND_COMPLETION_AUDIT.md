# Current State and Completion Audit

Last reviewed: 2026-05-17

This document maps `PRODUCTION_EXECUTION_PLAN.md` requirements to current repo
artifacts and verification evidence. A requirement is complete only when
implementation and a relevant verification path exist in the repository.

## 1. Current Verified Baseline

Latest confirmed implementation and gate commits:

- `735e2e9 Fix final handoff evidence template`
- `c3f9a36 Add staging handoff bundle generator`
- `c52572d Persist scheduler configuration state`
- `19d58a1 Add work queue feedback reason controls`
- `360b68e Trace node and finding LLM stages`
- `e964e3b Block analysis on masking policy violations`
- `9aa1c22 Add architecture verification finding rule`
- `c2004f2 Add improvement decision postgres mirror`
- `6418677 Document dashboard state RBAC`
- `156993e Add dashboard state postgres mirrors`
- `503a123 Persist dashboard work queue state`
- `43f72d0 Refresh readiness audit after Docker gates`
- `4f96977 Classify unavailable Docker readiness gates`
- `67eeb22 Refresh production completion audit`
- `0e438b0 Add relationship graph workbench interactions`
- `9135b84 Add production dashboard workbench`
- `5cb3edb Add local handoff completion gates`
- `edce126 Add project memory snapshot`
- `fee8aad Inject configured source adapters`
- `4c8fafa Cover audit archive idempotency restore`
- `cc0d36b Restore replay idempotency after restart`
- `3e6cb08 Trace replay runs separately`
- `55e3ef2 Record failed run audit state`
- `dd5aff7 Record run start audit events`
- `c8e1020 Block stale approval decisions`
- `ab6dde2 Trace counter evidence in reasoning output`
- `a333a77 Add deterministic approval risk scoring`
- `431c252 Align improvement candidate types`
- `8a54a78 Record replay comparison metadata`
- `8aff68b Refresh audit after docs alignment`
- `c2bac5b Align docs for step debug metadata`
- `5b56a60 Refresh audit after step debug metadata`
- `3984793 Add step validation debug metadata`
- `d44cc70 Validate source integration boundaries`
- `6777c28 Refresh audit after ontology improvement candidate`
- `3f59ab7 Add ontology normalization improvement candidate`
- `71a368f Refresh audit after feedback taxonomy aliases`
- `6fa6a9c Normalize feedback taxonomy aliases`
- `6b94dee Add registry activation rollback`
- `eb224f0 Refresh audit after improvement rollback`
- `a98adde Add controlled improvement rollback`
- `6863fe5 Back off source adapter retries`
- `dee09af Trace model gateway usage metrics`
- `149bb81 Require observability staging evidence`
- `7ac8a0a Refresh audit after observability assets`
- `2e530f3 Add observability deployment assets`
- `405a0bb Require masked restricted model requests`
- `d40bef7 Guard API methods in surface test`
- `e2ed56f Guard debug API surface`
- `91c821c Refresh audit after OpenTelemetry wiring test`
- `ac1c811 Cover enabled OpenTelemetry wiring`
- `eea6429 Add optional OpenTelemetry export foundation`
- `eea6942 Refresh audit after metrics rehearsal gate`
- `c9ca4ff Check metrics in full stack rehearsal`
- `08cd9d2 Propagate request trace context`
- `48f52f0 Add runtime metrics scrape endpoints`
- `e7a7d16 Refresh audit after CI coverage gate`
- `676e783 Validate CI release gate coverage`
- `ab21131 Validate readiness example evidence arrays`
- `72f103a Tighten readiness evidence example validation`
- `e843b48 Reject duplicate readiness evidence checks`
- `81f05c5 Tighten readiness evidence pass validation`
- `6dd7410 Require UTC readiness review timestamps`
- `f3fd0ee Require reviewed readiness evidence metadata`
- `844b52e Link rollback validator to release blockers`
- `fd888a7 Add postgres migration rollback validation gate`
- `f4f70d4 Add postgres typed mirror validation gate`
- `53a2d8c Add readiness evidence example gate`
- `97bd189 Make readiness evidence example non-passable`
- `d0e5eed Reject placeholder readiness evidence`
- `4a4b2a2 Add readiness template CI smoke`
- `16fad95 Add readiness evidence template generation`
- `d45067b Add explicit release gate CI steps`
- `ac42a78 Refresh audit after UI smoke gate`
- `f501294 Add operator UI graph smoke gate`
- `78e65c6 Add release blocker coverage gate`
- `660cb07 Gate kubernetes helm release evidence`
- `f17edfd Add helm chart readiness validation`
- `815d056 Add production helm scaffold`
- `8902254 Add postgres-backed scheduler lease`
- `4a82f90 Add operation state postgres mirrors`
- `2574604 Refresh audit after API surface guard`
- `54d2db6 Add production API surface guard`
- `aa5baaa Add project graph list read APIs`
- `e9f5340 Add gated registry activation APIs`
- `3fe398c Add deterministic ingest run API`
- `21ab111 Add finding detail and status APIs`
- `da832cb Cover remaining command idempotency`
- `c6901da Extend command API idempotency`
- `d7bb8fa Add analyze command idempotency`
- `c573f50 Record run trigger lineage`
- `459d8a5 Retry source network OS errors`
- `06ccd08 Tighten run debug RBAC`
- `512f7d7 Persist replay diff results`
- `83a8faf Add run listing API`
- `1c7a00f Record analysis input snapshot ids`
- `f4ab129 Trace dummy LLM reasoning in workflow`
- `2903f73 Add explicit debug API endpoints`
- `f369177 Add default model registry baseline`
- `22d7343 Add structured request logging`
- `5a66365 Anchor production repo shape docs`
- `93d96f0 Refresh audit after masking rehearsal`
- `f93b973 Add masking policy rehearsal gate`
- `7992fc5 Tighten production readiness pass gate`
- `133c2ad Refresh audit after decision email rehearsal`
- `d2e83fe Add decision email export rehearsal`
- `92368ca Add backup set verifier`
- `6d5cce8 Add trusted proxy rehearsal runner`
- `c499394 Add model gateway rehearsal runner`
- `8b80d0f Add company source rehearsal runner`
- `91b1d1e Add load smoke to full stack rehearsal`
- `d73849b Support production readiness evidence files`
- `a65315e Add production readiness gate checker`
- `b6c06c4 Refresh audit after feedback RBAC`
- `11a19e6 Protect feedback improvement endpoints`
- `03d266d Refresh audit after approval RBAC`
- `3e9a713 Protect approval decisions with RBAC`
- `426a67d Add runtime readiness endpoint`
- `a27c177 Refresh audit after runtime restore`
- `1349a9d Restore runtime state after restart`
- `dd10388 Refresh audit after eval canary rehearsal`
- `daff157 Add feedback eval canary rehearsal`
- `465080b Refresh audit after full stack rehearsal`
- `80e4369 Add full stack rehearsal runner`
- `0d2bbc5 Add source adapter smoke harness`
- `11da7f0 Add disposable backend integration runner`
- `8a61830 Add trusted proxy auth foundation`
- `56d4983 Refresh audit after model gateway smoke`
- `7d8bca8 Add local model gateway smoke harness`
- `4f11a09 Refresh audit after PostgreSQL archive pruning`
- `db72fdb Add PostgreSQL audit archive pruning`
- `7a0e019 Refresh audit after security hardening`
- `03c8a0a Add audit archive prune foundation`
- `a887e7b Add API key project authorization foundation`
- `ea62ffd Restrict decision email export scope`
- `10ba461 Refresh audit after operations assets`
- `204983f Add operations backup and load rehearsal assets`

Latest local verification:

- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: 263 passed, 3 skipped
- `uv run pytest tests/unit/model_gateway -q`: 16 passed, validating dummy
  provider calls, policy enforcement, structured validation retry, fallback
  trace recording, provider usage metadata, and same-input model/prompt
  comparison diff reporting
- `uv run pytest tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_debug_api.py tests/contract/test_run_api.py tests/contract/test_persistence_api.py tests/contract/test_replay_feedback_api.py -q`:
  33 passed, validating vector-backed edge retrieval context artifacts,
  debug step references, persistence restore, replay, and run contracts
- `uv run pytest tests/contract/test_health_api.py::test_metrics_summary_reports_http_and_runtime_counts tests/unit/model_gateway tests/contract/test_debug_api.py tests/contract/test_replay_feedback_api.py tests/contract/test_persistence_api.py tests/integration/test_dummy_analysis_pipeline.py -q`:
  40 passed, validating three traceable local LLM stages
  (`pv_node_extraction_v1`, `pv_edge_linking_v1`,
  `pv_finding_reasoning_v1`), model gateway debug artifact namespacing, debug
  API, replay diff metadata, persistence restore, integration workflow, and
  metrics summary counts
- `uv run pytest tests/unit/ingestion/test_masking_chunking.py tests/integration/test_dummy_analysis_pipeline.py tests/unit/api/test_runtime_state.py tests/contract/test_run_api.py tests/unit/debug/test_trace_recorder.py -q`:
  20 passed, validating masking, workflow-level masking violation block,
  runtime failed-run persistence, run API behavior, and trace failure metadata
- `uv run pytest tests/unit/findings/test_rules.py tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py -q`:
  17 passed, validating deterministic finding rules, dummy workflow routing,
  dashboard summaries, and work-queue ordering after the architecture
  verification-path rule
- `uv run pytest tests/unit/adapters/test_jira_rest_adapter.py -q`:
  6 passed, validating JIRA REST pagination/retry/permission handling, link
  extraction, comment metadata preservation, and changelog history metadata
  preservation
- `uv run pytest tests/unit/findings/test_rules.py tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_dashboard_api.py::test_dashboard_summary_after_compact_analysis -q`:
  6 passed, validating deterministic Confluence stale trace and
  issue-affects-critical-requirement rules plus compact dashboard blocked-health
  projection
- `uv run pytest tests/unit/adapters/test_confluence_rest_adapter.py::test_confluence_rest_adapter_preserves_previous_version_metadata tests/unit/findings/test_rules.py::test_confluence_version_change_creates_stale_trace_finding tests/integration/test_dummy_analysis_pipeline.py::test_confluence_version_change_is_routed_to_stale_finding -q`:
  3 passed, validating Confluence previous-version metadata preservation,
  deterministic stale trace finding generation, and workflow routing into the
  finding stage
- `uv run pytest tests/unit/adapters/test_export_file_adapter.py tests/unit/ops/test_decision_email_rehearsal.py -q`:
  8 passed, validating restricted decision/email export scope, email thread
  metadata masking, sensitive-thread manual-review routing, and rehearsal
  `manual_review_count`
- `uv run pytest tests/unit/ops/test_skill_export_rehearsal.py tests/unit/ops/test_production_readiness_check.py`:
  21 passed, validating source-skill export dry-run and readiness gate coverage
- `uv run pytest tests/contract/test_backend_settings_api.py tests/contract/test_health_api.py tests/contract/test_run_api.py tests/contract/test_debug_api.py tests/contract/test_persistence_api.py`:
  33 passed, validating datasource factory settings, skill/export adapter
  workflow injection, dummy defaults, debug cursor exposure, and persistence
- `uv run pytest tests/contract/test_debug_api.py tests/contract/test_security_api.py tests/contract/test_openapi_surface.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py tests/unit/storage/test_postgres_store.py tests/contract/test_models.py`:
  44 passed, validating source sync cursor contracts, persistence, debug API
  access, project filtering, and OpenAPI registration
- `uv run pytest tests/contract/test_audit_api.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py`:
  15 passed, validating run-start audit capture, analysis/ingestion run audit
  metadata, and SQLite restore of audit events
- `uv run pytest tests/contract/test_replay_feedback_api.py tests/contract/test_persistence_api.py tests/contract/test_audit_api.py`:
  14 passed, validating replay run type, replay audit boundary events,
  restart-safe replay run trace lookup, and replay trace persistence without
  overwriting reviewed findings
- `uv run pytest tests/contract/test_persistence_api.py tests/contract/test_replay_feedback_api.py tests/contract/test_security_api.py`:
  20 passed, validating replay idempotency response restore after restart,
  conflict detection after restart, protected replay access, and replay
  persistence contracts
- `uv run pytest tests/contract/test_persistence_api.py tests/contract/test_audit_api.py`:
  8 passed, validating audit archive/prune idempotency response restore after
  restart and duplicate audit-archive event prevention
- `uv run pytest tests/unit/api/test_runtime_state.py tests/unit/debug/test_trace_recorder.py tests/contract/test_audit_api.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py`:
  20 passed, validating immediate run-start audit persistence, failed run
  state, failed completion audit events, and failure audit persistence
- repo-shape anchor check for `.claude/skills`, `docs/api`, `docs/ontology`,
  `docs/security/DATA_POLICY.md`, `docs/security/RBAC_MATRIX.md`,
  `docs/runbooks/BACKUP_RESTORE.md`, `docs/runbooks/MODEL_POLICY.md`,
  `docs/runbooks/INCIDENT_RESPONSE.md`, `ops/migrations`, `ops/helm`,
  `tests/evals`, `tests/security`, and `tests/replay`: passed
- `uv run python ops/integration/run_backend_integration.py`: 3 passed
- `uv run python ops/source/smoke_source_adapters.py`: passed
- `uv run python ops/source/rehearse_skill_export_sources.py`: passed,
  validating `jira_export`, `confluence_export`, and `decision_email_export`
  through the API workflow and persisted source cursor debug state without
  company endpoints, tokens, MCP tools, or mailbox data
- `uv run python ops/source/rehearse_company_sources.py`: failed as expected on this local shell because JIRA/Confluence sandbox env vars are unset; output masks tokens and lists missing config
- `uv run python ops/source/rehearse_decision_email_export.py`: failed as expected on this local shell because `RUNE_EMAIL_EXPORT_PATH` is unset; output masks path state and lists missing config
- `uv run python ops/model_gateway/smoke_model_gateway.py`: passed
- `uv run python ops/ui/smoke_operator_ui.py`: passed, validating dashboard-first static UI assets, dashboard summary/work-queue/source-health read models, graph controls, SVG renderer hooks, and `RUNE_SCALE_150` projection modes with 150 total nodes, 120 visible overview nodes, 103 pending edges, 103 approval work items, 48 finding work items, and 9 orphan nodes
- `uv run python ops/observability/validate_observability_assets.py`: passed, validating Prometheus scrape config, alert rules, Grafana dashboard JSON, required runtime metric references, and absence of hardcoded observability credentials
- `uv run python ops/model_gateway/rehearse_model_gateway.py`: failed as expected on this local shell because `MODEL_GATEWAY_ENDPOINT_URL` is unset; output masks API key state and lists missing config
- `uv run python ops/security/rehearse_trusted_proxy_auth.py`: failed as expected on this local shell because `RUNE_API_BASE_URL` and `TRUSTED_PROXY_SECRET` are unset; output masks secret state and lists missing config
- `uv run python ops/security/rehearse_masking_policy.py`: passed, verifying representative sensitive inputs are redacted without printing raw sensitive strings or forbidden patterns
- `uv run python ops/security/check_release_blockers.py`: passed, validating coverage evidence for masking violations, approval-gated graph mutation, project authorization leaks, prompt/model regression and rollback gates, migration rollback/restore, and forbidden model payload policy
- `uv run python ops/source/validate_source_boundaries.py`: passed, validating that MCP configuration/tool names do not leak into core app code and source adapters do not contain JIRA/Confluence/Email write-back methods
- `uv run pytest tests/unit/ops/test_backup_verify.py`: passed, validating backup-set required files, SHA256 mismatch detection, artifact tar, Qdrant JSON, Neo4j dump marker, and git commit marker checks
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed,
  including API restart restore, `audit_total_events=3`, metrics surface check
  (`http_total_requests=7`, `graph_nodes=14`, `llm_calls=3`), and smoke-load
  pass (`load_smoke.p95_ms` about 2525 ms against a 5000 ms local rehearsal
  threshold)
- `uv run python ops/evals/run_feedback_eval_rehearsal.py`: passed, including review-ready, canary, active, rollback, and security-blocked eval paths
- `uv run python ops/rehearsal/check_production_readiness.py`: failed as expected on this local shell because production env/company-staging endpoints are unset; report produced failed env checks and manual-required gates without secret values
- `uv run python ops/rehearsal/check_production_readiness.py --write-evidence-template -`: passed, producing a review-safe unresolved-gate evidence template with `failed` TODO placeholders
- `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`: passed, validating 24 created PostgreSQL tables have matching rollback drops across 10 migration versions
- `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed, validating 21 PostgreSQL typed mirror tables against packaged migration DDL
- `uv run python ops/rehearsal/validate_evidence_example.py`: passed, validating that the committed example evidence file has 11 non-passable manual gates, matches the current manual gate list from `build_manual_evidence_template({})`, and has no passable placeholder entries, fake `run-123*` references, duplicate check IDs, missing evidence arrays, or missing top-level TODO metadata
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with `ci_command_count=33`, validating that GitHub Actions covers deterministic local release gates and only omits the documented Docker-backed integration/full-stack rehearsals
- `uv run python ops/rehearsal/validate_release_scope_artifacts.py`: passed with `release_ready=false`, `missing_artifacts=0`, `audit_coverage_missing=0`, status counts `local_complete=11`, `company_evidence_required=4`, and `plan_requirements` aligned to `PRODUCTION_EXECUTION_PLAN.md` first-release required-scope bullets
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete`: passed, reporting `goal_complete=false`, `remaining_blocker_count=22`, `release_scope_passed=true`, `release_scope_ready=false`, and `production_readiness_passed=false`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --evidence-file ops/rehearsal/production_readiness_evidence.example.json`: passed, reporting `goal_complete=false` while applying 11 example manual-evidence entries that remain failed TODO placeholders by design
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --run-local-gates`: passed structurally after Docker Desktop Linux engine became available, reporting `goal_complete=false`, `remaining_blocker_count=21`, `prompt_to_artifact_checklist_count=6`, and local regression gates passed; remaining blockers require company/staging environment configuration and reviewed manual evidence
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness failed as expected because company/staging environment variables and manual evidence are unset
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown`: passed, producing a masked command/evidence collection plan for unresolved company/staging gates without printing secret values
- `uv run pytest tests/unit/ops/test_handoff_bundle.py -q`: 3 passed, validating one-command handoff bundle generation, manifest contents, reviewed evidence file input, incomplete smoke exit behavior, and absence of env secret leakage in generated artifacts
- `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file .env.example --output-dir .local_artifacts/handoff-bundle`: passed, generating `manifest.json`, `staging-evidence-plan.md`, `manual-evidence-template.json`, `production-readiness-report.json`, and `goal-completion-report.json` for staging review; reports remain incomplete until real company/staging evidence is supplied
- `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py -q`: 4 passed, validating generated bundle acceptance, missing artifact rejection, manifest/report summary drift rejection, and missing manual-template gate rejection
- `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/handoff-bundle`: passed, validating required artifact presence, JSON parse/schema, manifest/report consistency, manual-evidence-template coverage for all `manual_required` readiness gates, and staging evidence plan heading
- `uv run pytest tests/unit/ops/test_runbook_docs.py -q`: 2 passed, validating incident response runbook coverage and Ubuntu handoff bundle workflow documentation
- `ops/rehearsal/check_production_readiness.py --run-local-gates` now includes the same handoff bundle smoke and validation commands for both `.env.example` and `ops/rehearsal/staging.env.example`, so release-style local gate runs and GitHub Actions exercise the same handoff artifact generator and verifier
- `uv run pytest`: 272 passed, 3 skipped after staging env template coverage was added
- `uv run python ops/rehearsal/check_production_readiness.py --env-file ops/rehearsal/staging.env.example --write-evidence-template -`: passed, validating staging template parsing and review-safe evidence template generation
- `uv run python ops/rehearsal/build_handoff_bundle.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --output-dir .local_artifacts/staging-handoff-bundle` plus `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`: passed, validating staging-template bundle generation and bundle integrity checks
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`: passed structurally with `goal_complete=false`, `remaining_blocker_count=20`, `prompt_to_artifact_checklist_count=6`, and readiness summary `failed=6`, `manual_required=10`, `passed=3`, `warning=0`; local gates pass, local-gate evidence includes the handoff bundle smoke and validation commands, and remaining blockers require real company/staging evidence
- GitHub Actions `CI` run `25979725389` for commit `c3f9a36`: success, including `Handoff bundle env-file smoke`
- `uv run pytest tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q`: passed after first verifying the new staging evidence plan CI smoke requirement failed when absent
- `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q`: passed after first verifying `LOCAL_GATE_COMMANDS` did not include the staging evidence plan smoke
- `uv run python ops/rehearsal/check_production_readiness.py --evidence-file ops/rehearsal/production_readiness_evidence.example.json`: failed as expected because the committed example evidence uses `failed` TODO placeholders and production env checks are unset; fake `run-123*` and `status: passed` examples are not present in the committed template
- `uv run pytest tests/unit/ops/test_production_readiness_check.py`: 20 passed, including manual evidence file loading, duplicate check-id rejection, TODO-placeholder rejection for passed evidence, reviewer metadata enforcement for passed evidence, schema-version and non-empty evidence enforcement for passed evidence, ISO-8601 UTC `reviewed_at` enforcement, failed TODO template loading, non-passable example evidence, review-safe evidence template generation, complete env/evidence pass behavior, unknown evidence warning blocking, Kubernetes Helm evidence gating, and Docker-unavailable local gate classification
- `uv run pytest tests/unit/ops/test_readiness_evidence_example.py -q`: 6 passed, including committed example evidence drift detection against the current manual production-readiness gate list
- `uv run pytest`: 273 passed, 3 skipped after adding the readiness evidence example drift guard
- `uv run pytest`: 274 passed, 3 skipped after adding handoff manifest remaining-blocker summary and validator drift checks
- `uv run pytest`: 275 passed, 3 skipped after fixing final reviewed-evidence handoff bundles so stale manual-evidence TODO gates are not emitted after reviewed evidence has resolved them
- `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`: 6 passed after adding a documentation-reference guard that verifies every staging evidence plan doc reference points to an existing Markdown file and, when a fragment is present, an existing heading anchor
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`: passed after adding the `README_ubuntu.md#production-readiness` anchor used by company/staging evidence guidance
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`: passed structurally after the staging evidence plan doc-reference guard, reporting `goal_complete=false`, `remaining_blocker_count=20`, and readiness summary `failed=6`, `manual_required=10`, `passed=3`, `warning=0`
- `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`: 7 passed after adding `final_validation_commands` to the staging evidence plan and rendering the `## Final Validation` Markdown section with readiness, goal-completion, handoff-bundle, and bundle-validation commands
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file ops/rehearsal/staging.env.example --format markdown`: passed after the final validation command sequence was added to the company/staging evidence guidance
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`: passed structurally after the staging evidence final-validation command addition, reporting `goal_complete=false`, `remaining_blocker_count=20`, and readiness summary `failed=6`, `manual_required=10`, `passed=3`, `warning=0`
- `uv run pytest tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_staging_evidence_plan.py -q`: 17 passed after strengthening the handoff bundle validator to reject a stale `staging-evidence-plan.md` that omits the `## Final Validation` section or final validation command references
- `uv run python ops/rehearsal/validate_handoff_bundle.py .local_artifacts/staging-handoff-bundle`: passed after the final validation section guard was added
- `uv run pytest tests/unit/ops/test_production_readiness_check.py tests/unit/ops/test_handoff_bundle_validator.py tests/unit/ops/test_handoff_bundle.py tests/unit/ops/test_readiness_evidence_example.py -q`: 41 passed after strengthening file-loaded passed manual evidence to require at least one traceable reference such as `artifact:`, `github-actions:`, `staging-ci:`, `run:`, or `approval:`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file ops/rehearsal/staging.env.example --run-local-gates`: passed structurally after the traceable manual-evidence reference guard, reporting `goal_complete=false`, `remaining_blocker_count=20`, and readiness summary `failed=6`, `manual_required=10`, `passed=3`, `warning=0`
- GitHub Actions JavaScript actions were updated to Node 24-backed tags:
  `actions/checkout@v6` and `actions/setup-python@v6`; the temporary
  `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` compatibility env was removed
- `.env.example` now includes company/staging rehearsal variables for
  PostgreSQL, Neo4j, Qdrant, model gateway, trusted proxy, observability, JIRA,
  Confluence, and restricted decision/email export handoff
- `ops/rehearsal/staging.env.example` now provides a staging/release rehearsal
  env template with production-oriented modes, empty endpoint/secret values,
  `DEPLOYMENT_TARGET=ubuntu`, and `KUBERNETES_DEPLOYMENT=false`
- `uv run pytest tests/unit/config/test_env_example.py -q`: 2 passed,
  validating `.env.example` production-readiness key coverage and
  `staging.env.example` production-mode/no-fake-secret/Ubuntu-target behavior
- `ops/rehearsal/check_production_readiness.py` and
  `ops/rehearsal/check_goal_completion.py` accept `--env-file` so release owners
  can load a secure KEY=VALUE staging env file together with reviewed evidence
  without printing secret values
- `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_load_env_file_merges_staging_values_without_printing_secrets tests/unit/ops/test_production_readiness_check.py::test_load_env_file_rejects_invalid_lines -q`: 2 passed
- `ops/rehearsal/build_staging_evidence_plan.py` accepts `--env-file` so the
  collection plan can be generated from the same secure staging env file as the
  readiness and goal-completion audits
- `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`: 5 passed
- `uv run python ops/rehearsal/build_staging_evidence_plan.py --env-file .env.example --format markdown`: passed, reporting `Unresolved gates: 17` and summary `failed=6`, `manual_required=11`, `passed=2`, `warning=0`
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example`: passed structurally with `goal_complete=false`, validating the env-file audit input path
- `uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete --env-file .env.example --run-local-gates`: passed structurally with `goal_complete=false`, `remaining_blocker_count=20`, `prompt_to_artifact_checklist_count=6`, and readiness summary `failed=6`, `manual_required=10`, `passed=3`, `warning=0`
- GitHub Actions `CI` now includes env-file smoke gates for readiness evidence template generation, staging env-template parsing, staging evidence plan generation, goal-completion audit, handoff bundle generation, and handoff bundle validation for both `.env.example` and `ops/rehearsal/staging.env.example`; `uv run python ops/rehearsal/validate_ci_gate_coverage.py` passed with `ci_command_count=33`
- `check_goal_completion.py` now resolves `company_evidence_required` release-scope items through mapped production-readiness checks, preserving local `release_ready=false` while allowing reviewed company/staging evidence to drive `release_scope_goal_ready=true` and ultimately `goal_complete=true`
- `uv run pytest tests/unit/ops/test_goal_completion_audit.py -q`: 5 passed, including complete reviewed-evidence goal-completion coverage
- `ops/rehearsal/check_production_readiness.py` and
  `ops/rehearsal/check_goal_completion.py` accept `--output` to persist JSON
  readiness and goal-completion report artifacts for staging review/retention
- `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_write_json_output_writes_report_artifact -q`: 1 passed
- `uv run pytest tests/unit/ops/test_helm_chart.py`: 4 passed, validating chart artifact presence, production environment mapping, secret references, no hardcoded secret/MCP transport names, and local chart validator behavior
- `uv run python ops/helm/validate_chart.py`: passed, validating required Helm chart files, production env defaults, secret references, and forbidden snippets without requiring a local Helm binary
- `helm version --short`: not available in this local shell; run `helm lint` and `helm template` in the target Kubernetes environment

Latest implementation GitHub Actions verification:

- GitHub Actions `CI` run `25980477607` for implementation commit `5cc4c20`
  (`Guard readiness evidence example against gate drift`): completed
  successfully
- GitHub Actions `CI` run `25980385129` for handoff commit `6ed3640`
  (`Set Ubuntu target in staging env template`): completed successfully
- GitHub Actions `CI` run `25980248459` for handoff commit `4822e2c`
  (`Add staging readiness env template`): completed successfully
- GitHub Actions `CI` run `25969313834` for implementation commit `f16b991`
  (`Accept manual evidence in goal audit`): completed successfully
- GitHub Actions `CI` run `25968150339` for documentation commit `ee3dea2`
  (`docs/api/README.md` scheduler persistence update): completed successfully
- GitHub Actions `CI` run `25968077139` for handoff commit `4934186`:
  completed successfully
- GitHub Actions `CI` run `25967994338` for implementation commit `c52572d`:
  completed successfully
- GitHub Actions `CI` run `25967835241` for implementation commit `19d58a1`:
  completed successfully
- GitHub Actions `CI` run `25967338344` for implementation commit `360b68e`: completed
  successfully
- GitHub Actions `CI` run `25967125938` for `e964e3b`: completed successfully
- GitHub Actions `CI` run `25966865346` for `9aa1c22`: completed successfully

## 2. Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Production plan is the source of truth | `PRODUCTION_EXECUTION_PLAN.md`, `docs/implementation/03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md` | Complete |
| Expected repository shape is anchored | `src/req_tracker/*`, `.claude/skills/rune-source-*`, `docs/api/README.md`, `docs/ontology/ONTOLOGY_V1.md`, `ops/migrations/README.md`, `ops/helm/README.md`, `tests/evals/README.md`, `tests/security/README.md`, `tests/replay/README.md`, `MEMORY.md` | Complete for implemented and deferred tracks |
| Ontology v1 is documented and executable | `docs/ontology/ONTOLOGY_V1.md`, `src/req_tracker/ontology/models.py`, `tests/contract/test_models.py` | Complete |
| API documentation path exists | `docs/api/README.md`, `src/req_tracker/api/routes/*`, `tests/contract/*`, `tests/contract/test_openapi_surface.py`, method/path OpenAPI guard, `/api/v1/projects`, `/api/v1/graph/nodes`, `/api/v1/graph/edges`, `/api/v1/runs/ingest`, `/api/v1/runs/analyze`, `/api/v1/runs`, `/api/v1/runs/{run_id}/steps`, `/api/v1/runs/{run_id}/llm-calls`, `/api/v1/runs/{run_id}/artifacts`, `/api/v1/runs/{run_id}/graph-delta`, `/api/v1/runs/{run_id}/replay`, `/api/v1/replays/{replay_id}/diff`, `/api/v1/debug/source-cursors`, `/api/v1/debug/approvals/{approval_id}/lineage`, `/api/v1/findings/{finding_id}`, `/api/v1/findings/{finding_id}/status`, `/api/v1/improvements/{candidate_id}/rollback`, `/api/v1/admin/model-profiles/{id}/activate`, `/api/v1/admin/model-profiles/{id}/rollback`, `/api/v1/admin/prompt-versions/{id}/activate`, `/api/v1/admin/prompt-versions/{id}/rollback`, optional `/openapi.json` with `ENABLE_DOCS=true` | Complete |
| Data and model policies are fixed | `docs/security/DATA_POLICY.md`, `docs/runbooks/MODEL_POLICY.md`, `config/model_profiles.json`, `config/prompt_versions.json`, `src/req_tracker/model_gateway/models.py`, `src/req_tracker/model_gateway/policy.py`, `src/req_tracker/api/routes/admin.py`, `ops/security/rehearse_masking_policy.py`, `ops/model_gateway/smoke_model_gateway.py` | Complete for local policy baseline, restricted/confidential `masking_applied` and `access_checked` enforcement, workflow-level masking violation block with security-review debug reference, gated activation records, and registry activation rollback records; company model profile approval pending |
| Release blocker coverage | `ops/security/check_release_blockers.py`, `ops/security/rehearse_masking_policy.py`, `tests/integration/test_dummy_analysis_pipeline.py`, `tests/contract/test_security_api.py`, `tests/contract/test_admin_registry_api.py`, `tests/contract/test_replay_feedback_api.py`, `tests/unit/storage/test_postgres_store.py`, `ops/rehearsal/validate_postgres_migration_rollbacks.py`, `tests/unit/model_gateway/test_dummy_gateway.py` | Local release-blocker evidence manifest complete, including workflow-level masking violation blocking, explicit migration rollback coverage validation, and restricted model payload masking/access policy tests; company/staging evidence still required for real endpoints |
| Structured request logging, trace context, and OpenTelemetry export foundation | `src/req_tracker/config/logging.py`, `src/req_tracker/api/app.py`, `src/req_tracker/observability/tracing.py`, `src/req_tracker/observability/otel.py`, `tests/contract/test_health_api.py`, `tests/unit/config/test_logging.py`, `tests/unit/observability/test_tracing.py`, `tests/unit/observability/test_otel.py` | Complete for JSON request logs with correlation id, W3C trace id, span id, user id, method, path, status, duration, `traceparent` response propagation, optional OTLP FastAPI span export, disabled/missing-endpoint safeguards, and enabled-path exporter/instrumentor wiring tests |
| Runtime metrics and scrape surface | `src/req_tracker/observability/metrics.py`, `src/req_tracker/api/routes/health.py`, `/api/v1/metrics`, `/api/v1/metrics/summary`, `ops/observability/prometheus.yml`, `ops/observability/rune-agent-alerts.yml`, `ops/observability/grafana-dashboard.json`, `ops/observability/validate_observability_assets.py`, `ops/rehearsal/run_full_stack_rehearsal.py`, `tests/contract/test_health_api.py`, `tests/unit/observability/test_metrics.py`, `tests/unit/ops/test_full_stack_rehearsal.py`, `tests/unit/ops/test_observability_assets.py` | Complete for in-process HTTP/runtime/LLM/graph/approval/finding/feedback/audit/scheduler counters, LLM token/cost gauges, Prometheus text exposition, packaged Prometheus scrape/alert starter assets, Grafana dashboard JSON, asset validation gate, readiness manual evidence gate, and disposable full-stack metrics rehearsal; company collector and dashboard import remain target-environment tasks |
| Claude Code source-skill boundary for JIRA/Confluence/Email | `.claude/skills/rune-source-*`, `JiraRestSourceAdapter`, `ConfluenceRestSourceAdapter`, datasource factory, workflow source-adapter injection, `request_with_retry`, `ops/source/smoke_source_adapters.py`, `ops/source/rehearse_skill_export_sources.py`, `ops/source/validate_source_boundaries.py`, `ops/source/rehearse_company_sources.py`, `ops/source/rehearse_decision_email_export.py`, export adapters, restricted decision/email export policy, `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` | Design/export path complete; DATASOURCE_MODE can select dummy, skill/export, JIRA REST, and Confluence REST adapters without MCP leakage into core code; synthetic source-skill export dry-run validates JIRA/Confluence/decision-email export workflow injection and cursor debugging; JIRA/Confluence REST retry with `Retry-After` and bounded exponential backoff, network `OSError` retry, pagination, permission-warning, issue link extraction, comment/changelog metadata preservation, section-path/table-cell metadata extraction, previous-version metadata preservation for stale trace rules, MCP/core boundary validation, local HTTP smoke validation, env-driven company sandbox rehearsal entrypoint, and restricted decision/email export rehearsal entrypoint with approved decision scope, sensitive-thread manual-review routing, and email thread metadata masking complete; Email live access and real company sandbox validation pending |
| Dummy/local validation path | `LocalAnalysisWorkflow`, dummy fixtures, API tests, integration test, readiness API, persisted runtime restore test, `ops/security/rehearse_masking_policy.py` | Complete, including masking policy violation analysis block before graph extraction or LLM reasoning |
| Core contracts | `src/req_tracker/ontology`, `src/req_tracker/adapters/base.py`, `debug`, `approvals`, `feedback`, `audit` models | Complete |
| Source snapshot lineage | `AgentRun.input_snapshot_ids`, normalized `SourceArtifact.artifact_id`, `SourceSyncCursorState`, `source_sync_cursors`, source-fetch step cursor metadata, datasource factory, skill/export ingestion contract test, `LocalAnalysisWorkflow` metadata update, run/debug API and integration tests | Complete for local/source-artifact snapshot lineage, configured source-adapter injection, and persisted source cursor snapshots |
| Run trigger lineage | `AgentRun.triggered_by`, `AgentRun.trigger_source`, API analyze path, schedule run-now path, periodic scheduler path, replay path, contract tests | Complete for local API/manual/schedule/replay trigger attribution |
| Agent workflow orchestration | `LocalAnalysisWorkflow`, stable public stage names, `AgentStepTrace`, `LLMCallTrace`, `docs/implementation/01_MODULE_DESIGN.md` LangGraph transition note | Complete for local/dummy workflow contract validation; LangGraph remains a later orchestration swap after production dependency and branching needs justify it |
| Command idempotency | `POST /api/v1/runs/ingest`, `POST /api/v1/runs/analyze`, `POST /api/v1/runs/{run_id}/replay`, `PUT /api/v1/schedule`, `POST /api/v1/schedule/run-now`, `POST /api/v1/approvals/{approval_id}/decision`, `POST /api/v1/findings/{finding_id}/status`, `POST /api/v1/feedback`, `POST /api/v1/improvements/{candidate_id}/activate`, `POST /api/v1/improvements/{candidate_id}/rollback`, `POST /api/v1/admin/model-profiles/{id}/activate`, `POST /api/v1/admin/model-profiles/{id}/rollback`, `POST /api/v1/admin/prompt-versions/{id}/activate`, `POST /api/v1/admin/prompt-versions/{id}/rollback`, and `POST /api/v1/audit/retention/archive-prune` `Idempotency-Key`/`X-Idempotency-Key`, persisted `idempotency_results`, API conflict tests, SQLite restart restore tests for analyze, replay, and audit archive/prune responses, graph commit idempotency keys | Complete for implemented local command APIs plus graph commit paths |
| Model gateway abstraction | `src/req_tracker/model_gateway` with dummy provider, HTTP JSON provider, provider factory, file-backed registry, policy, structured validation retry, fallback trace tests, same-input model/prompt comparison helper, restricted/confidential masking and access-check gates, provider usage metadata extraction, token/cost trace propagation, `ops/model_gateway/smoke_model_gateway.py`, `ops/model_gateway/rehearse_model_gateway.py` | Profile/registry/live-shaped HTTP foundation, same-input dummy model/prompt diff report, env-driven company sandbox rehearsal entrypoint, and provider-reported token/cost observability complete; real external provider sandbox validation pending |
| LLM-assisted workflow trace | `LocalAnalysisWorkflow` node extraction, vector-backed edge retrieval context artifact, `llm_assisted_reasoning`, and finding reasoning trace calls, `ModelGatewayClient`, structured reasoning output with confidence and counter-evidence refs, `LLMCallTrace`, step-level `retrieval_context_ref`/`validation_status`/`validation_result`, SQLite restore of `llm_call_traces` and step validation metadata, `/api/v1/runs/{run_id}/llm-calls`, debug diff LLM panes | Dummy model-gateway integration complete for `pv_node_extraction_v1`, `pv_edge_linking_v1`, and `pv_finding_reasoning_v1`; edge-linking LLM payload now includes retrieved chunk context from the configured vector backend; live model quality validation pending |
| Debug trace and local artifact store | `src/req_tracker/debug`, `/api/v1/debug/*`, `/api/v1/debug/source-cursors`, `/api/v1/runs/{run_id}/steps`, `/api/v1/runs/{run_id}/llm-calls`, `/api/v1/runs/{run_id}/artifacts`, `/api/v1/runs/{run_id}/graph-delta`, `/api/v1/replays/{replay_id}/diff`, restart-safe `replay_results`, replay `AgentRun`/step/LLM trace persistence, compared replay model/prompt metadata, approval lineage API, run diff-view API, run debug UI, LLM/graph delta side-by-side panes | Local debug workbench foundation complete with persisted retrieval/validation metadata on agent steps, source sync cursor snapshots, replay run type, replay audit boundaries, replay comparison version metadata, and typed PostgreSQL mirrors for LLM call traces and replay results; live LLM payload validation pending |
| SQLite state persistence | `SQLiteStateStore`, persistence contract test, restart restore contract test, restart restore of `source_sync_cursors` | Complete |
| PostgreSQL migration foundation | `PostgreSQLStateStore`, `001_state_entities.sql`, `003_audit_archive_batches.sql`, `004_operation_state_tables.sql`, `005_scheduler_leases.sql`, `007_source_cursor_state_tables.sql`, `008_debug_replay_state_tables.sql`, `009_improvement_decision_state_tables.sql`, `010_schedule_config_state_tables.sql`, migration loader tests, rollback scripts, `ops/rehearsal/validate_postgres_migration_rollbacks.py` | Complete with migration-to-rollback coverage validation |
| Typed PostgreSQL core and operation-state table foundation | `002_core_state_tables.sql`, `004_operation_state_tables.sql`, `006_dashboard_state_tables.sql`, `007_source_cursor_state_tables.sql`, `008_debug_replay_state_tables.sql`, `009_improvement_decision_state_tables.sql`, `010_schedule_config_state_tables.sql`, typed mirror upsert/read dispatch for core state, source sync cursors, LLM call traces, replay results, improvement decisions, idempotency results, registry activations, dashboard preferences, dashboard assignments, and schedule configs, rollback scripts, unit tests, optional `POSTGRES_TEST_DSN` integration test, `ops/integration/run_backend_integration.py`, `ops/rehearsal/validate_postgres_typed_mirrors.py` | Foundation complete with spec-to-DDL drift validation; disposable Docker PostgreSQL integration passed; company/staging DB rehearsal pending |
| Graph backend | `GraphBackend` protocol, `MemoryGraphBackend`, `Neo4jGraphBackend`, graph projection, traceability chain APIs, optional `NEO4J_TEST_*` integration test, Docker integration runner | Neo4j foundation complete; disposable Docker Neo4j integration passed; company/staging graph rehearsal pending |
| Vector backend | `VectorBackend` protocol, `MemoryVectorBackend`, `QdrantVectorBackend`, optional `QDRANT_TEST_URL` integration test, Docker integration runner | Qdrant foundation complete; disposable Docker Qdrant integration passed; company/staging vector rehearsal pending |
| Approval workflow | approval queue, deterministic confidence/relation-based risk routing in `src/req_tracker/reasoning/scoring.py`, approve/reject/hold/modify path, expected-version/proposal-hash stale approval guard with blocked audit outcome, graph commit, developer/operator RBAC and project-scope checks | Complete for local and protected API paths |
| Deterministic traceability rules | `src/req_tracker/findings/rules.py`, source metadata routed into `LocalAnalysisWorkflow`, `tests/unit/findings/test_rules.py`, compact/dashboard contract tests | Complete for requirement without implementation, requirement without verification, design without parent requirement, conflicting alternatives, Confluence page version stale trace, issue affecting critical requirement, and architecture without verification path; company data calibration still pending |
| Feedback loop | feedback events, command-style feedback action/reason aliases normalized to canonical taxonomy, work queue approval reason-code controls, eval candidates, improvement candidates including few-shot-example and ontology-normalization candidate contracts, ontology-normalization candidates for wrong-node-type feedback, eval gate, controlled review/canary promotion, canary/active rollback, persisted and PostgreSQL-typed improvement decisions, feedback/eval/improvement RBAC, `ops/evals/run_feedback_eval_rehearsal.py` | Local feedback/eval/canary/rollback rehearsal complete with UI reason-code selection for approval reject/hold/approve decisions; real production feedback calibration pending |
| Audit trail | `AuditService`, `/api/v1/audit/events`, `/api/v1/audit/retention`, `/api/v1/audit/retention/archive-prune`, local JSONL archive writer, PostgreSQL archive batch writer, UI audit panel, persistence, API-key RBAC/project-scope foundation, trusted SSO/OIDC proxy auth foundation, `ops/security/rehearse_trusted_proxy_auth.py`, approval/query/scheduler/debug/run-step/replay/finding-status RBAC, analysis/ingestion/replay run start/completion audit boundary events with trigger metadata, failed run status and failed completion audit events, blocked debug artifact read audit events, finding status change audit events, improvement activation/rollback audit events, model/prompt activation/rollback audit events | Local and PostgreSQL archive/prune foundations plus trusted-proxy rehearsal entrypoint complete; direct company IdP validation pending |
| Graph view scalability | `07_GRAPH_VIEW_SCALABILITY_PLAN.md`, `11_GRAPH_RELATIONSHIP_VIEW_PLAN.md`, SVG graph controls, projection API, relationship/component layout, relationship node drag/pin/reset interaction, `ops/ui/smoke_operator_ui.py`, `tests/unit/ops/test_operator_ui_smoke.py` | Dummy 150-node path, graph controls, SVG renderer hooks, overview/pending/orphan modes, truncation metadata, Relationship Graph layout, component grouping, dense-label reduction, node drag, edge rerender, and reset-to-auto-layout are locally validated. The deterministic SVG relationship graph is the first-release renderer; React Flow/Cytoscape remains a future renderer-decision gate after real graph shape validation |
| Dashboard production uplift | `10_DASHBOARD_PRODUCTION_PLAN.md`, `src/req_tracker/dashboard/*`, `/api/v1/dashboard/summary`, `/api/v1/dashboard/work-queue`, `/api/v1/dashboard/work-queue/preferences`, `/api/v1/dashboard/work-queue/assignments`, `/api/v1/dashboard/source-health`, `/api/v1/dashboard/run-health`, `/api/v1/dashboard/risk-summary`, `/api/v1/dashboard/recent-activity`, dashboard-first static UI, split UI modules under `src/req_tracker/ui`, `tests/contract/test_dashboard_api.py`, `tests/contract/test_persistence_api.py`, `tests/unit/dashboard/test_summary_service.py`, `ops/ui/smoke_operator_ui.py`, `docs/security/RBAC_MATRIX.md` | Local dashboard read model and production-shaped UI complete for empty state, compact 10-node fixture, 150-node fixture, approval count update, source export health, RBAC, view split, work queue detail, approval feedback reason controls, source/run health detail, hash deep links, backend-backed saved filters, backend-backed work queue assignment, idempotent assignment writes, SQLite/PostgreSQL typed state for preferences/assignments, RBAC matrix coverage for dashboard state routes, UI module split, and operator smoke; CI browser screenshot smoke is intentionally skipped, and React/React Flow remains a future decision after real graph shape validation |
| Scheduler | `RunScheduler`, API/UI/runbook, viewer/operator RBAC and audit actor capture, persisted schedule configuration, PostgreSQL `scheduler_leases` and `schedule_configs` tables, lease acquire/release tests, Ubuntu multi-replica note | Periodic run path complete for single-process and PostgreSQL lease-backed multi-worker deployments, including restart-safe schedule configuration; external orchestration/Kubernetes CronJob remains an optional platform decision |
| Ubuntu runbook | `README_ubuntu.md`, `docs/runbooks/BACKUP_RESTORE.md`, `docs/runbooks/INCIDENT_RESPONSE.md`, `ops/backup/verify_backup_set.py`, `ops/load/smoke_load.py`, `ops/integration/run_backend_integration.py`, `ops/rehearsal/run_full_stack_rehearsal.py`, `ops/rehearsal/check_production_readiness.py`, `ops/rehearsal/build_staging_evidence_plan.py`, `ops/rehearsal/build_handoff_bundle.py`, `ops/rehearsal/validate_handoff_bundle.py`, `ops/rehearsal/validate_postgres_migration_rollbacks.py`, `ops/rehearsal/validate_postgres_typed_mirrors.py`, `ops/rehearsal/validate_evidence_example.py`, `ops/rehearsal/production_readiness_evidence.example.json` | Local/server scaffold, readiness checks, backup-set verification, incident response triage/rollback/evidence/review runbook, disposable full-stack rehearsal, API restart restore check, smoke-load pass, production-readiness gate reporting, masked staging evidence collection plan generation, one-command handoff bundle generation and validation with manifest remaining-blocker summary/drift checks and final reviewed-evidence template behavior, PostgreSQL migration rollback validation through `010_schedule_config_state_tables`, PostgreSQL typed mirror drift validation including dashboard preferences/assignments, schedule configs, source sync cursors, LLM call traces, replay results, and improvement decisions, observability dashboard manual evidence gate, review-safe manual-evidence template generation, non-passable committed evidence example validation, reviewer metadata, schema-version, non-empty evidence, unique check-id, and UTC review timestamp enforcement for passed manual evidence, reviewed manual-evidence input path, and strict no-failed/no-warning/no-manual release gate complete; company/staging environment rehearsal pending |
| Migration and Helm operation tracks | packaged migrations under `src/req_tracker/storage/migrations/postgres`, `ops/migrations/README.md`, `ops/helm/rune-agent`, `ops/helm/validate_chart.py`, `tests/unit/ops/test_helm_chart.py` | Migration foundation and production-shaped Helm scaffold complete with local structural validation; target-cluster `helm lint/template` and platform-specific values remain pending until Kubernetes environment details are available |
| Eval/security/replay test tracks | `tests/unit/evals`, `tests/contract/test_replay_feedback_api.py`, `tests/contract/test_security_api.py`, `tests/evals/README.md`, `tests/security/README.md`, `tests/replay/README.md` | Current coverage exists; dedicated folders anchored for larger end-to-end fixtures |
| CI | `.github/workflows/ci.yml` runs ruff, mypy, pytest, masking rehearsal, release-blocker coverage, source boundary validation, source/model gateway smokes, Helm structural validation, observability asset validation, PostgreSQL migration rollback validation, PostgreSQL typed mirror validation, readiness evidence template smoke, staging evidence plan smoke, release-scope artifact validation, goal completion audit, handoff bundle smoke and validation for both `.env.example` and `ops/rehearsal/staging.env.example`, readiness example safety validation, CI gate coverage validation, operator UI graph smoke, and feedback eval rehearsal | Complete for deterministic local gates in GitHub Actions with automated drift detection; disposable Docker/full-stack and company/staging gates remain runbook/readiness responsibilities |
| Local handoff package | `MEMORY.md`, `docs/implementation/09_LOCAL_HANDOFF_COMPLETION.md`, source-skill export dry-run, readiness evidence template, staging evidence plan, handoff bundle, handoff bundle validator | Complete for non-company local handoff scope |

## 3. Remaining Implementation Backlog

### P0: Production Persistence Hardening

- Extend typed PostgreSQL repositories beyond the current core and operation
  mirror tables as API query needs grow.
- Re-run PostgreSQL integration tests against company/staging PostgreSQL once
  that environment exists.

### P1: Production Backend Expansion

- Re-run Neo4j integration tests against company/staging Neo4j once that
  environment exists.
- Re-run Qdrant integration tests against company/staging Qdrant once that
  environment exists.
- Keep memory backends as deterministic contract-test baselines.

### P2: JIRA Production Connector

- Run JIRA connector against a real company sandbox JIRA project.
- Use `ops/source/rehearse_company_sources.py --source jira` for the first
  sandbox proof, and attach its masked JSON output to the production readiness
  evidence file.
- Keep MCP/REST/export selection inside Claude Code source skills and local
  config, not in core Python workflow code.
- Map source permission results to project authorization policy after real
  company identity rules are available.
- Extend the same live-source validation path to a real company Confluence
  sandbox space.
- Use `ops/source/rehearse_decision_email_export.py` for approved
  decision-archive or restricted Email export validation; do not validate broad
  mailbox ingestion for the first production release.

### P3: Model Provider and Debug Workbench

- Run retry/fallback behavior against real external or company model provider sandboxes.
- Use `ops/model_gateway/rehearse_model_gateway.py` for the first sandbox proof,
  and attach its masked JSON output to the production readiness evidence file.
- Validate LLM payload diff panes with real sandbox model calls once a model
  endpoint is available.
- Calibrate eval thresholds and canary policy with real reviewer feedback once
  production proposals are reviewed.

### P4: Security and Operations

- Rehearse trusted-proxy auth behind a real company SSO/OIDC reverse proxy and
  replace it with direct IdP token validation only if required.
- Use `ops/security/rehearse_trusted_proxy_auth.py` for the first staging
  trusted-proxy RBAC proof and attach its masked JSON output to the production
  readiness evidence file.
- Run backup/restore and load rehearsals against company/staging PostgreSQL,
  Neo4j, Qdrant, and artifact store environments.
- Configure a company-approved OpenTelemetry collector and set
  `OTEL_ENABLED=true` plus `OTEL_EXPORTER_OTLP_ENDPOINT` in staging before
  release approval.
- Import the packaged Grafana dashboard and Prometheus alert rules in staging,
  then attach reviewed evidence for `observability_dashboard_rehearsal`.
- Run `ops/backup/verify_backup_set.py --backup-root <BACKUP_ROOT>` on the
  staging backup set before restore rehearsal, and attach its JSON output to
  production readiness evidence.
- Run `ops/rehearsal/check_production_readiness.py --run-local-gates` on a
  staging host with production-shaped environment variables before release
  approval.
- Record reviewed staging evidence in a secure copy of
  `ops/rehearsal/production_readiness_evidence.example.json` and pass it to
  `check_production_readiness.py --evidence-file`; do not commit real evidence
  files if they contain internal CI URLs, artifact IDs, or incident references.
- Keep the deterministic SVG relationship graph as the first-release renderer.
  Decide React Flow/Cytoscape migration only after real graph shape validation.
- If Kubernetes or multiple Ubuntu nodes are selected instead of multi-process
  API replicas on one PostgreSQL-backed service, decide whether to keep the
  in-app PostgreSQL scheduler lease or move periodic execution to CronJob or a
  queue worker.
- Run `helm lint ops/helm/rune-agent` and `helm template` with company values
  once Helm and the target Kubernetes policy are available.

## 4. Latest Local Verification

2026-05-12 local verification after controlled improvement rollback,
runtime metrics, trace-context, OpenTelemetry export foundation, restricted
model payload policy, provider usage metadata, observability asset
implementation, step-level retrieval/validation debug metadata, deterministic
approval risk scoring, counter-evidence reasoning output, and stale approval
blocking:

- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `203 passed, 3 skipped`
- `uv run pytest tests/contract/test_audit_api.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py`:
  `15 passed`
- `uv run pytest tests/contract/test_replay_feedback_api.py tests/contract/test_persistence_api.py tests/contract/test_audit_api.py`:
  `14 passed`
- `uv run pytest tests/contract/test_persistence_api.py tests/contract/test_replay_feedback_api.py tests/contract/test_security_api.py`:
  `20 passed`
- `uv run pytest tests/contract/test_persistence_api.py tests/contract/test_audit_api.py`:
  `8 passed`
- `uv run pytest tests/contract/test_debug_api.py tests/contract/test_security_api.py tests/contract/test_openapi_surface.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py tests/unit/storage/test_postgres_store.py tests/contract/test_models.py`:
  `44 passed`
- `uv run pytest tests/contract/test_backend_settings_api.py tests/contract/test_health_api.py tests/contract/test_run_api.py tests/contract/test_debug_api.py tests/contract/test_persistence_api.py`:
  `33 passed`
- `uv run pytest tests/unit/ops/test_skill_export_rehearsal.py tests/unit/ops/test_production_readiness_check.py`:
  `19 passed`
- `uv run pytest`: `209 passed, 3 skipped`
- 2026-05-15 dashboard production uplift verification:
  - `node --check` for `src/req_tracker/ui/app.js`, `core.js`,
    `dashboard.js`, `work_queue.js`, `graph_workbench.js`,
    `debug_workbench.js`, and `source_health.js`: passed
  - `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_dashboard_api.py tests/unit/dashboard/test_summary_service.py`:
    `13 passed`
  - `uv run python ops/ui/smoke_operator_ui.py`: passed, including
    dashboard read models, UI module asset serving, hash routing hooks, saved
    filter/assignment hooks, and `RUNE_SCALE_150` work queue/graph contracts
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `219 passed, 3 skipped`
  - Playwright CLI screenshots were used manually for dashboard/work-queue
    rendering and deep-link behavior; CI browser screenshot smoke is
    intentionally skipped per product decision.
- 2026-05-16 relationship graph verification:
  - Commit `0e438b0 Add relationship graph workbench interactions` pushed to
    `origin/main`
  - GitHub Actions `CI` run `25929814655`: success
  - `node --check src/req_tracker/ui/graph_workbench.js`: passed
  - `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py`:
    `6 passed`
  - `uv run python ops/ui/smoke_operator_ui.py`: passed, including
    `RUNE_SCALE_150` with 150 total nodes, 120 visible overview nodes,
    103 pending edges, 103 approval work items, 48 finding work items,
    and 9 orphan nodes
  - Playwright CLI verified `Relationship Graph` with `layout=relationship`,
    120 rendered relationship nodes, 73 rendered edges, 26 dense-mode labels,
    node drag changing `Scaled architecture block 001` from its auto layout
    position to a pinned position, edge rerender preservation, and `Reset View`
    restoring the auto layout position
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `222 passed, 3 skipped`
- 2026-05-16 production-readiness local gate check:
  - Commit `4f96977 Classify unavailable Docker readiness gates` pushed to
    `origin/main`
  - GitHub Actions `CI` run `25964404814`: success
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    failed overall as expected for this workstation because production/staging
    environment variables are unset; local regression gates passed after
    Docker Desktop Linux engine was started
  - `uv run pytest tests/unit/ops/test_production_readiness_check.py`:
    `20 passed`, including coverage that Docker daemon unavailability is
    reported as `manual_required`/`docker_unavailable` only when the remaining
    local gates pass, and that mixed non-Docker failures still fail the local
    gate summary
  - Non-Docker local gates in the readiness run passed, including ruff, mypy,
    pytest, masking rehearsal, release blocker coverage, source boundary
    validation, source adapter smoke, source-skill export rehearsal, model
    gateway smoke, Helm chart validation, observability asset validation,
    PostgreSQL migration rollback validation, PostgreSQL typed mirror
    validation, evidence example validation, CI gate coverage validation, UI
    smoke, and feedback eval rehearsal
  - `uv run python ops/integration/run_backend_integration.py`: passed with
    disposable PostgreSQL, Neo4j, and Qdrant containers (`3 passed`)
  - `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed with
    disposable PostgreSQL, Neo4j, and Qdrant containers, API restart restore,
    `audit_total_events=3`, metrics surface check, and smoke-load p95 under
    the 5 second local rehearsal threshold
- `uv run pytest tests/unit/api/test_runtime_state.py tests/unit/debug/test_trace_recorder.py tests/contract/test_audit_api.py tests/contract/test_persistence_api.py tests/contract/test_run_api.py`:
  `20 passed`
- `uv run python ops/observability/validate_observability_assets.py`: passed
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed, including
  `audit_total_events=3`, metrics surface check with `http_total_requests=7`,
  `graph_nodes=14`, `llm_calls=1`, restart restore, load smoke p95 under
  5 seconds, OpenTelemetry disabled-by-default health status, and Prometheus
  text counters
- `uv run python ops/security/check_release_blockers.py`: passed, including
  rollback evidence for prompt/model regression or ungated activation coverage
- `uv run python ops/source/validate_source_boundaries.py`: passed
- `uv run python ops/source/rehearse_skill_export_sources.py`: passed, including
  JIRA, Confluence, and decision/email export-mode workflow injection and
  source cursor debug state
- `uv run python ops/evals/run_feedback_eval_rehearsal.py`: passed, including
  review-ready, canary, active, rollback, and security-blocked eval paths
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
  all local regression gates passed, while overall readiness remained failed as
  expected because company/staging PostgreSQL, Neo4j, Qdrant, model gateway,
  trusted proxy, artifact storage, OpenTelemetry collector, source,
  Prometheus/Grafana dashboard, backup/restore, and load-test evidence variables
  are not configured in the local workstation environment. The readiness
  summary was `failed=7`, `manual_required=10`, `passed=2`.
- 2026-05-16 dashboard backend preference/assignment verification:
  - `uv run pytest tests/contract/test_dashboard_api.py tests/contract/test_persistence_api.py tests/contract/test_openapi_surface.py -q`:
    `15 passed`
  - `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py tests/contract/test_dashboard_api.py tests/contract/test_persistence_api.py tests/contract/test_openapi_surface.py -q`:
    `21 passed`
  - `node --check src/req_tracker/ui/app.js` and
    `node --check src/req_tracker/ui/work_queue.js`: passed
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `225 passed, 3 skipped`
  - `uv run python ops/ui/smoke_operator_ui.py`: passed, including backend
    work queue preference and assignment contracts
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed; overall readiness still failed as expected
    because company/staging environment variables and reviewed manual evidence
    are unset
- 2026-05-16 dashboard PostgreSQL typed-state hardening:
  - `uv run pytest tests/unit/storage/test_postgres_store.py -q`: `9 passed`
  - `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
    passed with migration/rollback versions `001` through `006`
  - `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
    with typed mirror coverage for `dashboard_preferences` and
    `dashboard_assignments`
- 2026-05-17 source sync cursor PostgreSQL typed-state hardening:
  - Added migration/rollback `007_source_cursor_state_tables` for
    `source_sync_cursors`
  - Added typed PostgreSQL mirror spec for `source_sync_cursors`, preserving
    the full JSON payload while promoting source type, project key, scenario,
    run, cursor counters, failure state, and update metadata to typed columns
  - `uv run pytest tests/unit/storage/test_postgres_store.py -q`: `9 passed`
  - `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
    passed with migration/rollback versions `001` through `007`
  - `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
    with typed mirror coverage for `source_sync_cursors`
- 2026-05-17 debug/replay PostgreSQL typed-state hardening:
  - Added migration/rollback `008_debug_replay_state_tables` for
    `llm_call_traces` and `replay_results`
  - Added typed PostgreSQL mirror specs for LLM call traces and replay results,
    preserving the full JSON payload while promoting debug/replay lookup fields
    to typed columns
  - `uv run pytest tests/unit/storage/test_postgres_store.py -q`: `10 passed`
  - `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
    passed with migration/rollback versions `001` through `008`
  - `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
    with typed mirror coverage for `llm_call_traces` and `replay_results`
- 2026-05-17 improvement decision PostgreSQL typed-state hardening:
  - Added migration/rollback `009_improvement_decision_state_tables` for
    `improvement_decisions`
  - Added typed PostgreSQL mirror spec for controlled improvement activation
    and rollback decisions, preserving full payload JSON while promoting
    candidate id, status, decision type, eval run, reviewer, and version fields
    to typed columns
  - `uv run pytest tests/unit/storage/test_postgres_store.py -q`: `11 passed`
  - `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
    passed with migration/rollback versions `001` through `009`
  - `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
    with typed mirror coverage for `improvement_decisions`
- 2026-05-16 dashboard state RBAC documentation and regression:
  - Commit `6418677 Document dashboard state RBAC` pushed to `origin/main`
  - GitHub Actions `CI` run `25965051096`: success
  - `uv run pytest tests/contract/test_dashboard_api.py::test_rbac_matrix_documents_dashboard_work_queue_state_routes -q`:
    failed before the RBAC matrix update, then passed after the document was
    updated
  - `uv run pytest tests/contract/test_dashboard_api.py tests/contract/test_security_api.py tests/contract/test_openapi_surface.py -q`:
    `17 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `git diff --check`: passed
  - `uv run pytest`: `229 passed, 3 skipped`
- 2026-05-17 production-readiness local gate refresh:
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed, including `ruff`, `mypy`, full `pytest`,
    masking rehearsal, release blocker coverage, source boundary validation,
    disposable PostgreSQL/Neo4j/Qdrant integration, source adapter smoke,
    source-skill export rehearsal, model gateway smoke, Helm chart validation,
    observability asset validation, PostgreSQL migration rollback validation,
    PostgreSQL typed mirror validation, evidence example validation, CI gate
    coverage validation, operator UI smoke, Docker-backed full-stack rehearsal,
    and feedback eval rehearsal
  - Overall production readiness still failed as expected with summary
    `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because
    company/staging environment variables and reviewed manual evidence are not
    configured on this workstation
  - Docker-backed disposable integration and full-stack rehearsal both ran in
    this refresh; full-stack rehearsal reported `passed=true`,
    `restart_restored=true`, `audit_total_events=3`, and local smoke-load p95
    below the 5 second rehearsal threshold
- 2026-05-17 traceable node/finding LLM stage coverage:
  - Commit `360b68e Trace node and finding LLM stages` pushed to `origin/main`
  - GitHub Actions `CI` run `25967338344`: success
  - `uv run pytest tests/contract/test_health_api.py::test_metrics_summary_reports_http_and_runtime_counts tests/unit/model_gateway tests/contract/test_debug_api.py tests/contract/test_replay_feedback_api.py tests/contract/test_persistence_api.py tests/integration/test_dummy_analysis_pipeline.py -q`:
    `40 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `239 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed; overall readiness still failed as expected
    with summary `failed=7`, `manual_required=10`, `passed=2`,
    `warning=0` because company/staging environment variables and reviewed
    manual evidence are not configured on this workstation
- 2026-05-17 model gateway comparison coverage:
  - Added `src/req_tracker/model_gateway/comparison.py` for same-input
    model/prompt candidate execution and top-level output diff reporting
  - `uv run pytest tests/unit/model_gateway -q`: `16 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `240 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed; overall readiness still failed as expected
    with summary `failed=7`, `manual_required=10`, `passed=2`,
    `warning=0` because company/staging environment variables and reviewed
    manual evidence are not configured on this workstation
- 2026-05-17 vector-backed edge retrieval context:
  - Edge-linking LLM reasoning now calls the configured vector backend and
    writes `edge_retrieval_context.json` with query, retrieval policy,
    retrieved chunk ids, source artifact ids, and candidate edge ids
  - `uv run pytest tests/integration/test_dummy_analysis_pipeline.py tests/contract/test_debug_api.py tests/contract/test_run_api.py tests/contract/test_persistence_api.py tests/contract/test_replay_feedback_api.py -q`:
    `33 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `240 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed; overall readiness still failed as expected
    with summary `failed=7`, `manual_required=10`, `passed=2`,
    `warning=0` because company/staging environment variables and reviewed
    manual evidence are not configured on this workstation
- 2026-05-17 work queue approval feedback controls:
  - Work queue approval details now expose canonical feedback reason-code
    selection and route approve/reject/hold decisions through the shared
    approval decision handler.
  - Operator UI smoke now checks for the feedback reason selector, canonical
    reason codes, and hold action wiring.
  - `node --check src/req_tracker/ui/work_queue.js`: passed
  - `node --check src/req_tracker/ui/app.js`: passed
  - `uv run pytest tests/contract/test_run_api.py::test_analyze_run_and_approve_edge tests/contract/test_run_api.py::test_modify_approval_commits_corrected_edge_and_feedback tests/contract/test_replay_feedback_api.py::test_feedback_api_normalizes_command_style_actions tests/unit/ops/test_operator_ui_smoke.py -q`:
    `4 passed`
  - `uv run ruff check .`: passed
  - `uv run mypy src`: passed
  - `uv run pytest`: `240 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed; overall readiness still failed as expected
    with summary `failed=7`, `manual_required=10`, `passed=2`,
    `warning=0` because company/staging environment variables and reviewed
    manual evidence are not configured on this workstation
- 2026-05-17 persisted schedule configuration:
  - Added restart-safe schedule configuration persistence through the configured
    state store.
  - Added PostgreSQL typed mirror migration/rollback
    `010_schedule_config_state_tables` for `schedule_configs`.
  - `uv run pytest tests/contract/test_persistence_api.py::test_sqlite_state_store_restores_schedule_configuration -q`:
    passed after first reproducing the missing restore behavior.
  - `uv run pytest tests/unit/storage/test_postgres_store.py::test_postgres_store_typed_schedule_config_table tests/unit/storage/test_postgres_store.py::test_load_postgres_migrations_returns_ordered_state_schema tests/unit/storage/test_postgres_store.py::test_load_postgres_rollbacks_returns_versioned_scripts -q`:
    `3 passed`
  - `uv run pytest tests/contract/test_schedule_api.py tests/contract/test_persistence_api.py tests/unit/storage/test_postgres_store.py tests/unit/ops/test_postgres_migration_rollback_validator.py tests/unit/ops/test_postgres_typed_mirror_validator.py -q`:
    `26 passed`
  - `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`:
    passed with `010:schedule_configs`
  - `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed
    with typed mirror coverage for `schedule_configs`
  - `uv run ruff check src/req_tracker/api/state.py src/req_tracker/api/routes/runs.py src/req_tracker/storage/postgres_store.py tests/contract/test_persistence_api.py tests/unit/storage/test_postgres_store.py`:
    passed
  - `uv run mypy src`: passed
  - `uv run ruff check .`: passed
  - `uv run pytest`: `242 passed, 3 skipped`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed; overall readiness still failed as expected
    with summary `failed=7`, `manual_required=10`, `passed=2`,
    `warning=0` because company/staging environment variables and reviewed
    manual evidence are not configured on this workstation
- 2026-05-17 staging evidence plan:
  - Added `ops/rehearsal/build_staging_evidence_plan.py` so release owners can
    generate masked JSON or Markdown instructions for each unresolved
    company/staging gate.
  - `uv run pytest tests/unit/ops/test_staging_evidence_plan.py -q`: 3 passed
  - `uv run ruff check ops/rehearsal/build_staging_evidence_plan.py tests/unit/ops/test_staging_evidence_plan.py`: passed
  - `uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown`: passed
  - Added the same command to GitHub Actions `CI` and
    `ops/rehearsal/validate_ci_gate_coverage.py` required extra commands.
  - RED/GREEN: `uv run pytest tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q` failed before the CI requirement was added and passed after adding it.
  - Added the same command to
    `ops/rehearsal/check_production_readiness.py` `LOCAL_GATE_COMMANDS`.
  - RED/GREEN: `uv run pytest tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q` failed before the local gate list was updated and passed after adding it.
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed with the staging evidence plan smoke included; overall readiness still failed as expected with summary `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because company/staging variables and reviewed evidence are unset.
  - Added a guard that every unresolved staging evidence gate has command,
    evidence, and docs guidance; filled Neo4j/Qdrant staging doc references.
  - RED/GREEN: `uv run pytest tests/unit/ops/test_staging_evidence_plan.py::test_staging_evidence_plan_guides_every_unresolved_gate -q` failed before Neo4j/Qdrant doc guidance was added and passed after adding it.
- 2026-05-17 first-release scope artifact verifier:
  - Added `ops/rehearsal/validate_release_scope_artifacts.py` to map
    `PRODUCTION_EXECUTION_PLAN.md` first-release scope items to concrete repo
    artifacts, verification commands, and current status classification.
  - Added GitHub Actions `CI`, CI coverage validation, and production-readiness
    local gate coverage for the verifier.
  - Current verifier result is intentionally not release-ready:
    `local_complete=11`, `company_evidence_required=4`,
    `missing_artifacts=0`.
  - RED/GREEN: local readiness and CI coverage tests failed while the verifier
    command was absent from the gate lists, then passed after adding it.
  - `uv run pytest tests/unit/ops/test_release_scope_artifacts.py tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke tests/unit/ops/test_ci_gate_coverage.py::test_ci_gate_coverage_reports_missing_required_command -q`:
    `6 passed`
  - `uv run python ops/rehearsal/validate_release_scope_artifacts.py`: passed
  - `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed with
    `ci_command_count=22`
  - `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
    local regression gates passed with the release-scope verifier included;
    overall readiness still failed as expected with summary `failed=7`,
    `manual_required=10`, `passed=2`, `warning=0`.
  - Resolved the local graph renderer decision by aligning
    `PRODUCTION_EXECUTION_PLAN.md` first-release scope to `production graph UI
    with renderer decision gate`; deterministic SVG is now the first-release
    renderer and React Flow/Cytoscape remains a future gate.
  - RED/GREEN: `uv run pytest tests/unit/ops/test_release_scope_artifacts.py -q`
    failed while the verifier still reported `decision_pending=1`, then passed
    after the graph UI item moved to `local_complete`.
  - Added a plan-alignment guard so
    `ops/rehearsal/validate_release_scope_artifacts.py` parses the
    `PRODUCTION_EXECUTION_PLAN.md` first-release required-scope bullets and
    fails if verifier requirements drift from the plan.
  - RED/GREEN: `uv run pytest tests/unit/ops/test_release_scope_artifacts.py::test_release_scope_requirements_match_production_plan -q`
    failed before the plan parser existed and passed after adding it.
  - `uv run pytest tests/unit/ops/test_release_scope_artifacts.py -q`:
    `6 passed`
  - Added completion-audit marker coverage for every first-release scope item;
    `validate_release_scope_artifacts.py` now fails if an item is not traceable
    from `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md`.
  - RED/GREEN: `uv run pytest tests/unit/ops/test_release_scope_artifacts.py::test_release_scope_items_have_completion_audit_coverage -q`
    failed before audit coverage was reported and passed after adding
    `audit_markers`, `audit_covered`, and `audit_coverage_missing`.

## 5. Completion Gate

The overall production objective is not complete yet. The current repo is a
validated local/dummy, persistence-foundation, backend-interface, source-adapter,
debuggability, runtime-metrics, trace-context propagation, dashboard/workbench,
relationship graph, and operations-rehearsal stage. The latest deterministic
local gates and Docker-backed disposable rehearsals pass in the current local
workspace. The latest pushed GitHub Actions CI is tracked in the verified
baseline section above.

One category remains outside the evidence that can be completed in the current
shell:

- Company/staging readiness requires PostgreSQL, Neo4j, Qdrant,
  JIRA/Confluence, SSO/OIDC proxy, OpenTelemetry collector,
  Prometheus/Grafana dashboard import, backup/restore/load evidence, approved
  decision/email export data, and a real sandbox model endpoint so integration,
  replay, backup, restore, load, live-source, live-provider, and observability
  validation can run against real organization dependencies.

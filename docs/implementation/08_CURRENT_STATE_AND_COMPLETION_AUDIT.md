# Current State and Completion Audit

Last reviewed: 2026-05-12

This document maps `PRODUCTION_EXECUTION_PLAN.md` requirements to current repo
artifacts and verification evidence. A requirement is complete only when
implementation and a relevant verification path exist in the repository.

## 1. Current Verified Baseline

Latest confirmed commits:

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
- `uv run pytest`: 183 passed, 3 skipped
- repo-shape anchor check for `.claude/skills`, `docs/api`, `docs/ontology`,
  `docs/security/DATA_POLICY.md`, `docs/security/RBAC_MATRIX.md`,
  `docs/runbooks/BACKUP_RESTORE.md`, `docs/runbooks/MODEL_POLICY.md`,
  `ops/migrations`, `ops/helm`, `tests/evals`, `tests/security`, and
  `tests/replay`: passed
- `uv run python ops/integration/run_backend_integration.py`: 3 passed
- `uv run python ops/source/smoke_source_adapters.py`: passed
- `uv run python ops/source/rehearse_company_sources.py`: failed as expected on this local shell because JIRA/Confluence sandbox env vars are unset; output masks tokens and lists missing config
- `uv run python ops/source/rehearse_decision_email_export.py`: failed as expected on this local shell because `RUNE_EMAIL_EXPORT_PATH` is unset; output masks path state and lists missing config
- `uv run python ops/model_gateway/smoke_model_gateway.py`: passed
- `uv run python ops/ui/smoke_operator_ui.py`: passed, validating static operator UI assets, graph controls, SVG renderer hooks, and `RUNE_SCALE_150` projection modes with 150 total nodes, 120 visible overview nodes, 103 pending edges, and 9 orphan nodes
- `uv run python ops/observability/validate_observability_assets.py`: passed, validating Prometheus scrape config, alert rules, Grafana dashboard JSON, required runtime metric references, and absence of hardcoded observability credentials
- `uv run python ops/model_gateway/rehearse_model_gateway.py`: failed as expected on this local shell because `MODEL_GATEWAY_ENDPOINT_URL` is unset; output masks API key state and lists missing config
- `uv run python ops/security/rehearse_trusted_proxy_auth.py`: failed as expected on this local shell because `RUNE_API_BASE_URL` and `TRUSTED_PROXY_SECRET` are unset; output masks secret state and lists missing config
- `uv run python ops/security/rehearse_masking_policy.py`: passed, verifying representative sensitive inputs are redacted without printing raw sensitive strings or forbidden patterns
- `uv run python ops/security/check_release_blockers.py`: passed, validating coverage evidence for masking violations, approval-gated graph mutation, project authorization leaks, prompt/model regression gates, migration rollback/restore, and forbidden model payload policy
- `uv run pytest tests/unit/ops/test_backup_verify.py`: passed, validating backup-set required files, SHA256 mismatch detection, artifact tar, Qdrant JSON, Neo4j dump marker, and git commit marker checks
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed,
  including API restart restore, metrics surface check
  (`http_total_requests=7`, `graph_nodes=14`, `llm_calls=1`), and smoke-load
  pass (`load_smoke.p95_ms` about 3247 ms against a 5000 ms local rehearsal
  threshold)
- `uv run python ops/evals/run_feedback_eval_rehearsal.py`: passed
- `uv run python ops/rehearsal/check_production_readiness.py`: failed as expected on this local shell because production env/company-staging endpoints are unset; report produced failed env checks and manual-required gates without secret values
- `uv run python ops/rehearsal/check_production_readiness.py --write-evidence-template -`: passed, producing a review-safe unresolved-gate evidence template with `failed` TODO placeholders
- `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`: passed, validating 17 created PostgreSQL tables have matching rollback drops across 5 migration versions
- `uv run python ops/rehearsal/validate_postgres_typed_mirrors.py`: passed, validating 14 PostgreSQL typed mirror tables against packaged migration DDL
- `uv run python ops/rehearsal/validate_evidence_example.py`: passed, validating that the committed example evidence file has 11 non-passable manual gates, no passable placeholder entries, fake `run-123*` references, duplicate check IDs, missing evidence arrays, or missing top-level TODO metadata
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed, validating that GitHub Actions covers deterministic local release gates and only omits the documented Docker-backed integration/full-stack rehearsals
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness failed as expected because company/staging environment variables and manual evidence are unset
- `uv run python ops/rehearsal/check_production_readiness.py --evidence-file ops/rehearsal/production_readiness_evidence.example.json`: failed as expected because the committed example evidence uses `failed` TODO placeholders and production env checks are unset; fake `run-123*` and `status: passed` examples are not present in the committed template
- `uv run pytest tests/unit/ops/test_production_readiness_check.py`: 18 passed, including manual evidence file loading, duplicate check-id rejection, TODO-placeholder rejection for passed evidence, reviewer metadata enforcement for passed evidence, schema-version and non-empty evidence enforcement for passed evidence, ISO-8601 UTC `reviewed_at` enforcement, failed TODO template loading, non-passable example evidence, review-safe evidence template generation, complete env/evidence pass behavior, unknown evidence warning blocking, and Kubernetes Helm evidence gating
- `uv run pytest tests/unit/ops/test_helm_chart.py`: 4 passed, validating chart artifact presence, production environment mapping, secret references, no hardcoded secret/MCP transport names, and local chart validator behavior
- `uv run python ops/helm/validate_chart.py`: passed, validating required Helm chart files, production env defaults, secret references, and forbidden snippets without requiring a local Helm binary
- `helm version --short`: not available in this local shell; run `helm lint` and `helm template` in the target Kubernetes environment

Latest GitHub verification:

- GitHub Actions `CI` run `25697689042` for `7ac8a0a`: completed successfully

## 2. Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Production plan is the source of truth | `PRODUCTION_EXECUTION_PLAN.md`, `docs/implementation/03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md` | Complete |
| Expected repository shape is anchored | `src/req_tracker/*`, `.claude/skills/rune-source-*`, `docs/api/README.md`, `docs/ontology/ONTOLOGY_V1.md`, `ops/migrations/README.md`, `ops/helm/README.md`, `tests/evals/README.md`, `tests/security/README.md`, `tests/replay/README.md` | Complete for implemented and deferred tracks |
| Ontology v1 is documented and executable | `docs/ontology/ONTOLOGY_V1.md`, `src/req_tracker/ontology/models.py`, `tests/contract/test_models.py` | Complete |
| API documentation path exists | `docs/api/README.md`, `src/req_tracker/api/routes/*`, `tests/contract/*`, `tests/contract/test_openapi_surface.py`, method/path OpenAPI guard, `/api/v1/projects`, `/api/v1/graph/nodes`, `/api/v1/graph/edges`, `/api/v1/runs/ingest`, `/api/v1/runs/analyze`, `/api/v1/runs`, `/api/v1/runs/{run_id}/steps`, `/api/v1/runs/{run_id}/llm-calls`, `/api/v1/runs/{run_id}/artifacts`, `/api/v1/runs/{run_id}/graph-delta`, `/api/v1/runs/{run_id}/replay`, `/api/v1/replays/{replay_id}/diff`, `/api/v1/debug/approvals/{approval_id}/lineage`, `/api/v1/findings/{finding_id}`, `/api/v1/findings/{finding_id}/status`, `/api/v1/admin/model-profiles/{id}/activate`, `/api/v1/admin/prompt-versions/{id}/activate`, optional `/openapi.json` with `ENABLE_DOCS=true` | Complete |
| Data and model policies are fixed | `docs/security/DATA_POLICY.md`, `docs/runbooks/MODEL_POLICY.md`, `config/model_profiles.json`, `config/prompt_versions.json`, `src/req_tracker/model_gateway/models.py`, `src/req_tracker/model_gateway/policy.py`, `src/req_tracker/api/routes/admin.py`, `ops/security/rehearse_masking_policy.py`, `ops/model_gateway/smoke_model_gateway.py` | Complete for local policy baseline, restricted/confidential `masking_applied` and `access_checked` enforcement, and gated activation records; company model profile approval pending |
| Release blocker coverage | `ops/security/check_release_blockers.py`, `ops/security/rehearse_masking_policy.py`, `tests/contract/test_security_api.py`, `tests/contract/test_admin_registry_api.py`, `tests/contract/test_replay_feedback_api.py`, `tests/unit/storage/test_postgres_store.py`, `ops/rehearsal/validate_postgres_migration_rollbacks.py`, `tests/unit/model_gateway/test_dummy_gateway.py` | Local release-blocker evidence manifest complete, including explicit migration rollback coverage validation and restricted model payload masking/access policy tests; company/staging evidence still required for real endpoints |
| Structured request logging, trace context, and OpenTelemetry export foundation | `src/req_tracker/config/logging.py`, `src/req_tracker/api/app.py`, `src/req_tracker/observability/tracing.py`, `src/req_tracker/observability/otel.py`, `tests/contract/test_health_api.py`, `tests/unit/config/test_logging.py`, `tests/unit/observability/test_tracing.py`, `tests/unit/observability/test_otel.py` | Complete for JSON request logs with correlation id, W3C trace id, span id, user id, method, path, status, duration, `traceparent` response propagation, optional OTLP FastAPI span export, disabled/missing-endpoint safeguards, and enabled-path exporter/instrumentor wiring tests |
| Runtime metrics and scrape surface | `src/req_tracker/observability/metrics.py`, `src/req_tracker/api/routes/health.py`, `/api/v1/metrics`, `/api/v1/metrics/summary`, `ops/observability/prometheus.yml`, `ops/observability/rune-agent-alerts.yml`, `ops/observability/grafana-dashboard.json`, `ops/observability/validate_observability_assets.py`, `ops/rehearsal/run_full_stack_rehearsal.py`, `tests/contract/test_health_api.py`, `tests/unit/observability/test_metrics.py`, `tests/unit/ops/test_full_stack_rehearsal.py`, `tests/unit/ops/test_observability_assets.py` | Complete for in-process HTTP/runtime/LLM/graph/approval/finding/feedback/audit/scheduler counters, Prometheus text exposition, packaged Prometheus scrape/alert starter assets, Grafana dashboard JSON, asset validation gate, readiness manual evidence gate, and disposable full-stack metrics rehearsal; company collector and dashboard import remain target-environment tasks |
| Claude Code source-skill boundary for JIRA/Confluence/Email | `.claude/skills/rune-source-*`, `JiraRestSourceAdapter`, `ConfluenceRestSourceAdapter`, `request_with_retry`, `ops/source/smoke_source_adapters.py`, `ops/source/rehearse_company_sources.py`, `ops/source/rehearse_decision_email_export.py`, export adapters, restricted decision/email export policy, `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` | Design/export path complete; JIRA/Confluence REST retry, network `OSError` retry, pagination, permission-warning, local HTTP smoke validation, env-driven company sandbox rehearsal entrypoint, and restricted decision/email export rehearsal entrypoint complete; Email live access and real company sandbox validation pending |
| Dummy/local validation path | `LocalAnalysisWorkflow`, dummy fixtures, API tests, integration test, readiness API, persisted runtime restore test, `ops/security/rehearse_masking_policy.py` | Complete |
| Core contracts | `src/req_tracker/ontology`, `debug`, `approvals`, `feedback`, `audit` models | Complete |
| Source snapshot lineage | `AgentRun.input_snapshot_ids`, normalized `SourceArtifact.artifact_id`, `LocalAnalysisWorkflow` metadata update, run API and integration tests | Complete for local/source-artifact snapshot lineage |
| Run trigger lineage | `AgentRun.triggered_by`, `AgentRun.trigger_source`, API analyze path, schedule run-now path, periodic scheduler path, replay path, contract tests | Complete for local API/manual/schedule/replay trigger attribution |
| Command idempotency | `POST /api/v1/runs/ingest`, `POST /api/v1/runs/analyze`, `POST /api/v1/runs/{run_id}/replay`, `PUT /api/v1/schedule`, `POST /api/v1/schedule/run-now`, `POST /api/v1/approvals/{approval_id}/decision`, `POST /api/v1/findings/{finding_id}/status`, `POST /api/v1/feedback`, `POST /api/v1/improvements/{candidate_id}/activate`, `POST /api/v1/admin/model-profiles/{id}/activate`, `POST /api/v1/admin/prompt-versions/{id}/activate`, and `POST /api/v1/audit/retention/archive-prune` `Idempotency-Key`/`X-Idempotency-Key`, persisted `idempotency_results`, API conflict tests, SQLite restart restore test, graph commit idempotency keys | Complete for implemented local command APIs plus graph commit paths |
| Model gateway abstraction | `src/req_tracker/model_gateway` with dummy provider, HTTP JSON provider, provider factory, file-backed registry, policy, structured validation retry, fallback trace tests, restricted/confidential masking and access-check gates, `ops/model_gateway/smoke_model_gateway.py`, `ops/model_gateway/rehearse_model_gateway.py` | Profile/registry/live-shaped HTTP foundation and env-driven company sandbox rehearsal entrypoint complete; real external provider sandbox validation pending |
| LLM-assisted workflow trace | `LocalAnalysisWorkflow` `llm_assisted_reasoning` stage, `ModelGatewayClient`, `LLMCallTrace`, SQLite restore of `llm_call_traces`, `/api/v1/runs/{run_id}/llm-calls`, debug diff LLM panes | Dummy model-gateway integration complete; live model quality validation pending |
| Debug trace and local artifact store | `src/req_tracker/debug`, `/api/v1/debug/*`, `/api/v1/runs/{run_id}/llm-calls`, `/api/v1/runs/{run_id}/artifacts`, `/api/v1/runs/{run_id}/graph-delta`, `/api/v1/replays/{replay_id}/diff`, restart-safe `replay_results`, approval lineage API, run diff-view API, run debug UI, LLM/graph delta side-by-side panes | Local debug workbench foundation complete; live LLM payload validation pending |
| SQLite state persistence | `SQLiteStateStore`, persistence contract test, restart restore contract test | Complete |
| PostgreSQL migration foundation | `PostgreSQLStateStore`, `001_state_entities.sql`, `003_audit_archive_batches.sql`, `004_operation_state_tables.sql`, `005_scheduler_leases.sql`, migration loader tests, rollback scripts, `ops/rehearsal/validate_postgres_migration_rollbacks.py` | Complete with migration-to-rollback coverage validation |
| Typed PostgreSQL core and operation-state table foundation | `002_core_state_tables.sql`, `004_operation_state_tables.sql`, typed mirror upsert/read dispatch for core state, idempotency results, and registry activations, rollback scripts, unit tests, optional `POSTGRES_TEST_DSN` integration test, `ops/integration/run_backend_integration.py`, `ops/rehearsal/validate_postgres_typed_mirrors.py` | Foundation complete with spec-to-DDL drift validation; disposable Docker PostgreSQL integration passed; company/staging DB rehearsal pending |
| Graph backend | `GraphBackend` protocol, `MemoryGraphBackend`, `Neo4jGraphBackend`, graph projection, traceability chain APIs, optional `NEO4J_TEST_*` integration test, Docker integration runner | Neo4j foundation complete; disposable Docker Neo4j integration passed; company/staging graph rehearsal pending |
| Vector backend | `VectorBackend` protocol, `MemoryVectorBackend`, `QdrantVectorBackend`, optional `QDRANT_TEST_URL` integration test, Docker integration runner | Qdrant foundation complete; disposable Docker Qdrant integration passed; company/staging vector rehearsal pending |
| Approval workflow | approval queue, approve/reject/hold/modify path, graph commit, developer/operator RBAC and project-scope checks | Complete for local and protected API paths |
| Feedback loop | feedback events, eval candidates, improvement candidates, eval gate, controlled review/canary promotion, feedback/eval/improvement RBAC, `ops/evals/run_feedback_eval_rehearsal.py` | Local feedback/eval/canary rehearsal complete; real production feedback calibration pending |
| Audit trail | `AuditService`, `/api/v1/audit/events`, `/api/v1/audit/retention`, `/api/v1/audit/retention/archive-prune`, local JSONL archive writer, PostgreSQL archive batch writer, UI audit panel, persistence, API-key RBAC/project-scope foundation, trusted SSO/OIDC proxy auth foundation, `ops/security/rehearse_trusted_proxy_auth.py`, approval/query/scheduler/debug/run-step/replay/finding-status RBAC, blocked debug artifact read audit events, finding status change audit events | Local and PostgreSQL archive/prune foundations plus trusted-proxy rehearsal entrypoint complete; direct company IdP validation pending |
| Graph view scalability | `07_GRAPH_VIEW_SCALABILITY_PLAN.md`, SVG graph controls, projection API, `ops/ui/smoke_operator_ui.py`, `tests/unit/ops/test_operator_ui_smoke.py` | Dummy 150-node path, graph controls, SVG renderer hooks, overview/pending/orphan modes, and truncation metadata are locally validated; React Flow decision pending after real graph shape validation |
| Scheduler | `RunScheduler`, API/UI/runbook, viewer/operator RBAC and audit actor capture, PostgreSQL `scheduler_leases` table, lease acquire/release tests, Ubuntu multi-replica note | Periodic run path complete for single-process and PostgreSQL lease-backed multi-worker deployments; external orchestration/Kubernetes CronJob remains an optional platform decision |
| Ubuntu runbook | `README_ubuntu.md`, `docs/runbooks/BACKUP_RESTORE.md`, `ops/backup/verify_backup_set.py`, `ops/load/smoke_load.py`, `ops/integration/run_backend_integration.py`, `ops/rehearsal/run_full_stack_rehearsal.py`, `ops/rehearsal/check_production_readiness.py`, `ops/rehearsal/validate_postgres_migration_rollbacks.py`, `ops/rehearsal/validate_postgres_typed_mirrors.py`, `ops/rehearsal/validate_evidence_example.py`, `ops/rehearsal/production_readiness_evidence.example.json` | Local/server scaffold, readiness checks, backup-set verification, disposable full-stack rehearsal, API restart restore check, smoke-load pass, production-readiness gate reporting, PostgreSQL migration rollback validation, PostgreSQL typed mirror drift validation, observability dashboard manual evidence gate, review-safe manual-evidence template generation, non-passable committed evidence example validation, reviewer metadata, schema-version, non-empty evidence, unique check-id, and UTC review timestamp enforcement for passed manual evidence, reviewed manual-evidence input path, and strict no-failed/no-warning/no-manual release gate complete; company/staging environment rehearsal pending |
| Migration and Helm operation tracks | packaged migrations under `src/req_tracker/storage/migrations/postgres`, `ops/migrations/README.md`, `ops/helm/rune-agent`, `ops/helm/validate_chart.py`, `tests/unit/ops/test_helm_chart.py` | Migration foundation and production-shaped Helm scaffold complete with local structural validation; target-cluster `helm lint/template` and platform-specific values remain pending until Kubernetes environment details are available |
| Eval/security/replay test tracks | `tests/unit/evals`, `tests/contract/test_replay_feedback_api.py`, `tests/contract/test_security_api.py`, `tests/evals/README.md`, `tests/security/README.md`, `tests/replay/README.md` | Current coverage exists; dedicated folders anchored for larger end-to-end fixtures |
| CI | `.github/workflows/ci.yml` runs ruff, mypy, pytest, masking rehearsal, release-blocker coverage, source/model gateway smokes, Helm structural validation, observability asset validation, PostgreSQL migration rollback validation, PostgreSQL typed mirror validation, readiness evidence template smoke, readiness example safety validation, CI gate coverage validation, operator UI graph smoke, and feedback eval rehearsal | Complete for deterministic local gates in GitHub Actions with automated drift detection; disposable Docker/full-stack and company/staging gates remain runbook/readiness responsibilities |

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
- Decide React/React Flow migration after real graph shape validation.
- If Kubernetes or multiple Ubuntu nodes are selected instead of multi-process
  API replicas on one PostgreSQL-backed service, decide whether to keep the
  in-app PostgreSQL scheduler lease or move periodic execution to CronJob or a
  queue worker.
- Run `helm lint ops/helm/rune-agent` and `helm template` with company values
  once Helm and the target Kubernetes policy are available.

## 4. Latest Local Verification

2026-05-12 local verification after runtime metrics, trace-context,
OpenTelemetry export foundation, restricted model payload policy, and
observability asset implementation:

- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: `183 passed, 3 skipped`
- `uv run python ops/observability/validate_observability_assets.py`: passed
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed, including
  metrics surface check with `http_total_requests=7`, `graph_nodes=14`,
  `llm_calls=1`, OpenTelemetry disabled-by-default health status, and
  Prometheus text counters
- `uv run python ops/security/check_release_blockers.py`: passed
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
  all local regression gates passed, while overall readiness remained failed as
  expected because company/staging PostgreSQL, Neo4j, Qdrant, model gateway,
  trusted proxy, artifact storage, OpenTelemetry collector, source,
  Prometheus/Grafana dashboard, backup/restore, and load-test evidence variables
  are not configured in the local workstation environment.

## 5. Completion Gate

The overall production objective is not complete yet. The current repo is a
validated local/dummy, persistence-foundation, backend-interface, source-adapter,
debuggability, runtime-metrics, trace-context propagation, disposable backend
integration, full-stack rehearsal, and operations-rehearsal stage. The next concrete completion gate requires
company/staging PostgreSQL, Neo4j, Qdrant, JIRA/Confluence, SSO/OIDC proxy,
OpenTelemetry collector, Prometheus/Grafana dashboard import, and a real sandbox
model endpoint so integration, replay, backup, restore, load, live-source,
live-provider, and observability validation can run against real organization
dependencies.

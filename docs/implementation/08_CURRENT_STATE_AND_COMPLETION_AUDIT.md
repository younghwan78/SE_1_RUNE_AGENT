# Current State and Completion Audit

Last reviewed: 2026-05-12

This document maps `PRODUCTION_EXECUTION_PLAN.md` requirements to current repo
artifacts and verification evidence. A requirement is complete only when
implementation and a relevant verification path exist in the repository.

## 1. Current Verified Baseline

Latest confirmed commits:

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
- `uv run pytest`: 116 passed, 3 skipped
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
- `uv run python ops/model_gateway/rehearse_model_gateway.py`: failed as expected on this local shell because `MODEL_GATEWAY_ENDPOINT_URL` is unset; output masks API key state and lists missing config
- `uv run python ops/security/rehearse_trusted_proxy_auth.py`: failed as expected on this local shell because `RUNE_API_BASE_URL` and `TRUSTED_PROXY_SECRET` are unset; output masks secret state and lists missing config
- `uv run python ops/security/rehearse_masking_policy.py`: passed, verifying representative sensitive inputs are redacted without printing raw sensitive strings or forbidden patterns
- `uv run pytest tests/unit/ops/test_backup_verify.py`: passed, validating backup-set required files, SHA256 mismatch detection, artifact tar, Qdrant JSON, Neo4j dump marker, and git commit marker checks
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed, including API restart restore and smoke-load pass (`load_smoke.p95_ms` about 3265 ms against a 5000 ms local rehearsal threshold)
- `uv run python ops/evals/run_feedback_eval_rehearsal.py`: passed
- `uv run python ops/rehearsal/check_production_readiness.py`: failed as expected on this local shell because production env/company-staging endpoints are unset; report produced failed env checks and manual-required gates without secret values
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`: local regression gates passed; overall readiness failed as expected because company/staging environment variables and manual evidence are unset
- `uv run python ops/rehearsal/check_production_readiness.py --evidence-file ops/rehearsal/production_readiness_evidence.example.json`: failed as expected on this local shell because production env checks are still unset; manual evidence resolved example manual gates
- `uv run pytest tests/unit/ops/test_production_readiness_check.py`: 6 passed, including manual evidence file loading, complete env/evidence pass behavior, and unknown evidence warning blocking

Latest GitHub verification:

- GitHub Actions `CI` run `25686556799` for `f369177`: completed successfully

## 2. Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Production plan is the source of truth | `PRODUCTION_EXECUTION_PLAN.md`, `docs/implementation/03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md` | Complete |
| Expected repository shape is anchored | `src/req_tracker/*`, `.claude/skills/rune-source-*`, `docs/api/README.md`, `docs/ontology/ONTOLOGY_V1.md`, `ops/migrations/README.md`, `ops/helm/README.md`, `tests/evals/README.md`, `tests/security/README.md`, `tests/replay/README.md` | Complete for implemented and deferred tracks |
| Ontology v1 is documented and executable | `docs/ontology/ONTOLOGY_V1.md`, `src/req_tracker/ontology/models.py`, `tests/contract/test_models.py` | Complete |
| API documentation path exists | `docs/api/README.md`, `src/req_tracker/api/routes/*`, `tests/contract/*`, optional `/openapi.json` with `ENABLE_DOCS=true` | Complete |
| Data and model policies are fixed | `docs/security/DATA_POLICY.md`, `docs/runbooks/MODEL_POLICY.md`, `config/model_profiles.json`, `config/prompt_versions.json`, `src/req_tracker/model_gateway/policy.py`, `ops/security/rehearse_masking_policy.py`, `ops/model_gateway/smoke_model_gateway.py` | Complete for local policy baseline; company model profile approval pending |
| Structured request logging | `src/req_tracker/config/logging.py`, `src/req_tracker/api/app.py`, `tests/contract/test_health_api.py`, `tests/unit/config/test_logging.py` | Complete for JSON request logs with correlation id, user id, method, path, status, and duration |
| Claude Code source-skill boundary for JIRA/Confluence/Email | `.claude/skills/rune-source-*`, `JiraRestSourceAdapter`, `ConfluenceRestSourceAdapter`, `request_with_retry`, `ops/source/smoke_source_adapters.py`, `ops/source/rehearse_company_sources.py`, `ops/source/rehearse_decision_email_export.py`, export adapters, restricted decision/email export policy, `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` | Design/export path complete; JIRA/Confluence REST retry, pagination, permission-warning, local HTTP smoke validation, env-driven company sandbox rehearsal entrypoint, and restricted decision/email export rehearsal entrypoint complete; Email live access and real company sandbox validation pending |
| Dummy/local validation path | `LocalAnalysisWorkflow`, dummy fixtures, API tests, integration test, readiness API, persisted runtime restore test, `ops/security/rehearse_masking_policy.py` | Complete |
| Core contracts | `src/req_tracker/ontology`, `debug`, `approvals`, `feedback`, `audit` models | Complete |
| Model gateway abstraction | `src/req_tracker/model_gateway` with dummy provider, HTTP JSON provider, provider factory, file-backed registry, policy, structured validation retry, fallback trace tests, `ops/model_gateway/smoke_model_gateway.py`, `ops/model_gateway/rehearse_model_gateway.py` | Profile/registry/live-shaped HTTP foundation and env-driven company sandbox rehearsal entrypoint complete; real external provider sandbox validation pending |
| LLM-assisted workflow trace | `LocalAnalysisWorkflow` `llm_assisted_reasoning` stage, `ModelGatewayClient`, `LLMCallTrace`, SQLite restore of `llm_call_traces`, `/api/v1/runs/{run_id}/llm-calls`, debug diff LLM panes | Dummy model-gateway integration complete; live model quality validation pending |
| Debug trace and local artifact store | `src/req_tracker/debug`, `/api/v1/debug/*`, `/api/v1/runs/{run_id}/llm-calls`, `/api/v1/runs/{run_id}/artifacts`, `/api/v1/runs/{run_id}/graph-delta`, `/api/v1/replays/{replay_id}/diff`, approval lineage API, run diff-view API, run debug UI, LLM/graph delta side-by-side panes | Local debug workbench foundation complete; live LLM payload validation pending |
| SQLite state persistence | `SQLiteStateStore`, persistence contract test, restart restore contract test | Complete |
| PostgreSQL migration foundation | `PostgreSQLStateStore`, `001_state_entities.sql`, `003_audit_archive_batches.sql`, migration loader tests | Complete |
| Typed PostgreSQL core table foundation | `002_core_state_tables.sql`, typed mirror upsert/read dispatch, rollback scripts, unit tests, optional `POSTGRES_TEST_DSN` integration test, `ops/integration/run_backend_integration.py` | Foundation complete; disposable Docker PostgreSQL integration passed; company/staging DB rehearsal pending |
| Graph backend | `GraphBackend` protocol, `MemoryGraphBackend`, `Neo4jGraphBackend`, graph projection, traceability chain APIs, optional `NEO4J_TEST_*` integration test, Docker integration runner | Neo4j foundation complete; disposable Docker Neo4j integration passed; company/staging graph rehearsal pending |
| Vector backend | `VectorBackend` protocol, `MemoryVectorBackend`, `QdrantVectorBackend`, optional `QDRANT_TEST_URL` integration test, Docker integration runner | Qdrant foundation complete; disposable Docker Qdrant integration passed; company/staging vector rehearsal pending |
| Approval workflow | approval queue, approve/reject/hold/modify path, graph commit, developer/operator RBAC and project-scope checks | Complete for local and protected API paths |
| Feedback loop | feedback events, eval candidates, improvement candidates, eval gate, controlled review/canary promotion, feedback/eval/improvement RBAC, `ops/evals/run_feedback_eval_rehearsal.py` | Local feedback/eval/canary rehearsal complete; real production feedback calibration pending |
| Audit trail | `AuditService`, `/api/v1/audit/events`, `/api/v1/audit/retention`, `/api/v1/audit/retention/archive-prune`, local JSONL archive writer, PostgreSQL archive batch writer, UI audit panel, persistence, API-key RBAC/project-scope foundation, trusted SSO/OIDC proxy auth foundation, `ops/security/rehearse_trusted_proxy_auth.py`, approval/query/scheduler/debug RBAC, blocked debug artifact read audit events | Local and PostgreSQL archive/prune foundations plus trusted-proxy rehearsal entrypoint complete; direct company IdP validation pending |
| Graph view scalability | `07_GRAPH_VIEW_SCALABILITY_PLAN.md`, SVG graph controls, projection API | Dummy 100+ node path complete; React Flow decision pending |
| Scheduler | process-local `RunScheduler`, API/UI/runbook, viewer/operator RBAC and audit actor capture | Single-process complete; multi-worker orchestration pending |
| Ubuntu runbook | `README_ubuntu.md`, `docs/runbooks/BACKUP_RESTORE.md`, `ops/backup/verify_backup_set.py`, `ops/load/smoke_load.py`, `ops/integration/run_backend_integration.py`, `ops/rehearsal/run_full_stack_rehearsal.py`, `ops/rehearsal/check_production_readiness.py`, `ops/rehearsal/production_readiness_evidence.example.json` | Local/server scaffold, readiness checks, backup-set verification, disposable full-stack rehearsal, API restart restore check, smoke-load pass, production-readiness gate reporting, reviewed manual-evidence input path, and strict no-failed/no-warning/no-manual release gate complete; company/staging environment rehearsal pending |
| Migration and Helm operation tracks | packaged migrations under `src/req_tracker/storage/migrations/postgres`, `ops/migrations/README.md`, `ops/helm/README.md` | Migration foundation complete; Helm packaging intentionally deferred until platform details are known |
| Eval/security/replay test tracks | `tests/unit/evals`, `tests/contract/test_replay_feedback_api.py`, `tests/contract/test_security_api.py`, `tests/evals/README.md`, `tests/security/README.md`, `tests/replay/README.md` | Current coverage exists; dedicated folders anchored for larger end-to-end fixtures |
| CI | `.github/workflows/ci.yml` | Complete |

## 3. Remaining Implementation Backlog

### P0: Production Persistence Hardening

- Extend typed PostgreSQL repositories beyond the current core mirror tables as
  API query needs grow.
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

## 4. Completion Gate

The overall production objective is not complete yet. The current repo is a
validated local/dummy, persistence-foundation, backend-interface, source-adapter,
debuggability, disposable backend integration, full-stack rehearsal, and
operations-rehearsal stage. The next concrete completion gate requires
company/staging PostgreSQL, Neo4j, Qdrant, JIRA/Confluence, SSO/OIDC proxy, and
a real sandbox model endpoint so integration, replay, backup, restore, load,
live-source, and live-provider validation can run against real organization
dependencies.

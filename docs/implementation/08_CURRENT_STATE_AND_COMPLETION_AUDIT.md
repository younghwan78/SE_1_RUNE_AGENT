# Current State and Completion Audit

Last reviewed: 2026-05-12

This document maps `PRODUCTION_EXECUTION_PLAN.md` requirements to current repo
artifacts and verification evidence. A requirement is complete only when
implementation and a relevant verification path exist in the repository.

## 1. Current Verified Baseline

Latest confirmed commits:

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
- `uv run pytest`: 87 passed, 3 skipped
- `uv run python ops/integration/run_backend_integration.py`: 3 passed
- `uv run python ops/source/smoke_source_adapters.py`: passed
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed
- `uv run python ops/evals/run_feedback_eval_rehearsal.py`: passed

Latest GitHub verification:

- GitHub Actions `CI` run for `80e4369`: completed successfully

## 2. Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Production plan is the source of truth | `PRODUCTION_EXECUTION_PLAN.md`, `docs/implementation/03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md` | Complete |
| Claude Code source-skill boundary for JIRA/Confluence/Email | `.claude/skills/rune-source-*`, `JiraRestSourceAdapter`, `ConfluenceRestSourceAdapter`, `request_with_retry`, `ops/source/smoke_source_adapters.py`, export adapters, restricted decision/email export policy, `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` | Design/export path complete; JIRA/Confluence REST retry, pagination, permission-warning, and local HTTP smoke validation complete; restricted decision/email file path complete; Email live access and real company sandbox validation pending |
| Dummy/local validation path | `LocalAnalysisWorkflow`, dummy fixtures, API tests, integration test | Complete |
| Core contracts | `src/req_tracker/ontology`, `debug`, `approvals`, `feedback`, `audit` models | Complete |
| Model gateway abstraction | `src/req_tracker/model_gateway` with dummy provider, HTTP JSON provider, provider factory, file-backed registry, policy, structured validation retry, fallback trace tests, `ops/model_gateway/smoke_model_gateway.py` | Profile/registry/live-shaped HTTP foundation complete; real external provider sandbox validation pending |
| Debug trace and local artifact store | `src/req_tracker/debug`, `/api/v1/debug/*`, approval lineage API, run diff-view API, run debug UI, LLM/graph delta side-by-side panes | Local debug workbench foundation complete; live LLM payload validation pending |
| SQLite state persistence | `SQLiteStateStore`, persistence contract test | Complete |
| PostgreSQL migration foundation | `PostgreSQLStateStore`, `001_state_entities.sql`, `003_audit_archive_batches.sql`, migration loader tests | Complete |
| Typed PostgreSQL core table foundation | `002_core_state_tables.sql`, typed mirror upsert/read dispatch, rollback scripts, unit tests, optional `POSTGRES_TEST_DSN` integration test, `ops/integration/run_backend_integration.py` | Foundation complete; disposable Docker PostgreSQL integration passed; company/staging DB rehearsal pending |
| Graph backend | `GraphBackend` protocol, `MemoryGraphBackend`, `Neo4jGraphBackend`, graph projection, traceability chain APIs, optional `NEO4J_TEST_*` integration test, Docker integration runner | Neo4j foundation complete; disposable Docker Neo4j integration passed; company/staging graph rehearsal pending |
| Vector backend | `VectorBackend` protocol, `MemoryVectorBackend`, `QdrantVectorBackend`, optional `QDRANT_TEST_URL` integration test, Docker integration runner | Qdrant foundation complete; disposable Docker Qdrant integration passed; company/staging vector rehearsal pending |
| Approval workflow | approval queue, approve/reject/hold/modify path, graph commit | Complete for local backend |
| Feedback loop | feedback events, eval candidates, improvement candidates, eval gate, controlled review/canary promotion, `ops/evals/run_feedback_eval_rehearsal.py` | Local feedback/eval/canary rehearsal complete; real production feedback calibration pending |
| Audit trail | `AuditService`, `/api/v1/audit/events`, `/api/v1/audit/retention`, `/api/v1/audit/retention/archive-prune`, local JSONL archive writer, PostgreSQL archive batch writer, UI audit panel, persistence, API-key RBAC/project-scope foundation, trusted SSO/OIDC proxy auth foundation, blocked debug artifact read audit events | Local and PostgreSQL archive/prune foundations complete; direct company IdP validation pending |
| Graph view scalability | `07_GRAPH_VIEW_SCALABILITY_PLAN.md`, SVG graph controls, projection API | Dummy 100+ node path complete; React Flow decision pending |
| Scheduler | process-local `RunScheduler`, API/UI/runbook | Single-process complete; multi-worker orchestration pending |
| Ubuntu runbook | `README_ubuntu.md`, `docs/runbooks/BACKUP_RESTORE.md`, `ops/load/smoke_load.py`, `ops/integration/run_backend_integration.py`, `ops/rehearsal/run_full_stack_rehearsal.py` | Local/server scaffold and disposable full-stack rehearsal complete; company/staging environment rehearsal pending |
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
- Keep MCP/REST/export selection inside Claude Code source skills and local
  config, not in core Python workflow code.
- Map source permission results to project authorization policy after real
  company identity rules are available.
- Extend the same live-source validation path to a real company Confluence
  sandbox space.

### P3: Model Provider and Debug Workbench

- Run retry/fallback behavior against real external or company model provider sandboxes.
- Validate LLM payload diff panes with real sandbox model calls once a model
  endpoint is available.
- Calibrate eval thresholds and canary policy with real reviewer feedback once
  production proposals are reviewed.

### P4: Security and Operations

- Rehearse trusted-proxy auth behind a real company SSO/OIDC reverse proxy and
  replace it with direct IdP token validation only if required.
- Run backup/restore and load rehearsals against company/staging PostgreSQL,
  Neo4j, Qdrant, and artifact store environments.
- Decide React/React Flow migration after real graph shape validation.

## 4. Completion Gate

The overall production objective is not complete yet. The current repo is a
validated local/dummy, persistence-foundation, backend-interface, source-adapter,
debuggability, and operations-rehearsal stage. The next concrete completion gate
requires disposable production-like services for PostgreSQL, Neo4j, Qdrant,
JIRA/Confluence, and a sandbox model endpoint so integration, replay, backup,
restore, load, and live-provider validation can run against real dependencies.

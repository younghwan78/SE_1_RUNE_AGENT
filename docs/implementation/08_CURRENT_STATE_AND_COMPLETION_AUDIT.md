# Current State and Completion Audit

Last reviewed: 2026-05-11

This document maps `PRODUCTION_EXECUTION_PLAN.md` requirements to current repo
artifacts and verification evidence. A requirement is complete only when
implementation and a relevant verification path exist in the repository.

## 1. Current Verified Baseline

Latest confirmed commits:

- `204983f Add operations backup and load rehearsal assets`
- `d760f79 Add audit retention status policy`
- `a4b6d0c Add debug artifact access policy`
- `941fc96 Add debug diff workbench view`
- `58a459e Add HTTP model provider registry foundation`

Latest local verification:

- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run pytest`: 74 passed, 3 skipped

Latest GitHub verification:

- GitHub Actions `CI` run for `204983f`: completed successfully

## 2. Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Production plan is the source of truth | `PRODUCTION_EXECUTION_PLAN.md`, `docs/implementation/03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md` | Complete |
| Claude Code source-skill boundary for JIRA/Confluence/Email | `.claude/skills/rune-source-*`, `JiraRestSourceAdapter`, `ConfluenceRestSourceAdapter`, `request_with_retry`, export adapters, restricted decision/email export policy, `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` | Design/export path complete; JIRA/Confluence REST retry and permission-warning foundation complete; restricted decision/email file path complete; Email live access pending |
| Dummy/local validation path | `LocalAnalysisWorkflow`, dummy fixtures, API tests, integration test | Complete |
| Core contracts | `src/req_tracker/ontology`, `debug`, `approvals`, `feedback`, `audit` models | Complete |
| Model gateway abstraction | `src/req_tracker/model_gateway` with dummy provider, HTTP JSON provider, provider factory, file-backed registry, policy, structured validation retry, fallback trace tests | Profile/registry/live HTTP foundation complete; live provider sandbox validation pending |
| Debug trace and local artifact store | `src/req_tracker/debug`, `/api/v1/debug/*`, approval lineage API, run diff-view API, run debug UI, LLM/graph delta side-by-side panes | Local debug workbench foundation complete; live LLM payload validation pending |
| SQLite state persistence | `SQLiteStateStore`, persistence contract test | Complete |
| PostgreSQL migration foundation | `PostgreSQLStateStore`, `001_state_entities.sql`, migration loader tests | Complete |
| Typed PostgreSQL core table foundation | `002_core_state_tables.sql`, typed mirror upsert/read dispatch, rollback scripts, unit tests, optional `POSTGRES_TEST_DSN` integration test | Foundation complete; production DB environment validation pending |
| Graph backend | `GraphBackend` protocol, `MemoryGraphBackend`, `Neo4jGraphBackend`, graph projection, traceability chain APIs, optional `NEO4J_TEST_*` integration test | Neo4j foundation complete; production DB environment validation pending |
| Vector backend | `VectorBackend` protocol, `MemoryVectorBackend`, `QdrantVectorBackend`, optional `QDRANT_TEST_URL` integration test | Qdrant foundation complete; production DB environment validation pending |
| Approval workflow | approval queue, approve/reject/hold/modify path, graph commit | Complete for local backend |
| Feedback loop | feedback events, eval candidates, improvement candidates, eval gate | Local foundation complete; real eval datasets/canary pending |
| Audit trail | `AuditService`, `/api/v1/audit/events`, `/api/v1/audit/retention`, `/api/v1/audit/retention/archive-prune`, local JSONL archive writer, UI audit panel, persistence, API-key RBAC/project-scope foundation, blocked debug artifact read audit events | Local archive/prune foundation complete; SSO and PostgreSQL-backed archive/prune job pending |
| Graph view scalability | `07_GRAPH_VIEW_SCALABILITY_PLAN.md`, SVG graph controls, projection API | Dummy 100+ node path complete; React Flow decision pending |
| Scheduler | process-local `RunScheduler`, API/UI/runbook | Single-process complete; multi-worker orchestration pending |
| Ubuntu runbook | `README_ubuntu.md`, `docs/runbooks/BACKUP_RESTORE.md`, `ops/load/smoke_load.py` | Local/server scaffold and rehearsal assets complete; real environment rehearsal pending |
| CI | `.github/workflows/ci.yml` | Complete |

## 3. Remaining Implementation Backlog

### P0: Production Persistence Hardening

- Run the optional PostgreSQL integration test in a disposable production-like
  database environment.

### P1: Production Backend Expansion

- Run the optional Neo4j integration test in a disposable production-like
  database environment.
- Run the optional Qdrant integration test in a disposable production-like
  database environment.
- Keep memory backends as deterministic contract-test baselines.

### P2: JIRA Production Connector

- Run JIRA connector against a disposable or sandbox JIRA project.
- Keep MCP/REST/export selection inside Claude Code source skills and local
  config, not in core Python workflow code.
- Map source permission results to project authorization policy after real
  company identity rules are available.
- Extend the same live-source validation path to Confluence sandbox access.

### P3: Model Provider and Debug Workbench

- Run retry/fallback behavior against live model provider sandboxes.
- Validate LLM payload diff panes with real sandbox model calls once a model
  endpoint is available.

### P4: Security and Operations

- Replace API-key RBAC/project-scope foundation with OIDC/SSO-backed group mapping.
- Add PostgreSQL-backed audit archive/prune job.
- Run backup/restore and load rehearsals against disposable production-like
  PostgreSQL, Neo4j, Qdrant, and artifact store environments.
- Decide React/React Flow migration after real graph shape validation.

## 4. Completion Gate

The overall production objective is not complete yet. The current repo is a
validated local/dummy, persistence-foundation, backend-interface, source-adapter,
debuggability, and operations-rehearsal stage. The next concrete completion gate
requires disposable production-like services for PostgreSQL, Neo4j, Qdrant,
JIRA/Confluence, and a sandbox model endpoint so integration, replay, backup,
restore, load, and live-provider validation can run against real dependencies.

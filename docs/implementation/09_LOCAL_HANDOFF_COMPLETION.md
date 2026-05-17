# Local Handoff Completion

This document defines the final local handoff goal for the current repository.
It intentionally excludes company-only validation that requires internal
PostgreSQL, Neo4j, Qdrant, JIRA, Confluence, SSO/OIDC, model gateway,
observability, backup, or approved decision/email data.

## 1. Local Goal

Finish everything that can be completed on the current workstation before the
project moves into company/staging validation.

Concrete deliverables:

- implementation is aligned to `PRODUCTION_EXECUTION_PLAN.md`
- local/dummy production-shaped workflow is executable
- source adapters can be selected without code changes
- source-skill export files can be rehearsed without company systems
- debug, replay, approval, feedback, audit, scheduler, and graph views have
  local validation paths
- local release gates are executable and covered by CI
- company/staging gates are explicitly listed with commands and evidence needs
- `MEMORY.md` records the handoff state for the next environment

## 2. Current Local Completion Checklist

| Area | Evidence | Local status |
| --- | --- | --- |
| Source of truth | `PRODUCTION_EXECUTION_PLAN.md` | Complete |
| Repository memory | `MEMORY.md` | Complete |
| Implementation audit | `docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md` | Complete |
| API contract | `tests/contract/test_openapi_surface.py`, `docs/api/README.md` | Complete |
| Ontology and Pydantic contracts | `tests/contract/test_models.py` | Complete |
| Local workflow | `LocalAnalysisWorkflow`, run API tests | Complete |
| Source adapter selection | `src/req_tracker/adapters/factory.py`, `DATASOURCE_MODE` | Complete |
| Source skill export dry-run | `ops/source/rehearse_skill_export_sources.py` | Complete |
| Source boundary check | `ops/source/validate_source_boundaries.py` | Complete |
| JIRA/Confluence REST adapter foundation | adapter unit tests and source smoke | Complete |
| Restricted decision/email export policy | `ops/source/rehearse_decision_email_export.py` | Complete for local/export path |
| Model gateway local foundation | `ops/model_gateway/smoke_model_gateway.py` | Complete |
| Approval and graph commit safety | approval contract/security tests | Complete |
| Feedback/eval/improvement loop | `ops/evals/run_feedback_eval_rehearsal.py` | Complete |
| Debug and replay workbench | debug/replay contract tests | Complete |
| Persistence foundation | SQLite/PostgreSQL tests and migration validators, including dashboard preference/assignment, schedule config, source sync cursor, LLM call trace, replay result, and improvement decision typed mirrors | Complete |
| Disposable backend integration | `ops/integration/run_backend_integration.py` | Complete; latest 2026-05-17 workstation run passed with Docker Desktop Linux engine available |
| Full-stack rehearsal | `ops/rehearsal/run_full_stack_rehearsal.py` | Complete; latest 2026-05-17 workstation run passed with Docker Desktop Linux engine available |
| Release blocker gate | `ops/security/check_release_blockers.py` | Complete locally |
| Incident response runbook | `docs/runbooks/INCIDENT_RESPONSE.md`, `tests/unit/ops/test_runbook_docs.py` | Complete locally |
| Dashboard state RBAC | `docs/security/RBAC_MATRIX.md`, `tests/contract/test_dashboard_api.py` | Complete locally |
| Readiness template | `ops/rehearsal/check_production_readiness.py --write-evidence-template -` | Complete |
| CI gate coverage | `.github/workflows/ci.yml`, `ops/rehearsal/validate_ci_gate_coverage.py` | Complete |

## 3. Local Gate Command Set

Run these before handing off a new local change:

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv run python ops/security/rehearse_masking_policy.py
uv run python ops/security/check_release_blockers.py
uv run python ops/source/validate_source_boundaries.py
uv run python ops/source/smoke_source_adapters.py
uv run python ops/source/rehearse_skill_export_sources.py
uv run python ops/model_gateway/smoke_model_gateway.py
uv run python ops/helm/validate_chart.py
uv run python ops/observability/validate_observability_assets.py
uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py
uv run python ops/rehearsal/validate_postgres_typed_mirrors.py
uv run python ops/rehearsal/validate_evidence_example.py
uv run python ops/rehearsal/validate_ci_gate_coverage.py
uv run python ops/ui/smoke_operator_ui.py
uv run python ops/evals/run_feedback_eval_rehearsal.py
```

Docker-backed local gates:

```bash
uv run python ops/integration/run_backend_integration.py
uv run python ops/rehearsal/run_full_stack_rehearsal.py
```

The GitHub CI intentionally runs deterministic local gates and omits the
Docker-backed integration/full-stack gates where documented by
`ops/rehearsal/validate_ci_gate_coverage.py`.

On a Windows workstation, start Docker Desktop with the Linux engine before
running these two Docker-backed gates. If Docker is unavailable, treat these as
environment-blocked verification gates rather than evidence of application
logic failure. `check_production_readiness.py --run-local-gates` reports this
case as `manual_required` with `docker_unavailable` evidence.

Latest 2026-05-17 local evidence with Docker Desktop Linux engine available:

- `uv run python ops/integration/run_backend_integration.py`: passed with
  disposable PostgreSQL, Neo4j, and Qdrant containers.
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py`: passed with API
  restart restore, metrics surface check, audit event persistence, and local
  smoke-load threshold coverage.
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`:
  local regression gates passed; overall readiness still failed with summary
  `failed=7`, `manual_required=10`, `passed=2`, `warning=0` because
  company/staging environment variables and manual evidence are not configured
  on this workstation.
- Commit `c52572d Persist scheduler configuration state` added restart-safe
  scheduler configuration persistence and PostgreSQL typed mirror coverage for
  `schedule_configs`; GitHub Actions `CI` run `25967994338` passed.
- Commit `ba9a973 Refresh audit after scheduler persistence` refreshed the
  audit/handoff evidence; GitHub Actions `CI` run `25968026265` passed.
- Commit `ee3dea2 Document schedule configuration persistence` updated the API
  documentation for `PUT /api/v1/schedule` restart-safe persistence and the
  `schedule_configs` typed mirror; GitHub Actions `CI` run `25968150339`
  passed.
- Latest full local regression after scheduler persistence: `uv run pytest`
  reported `242 passed, 3 skipped`; readiness local regression gates passed,
  while the overall readiness summary remains
  `failed=7`, `manual_required=10`, `passed=2`, `warning=0` until
  company/staging evidence is supplied.

## 4. Company/Staging Gates

These cannot be completed on the current workstation without company systems.
They must be handled as reviewed evidence, not as local TODOs.

| Gate | Command or evidence path | Required evidence |
| --- | --- | --- |
| PostgreSQL staging | `POSTGRES_TEST_DSN` or full-stack rehearsal | reviewed run id or artifact |
| Neo4j staging | `NEO4J_TEST_URI` or full-stack rehearsal | reviewed run id or artifact |
| Qdrant staging | `QDRANT_TEST_URL` or full-stack rehearsal | reviewed run id or artifact |
| JIRA sandbox | `uv run python ops/source/rehearse_company_sources.py --source jira` | masked JSON output |
| Confluence sandbox | `uv run python ops/source/rehearse_company_sources.py --source confluence` | masked JSON output |
| Model gateway sandbox | `uv run python ops/model_gateway/rehearse_model_gateway.py` | masked JSON output |
| Trusted proxy SSO/OIDC | `uv run python ops/security/rehearse_trusted_proxy_auth.py` | masked JSON output |
| Decision/email policy | `uv run python ops/source/rehearse_decision_email_export.py` | approved export rehearsal output |
| Observability | Prometheus scrape and Grafana import | dashboard/scrape evidence |
| Backup/restore/load | `docs/runbooks/BACKUP_RESTORE.md`, `ops/load/smoke_load.py` | reviewed restore/load output |
| Helm target cluster, if selected | `helm lint/template` in target platform | reviewed platform output |

Generate the initial evidence file:

```bash
uv run python ops/rehearsal/check_production_readiness.py \
  --write-evidence-template /secure/path/production_readiness_evidence.json
```

Generate the matching command/evidence collection plan:

```bash
uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown \
  --env-file /secure/path/staging.env \
  --output /secure/path/staging_evidence_plan.md
```

After replacing TODO entries with reviewed evidence:

```bash
uv run python ops/rehearsal/check_production_readiness.py \
  --env-file /secure/path/staging.env \
  --evidence-file /secure/path/production_readiness_evidence.json
```

Before declaring the overall implementation goal complete, run the top-level
completion audit with the same reviewed evidence file:

```bash
uv run python ops/rehearsal/check_goal_completion.py \
  --env-file /secure/path/staging.env \
  --run-local-gates \
  --evidence-file /secure/path/production_readiness_evidence.json
```

## 5. Source Skill Export Dry-Run

Use this local command to prove that skill-produced source files can drive the
same ingestion workflow as production source adapters:

```bash
uv run python ops/source/rehearse_skill_export_sources.py
```

This command validates:

- `jira_export`
- `confluence_export`
- `decision_email_export`
- datasource factory wiring
- runtime workflow source-adapter injection
- persisted `source_sync_cursors`
- `/api/v1/debug/source-cursors`

It uses synthetic local export files only and does not use company endpoints,
tokens, MCP tool names, or mailbox data.

## 6. Final Local Status

The current repository should be treated as:

- complete for local/dummy production-shaped foundation
- complete for source-skill/export handoff rehearsal
- complete for deterministic CI/local release gates
- complete for Docker-backed disposable backend and full-stack rehearsal scripts,
  with latest 2026-05-17 local pass evidence after Docker Desktop Linux engine
  was started
- complete for restart-safe scheduler configuration persistence in local
  SQLite and PostgreSQL typed mirror foundations
- incomplete for company/staging production readiness until reviewed external
  evidence is attached

Do not mark the broader production goal complete until
`docs/implementation/08_CURRENT_STATE_AND_COMPLETION_AUDIT.md` and the
production readiness evidence file show all company/staging gates as reviewed
and passed.

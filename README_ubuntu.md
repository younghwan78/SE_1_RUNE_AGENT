# Ubuntu Server Runbook

This runbook is for running the current dummy/local production scaffold on an internal Ubuntu server.

## 1. Install Runtime

```bash
sudo apt-get update
sudo apt-get install -y curl git
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

## 2. Checkout and Sync

```bash
sudo mkdir -p /opt/rune-agent
sudo chown "$USER":"$USER" /opt/rune-agent
git clone https://github.com/younghwan78/SE_1_RUNE_AGENT.git /opt/rune-agent
cd /opt/rune-agent
uv sync
```

## 3. Configure Environment

```bash
cp .env.example .env
cp ops/rehearsal/staging.env.example /secure/path/staging.env
chmod 600 .env /secure/path/staging.env
mkdir -p /var/lib/rune-agent/artifacts
```

Use `.env` for the running service. Use `/secure/path/staging.env` for
readiness, evidence-plan, and handoff-bundle rehearsals after filling endpoint
and secret values from the company secret store. The staging template sets
`DEPLOYMENT_TARGET=ubuntu` and `KUBERNETES_DEPLOYMENT=false`; change those only
when preparing Kubernetes-specific Helm evidence.

Recommended initial server `.env`:

```env
REQ_TRACKER_ENV=production
DATASOURCE_MODE=dummy
SOURCE_EXPORT_PATH=
JIRA_BASE_URL=
JIRA_TOKEN=
JIRA_JQL=
CONFLUENCE_BASE_URL=
CONFLUENCE_TOKEN=
CONFLUENCE_SPACE_KEY=
CONFLUENCE_CQL=
GRAPH_BACKEND=memory
NEO4J_URI=
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j
VECTOR_BACKEND=memory
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=rune_chunks
QDRANT_VECTOR_SIZE=64
MODEL_GATEWAY_MODE=dummy
ARTIFACT_STORE=local
ARTIFACT_ROOT=/var/lib/rune-agent/artifacts
AUTH_MODE=trusted_proxy
TRUSTED_PROXY_SECRET=
TRUSTED_DEFAULT_ROLE=viewer
TRUSTED_GROUP_ROLE_MAP='{"rune-viewers":"viewer","rune-developers":"developer","rune-operators":"operator","rune-admins":"admin"}'
STATE_STORE=sqlite
SQLITE_STATE_PATH=/var/lib/rune-agent/rune_state.sqlite3
POSTGRES_DSN=
LOG_LEVEL=INFO
OTEL_ENABLED=false
OTEL_SERVICE_NAME=rune-agent-api
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_EXPORTER_OTLP_INSECURE=true
ENABLE_DOCS=false
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_SECONDS=3600
SCHEDULER_PROJECT_KEY=RUNE_CAM_ALPHA
SCHEDULER_SCENARIO=RUNE_MULTI_SOURCE
SCHEDULER_LEASE_NAME=rune-periodic-analysis
SCHEDULER_LEASE_TTL_SECONDS=300
```

For actual company deployment, keep JIRA, Confluence, and Email credentials outside this repo and expose them through the company-approved Claude Code skill/MCP setup.
`DATASOURCE_MODE` supports `dummy`, `jira_export`, `confluence_export`,
`decision_email_export`, `jira_rest`, and `confluence_rest`. Export modes read
the skill-produced file at `SOURCE_EXPORT_PATH`; REST modes require the matching
base URL/token settings above.

When using `AUTH_MODE=trusted_proxy`, terminate OIDC/SAML at a company-approved
reverse proxy and inject `x-rune-user`, `x-rune-groups`, `x-rune-projects`, and
`x-rune-trusted-secret`. The proxy must strip incoming client-supplied versions
of these headers before adding trusted values.

After the staging API is running behind the trusted proxy boundary, rehearse the
RBAC contract:

```bash
export RUNE_API_BASE_URL=https://rune-agent.example.com
export TRUSTED_PROXY_SECRET=<from-secret-store>
export RUNE_PROJECT_KEY=RUNE_CAM_ALPHA
uv run python ops/security/rehearse_trusted_proxy_auth.py
```

The rehearsal output masks the shared secret and checks viewer, developer,
operator, and project-scope behavior without mutating data.

To use PostgreSQL instead of SQLite, create the database/user with your company
standard policy and switch only these values:

```env
STATE_STORE=postgres
POSTGRES_DSN=postgresql://rune:${RUNE_POSTGRES_PASSWORD}@127.0.0.1:5432/rune_agent
```

On startup, the app applies packaged PostgreSQL migrations through
`schema_migrations` and stores production-shaped contract payloads in
`state_entities`. Audit archive/prune stores archive batches in
`audit_archive_batches` and deletes pruned audit rows from the PostgreSQL state
tables. When `STATE_STORE=postgres`, periodic scheduler workers use the
`scheduler_leases` table so multiple API replicas do not start the same
scheduled run at the same interval.

## 4. Smoke Test

```bash
cd /opt/rune-agent
uv run pytest
uv run uvicorn req_tracker.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

In another shell:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/ready
curl -s -H "x-rune-trusted-secret: $TRUSTED_PROXY_SECRET" \
  -H "x-rune-user: smoke.operator@example.com" \
  -H "x-rune-groups: rune-operators" \
  http://127.0.0.1:8000/api/v1/metrics
curl -s -H "x-rune-trusted-secret: $TRUSTED_PROXY_SECRET" \
  -H "x-rune-user: smoke.operator@example.com" \
  -H "x-rune-groups: rune-operators" \
  http://127.0.0.1:8000/api/v1/metrics/summary
curl -s -H "x-rune-trusted-secret: $TRUSTED_PROXY_SECRET" \
  -H "x-rune-user: smoke.operator@example.com" \
  -H "x-rune-groups: rune-operators" \
  -H "x-rune-projects: RUNE_CAM_ALPHA" \
  -X POST http://127.0.0.1:8000/api/v1/schedule/run-now
curl -s -H "x-rune-trusted-secret: $TRUSTED_PROXY_SECRET" \
  -H "x-rune-user: smoke.viewer@example.com" \
  -H "x-rune-groups: rune-viewers" \
  -H "x-rune-projects: RUNE_CAM_ALPHA" \
  http://127.0.0.1:8000/api/v1/schedule
curl -s -H "x-rune-trusted-secret: $TRUSTED_PROXY_SECRET" \
  -H "x-rune-user: smoke.developer@example.com" \
  -H "x-rune-groups: rune-developers" \
  -H "x-rune-projects: RUNE_CAM_ALPHA" \
  http://127.0.0.1:8000/api/v1/debug/runs
```

Run a small API load smoke after the service is up:

```bash
uv run python ops/load/smoke_load.py --base-url http://127.0.0.1:8000 --runs 5
```

Validate the packaged Prometheus scrape config, alert rules, and Grafana
dashboard before handing them to the platform team:

```bash
uv run python ops/observability/validate_observability_assets.py
```

The Prometheus starter config scrapes `/api/v1/metrics` from
`127.0.0.1:8000`. Change the target in the deployment environment, not by
committing company-local hostnames or credentials.

Run the local model-gateway fallback smoke without a real model endpoint:

```bash
uv run python ops/model_gateway/smoke_model_gateway.py
```

Run a model gateway rehearsal against a company-approved sandbox endpoint:

```bash
export MODEL_GATEWAY_ENDPOINT_URL=https://models.example.com/v1/complete
export MODEL_GATEWAY_API_KEY=<from-secret-store>
export MODEL_GATEWAY_PROFILE_ID=company-sandbox
uv run python ops/model_gateway/rehearse_model_gateway.py
```

The rehearsal output masks secrets and includes trace hashes, structured
validation status, and provider-reported token/cost usage for the public
internal probe payload.

Run local source-adapter smoke without company systems:

```bash
uv run python ops/source/smoke_source_adapters.py
```

Run local source-skill export rehearsal without company systems:

```bash
uv run python ops/source/rehearse_skill_export_sources.py
```

This proves that `DATASOURCE_MODE=jira_export`, `confluence_export`, and
`decision_email_export` can drive the API workflow from skill-produced export
files and persist source cursor debug state.

Run source rehearsals against company-approved sandbox systems:

```bash
export JIRA_BASE_URL=https://jira.example.com
export JIRA_TOKEN=<from-secret-store>
export JIRA_PROJECT_KEY=CAM
export CONFLUENCE_BASE_URL=https://confluence.example.com
export CONFLUENCE_TOKEN=<from-secret-store>
export CONFLUENCE_SPACE_KEY=CAM
uv run python ops/source/rehearse_company_sources.py --source all
```

The rehearsal output masks tokens and reports only artifact shape summaries,
warnings, and counts.

Run the restricted decision/email export rehearsal for approved decision
archives or limited mailbox exports:

```bash
export RUNE_EMAIL_EXPORT_PATH=/secure/exports/decision_email.jsonl
export RUNE_PROJECT_KEY=RUNE_CAM_ALPHA
uv run python ops/source/rehearse_decision_email_export.py
```

The rehearsal accepts only approved decision-source artifacts and reports broad
mailbox artifacts as skipped warnings.

Run disposable backend integration tests on a development server with Docker:

```bash
uv run python ops/integration/run_backend_integration.py
```

Run a production-shaped API rehearsal against those disposable backends:

```bash
uv run python ops/rehearsal/run_full_stack_rehearsal.py
```

The full-stack rehearsal includes readiness, analysis, approval commit, graph
projection, audit retention, API restart restore, and a small smoke-load pass.

Run feedback/eval/canary/rollback rehearsal:

```bash
uv run python ops/evals/run_feedback_eval_rehearsal.py
```

Run masking policy rehearsal:

```bash
uv run python ops/security/rehearse_masking_policy.py
```

### Production Readiness

Check release-readiness gates:

```bash
uv run python ops/rehearsal/check_production_readiness.py
```

The checker reports missing production environment variables and separates
local gates from company/staging rehearsals that must be run against real
PostgreSQL, Neo4j, Qdrant, JIRA, Confluence, SSO/OIDC, model gateway, backup,
restore, load-test targets, and the Prometheus/Grafana observability stack. Use
`--run-local-gates` on a development or staging host when you want it to execute
the local regression command list. The release gate passes only when there are
no failed, warning, or manual-required checks.

Generate a review-safe evidence template from the currently unresolved manual
gates:

```bash
uv run python ops/rehearsal/check_production_readiness.py \
  --write-evidence-template /secure/path/production_readiness_evidence.json
```

Generate a concrete collection plan for the same unresolved company/staging
gates:

```bash
uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown \
  --env-file /secure/path/staging.env \
  --output /secure/path/staging_evidence_plan.md
```

The plan lists each unresolved gate, required environment variables, the
recommended rehearsal command, the expected evidence artifact, and the relevant
runbook. It masks current environment evidence and must not be used to store
secrets.

The generated template intentionally marks every unresolved gate as `failed`
until a release owner replaces the TODO fields with reviewed CI/artifact IDs or
approval records. If any manual evidence entry is marked `passed`, the evidence
file must also include non-TODO top-level `reviewed_by` and `reviewed_at`
metadata, `schema_version: "v1"`, a non-empty evidence array with at least one
traceable reference such as `artifact:...`, `github-actions:...`,
`staging-ci:...`, `run:...`, or `approval:...`, and an ISO-8601 UTC
`reviewed_at` timestamp. Each `check_id` may appear only once. Validate that
the committed example file is still non-passable:

```bash
uv run python ops/rehearsal/validate_evidence_example.py
```

Validate that PostgreSQL typed mirror specs still match packaged migration DDL:

```bash
uv run python ops/rehearsal/validate_postgres_typed_mirrors.py
```

Validate that every packaged PostgreSQL migration has a rollback script covering
its created tables:

```bash
uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py
```

Validate observability assets:

```bash
uv run python ops/observability/validate_observability_assets.py
```

Build a single release handoff bundle for review:

```bash
uv run python ops/rehearsal/build_handoff_bundle.py \
  --allow-incomplete \
  --env-file /secure/path/staging.env \
  --evidence-file /secure/path/production_readiness_evidence.json \
  --run-local-gates \
  --output-dir /secure/path/rune_handoff_bundle
```

Use `--allow-incomplete` while the bundle is still collecting company/staging
evidence. Remove it only when the bundle is expected to represent a final
release decision. Validate the generated bundle before review:

```bash
uv run python ops/rehearsal/validate_handoff_bundle.py \
  /secure/path/rune_handoff_bundle
```

The validator checks manifest/report consistency, required artifact presence,
JSON schema shape, staging evidence plan structure, and
manual-evidence-template coverage for every `manual_required` readiness gate.
The manifest includes `blocker_summary` from the goal-completion report:
`local_action_required` should be zero before handoff from a local workstation,
and `company_or_staging_evidence_required` shows the blockers that still need
company/staging endpoints or reviewed evidence. The validator rejects
`blocker_summary_mismatch` when the manifest and goal-completion report differ.

After real staging rehearsals, run:

```bash
uv run python ops/rehearsal/check_production_readiness.py \
  --run-local-gates \
  --env-file /secure/path/staging.env \
  --evidence-file /secure/path/production_readiness_evidence.json
```

Use `RUNE_IT_POSTGRES_PORT`, `RUNE_IT_NEO4J_BOLT_PORT`, and
`RUNE_IT_QDRANT_HTTP_PORT` if the default local ports conflict with existing
services.

## 5. systemd Service

Create `/etc/systemd/system/rune-agent.service`:

```ini
[Unit]
Description=SE 1 RUNE Agent API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/rune-agent
EnvironmentFile=/opt/rune-agent/.env
ExecStart=/home/ubuntu/.local/bin/uv run uvicorn req_tracker.api.app:create_app --factory --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rune-agent
sudo systemctl status rune-agent
journalctl -u rune-agent -f
```

## 6. Operations

Check scheduler:

```bash
curl -s http://127.0.0.1:8000/api/v1/schedule
```

Change interval to 30 minutes:

```bash
curl -s -X PUT http://127.0.0.1:8000/api/v1/schedule \
  -H 'content-type: application/json' \
  -d '{"enabled":true,"interval_seconds":1800,"project_key":"RUNE_CAM_ALPHA","scenario":"RUNE_MULTI_SOURCE","run_id_prefix":"sched","lease_name":"rune-periodic-analysis","lease_ttl_seconds":300}'
```

Run immediately:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/schedule/run-now
```

With `STATE_STORE=postgres`, every periodic run attempts to acquire the
configured scheduler lease before executing. Manual `run-now` remains an
operator command and does not require the periodic lease. With `STATE_STORE`
set to `memory` or `sqlite`, the scheduler remains single-process and should
only be enabled in one API instance. Schedule configuration changes are
persisted through the configured state store; the PostgreSQL deployment stores
them in the `schedule_configs` typed mirror table.

Backup and restore rehearsal steps are in `docs/runbooks/BACKUP_RESTORE.md`.
After creating a staging backup set, verify its required files, checksums, and
artifact archive shape:

```bash
uv run python ops/backup/verify_backup_set.py --backup-root "$BACKUP_ROOT"
```

Incident response triage, rollback, evidence preservation, and post-incident
review steps are in `docs/runbooks/INCIDENT_RESPONSE.md`.

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
mkdir -p /var/lib/rune-agent/artifacts
```

Recommended initial server `.env`:

```env
REQ_TRACKER_ENV=production
DATASOURCE_MODE=dummy
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
ENABLE_DOCS=false
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_SECONDS=3600
SCHEDULER_PROJECT_KEY=RUNE_CAM_ALPHA
SCHEDULER_SCENARIO=RUNE_MULTI_SOURCE
```

For actual company deployment, keep JIRA, Confluence, and Email credentials outside this repo and expose them through the company-approved Claude Code skill/MCP setup.

When using `AUTH_MODE=trusted_proxy`, terminate OIDC/SAML at a company-approved
reverse proxy and inject `x-rune-user`, `x-rune-groups`, `x-rune-projects`, and
`x-rune-trusted-secret`. The proxy must strip incoming client-supplied versions
of these headers before adding trusted values.

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
tables.

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

Run the local model-gateway fallback smoke without a real model endpoint:

```bash
uv run python ops/model_gateway/smoke_model_gateway.py
```

Run local source-adapter smoke without company systems:

```bash
uv run python ops/source/smoke_source_adapters.py
```

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

Run feedback/eval/canary rehearsal:

```bash
uv run python ops/evals/run_feedback_eval_rehearsal.py
```

Check release-readiness gates:

```bash
uv run python ops/rehearsal/check_production_readiness.py
```

The checker reports missing production environment variables and separates
local gates from company/staging rehearsals that must be run against real
PostgreSQL, Neo4j, Qdrant, JIRA, Confluence, SSO/OIDC, model gateway, backup,
restore, and load-test targets. Use `--run-local-gates` on a development or
staging host when you want it to execute the local regression command list.
After real staging rehearsals, copy
`ops/rehearsal/production_readiness_evidence.example.json` outside the repo,
replace the placeholder evidence references with reviewed CI/artifact IDs, and
run:

```bash
uv run python ops/rehearsal/check_production_readiness.py \
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
  -d '{"enabled":true,"interval_seconds":1800,"project_key":"RUNE_CAM_ALPHA","scenario":"RUNE_MULTI_SOURCE","run_id_prefix":"sched"}'
```

Run immediately:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/schedule/run-now
```

The current scheduler is process-local. For multi-worker or multi-node production, run a single scheduler instance or move scheduling to system cron/Kubernetes CronJob/queue-backed orchestration before enabling multiple API replicas.

Backup and restore rehearsal steps are in `docs/runbooks/BACKUP_RESTORE.md`.

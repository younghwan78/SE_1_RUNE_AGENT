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
VECTOR_BACKEND=memory
MODEL_GATEWAY_MODE=dummy
ARTIFACT_STORE=local
ARTIFACT_ROOT=/var/lib/rune-agent/artifacts
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

To use PostgreSQL instead of SQLite, create the database/user with your company
standard policy and switch only these values:

```env
STATE_STORE=postgres
POSTGRES_DSN=postgresql://rune:${RUNE_POSTGRES_PASSWORD}@127.0.0.1:5432/rune_agent
```

On startup, the app applies packaged PostgreSQL migrations through
`schema_migrations` and stores production-shaped contract payloads in
`state_entities`.

## 4. Smoke Test

```bash
cd /opt/rune-agent
uv run pytest
uv run uvicorn req_tracker.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

In another shell:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s -X POST http://127.0.0.1:8000/api/v1/schedule/run-now
curl -s http://127.0.0.1:8000/api/v1/schedule
curl -s http://127.0.0.1:8000/api/v1/debug/runs
```

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

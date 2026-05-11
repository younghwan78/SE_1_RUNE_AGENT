# Backup and Restore Runbook

This runbook defines the production-shaped backup and restore rehearsal for the
RUNE MBSE agent stack. Keep credentials in the company secret store or shell
environment. Do not commit real DSNs, tokens, passwords, or backup archives.

## Scope

Back up and restore these stores as one recovery set:

- PostgreSQL app DB: runs, steps, approvals, audit, audit archives, feedback, policies
- artifact store: raw snapshots, stage outputs, masked payloads, debug outputs
- Neo4j graph DB: approved traceability graph
- Qdrant vector DB: chunk vectors and metadata
- deployment config: sanitized `.env`, systemd unit, migration version

## Backup

```bash
export BACKUP_ROOT=/var/backups/rune-agent/$(date -u +%Y%m%dT%H%M%SZ)
sudo mkdir -p "$BACKUP_ROOT"
sudo chown "$USER":"$USER" "$BACKUP_ROOT"

pg_dump "$POSTGRES_DSN" --format=custom --file="$BACKUP_ROOT/postgres.dump"
tar -C /var/lib/rune-agent -czf "$BACKUP_ROOT/artifacts.tar.gz" artifacts

neo4j-admin database dump neo4j --to-path="$BACKUP_ROOT"
curl -s -X POST "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots" \
  -H "api-key: $QDRANT_API_KEY" \
  > "$BACKUP_ROOT/qdrant_snapshot.json"

cp /opt/rune-agent/.env.example "$BACKUP_ROOT/env.example"
git -C /opt/rune-agent rev-parse HEAD > "$BACKUP_ROOT/git_commit.txt"
sha256sum "$BACKUP_ROOT"/* > "$BACKUP_ROOT/SHA256SUMS"
```

## Restore Rehearsal

Run restore rehearsal into disposable databases first.

```bash
createdb rune_agent_restore
pg_restore --clean --if-exists --dbname rune_agent_restore "$BACKUP_ROOT/postgres.dump"

sudo mkdir -p /var/lib/rune-agent-restore
tar -C /var/lib/rune-agent-restore -xzf "$BACKUP_ROOT/artifacts.tar.gz"

neo4j-admin database load neo4j --from-path="$BACKUP_ROOT" --overwrite-destination=true

curl -s -X PUT "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots/recover" \
  -H "content-type: application/json" \
  -H "api-key: $QDRANT_API_KEY" \
  -d '{"location":"<company-approved-qdrant-snapshot-location>"}'
```

## Post-Restore Validation

```bash
uv run pytest
uv run python ops/integration/run_backend_integration.py
uv run python ops/load/smoke_load.py --base-url http://127.0.0.1:8000 --runs 3
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/audit/retention
```

Validation criteria:

- app starts with restored config
- PostgreSQL migrations report no missing migration
- audit archive batches are present after archive/prune rehearsal when retention selects events
- restored artifact refs can be read only under the configured artifact root
- graph projection returns approved graph data after restore
- vector collection accepts query/upsert smoke tests
- audit retention report returns a valid policy and event count

## Rollback

If restore validation fails:

```bash
sudo systemctl stop rune-agent
git -C /opt/rune-agent checkout "$(cat "$BACKUP_ROOT/git_commit.txt")"
pg_restore --clean --if-exists --dbname "$POSTGRES_DSN" "$BACKUP_ROOT/postgres.dump"
sudo rm -rf /var/lib/rune-agent/artifacts
sudo tar -C /var/lib/rune-agent -xzf "$BACKUP_ROOT/artifacts.tar.gz"
sudo systemctl start rune-agent
```

Record the failed restore in the operations log with backup id, git commit,
database versions, validation output, and rollback result.

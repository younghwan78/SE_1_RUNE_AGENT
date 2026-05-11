CREATE TABLE IF NOT EXISTS audit_archive_batches (
    archive_id TEXT PRIMARY KEY,
    archive_ref TEXT NOT NULL,
    policy_json JSONB NOT NULL,
    event_ids TEXT[] NOT NULL,
    archived_events INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_archive_batches_created_at
ON audit_archive_batches(created_at);

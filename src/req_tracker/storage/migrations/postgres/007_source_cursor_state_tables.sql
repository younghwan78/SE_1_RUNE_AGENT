CREATE TABLE IF NOT EXISTS source_sync_cursors (
    cursor_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    project_key TEXT NOT NULL,
    scenario TEXT NOT NULL,
    run_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    artifact_count INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    partial_failure BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_source_sync_cursors_project_source
ON source_sync_cursors(project_key, source_type);

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS soc_artifacts (
    external_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    project_key TEXT NOT NULL,
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    labels TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    links TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    raw_hash TEXT,
    last_synced_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    schema_version TEXT NOT NULL DEFAULT 'soc-v0.1'
);

CREATE TABLE IF NOT EXISTS soc_classifications (
    artifact_id TEXT NOT NULL REFERENCES soc_artifacts(external_id) ON DELETE CASCADE,
    axis TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    run_id TEXT,
    step_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    schema_version TEXT NOT NULL DEFAULT 'soc-v0.1',
    PRIMARY KEY (artifact_id, axis, value, source)
);

CREATE TABLE IF NOT EXISTS soc_event_log (
    event_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    change_type TEXT NOT NULL,
    before_state JSONB,
    after_state JSONB,
    source TEXT NOT NULL,
    run_id TEXT,
    step_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    schema_version TEXT NOT NULL DEFAULT 'soc-v0.1'
);

CREATE TABLE IF NOT EXISTS soc_eval_runs (
    run_id TEXT PRIMARY KEY,
    query_set_id TEXT NOT NULL,
    coverage_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    regression_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    payload_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    schema_version TEXT NOT NULL DEFAULT 'soc-v0.1'
);

CREATE INDEX IF NOT EXISTS idx_soc_artifacts_project
    ON soc_artifacts(project_key);

CREATE INDEX IF NOT EXISTS idx_soc_artifacts_updated
    ON soc_artifacts(updated_at);

CREATE INDEX IF NOT EXISTS idx_soc_artifacts_metadata_axes
    ON soc_artifacts USING GIN ((metadata -> 'soc_axes'));

CREATE INDEX IF NOT EXISTS idx_soc_artifacts_fts
    ON soc_artifacts USING GIN (
        to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body_text, ''))
    );

CREATE INDEX IF NOT EXISTS idx_soc_artifacts_trgm
    ON soc_artifacts USING GIN (
        (coalesce(title, '') || ' ' || coalesce(body_text, '')) gin_trgm_ops
    );

CREATE INDEX IF NOT EXISTS idx_soc_classifications_axis_value
    ON soc_classifications(axis, value);

CREATE INDEX IF NOT EXISTS idx_soc_event_log_entity_ts
    ON soc_event_log(entity_id, ts);

CREATE INDEX IF NOT EXISTS idx_soc_eval_runs_mode_started
    ON soc_eval_runs(coverage_mode, started_at);

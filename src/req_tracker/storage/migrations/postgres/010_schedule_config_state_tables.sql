CREATE TABLE IF NOT EXISTS schedule_configs (
    config_id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    interval_seconds INTEGER NOT NULL,
    scenario TEXT NOT NULL,
    run_id_prefix TEXT NOT NULL,
    lease_name TEXT NOT NULL,
    lease_ttl_seconds INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

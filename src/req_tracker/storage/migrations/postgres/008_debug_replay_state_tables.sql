CREATE TABLE IF NOT EXISTS llm_call_traces (
    llm_call_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    model_profile_id TEXT NOT NULL,
    prompt_version_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_hash TEXT,
    validation_status TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_call_traces_run_step
ON llm_call_traces(run_id, step_id);

CREATE TABLE IF NOT EXISTS replay_results (
    replay_run_id TEXT PRIMARY KEY,
    source_run_id TEXT NOT NULL,
    replay_mode TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_replay_results_source_run
ON replay_results(source_run_id);

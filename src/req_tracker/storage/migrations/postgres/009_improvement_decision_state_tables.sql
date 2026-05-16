CREATE TABLE IF NOT EXISTS improvement_decisions (
    candidate_id TEXT PRIMARY KEY,
    candidate_type TEXT NOT NULL,
    status TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    previous_status TEXT,
    promotion_status TEXT,
    eval_run_id TEXT,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_improvement_decisions_status
ON improvement_decisions(status, decision_type);

CREATE INDEX IF NOT EXISTS idx_improvement_decisions_eval_run
ON improvement_decisions(eval_run_id);

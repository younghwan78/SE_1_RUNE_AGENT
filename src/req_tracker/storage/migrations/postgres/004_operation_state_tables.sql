CREATE TABLE IF NOT EXISTS idempotency_results (
    record_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    command TEXT NOT NULL,
    project_key TEXT,
    request_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempotency_results_command_key
ON idempotency_results(command, idempotency_key);

CREATE INDEX IF NOT EXISTS idx_idempotency_results_project
ON idempotency_results(project_key);

CREATE TABLE IF NOT EXISTS registry_activations (
    activation_id TEXT PRIMARY KEY,
    activation_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    status TEXT NOT NULL,
    activated_by TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_registry_activations_type_item
ON registry_activations(activation_type, item_id);

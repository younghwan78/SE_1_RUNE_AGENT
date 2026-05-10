CREATE TABLE IF NOT EXISTS state_entities (
    collection TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_key TEXT,
    payload_json JSONB NOT NULL,
    payload_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (collection, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_state_entities_project
ON state_entities(collection, project_key);

CREATE INDEX IF NOT EXISTS idx_state_entities_hash
ON state_entities(payload_hash);

CREATE INDEX IF NOT EXISTS idx_state_entities_payload_gin
ON state_entities USING GIN (payload_json);

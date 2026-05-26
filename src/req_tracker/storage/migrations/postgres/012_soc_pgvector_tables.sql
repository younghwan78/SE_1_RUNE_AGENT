CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS soc_artifact_embeddings (
    artifact_id TEXT NOT NULL REFERENCES soc_artifacts(external_id) ON DELETE CASCADE,
    chunk_idx INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    text_hash TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    schema_version TEXT NOT NULL DEFAULT 'soc-v0.1',
    PRIMARY KEY (artifact_id, chunk_idx, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_soc_artifact_embeddings_artifact
    ON soc_artifact_embeddings(artifact_id);

CREATE INDEX IF NOT EXISTS idx_soc_artifact_embeddings_model
    ON soc_artifact_embeddings(embedding_model);

CREATE INDEX IF NOT EXISTS idx_soc_artifact_embeddings_vector
    ON soc_artifact_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

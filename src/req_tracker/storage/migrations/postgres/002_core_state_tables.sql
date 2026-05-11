CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    triggered_by TEXT NOT NULL,
    trigger_source TEXT NOT NULL,
    model_profile_id TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_project_status
ON agent_runs(project_key, status);

CREATE TABLE IF NOT EXISTS agent_step_traces (
    step_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL,
    output_ref TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    retry_count INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_step_traces_run
ON agent_step_traces(run_id, stage_name);

CREATE TABLE IF NOT EXISTS source_artifacts (
    artifact_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    project_key TEXT NOT NULL,
    title TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    data_classification TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    UNIQUE(source_type, external_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_source_artifacts_project
ON source_artifacts(project_key, source_type);

CREATE TABLE IF NOT EXISTS artifact_chunks (
    chunk_id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    project_key TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifact_chunks_artifact
ON artifact_chunks(artifact_id, chunk_index);

CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    name TEXT NOT NULL,
    project_key TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL,
    created_by TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_project_type
ON graph_nodes(project_key, node_type);

CREATE TABLE IF NOT EXISTS candidate_edges (
    edge_id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candidate_edges_source_target
ON candidate_edges(source_node_id, target_node_id);

CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_source_target
ON graph_edges(source_node_id, target_node_id);

CREATE TABLE IF NOT EXISTS graph_deltas (
    delta_id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    created_from_run_id TEXT NOT NULL,
    created_from_step_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_deltas_project_run
ON graph_deltas(project_key, created_from_run_id);

CREATE TABLE IF NOT EXISTS approval_items (
    approval_id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    proposal_type TEXT NOT NULL,
    proposal_ref TEXT NOT NULL,
    graph_delta_ref TEXT,
    status TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    owner_role TEXT NOT NULL,
    created_from_run_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_approval_items_project_status
ON approval_items(project_key, status);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    finding_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    detection_method TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_status_severity
ON findings(approval_status, severity);

CREATE TABLE IF NOT EXISTS feedback_events (
    feedback_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    action TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_role TEXT NOT NULL,
    reason_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_events_target
ON feedback_events(target_type, target_id);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT,
    project_key TEXT,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reason_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_project_action
ON audit_events(project_key, action, created_at);

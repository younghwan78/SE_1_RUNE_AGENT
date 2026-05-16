CREATE TABLE IF NOT EXISTS dashboard_preferences (
    preference_id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    user_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dashboard_preferences_project_user
ON dashboard_preferences(project_key, user_id);

CREATE TABLE IF NOT EXISTS dashboard_assignments (
    assignment_id TEXT PRIMARY KEY,
    project_key TEXT NOT NULL,
    queue_id TEXT NOT NULL,
    assigned_to TEXT,
    assigned_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dashboard_assignments_project_queue
ON dashboard_assignments(project_key, queue_id);

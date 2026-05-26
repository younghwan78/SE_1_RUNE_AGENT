# Migration Operations

This directory anchors the operations-facing migration track from
`PRODUCTION_EXECUTION_PLAN.md`.

Packaged PostgreSQL migrations currently live with the storage implementation:

- `src/req_tracker/storage/migrations/postgres/001_state_entities.sql`
- `src/req_tracker/storage/migrations/postgres/002_core_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/003_audit_archive_batches.sql`
- `src/req_tracker/storage/migrations/postgres/004_operation_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/005_scheduler_leases.sql`
- `src/req_tracker/storage/migrations/postgres/006_dashboard_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/007_source_cursor_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/008_debug_replay_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/009_improvement_decision_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/010_schedule_config_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/011_soc_knowledge_tables.sql`
- `src/req_tracker/storage/migrations/postgres/012_soc_pgvector_tables.sql`
- `src/req_tracker/storage/migrations/postgres/013_soc_age_schema.sql`

`PostgreSQLStateStore` applies migrations on startup through the
`schema_migrations` table. The default runtime profile is
`POSTGRES_MIGRATION_PROFILE=core`, which applies the core application migrations
through `010` and does not require pgvector or Apache AGE. Set
`POSTGRES_MIGRATION_PROFILE=soc` only for a target database prepared for the SoC
Knowledge PoC profile (`pg_trgm`, `vector`, and `age`). Keep executable
migrations in the package so app startup, tests, and deployment use the same
files.

Use this ops directory for deployment runbooks or one-off operator wrappers
only. Do not duplicate SQL here unless there is a clear release artifact that
must be handed to database administrators.

Migration rules:

- every forward migration needs a rollback path or documented restore plan
- every schema change needs unit or integration coverage
- staging PostgreSQL rehearsal is required before production rollout
- migration output must not print secrets or confidential row payloads

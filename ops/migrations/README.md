# Migration Operations

This directory anchors the operations-facing migration track from
`PRODUCTION_EXECUTION_PLAN.md`.

Packaged PostgreSQL migrations currently live with the storage implementation:

- `src/req_tracker/storage/migrations/postgres/001_state_entities.sql`
- `src/req_tracker/storage/migrations/postgres/002_core_state_tables.sql`
- `src/req_tracker/storage/migrations/postgres/003_audit_archive_batches.sql`

`PostgreSQLStateStore` applies these migrations on startup through the
`schema_migrations` table. Keep executable migrations in the package so app
startup, tests, and deployment use the same files.

Use this ops directory for deployment runbooks or one-off operator wrappers
only. Do not duplicate SQL here unless there is a clear release artifact that
must be handed to database administrators.

Migration rules:

- every forward migration needs a rollback path or documented restore plan
- every schema change needs unit or integration coverage
- staging PostgreSQL rehearsal is required before production rollout
- migration output must not print secrets or confidential row payloads

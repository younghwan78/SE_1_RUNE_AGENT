# T026 External Evidence Audit

Decision: `external_evidence_dominates`

After T024 and T025, the local seed implementation and acceptance map are aligned for Stages A-F:

- A: implemented / implemented_seed only.
- B: implemented / implemented_seed only.
- C: implemented_seed only.
- D: implemented_seed only.
- E: implemented_seed only.
- F: implemented / implemented_seed only.
- G: still has `pending_live` and `pending_manual` items.

This means the next gap-reducing step is not another local code slice unless new evidence reveals a defect. The remaining work is to run and record live/manual evidence against approved environments.

## Remaining Required Evidence

1. Target PostgreSQL + Apache AGE + pgvector + pg_trgm
   - Owner input:
     - `POSTGRES_TEST_DSN` for an approved target/staging database.
     - Permission to apply SoC migrations.
     - AGE, pgvector, and pg_trgm installed.
   - Commands:
     - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/validate_soc_live_postgres.py --require-live --apply-migrations`
     - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json`
     - `POSTGRES_TEST_DSN=<target> uv run python ops/evals/run_soc_storage_backed_query_eval.py --live --require-live --apply-migrations --coverage-mode scale --format json`

2. Live local embedding and cross-encoder model quality
   - Owner input:
     - Approved local model download/cache path or preinstalled model files.
     - `soc-models` optional dependencies available.
   - Command:
     - `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json`

3. Live Claude Code quality
   - Owner input:
     - Approved Claude Code CLI access.
   - Commands:
     - `uv run python ops/evals/run_soc_classifier_enrichment_gate.py --live --format json`
     - `uv run python ops/evals/run_soc_claude_quality_gate.py --live --format json`

4. Real JIRA/Confluence/decision-email source switch
   - Owner input:
     - `JIRA_BASE_URL`, `JIRA_TOKEN`, `JIRA_PROJECT_KEY`.
     - `CONFLUENCE_BASE_URL`, `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE_KEY`.
     - `DECISION_EMAIL_EXPORT_PATH`.
     - Approved target `POSTGRES_TEST_DSN`.
   - Command:
     - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --live --require-live --format json`

5. Manual curation and real-sample review
   - Owner input:
     - Human review record for generated scale fixture naturalness.
     - Human-reviewed real-source sample classification result for Stage G.

## Completion Status

`full_outcome_complete: false`

The thread goal should remain active. The current active work should wait for external/live/manual evidence or a new user-approved local scope.

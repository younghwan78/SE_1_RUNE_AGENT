# T022 Remaining Gap Audit

Decision: `ready_for_next_worker`

The remaining gap map is now mostly external/live-evidence dominated, but one material local implementation gap remains before the target DB handoff is clean.

## Evidence Reviewed

- `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md`
- `SoC_Knowledge_PoC_Design_v4.0.md`
- `eval/stages/A.yaml` through `eval/stages/G.yaml`
- T019-T021 receipts in `docs/goals/soc-knowledge-poc-gap-closure/state.yaml`
- Current `ops/rehearsal/run_soc_live_storage_rehearsal.py`
- Current `tests/unit/ops/test_soc_live_storage_rehearsal.py`

## Remaining Gap Ranking

1. Target DB live evidence remains the highest-value external gap.
   - Required commands:
     - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json`
     - `POSTGRES_TEST_DSN=<target> uv run python ops/evals/run_soc_storage_backed_query_eval.py --live --require-live --apply-migrations --coverage-mode scale --format json`
   - Owner input needed: approved PostgreSQL target with pg_trgm, pgvector, Apache AGE, and SoC migrations.

2. Live local model and live Claude evidence remain external/runtime gaps.
   - Required commands:
     - `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json`
     - `uv run python ops/evals/run_soc_claude_quality_gate.py --live --format json`
   - Owner input needed: local model availability and approved Claude/model-gateway access.

3. Real-source switch remains external/source-access dominated.
   - Required command:
     - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --live --require-live --format json`
   - Owner input needed: approved JIRA, Confluence, and decision/email export access.

4. Manual curation remains a human evidence gap.
   - Owner input needed: curated scale query set and human review record for real samples.

5. Local implementation gap: live storage rehearsal does not yet pass side-car semantic relations into the AGE graph loader.
   - T019 added rule-only `mentions` and `authoredBy` extraction.
   - T020 made `SocAgeGraphLoader.upsert_artifact_graph(..., semantic_relations=...)` capable of projecting `MENTIONS` and `AUTHORED_BY` edges.
   - T021 stabilized ingestion IDs.
   - Current `run_soc_live_storage_rehearsal.py` still calls the graph loader without semantic relations, so the target DB rehearsal would not prove semantic edge loading.

## Next Worker

Create T023 to wire semantic relation extraction into the skip-safe live storage rehearsal. This is the largest safe local slice because it upgrades the target DB evidence gate itself without needing credentials or live services for local verification.

## Not Complete

The design target is not complete. After T023, local code gaps are likely dominated by target DB, live model, live Claude, target UI repetition, real-source, and manual curation evidence.

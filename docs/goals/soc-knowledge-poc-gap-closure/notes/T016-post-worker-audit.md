# T016 Post-Worker Audit

## Verdict

ready_for_next_worker

The goal is not complete. T013-T015 closed useful local Stage F/D storage gaps, but the PoC v4.0 target still has material local workflow integration work and several external evidence gates.

## Closed In T013-T015

- `soc_eval_runs` local persistence and reload rehearsal exists.
- Stage F eval-run metric/regression diff exists and is report-only.
- Fixture-to-Postgres loading now writes source-linked `artifact_synced` lifecycle events to `soc_event_log`.
- Fresh verification passed through focused tests, `ruff`, `mypy`, `uv lock --check`, profile validation, and full `uv run pytest` with 435 passed / 3 skipped.

## Remaining Gaps

Local implementation gaps:

- SoC ingestion is still not represented as a production-shaped workflow. The gap report names `SocKnowledgeIngestionWorkflow` as the intended path, but current pieces are still separate classifier, event builder, loader, graph loader, and query service.
- Storage-backed query reasoning persistence and replay/debug UI integration remain partial.
- Manual curation tracking for generated scale fixtures remains unstructured.

External evidence blockers:

- Target Postgres DSN with `pg_trgm`, `vector`, and AGE for live profile, storage rehearsal, and storage-backed query eval.
- Live local embedding/reranker model quality evidence.
- Live Claude Code quality evidence through the model gateway.
- Real JIRA, Confluence, and decision-email source sample access.
- Target UI repeat evidence and human source-link/manual review.

## Next Slice

Select a local workflow integration slice before more evidence-only scaffolding:

Objective: add a skip-safe SoC fixture ingestion workflow rehearsal that runs packaged fixtures through source snapshot, rule classification, lifecycle event generation, and storage projection counts without requiring a live DSN.

Why this is next: it closes the gap between isolated seed modules and the design-required `SocKnowledgeIngestionWorkflow` flow, while preserving production boundaries and avoiding external credentials.

Recommended verification:

- `uv run pytest tests/unit/workflows/test_soc_knowledge_workflow.py tests/unit/ops/test_soc_fixture_ingestion_workflow.py tests/unit/ops/test_soc_stage_b_c_foundation.py -q`
- `uv run python ops/rehearsal/run_soc_fixture_ingestion_workflow.py --coverage-mode scale --format json`
- `uv run ruff check .`
- `uv run mypy src`

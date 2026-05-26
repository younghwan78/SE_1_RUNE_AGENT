# T999 Final Audit

Decision: `not_complete`

`SoC_Knowledge_PoC_Design_v4.0.md` is not fully satisfied yet. The current worktree proves a strong seed baseline across Stage A-G, but the completion criteria in the design require Stage A-G acceptance to pass, including live/real-source evidence and Claude Code enrichment where applicable.

## Current Evidence

Fresh checks run during this audit:

- `uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --format json`
  - `status=skipped`, `dsn_provided=false`, missing `POSTGRES_DSN or POSTGRES_TEST_DSN`.
- `uv run python ops/evals/run_soc_storage_backed_query_eval.py --dry-run --format json`
  - `status=skipped`, `requires_live=true`, missing target DSN.
- `uv run python ops/evals/run_soc_local_model_quality_gate.py --dry-run --format json`
  - `status=skipped`, `requires_live=true`.
- `uv run python ops/evals/run_soc_claude_quality_gate.py --dry-run --format json`
  - `status=skipped`, `requires_live=true`, Claude command is found, but live execution was not run.
- `uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --dry-run --format json`
  - `status=skipped`, source skills and adapter boundaries pass, but live source env vars and target DSN are missing.
- `uv run python ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json`
  - `status=passed`, API-only UI boundary is present.
- `uv run python ops/fixtures/validate_soc_fixtures.py --coverage-mode scale --format json`
  - `status=passed`, 400 artifacts, 200 JIRA, 100 Confluence, 100 Email, 30 queries.
- `uv run python ops/evals/compare_soc_answer.py --coverage-mode scale --format json`
  - `status=passed`, recall/source/schema/unknown pass rates are 1.0.
- `uv run ruff check .`
  - passed.
- `uv run mypy src`
  - passed.

Stage status scan:

- A: 10 implemented or implemented_seed, 1 partial.
- B: all implemented or implemented_seed.
- C: 9 implemented_seed, 3 pending.
- D: all implemented_seed.
- E: all implemented_seed.
- F: all implemented or implemented_seed.
- G: 6 implemented_seed, 2 pending_live, 1 pending_manual, 1 deferred_optional.

## Requirement-by-Requirement Result

| Requirement area | Result | Evidence |
| --- | --- | --- |
| Fixture-first 400 artifact baseline | proved seed | scale fixture validator passed: 400 artifacts, expected source mix, 30 queries |
| 4-axis deterministic query loop | proved seed | scale answer comparer passed with 1.0 recall/source/schema/unknown |
| Single Postgres + AGE + pgvector target | not proved | live storage rehearsal and storage-backed query eval skipped without target DSN |
| Local embedding/reranker live model quality | not proved | local model quality gate is skip-safe but dry-run only |
| Claude Code query quality | not proved live | Claude dry-run reports command and contracts; live gate was not run |
| Real JIRA/Confluence/Email switch | not proved | source skills/adapters present, live source env vars missing |
| Manual curation / naturalness review | not proved | no human review record for generated scale fixtures |
| Stage C Claude Code classifier enrichment | local implementation gap | `eval/stages/C.yaml` still marks C6 pending |
| Stage C local embedder / graph-index builder labels | stale or partial evidence | embedder/graph loaders exist in A/D, but Stage C still marks C8/C9 pending |

## Next Worker Decision

The next useful local slice is C6: add a skip-safe Claude Code classifier enrichment path behind the model gateway. This directly addresses design sections 8.1, 10.2, 11.4, and Stage C C5/C6 without requiring live credentials by default.

External blockers should stay explicit:

- Target DB:
  - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json`
  - `POSTGRES_TEST_DSN=<target> uv run python ops/evals/run_soc_storage_backed_query_eval.py --live --require-live --apply-migrations --coverage-mode scale --format json`
- Live local model:
  - `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json`
- Live Claude:
  - `uv run python ops/evals/run_soc_claude_quality_gate.py --live --format json`
- Real source:
  - `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --live --require-live --format json`

## Completion

`full_outcome_complete: false`

Do not mark the thread goal complete. Continue with T024.

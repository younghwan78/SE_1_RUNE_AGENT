# T010 External Blocker Map

## Result

The remaining SoC Knowledge PoC gaps are split into two classes:

1. External evidence gates that need owner-provided credentials, target services, or live model access.
2. Local readiness gates that can be made skip-safe and verified without touching external systems.

## External Gates

| Gate | Required external state | Command |
| --- | --- | --- |
| Live SoC PostgreSQL profile | Target PostgreSQL DSN with `pg_trgm`, `vector`, AGE, and permission to apply/read SoC migrations | `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/validate_soc_live_postgres.py --require-live` |
| Live storage rehearsal | Same target PostgreSQL DSN plus ability to load fixture artifacts/classifications/embeddings and AGE graph edges | `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json` |
| Live local model quality | Local `soc-models` extra installed, bge/e5 embedding model and cross-encoder model available or downloadable | `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json` |
| Live Claude Code quality | Claude CLI access and model gateway profile usable in the environment | `uv run python ops/evals/run_soc_claude_quality_gate.py --live --format json` |
| Stage G real source switch | JIRA, Confluence, decision email export access plus target DB | `uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --live --format json` |
| Target UI evidence | Running target FastAPI and Streamlit endpoints reachable from browser automation | `uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url <target-ui-url> --format json --timeout-seconds 45` |

No command should print DSNs, tokens, or source credentials.

## Local Readiness Work Available

The live storage rehearsal already proves that a target DB can be loaded and queried when a DSN exists. The gap report still calls out missing storage-backed query quality evidence for the seed/scale query loop. That can be reduced locally by adding a skip-safe storage-backed query eval gate:

- Default run skips without `POSTGRES_TEST_DSN`.
- Unit tests inject a fake retrieval backend and fake live storage rehearsal.
- Live run can load seed or scale fixtures, execute the `PostgresHybridSocRetrievalBackend`, compare results against `SocGroundTruthQuery`, and report recall/source/schema metrics without exposing the DSN.

## Recommended Worker Slice

Create `T011` for a skip-safe storage-backed SoC query eval gate.

Allowed files:

- `ops/evals/run_soc_storage_backed_query_eval.py`
- `tests/unit/ops/test_soc_storage_backed_query_eval.py`
- `eval/stages/D.yaml`
- `eval/stages/F.yaml`
- `tests/unit/ops/test_soc_stage_d_foundation.py`
- `tests/unit/ops/test_soc_stage_f_foundation.py`
- `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md`
- `docs/goals/soc-knowledge-poc-gap-closure/state.yaml`

Verification:

- `uv run pytest tests/unit/ops/test_soc_storage_backed_query_eval.py -q`
- `uv run pytest tests/unit/ops/test_soc_storage_backed_query_eval.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_soc_stage_f_foundation.py -q`
- `uv run python ops/evals/run_soc_storage_backed_query_eval.py --dry-run --format json`
- `uv run ruff check .`
- `uv run mypy src`

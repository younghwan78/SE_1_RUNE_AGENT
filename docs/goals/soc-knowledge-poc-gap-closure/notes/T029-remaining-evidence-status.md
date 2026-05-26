# T029 Remaining Evidence Status

Date: 2026-05-27

## Decision

No additional live/manual evidence can be collected in the current environment without owner-approved target inputs. The local implementation/gate surface is present; the remaining gaps are evidence gates, not a reason to rewrite the existing seed baseline.

## Environment Inputs Checked

Checked without printing secret values:

- `POSTGRES_TEST_DSN`: absent
- `POSTGRES_DSN`: absent
- `JIRA_BASE_URL`: absent
- `JIRA_TOKEN`: absent
- `JIRA_PROJECT_KEY`: absent
- `CONFLUENCE_BASE_URL`: absent
- `CONFLUENCE_TOKEN`: absent
- `CONFLUENCE_SPACE_KEY`: absent
- `DECISION_EMAIL_EXPORT_PATH`: absent
- `HF_HOME`: absent
- `SENTENCE_TRANSFORMERS_HOME`: absent
- Claude CLI: present at `C:\Users\user\.local\bin\claude.exe`
- `sentence_transformers`: not installed in the current uv environment
- `torch`: not installed in the current uv environment

## Gate Results

- `uv run python ops/rehearsal/validate_soc_live_postgres.py`: exited 0, `status=skipped`, `dsn_provided=false`, failure is explicit DSN absence.
- `uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --format json`: exited 0, `status=skipped`, profile/fixture/AGE/hybrid retrieval checks skipped because no DSN is configured.
- `uv run python ops/evals/run_soc_storage_backed_query_eval.py --dry-run --format json`: exited 0, `status=skipped`, `requires_live=true`, missing DSN.
- `uv run python ops/evals/run_soc_local_model_quality_gate.py --dry-run --format json`: exited 0, `status=skipped`, `requires_live=true`, reports embedding/reranker model contracts without loading models.
- `uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --dry-run --format json`: exited 0, `status=skipped`, source skills and adapter boundaries passed; live source env and target DB are missing.
- `uv run python ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json`: exited 0, `status=passed`, API-only Streamlit boundary and modules load.

## Remaining Owner Inputs

To close the final evidence gaps, provide or approve:

1. A target PostgreSQL DSN with SoC profile support for `pg_trgm`, `pgvector`, and Apache AGE.
2. Approval to install/download/use live local models, or a pre-provisioned model cache path for bge-m3/e5 embedding and cross-encoder reranker checks.
3. Approved JIRA, Confluence, and decision-email source inputs for Stage G live sample rehearsal.
4. Target UI URL plus running FastAPI/Streamlit target services for repeated Stage E browser acceptance.
5. Manual curation/review records for the 400-fixture/scale query set and real-source sample classification.

## Next Commands When Inputs Exist

- `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/validate_soc_live_postgres.py --require-live`
- `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json`
- `POSTGRES_TEST_DSN=<target> uv run python ops/evals/run_soc_storage_backed_query_eval.py --live --require-live --apply-migrations --coverage-mode scale --format json`
- `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json`
- `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --live --require-live --format json`
- `uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url <target-streamlit-url> --format json`

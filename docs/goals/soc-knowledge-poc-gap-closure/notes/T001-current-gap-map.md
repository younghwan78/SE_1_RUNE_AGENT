# T001 Current Gap Map

## Evidence Read

- `PRODUCTION_EXECUTION_PLAN.md`: production source of truth requires evidence-first behavior, model gateway abstraction, approved graph vs AI proposal separation, source skills for JIRA/Confluence/Email procedures, deterministic core, and traceable LLM calls.
- `SoC_Knowledge_PoC_Design_v4.0.md`: PoC target is Stage A-G autonomous core with 4-axis SoC ontology, fixture-first query loop, single Postgres profile with AGE/pgvector/FTS, Claude Code-only LLM work, local embedding/reranking, Streamlit UI, Stage F eval loop, and Stage G real data switch.
- `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md`: current gap report says the existing implementation should be reused, not replaced; Stage A-F seed baseline exists; remaining large gaps are live storage evidence, live local model evidence, live Claude Code quality acceptance, Stage G real source switch, target UI evidence, and fuller usage guide.
- `git status --short`: worktree is heavily dirty with many tracked changes and untracked SoC PoC files. Preserve all unrelated existing changes.
- `eval/stages`: A-F exist; `eval/stages/G.yaml` is absent.
- `.claude/skills`: `rune-source-jira`, `rune-source-confluence`, and `rune-source-email` exist, so Stage G can reuse source-skill boundaries but still lacks acceptance/rehearsal proof.

## Requirement-To-Evidence Map

| Design Area | Current Evidence | Status |
| --- | --- | --- |
| Production boundary reuse | Existing FastAPI, Pydantic, adapters, model gateway, feedback, audit, approval, debug and test structure are referenced by source tree and gap report. | Implemented baseline; reuse recommended. |
| 4-axis SoC ontology | `src/req_tracker/ontology/soc_models.py`, `soc_schema.py`, `docs/ontology/soc/schema/v0.1/*`, `tests/contract/test_soc_models.py`, `tests/unit/ontology/test_soc_schema.py`. | Implemented seed. |
| Fixture-first data | `fixtures/soc_knowledge/*`, `ops/fixtures/*`, `src/req_tracker/fixtures/*`, fixture tests and Stage B/F YAML. | Implemented seed and generated scale fixture; manual naturalness review remains. |
| Rule classifier | `src/req_tracker/ingestion/soc_classification.py`, classifier tests, Stage C YAML. | Implemented deterministic baseline; Claude enrichment remains pending. |
| Query and answer contract | `/api/v1/soc/query`, `src/req_tracker/query/*`, `SocAnswer`, `SocSlice`, query eval scripts/tests. | Implemented seed. |
| Postgres AGE/pgvector/FTS profile | `011_soc_knowledge_tables.sql`, `012_soc_pgvector_tables.sql`, `013_soc_age_schema.sql`, validators, loader, AGE and hybrid retrieval modules. | Local/static and fake-connection coverage exists; target DB live proof missing. |
| Local embedding/rerank | `LocalSentenceTransformerEmbedder`, cross-encoder reranker, dry-run smoke, local model quality gate. | Gate exists; actual live model execution evidence missing. |
| Claude Code subprocess | Provider behind model gateway, profile and prompts exist, smoke script exists. | Gateway boundary exists; live multi-stage quality acceptance for slice/plan/answer remains missing. |
| Streamlit UI | `src/req_tracker/soc_ui/*`, `ops/ui/smoke_soc_streamlit_ui.py`, Stage E YAML. | Seed UI plus local live smoke evidence exists; fuller user guide and target repeated evidence missing. |
| Stage F eval loop | `ops/evals/run_soc_query_eval.py`, `compare_soc_answer.py`, failure diagnosis, Stage F YAML. | Seed and scale generated loop exists; storage-backed/manual curated acceptance missing. |
| Stage G real data switch | Source skills exist; `eval/stages/G.yaml` missing. | Major remaining stage gap. |

## Current Large Gaps

1. Target DB evidence: `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json` must pass on a real DB with `pg_trgm`, `vector`, and `age`.
2. Live local model evidence: `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json` must pass with the selected embedding and reranker models installed.
3. Live Claude Code quality acceptance: current smoke covers provider/profile wiring, but there is no quality gate proving slice planning, typed tool planning, and answer assembly produce schema-valid, source-preserving outputs through the gateway.
4. Stage G real source switch: source skills exist, but Stage G acceptance YAML, dry-run rehearsal, and real sample proof are not present.
5. Stage E target-readiness: local UI smoke exists, but target environment repeated evidence and a fuller architect/operator usage guide remain.
6. Manual curation: fixture naturalness and generated scale Q set need review evidence before treating them as production-quality PoC acceptance.

## External Blockers vs Local Work

| Category | Needs External State? | Notes |
| --- | --- | --- |
| Actual target DB live run | Yes | Requires DSN and DB with AGE/vector/pg_trgm privileges. |
| Actual live local model run | Maybe | Requires optional `soc-models` deps and local model download/cache. Can be run locally if environment allows. |
| Actual live Claude Code quality run | Yes-ish | Requires Claude CLI/auth and potentially cost/time. A skip-safe quality gate can still be implemented locally. |
| Real JIRA/Confluence/Email Stage G | Yes | Requires source credentials/scope approval. Local acceptance YAML and dry-run wrappers can still be added. |
| UI usage guide | No | Fully local documentation slice. |

## Ranked Candidate Worker Slices

1. Add a skip-safe SoC Claude Code quality gate for slice planning, typed tool planning, and answer assembly.
   - Why: closes a core design gap around "Claude Code only" without bypassing the model gateway.
   - Verification: unit tests with fake gateway plus dry-run CLI; Stage A/D YAML and gap report updated.
2. Add Stage G acceptance YAML plus a local real-source-switch readiness/dry-run rehearsal.
   - Why: makes the absent Stage G explicit and keeps real access blocked until credentials are provided.
   - Verification: YAML tests and dry-run rehearsal.
3. Add a fuller SoC Streamlit usage/runbook guide and link it from Stage E acceptance.
   - Why: closes E10 locally and helps target environment runs.
   - Verification: docs/runbook checks and UI stage test update.
4. Extend storage-backed eval to run against `POSTGRES_TEST_DSN` when available.
   - Why: moves target DB evidence closer to Stage F/D closure.
   - Verification: skip-safe dry-run plus fake/live-gated tests.
5. Run actual live target DB/model/Claude gates.
   - Why: strongest evidence, but depends on external state not currently present in Scout evidence.

## Recommended Next Slice

Choose candidate 1 first: implement `ops/evals/run_soc_claude_quality_gate.py` with dry-run skip-safe behavior and testable fake-gateway live path. This is the largest safe local slice because it strengthens D7-D9 and the design's Claude Code-only policy while preserving production model-gateway traceability.

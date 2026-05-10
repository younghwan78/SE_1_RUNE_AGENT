# AGENTS.md

## 1. Project Source of Truth

This repository builds an internal, production-grade MBSE traceability agent system.

The single source of truth is:

- `PRODUCTION_EXECUTION_PLAN.md`

Do not recreate or rely on older planning files such as `PRD.md` or `PRD_ref.md`. Those documents were intentionally removed to avoid scope confusion.

Before implementing any meaningful feature, read the relevant section of `PRODUCTION_EXECUTION_PLAN.md` and align the work to it.

## 2. Product Direction

The system is not expected to start as a perfect autonomous agent. It must be built as a feedback-driven, debuggable, model-agnostic system.

Core product principles:

- Start with a deterministic baseline before adding LLM autonomy.
- Treat every AI output as a proposal until approved.
- Store evidence for every node, edge, finding, and answer.
- Record every agent step so incorrect results can be debugged.
- Support internal models, self-hosted models, and external model APIs through a model gateway.
- Use user feedback to create improvement candidates, not to mutate production behavior immediately.
- Promote prompt/model/rule/retrieval changes only through eval, review, canary, and rollback.

## 3. Non-Negotiable Architecture Rules

- Approved graph data and pending AI proposals must stay logically separate.
- LLMs must not own authorization, approval state transitions, graph commits, audit, or deterministic graph rules.
- All LLM calls must be traceable by `run_id`, `step_id`, `model_profile_id`, `prompt_version_id`, request hash, response hash, and validation status.
- Every agent stage must persist or reference intermediate outputs.
- Model-specific SDK calls must be hidden behind the model gateway.
- No secrets, tokens, passwords, or internal endpoint credentials may be hardcoded.
- No unmasked confidential data may be sent to a model gateway.
- AI must not write back to JIRA, Confluence, or Email in the first production release.

## 4. Implementation Order

Follow this order unless the user explicitly changes scope:

1. Common contracts, Pydantic models, FastAPI skeleton, and CI.
2. Model gateway, prompt/model registry, LLM call trace, and replay skeleton.
3. Persistence layer: PostgreSQL, Neo4j, Qdrant, artifact/debug storage abstractions.
4. JIRA production connector with incremental sync and source snapshots.
5. Ingestion, masking, evidence, chunking, and embedding pipeline.
6. Deterministic traceability baseline and graph rules.
7. LLM-assisted extraction, linking, reasoning, and confidence scoring.
8. Approval workbench, graph delta preview, feedback event store, and graph commit.
9. Graph UI, findings UI, debug workbench, and replay diff view.
10. Eval gate and controlled self-improvement loop.
11. Confluence expansion.
12. Decision archive or limited Email expansion.
13. Production deployment, SSO/RBAC, backup/restore, load testing, and operations.

## 5. Expected Repository Shape

Prefer the structure defined in `PRODUCTION_EXECUTION_PLAN.md`:

```text
src/req_tracker/
  adapters/
  api/
  approvals/
  audit/
  config/
  debug/
  evidence/
  feedback/
  findings/
  graph/
  ingestion/
  model_gateway/
  ontology/
  reasoning/
  workflows/
  vector/
  evals/
  ui/
tests/
  contract/
  integration/
  evals/
  security/
  replay/
docs/
  api/
  ontology/
  security/
  runbooks/
ops/
  migrations/
  helm/
```

Do not add large new framework choices without a concrete reason grounded in the production plan.

## 6. Coding Standards

- Use Python 3.12+.
- Use `uv` for dependency and environment management.
- Use Pydantic for external and internal data contracts.
- Use FastAPI for API surfaces.
- Use type hints for public functions and service boundaries.
- Keep deterministic logic testable without live LLM calls.
- Keep model gateway interfaces mockable.
- Use structured logs with correlation ids and run ids.
- Use idempotency keys for command APIs and graph commit operations.
- Prefer small focused modules over broad utility files.

## 7. Debuggability Requirements

Any agent workflow implementation must make debugging practical.

At minimum, preserve:

- source snapshot id
- run id
- step id
- stage name
- input hash
- output hash
- prompt version
- model profile
- retrieval context reference
- structured output validation result
- retry count
- graph delta preview
- approval item lineage
- feedback linkage

If a stage cannot persist full output for security or storage reasons, persist a secure reference and a hash.

## 8. Feedback and Improvement Rules

User feedback is a product feature, not a side log.

Required feedback actions:

- approve
- reject
- modify
- comment
- mark low quality

Required reason-code categories:

- wrong relation
- weak evidence
- wrong node type
- duplicate
- missing context
- wrong severity
- security concern
- other

Feedback may create an improvement candidate for prompt, rule, retrieval policy, scoring threshold, ontology normalization, or model profile. It must not directly change active production behavior.

## 9. Testing Expectations

Use tests that match the blast radius of the change.

Required test areas as the system grows:

- contract tests for Pydantic and OpenAPI schemas
- unit tests for masking, evidence, resolver, graph rules, and scoring
- integration tests for JIRA, PostgreSQL, Neo4j, Qdrant, and API flows
- replay tests for agent run reproducibility
- eval tests for prompt/model changes
- security tests for masking, RBAC, and audit behavior

Release blockers:

- masking violation
- approved graph mutation without approval
- project-level authorization leak
- prompt/model regression beyond threshold
- graph migration without rollback path

## 10. Git and Change Discipline

- Keep commits scoped to one meaningful change.
- Do not mix planning rewrites, infrastructure changes, and feature implementation in one commit unless requested.
- Do not reintroduce removed PRD files.
- Do not commit local secrets, `.env`, virtual environments, local database files, or generated debug artifacts.
- When changing contracts, update tests and relevant docs in the same change.


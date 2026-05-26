# T018 Remaining Gap Audit

## Verdict

ready_for_next_worker

The current work has moved the SoC PoC closer to the v4.0 target, but remaining work is not yet purely external evidence. Stage C still has a material local implementation gap: rule-based entity extraction and cross-reference relation projection.

## Evidence

Closed locally:

- Stage C fixture ingestion workflow exists and emits `AgentRun` / `AgentStepTrace`.
- Rule axis classification exists.
- Source-linked lifecycle event generation exists.
- Stage F eval persistence, reload, and eval-run diff exist.

Still local:

- `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md` still names missing entity extraction and JIRA key mention handling.
- `SoC_Knowledge_PoC_Design_v4.0.md` Stage C acceptance requires cross-reference edge generation from JIRA key mentions.
- `eval/stages/C.yaml` still marks entity extractor pending.

Still external:

- Target Postgres live AGE/pgvector/FTS proof.
- Live local embedding/reranker quality.
- Live Claude Code quality.
- Real JIRA/Confluence/decision-email source access.
- Target UI/manual source-link review.

## Next Worker

Implement a rule-only SoC entity extractor that:

- extracts artifact references from explicit links and JIRA-key-like body text;
- emits `mentions` semantic relations from source artifact to referenced artifact;
- emits `authoredBy` relations when an artifact has `author_id`;
- integrates entity/relation counts into `SocKnowledgeIngestionWorkflow`;
- does not write approved graph state or pending AI proposals.

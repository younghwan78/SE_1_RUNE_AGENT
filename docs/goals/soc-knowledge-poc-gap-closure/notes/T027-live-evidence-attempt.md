# T027 Live Evidence Attempt

Result: `partial_external_evidence_collected`

The environment does not currently provide target DB or live source credentials:

- `POSTGRES_TEST_DSN`: missing.
- `POSTGRES_DSN`: missing.
- `JIRA_BASE_URL`, `JIRA_TOKEN`, `JIRA_PROJECT_KEY`: missing.
- `CONFLUENCE_BASE_URL`, `CONFLUENCE_TOKEN`, `CONFLUENCE_SPACE_KEY`: missing.
- `DECISION_EMAIL_EXPORT_PATH`: missing.

Local model live evidence is also not available in the current environment:

- `sentence_transformers`: missing.
- `torch`: missing.

Claude CLI is available, so live Claude gates were attempted.

## Commands Run

- `uv run python ops/evals/run_soc_classifier_enrichment_gate.py --live --format json`
  - Result: failed.
  - Evidence: `classifier_enrichment.status=failed`, `proposal_count=0`, `pending_count=0`.

- `uv run python ops/evals/run_soc_claude_quality_gate.py --live --format json`
  - Result: failed.
  - Evidence: `slice_planning.status=failed`.
  - Failure shape: Claude CLI returned a `type=result` wrapper whose `result` text was natural language rather than a `SocSlice` JSON object.

## Decision

This is not only an external blocker. Claude was callable, so the failure exposes a local hardening gap: the Claude subprocess provider and/or prompt payload should force a schema-first JSON-only response for live quality gates.

Next task: T028 Worker to harden Claude Code structured output prompting/normalization and rerun live Claude gates.

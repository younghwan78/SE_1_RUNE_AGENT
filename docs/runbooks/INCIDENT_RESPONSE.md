# Incident Response Runbook

This runbook defines the first production response path for the RUNE MBSE agent
system. Keep incident records, internal URLs, user names, and raw evidence in
the company incident system. Do not commit real incident evidence to this repo.

## Scope

Use this runbook for incidents involving:

- failed or stuck analysis, ingestion, replay, or scheduled runs
- source sync failure for JIRA, Confluence, or approved decision/email exports
- model gateway incident, timeout surge, validation failures, or policy blocks
- approval or graph commit incident, including stale approval conflicts
- security or masking incident, including forbidden model payload attempts
- PostgreSQL, Neo4j, Qdrant, artifact store, or observability degradation

## Incident Severity

| Severity | Example | Initial response |
| --- | --- | --- |
| SEV1 | project authorization leak, masking violation, approved graph corruption | stop affected write paths, preserve evidence, notify security/release owner |
| SEV2 | production run failures, model gateway outage, source sync blocked | disable scheduler or affected source, keep read-only UI available |
| SEV3 | delayed sync, dashboard stale data, non-critical debug artifact issue | open operational ticket and schedule fix |

Release blockers from `docs/security/DATA_POLICY.md` are SEV1 until the release
owner and security reviewer explicitly downgrade them.

## First 15 Minutes

1. Identify the affected project, run id, source, model profile, and user scope.
2. Check service health:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/ready
curl -s http://127.0.0.1:8000/api/v1/metrics/summary
```

3. Freeze risky writes if graph integrity or security is in question:

```bash
sudo systemctl stop rune-agent-scheduler || true
```

4. Preserve the evidence listed in the "Evidence to Preserve" section before
   restarting services, pruning audit, or deleting artifacts.
5. Route SEV1 incidents to the release owner, security reviewer, and project
   owner before any rollback that may destroy evidence.

## Run Failure Triage

Use this path when a run is failed, partial, or missing expected outputs.

```bash
curl -s http://127.0.0.1:8000/api/v1/debug/runs
curl -s http://127.0.0.1:8000/api/v1/runs/<run_id>/steps
curl -s http://127.0.0.1:8000/api/v1/runs/<run_id>/llm-calls
curl -s http://127.0.0.1:8000/api/v1/runs/<run_id>/graph-delta
```

Decision path:

- If a deterministic stage failed, inspect `failure_code`, `failure_message`,
  source cursor metadata, and artifact refs.
- If an LLM stage failed, inspect validation status, retry count, prompt
  version, model profile, request hash, and response hash.
- If source fetch was partial, use the source sync failure path below.
- If the same input must be compared after a fix, start replay rather than
  overwriting the original run:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/runs/<run_id>/replay \
  -H "Idempotency-Key: incident-replay-<ticket-id>"
```

Do not approve graph deltas from a failed or unexplained run.

## Source Sync Failure

Use this path when JIRA, Confluence, or approved decision/email export sync is
blocked, partial, or stale.

```bash
curl -s "http://127.0.0.1:8000/api/v1/debug/source-cursors?project_key=<project>"
uv run python ops/source/rehearse_company_sources.py --source jira
uv run python ops/source/rehearse_company_sources.py --source confluence
uv run python ops/source/rehearse_decision_email_export.py
```

Check:

- cursor id, completed cursor, and next cursor
- source warnings, permission-denied warnings, rate-limit warnings, and partial
  failure state
- source adapter mode and source skill/export path
- whether the source skill or MCP/REST transport changed outside application
  code

If a source permission change is suspected, keep the last good cursor and open a
company source-access ticket. Do not bypass source skills by hardcoding
credentials or endpoint URLs in Python code.

## Model Gateway Incident

Use this path when model calls time out, validation fails repeatedly, costs
spike, or data policy blocks model submission.

```bash
uv run python ops/model_gateway/smoke_model_gateway.py
uv run python ops/model_gateway/rehearse_model_gateway.py
curl -s http://127.0.0.1:8000/api/v1/metrics/summary
```

Check:

- active model profile and prompt version
- request hash, masked payload ref, response hash, retry count, and validation
  status
- provider usage metadata, token counts, latency, timeout, and cost gauges
- whether restricted/confidential payloads had masking and access checks

If a prompt or model version is suspected, do not edit active registry files in
place. Use the controlled activation and rollback APIs from
`docs/runbooks/MODEL_POLICY.md`.

## Approval Or Graph Commit Incident

Use this path when approved graph data looks wrong, stale approvals are reported,
or an approval decision failed.

```bash
curl -s http://127.0.0.1:8000/api/v1/approvals
curl -s http://127.0.0.1:8000/api/v1/debug/approvals/<approval_id>/lineage
curl -s "http://127.0.0.1:8000/api/v1/graph/edges?project_key=<project>&include_pending=true"
curl -s http://127.0.0.1:8000/api/v1/audit/events
```

Check:

- approval id, proposal hash, expected version, and stale decision result
- graph delta before/after payload
- approver role and project scope
- audit event outcome and reason code

If an approved edge is wrong but authorization and approval flow were valid,
create a correction approval item and feedback event. If authorization, stale
approval protection, or audit integrity failed, treat it as SEV1.

## Security Or Masking Incident

Use this path when a forbidden payload, masking violation, project leak, or
debug artifact access violation is suspected.

```bash
uv run python ops/security/rehearse_masking_policy.py
uv run python ops/security/check_release_blockers.py
uv run python ops/security/rehearse_trusted_proxy_auth.py
curl -s http://127.0.0.1:8000/api/v1/audit/events
```

Immediate actions:

- stop scheduler or affected source ingestion if new unsafe runs may start
- preserve raw artifact refs, masked payload refs, request/response hashes, and
  audit events
- verify no unmasked confidential data was sent to the model gateway
- rotate affected credentials through the company secret manager if exposure is
  confirmed

Do not delete the local artifact or audit archive before security review.

## Rollback

Rollback must target the component that caused the incident:

- Prompt/model/policy regression: use the admin rollback endpoint and rerun eval.
- Improvement candidate regression: use the improvement rollback endpoint.
- Application deployment issue: revert to the last reviewed git commit and
  rerun local regression gates.
- Data restore issue: follow `docs/runbooks/BACKUP_RESTORE.md`.
- Scheduler issue: stop the scheduler, clear or wait for the PostgreSQL lease,
  and restart only after root cause is known.

Minimum rollback validation:

```bash
uv run ruff check .
uv run mypy src
uv run pytest
uv run python ops/security/check_release_blockers.py
uv run python ops/rehearsal/check_production_readiness.py --run-local-gates
```

The full readiness command may still fail if company/staging evidence is absent;
the incident record must distinguish local regression pass from production
readiness evidence.

## Evidence To Preserve

Record these in the company incident system:

- incident id, severity, opened_at, owner, impacted project keys, and user scope
- git commit, deployment id, environment, and configuration mode
- run id, step id, stage name, source snapshot id, and source cursor id
- model profile id, prompt version id, request hash, response hash, validation
  status, retry count, and latency
- graph delta preview, approval id, proposal hash, approver, and audit ids
- feedback ids, improvement candidate ids, eval run ids, canary status, and
  rollback result
- backup id, restore result, smoke-load output, and readiness report summary

Never paste raw secrets, tokens, passwords, unmasked customer data, or
confidential source text into the incident record.

## Post-Incident Review

Complete post-incident review within five business days for SEV1/SEV2:

- root cause and contributing factors
- user impact and affected graph/source/model records
- whether release blockers were triggered
- whether tests, eval datasets, source adapters, prompts, rules, or runbooks
  need improvement
- whether a controlled improvement candidate should be created
- rollback or restore evidence
- owner and due date for follow-up actions

Follow-up changes still need normal eval, review, canary, and rollback gates.

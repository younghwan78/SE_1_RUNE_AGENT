# RBAC Matrix

This is the initial RBAC foundation before direct company IdP/OIDC validation is
wired. `AUTH_MODE=local` keeps local development open. `AUTH_MODE=api_key`
requires `x-rune-api-key` and evaluates `x-rune-role`. `AUTH_MODE=trusted_proxy`
expects a company-controlled SSO/OIDC reverse proxy to inject trusted identity,
group, project, and shared-secret headers.

| Role | Intended users | Minimum protected access |
| --- | --- | --- |
| `viewer` | read-only project users | non-sensitive health/read endpoints |
| `developer` | agent/debug developers | findings, debug run list, source sync cursor snapshots, debug run summary, approval lineage, debug artifact read |
| `operator` | service operators and reviewers | developer access plus audit event read |
| `admin` | service administrators | all local protected routes |

Current protected routes:

| Route | Minimum role | Reason |
| --- | --- | --- |
| `GET /api/v1/findings` | `developer` | exposes analysis finding details and evidence references |
| `GET /api/v1/schedule` | `viewer` | exposes project-scoped scheduler state |
| `PUT /api/v1/schedule` | `operator` | changes periodic analysis schedule |
| `POST /api/v1/schedule/run-now` | `operator` | starts an operator-triggered analysis run |
| `GET /api/v1/approvals` | `developer` | exposes pending graph proposals and evidence references |
| `POST /api/v1/approvals/{approval_id}/decision` | `operator` | commits/rejects/holds approved graph proposals |
| `GET /api/v1/dashboard/summary` | `viewer` | exposes project-scoped first-viewport dashboard counts |
| `GET /api/v1/dashboard/run-health` | `viewer` | exposes project-scoped run status summary |
| `GET /api/v1/dashboard/risk-summary` | `viewer` | exposes aggregated finding severity and top risk items |
| `GET /api/v1/dashboard/work-queue` | `developer` | exposes actionable findings, approvals, source warnings, failed runs, and eval gate items |
| `GET /api/v1/dashboard/work-queue/preferences` | `developer` | exposes project-scoped reviewer filter presets for the current user |
| `PUT /api/v1/dashboard/work-queue/preferences` | `developer` | saves project-scoped reviewer filter presets and writes an audit event |
| `GET /api/v1/dashboard/work-queue/assignments` | `developer` | exposes project-scoped reviewer work queue ownership state |
| `POST /api/v1/dashboard/work-queue/assignments/{queue_id}` | `developer` | assigns or clears a work queue item through an idempotent audited write |
| `GET /api/v1/dashboard/source-health` | `developer` | exposes source sync cursor health without secrets or transport names |
| `GET /api/v1/dashboard/recent-activity` | `operator` | exposes sanitized operational audit activity |
| `GET /api/v1/debug/runs` | `developer` | exposes run inventory for debug navigation |
| `GET /api/v1/debug/source-cursors` | `developer` | exposes source sync cursor state for ingestion debugging |
| `GET /api/v1/debug/runs/{run_id}/summary` | `developer` | may expose model trace and artifact refs |
| `GET /api/v1/debug/runs/{run_id}/diff-view` | `developer` | exposes side-by-side LLM and graph delta debug payloads |
| `GET /api/v1/metrics` | `operator` | exposes operational counters for Prometheus scraping |
| `GET /api/v1/metrics/summary` | `operator` | exposes runtime counters and scheduler state |
| `GET /api/v1/debug/approvals/{approval_id}/lineage` | `developer` | links reviewer decisions, feedback, audit |
| `GET /api/v1/debug/artifact` | `developer` | reads raw local debug artifacts |
| `POST /api/v1/feedback` | `developer` | records reviewer feedback that feeds eval datasets |
| `GET /api/v1/feedback/summary` | `developer` | exposes reviewer feedback taxonomy counts |
| `GET /api/v1/eval/candidates` | `developer` | exposes feedback-derived eval dataset candidates |
| `GET /api/v1/eval/gate` | `developer` | runs local eval gate over feedback-derived datasets |
| `GET /api/v1/improvements/candidates` | `developer` | exposes controlled improvement candidates |
| `POST /api/v1/improvements/{candidate_id}/activate` | `admin` | promotes improvement candidates through review/canary/active states |
| `POST /api/v1/improvements/{candidate_id}/rollback` | `admin` | rolls back a canary or active improvement after regression |
| `POST /api/v1/admin/model-profiles/{model_profile_id}/rollback` | `admin` | rolls back a recorded model profile activation decision |
| `POST /api/v1/admin/prompt-versions/{prompt_version_id}/rollback` | `admin` | rolls back a recorded prompt version activation decision |
| `GET /api/v1/audit/events` | `operator` | exposes operational audit history |

Trusted proxy mode:

- `x-rune-trusted-secret` must match `TRUSTED_PROXY_SECRET`.
- `x-rune-user` is required and becomes the audit actor.
- `x-rune-groups` maps through `TRUSTED_GROUP_ROLE_MAP`; the highest mapped role wins.
- `x-rune-projects` limits project-scoped routes unless it contains `*`.

The reverse proxy must strip client-supplied versions of these headers before
adding trusted values. Direct OIDC token validation can replace this boundary
later, but should preserve these role names or provide an explicit mapping from
company groups to these roles.

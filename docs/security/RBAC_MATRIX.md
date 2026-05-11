# RBAC Matrix

This is the initial RBAC foundation before direct company IdP/OIDC validation is
wired. `AUTH_MODE=local` keeps local development open. `AUTH_MODE=api_key`
requires `x-rune-api-key` and evaluates `x-rune-role`. `AUTH_MODE=trusted_proxy`
expects a company-controlled SSO/OIDC reverse proxy to inject trusted identity,
group, project, and shared-secret headers.

| Role | Intended users | Minimum protected access |
| --- | --- | --- |
| `viewer` | read-only project users | non-sensitive health/read endpoints |
| `developer` | agent/debug developers | debug run summary, approval lineage, debug artifact read |
| `operator` | service operators and reviewers | developer access plus audit event read |
| `admin` | service administrators | all local protected routes |

Current protected routes:

| Route | Minimum role | Reason |
| --- | --- | --- |
| `GET /api/v1/approvals` | `developer` | exposes pending graph proposals and evidence references |
| `POST /api/v1/approvals/{approval_id}/decision` | `operator` | commits/rejects/holds approved graph proposals |
| `GET /api/v1/debug/runs/{run_id}/summary` | `developer` | may expose model trace and artifact refs |
| `GET /api/v1/debug/approvals/{approval_id}/lineage` | `developer` | links reviewer decisions, feedback, audit |
| `GET /api/v1/debug/artifact` | `developer` | reads raw local debug artifacts |
| `POST /api/v1/feedback` | `developer` | records reviewer feedback that feeds eval datasets |
| `GET /api/v1/feedback/summary` | `developer` | exposes reviewer feedback taxonomy counts |
| `GET /api/v1/eval/candidates` | `developer` | exposes feedback-derived eval dataset candidates |
| `GET /api/v1/eval/gate` | `developer` | runs local eval gate over feedback-derived datasets |
| `GET /api/v1/improvements/candidates` | `developer` | exposes controlled improvement candidates |
| `POST /api/v1/improvements/{candidate_id}/activate` | `admin` | promotes improvement candidates through review/canary/active states |
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

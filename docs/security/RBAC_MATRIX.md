# RBAC Matrix

This is the initial API-key RBAC foundation before company SSO/OIDC is wired.
`AUTH_MODE=local` keeps local development open. `AUTH_MODE=api_key` requires
`x-rune-api-key` and evaluates `x-rune-role`.

| Role | Intended users | Minimum protected access |
| --- | --- | --- |
| `viewer` | read-only project users | non-sensitive health/read endpoints |
| `developer` | agent/debug developers | debug run summary, approval lineage, debug artifact read |
| `operator` | service operators and reviewers | developer access plus audit event read |
| `admin` | service administrators | all local protected routes |

Current protected routes:

| Route | Minimum role | Reason |
| --- | --- | --- |
| `GET /api/v1/debug/runs/{run_id}/summary` | `developer` | may expose model trace and artifact refs |
| `GET /api/v1/debug/approvals/{approval_id}/lineage` | `developer` | links reviewer decisions, feedback, audit |
| `GET /api/v1/debug/artifact` | `developer` | reads raw local debug artifacts |
| `GET /api/v1/audit/events` | `operator` | exposes operational audit history |

SSO/OIDC integration should replace API-key identity, but preserve these role
names or provide an explicit mapping from company groups to these roles.

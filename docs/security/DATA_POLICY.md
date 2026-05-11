# Data Policy

This policy defines the data-classification boundary used by the current
implementation. The executable contract is
`src/req_tracker/ontology/models.py`.

## Classification Levels

| Class | Meaning | Model handling |
| --- | --- | --- |
| `public_internal` | Internal content approved for broad company use, such as non-sensitive dummy fixtures or public project metadata. | May be sent to approved internal or external model profiles if the profile explicitly allows it. |
| `restricted` | Project-scoped engineering content, source snapshots, requirements, design notes, and review comments. | May be sent only to profiles approved for restricted project data after masking and access checks. |
| `confidential` | Sensitive internal content, customer-identifying content, unreleased product details, or content requiring stricter handling. | Must stay inside company-approved confidential-capable model boundaries after masking. |
| `no_external_llm` | Secrets, credentials, raw personal data, broad mailbox content, or documents marked as not approved for external LLM use. | Must not be sent to external model profiles. Use deterministic logic, local redaction, or explicitly approved internal profiles only. |

## Mandatory Rules

- No secrets, tokens, passwords, or internal endpoint credentials may be stored
  in source files, docs, tests, debug artifacts, or committed evidence.
- Source snapshots, chunks, nodes, edges, findings, answers, and approval items
  must retain evidence references or secure artifact references.
- Masking must run before model submission when payloads contain email
  addresses, serial-like identifiers, credentials, or other configured sensitive
  patterns.
- AI output remains a proposal until a human-approved graph commit path accepts
  it.
- Broad Email ingestion is out of scope for the first production release.
  Decision archive or limited Email export validation must use approved export
  files and policy-gated adapters.
- Company-specific JIRA, Confluence, and Email access procedures belong in
  `.claude/skills/` and local runtime configuration, not in core application
  code.

## Release Blockers

- masking violation
- approved graph mutation without approval
- project-level authorization leak
- unmasked confidential content sent to an unapproved model profile
- committed secret, token, password, internal endpoint credential, or raw
  production evidence file
- graph migration or data retention change without rollback or restore path

## Verification

Current local verification paths:

- `uv run pytest`
- `uv run python ops/security/rehearse_masking_policy.py`
- `uv run python ops/source/rehearse_decision_email_export.py`
- `uv run python ops/rehearsal/check_production_readiness.py --run-local-gates`

Company/staging release verification must also include real trusted-proxy RBAC,
source, model-gateway, backup, restore, and load rehearsals.

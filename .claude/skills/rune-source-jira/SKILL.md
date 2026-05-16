---
name: rune-source-jira
description: Use when Claude Code needs to design, implement, configure, or debug JIRA ingestion for the RUNE MBSE traceability agent, including JIRA MCP access, JIRA REST fallback, exported JIRA JSON/CSV, dummy JIRA fixtures, JQL scope, issue links, comments, changelog, and mapping JIRA data into SourceArtifact contracts.
---

# RUNE JIRA Source Skill

## Priority

1. Follow `PRODUCTION_EXECUTION_PLAN.md`.
2. Follow `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md`.
3. Use this skill for JIRA-specific access and mapping rules.

## Transport Selection

Use this order unless the user or local environment says otherwise:

1. JIRA MCP server
2. JIRA REST API
3. exported JIRA JSON/CSV
4. dummy fixture

Do not put MCP tool names into application code. MCP belongs to Claude Code skill/config, not to `src/req_tracker`.

## Required Inputs

Get these from local config or environment, not hardcoded code:

- JIRA base URL or MCP server alias
- project key
- JQL scope
- component/release filters
- sync cursor
- auth token or Claude Code MCP auth

## Data To Fetch

Fetch enough data to support traceability and evidence:

- issue key
- issue type
- summary
- description
- status
- priority
- labels
- components
- fix versions/releases
- reporter/assignee ids
- created/updated timestamps
- issue links
- parent/child relationship
- comments, if allowed
- changelog, if allowed

## Mapping Rules

- Do not trust JIRA issue type as MBSE type.
- Use issue type, labels, title, body, links, and comments as classification signals.
- Preserve original JIRA issue type in metadata.
- Preserve comment summaries in `metadata.comment_refs` and the total as
  `metadata.comment_count` when comments are allowed.
- Preserve changelog summaries in `metadata.history_refs` and the total as
  `metadata.history_count` when history is allowed.
- Preserve source URL for evidence.
- Map JIRA links into relation candidates only, not approved graph edges.
- Mark low-confidence classification as review-required.

## Security Rules

- Do not export tokens, cookies, or personal data into fixtures.
- Mask emails and user ids when producing dummy fixtures.
- If data is marked `no_external_llm`, do not send it to an external model profile.

## Expected Output

Normalize fetched issues into source artifact records matching the shared source contract. Include source warnings for malformed, inaccessible, deleted, moved, or partially fetched issues.

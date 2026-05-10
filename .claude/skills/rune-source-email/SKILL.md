---
name: rune-source-email
description: Use when Claude Code needs to design, implement, configure, or debug Email or decision-archive ingestion for the RUNE MBSE traceability agent, including Email MCP access, mailbox restrictions, exported thread files, decision extraction, participant masking, JIRA/Confluence reference linking, and secure mapping into SourceArtifact contracts.
---

# RUNE Email and Decision Source Skill

## Priority

1. Follow `PRODUCTION_EXECUTION_PLAN.md`.
2. Follow `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md`.
3. Prefer decision archive ingestion over general mailbox ingestion.

## Scope Rule

Email ingestion is not a general mailbox crawler. Only ingest approved decision sources:

- decision archive
- approved mailbox
- approved label/folder
- approved export file
- explicit date range

If scope is unclear, stop and require policy clarification.

## Transport Selection

Use this order unless local policy says otherwise:

1. decision archive MCP server
2. restricted Email MCP server
3. exported thread archive
4. dummy fixture

Do not put mailbox-specific tool names into application code.

## Data To Fetch

Fetch only what is needed for engineering decision traceability:

- message/thread id
- subject
- sanitized participant ids
- sent/received timestamps
- thread body or approved summary
- referenced JIRA issue keys
- referenced Confluence page links
- decision text
- approval/change wording
- attachments metadata, if allowed

## Mapping Rules

- Map clear decisions to `Decision` candidates.
- Map risks or blockers to `Risk` or `Issue` candidates.
- Link decisions to JIRA/Confluence artifacts as relation candidates.
- Preserve evidence preview and source reference.
- Use manual review for ambiguous or sensitive threads.

## Security Rules

- Mask personal email addresses and participant names unless policy allows them.
- Do not ingest private, HR, legal, or unrelated business mail.
- Do not send unmasked thread body to external model profiles.
- Store only approved summaries when raw thread retention is not allowed.

## Expected Output

Normalize approved decision records into source artifacts. If an email cannot be safely normalized, produce a source warning and route to manual review rather than forcing ingestion.


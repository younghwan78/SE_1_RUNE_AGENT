---
name: rune-source-confluence
description: Use when Claude Code needs to design, implement, configure, or debug Confluence ingestion for the RUNE MBSE traceability agent, including Confluence MCP access, REST fallback, exported pages, page tree scope, section and table extraction, page version diff, JIRA mention linking, and mapping pages into SourceArtifact and evidence spans.
---

# RUNE Confluence Source Skill

## Priority

1. Follow `PRODUCTION_EXECUTION_PLAN.md`.
2. Follow `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md`.
3. Use this skill for Confluence-specific access and mapping rules.

## Transport Selection

Use this order unless local policy says otherwise:

1. Confluence MCP server
2. Confluence REST API
3. exported Confluence HTML/Markdown/JSON
4. dummy fixture

MCP tool names stay in Claude Code config or skill references. Application code only sees normalized source artifacts.

## Required Inputs

Get these from local config or environment:

- Confluence base URL or MCP server alias
- space key
- ancestor page id or label scope
- page version cursor
- auth token or Claude Code MCP auth

## Data To Fetch

Fetch enough data to preserve document structure:

- page id
- title
- space key
- page URL
- body storage/view content
- author id
- created/updated timestamps
- version number
- previous version number when version history/diff data is available
- ancestors and children
- labels
- JIRA issue mentions
- table content
- attachment metadata, if allowed

## Mapping Rules

- Preserve heading hierarchy as `section_path`.
- Preserve table coordinates as `table_cell_ref` where possible.
- Extract JIRA mentions and links into metadata and relation candidates.
- Treat page version changes as possible stale trace triggers. When available,
  write the previous page version to `metadata.previous_version_number` and the
  current page version to `metadata.version_number`.
- Do not turn design prose directly into approved graph data; create candidates with evidence.

## Security Rules

- Do not ingest unrestricted spaces by default.
- Avoid attachment body extraction until policy explicitly allows it.
- Mark confidential pages according to local classification policy.

## Expected Output

Normalize pages and page sections into source artifact records and evidence span candidates. Preserve page version so replay and stale trace detection can compare old/new source state.

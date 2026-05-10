---
name: rune-source-skill-pattern
description: Use when adding or modifying RUNE source ingestion skills for Claude Code, including JIRA, Confluence, Email, decision archives, MCP-backed source access, REST fallback, export-file ingestion, or dummy source fixtures for the MBSE traceability agent system.
---

# RUNE Source Skill Pattern

Use this pattern for every source skill in this repository.

## Required Behavior

1. Read `PRODUCTION_EXECUTION_PLAN.md` and `docs/implementation/06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` before changing source ingestion behavior.
2. Treat MCP as an optional transport, not as the application contract.
3. Normalize every source into the same source artifact shape:
   - `source_type`
   - `external_id`
   - `source_url`
   - `project_key`
   - `title`
   - `body_text`
   - `author_id`
   - `created_at`
   - `updated_at`
   - `labels`
   - `links`
   - `parent_id`
   - `child_ids`
   - `metadata`
   - `access_scope`
   - `data_classification`
   - `content_hash`
4. Do not hardcode internal endpoints, tokens, project keys, mailbox names, or user ids.
5. Prefer this transport order:
   - MCP
   - REST API
   - exported file
   - dummy fixture
6. Preserve evidence candidates and source links whenever possible.
7. Route sensitive or ambiguous data to manual review instead of forcing ingestion.

## MCP Rules

- Use `.mcp.example.json` as the committed template.
- Keep actual `.mcp.json` local-only.
- Use environment variables for endpoint URLs and tokens.
- If an MCP tool is unavailable, fall back to REST/export/dummy only when the user or local config allows it.

## Output Requirement

Any implementation or fixture generated from a source skill must be validatable against the repository's Pydantic contracts once those contracts exist.


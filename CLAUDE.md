# CLAUDE.md

Claude Code should use `AGENTS.md` as the primary project instruction file.

Before making changes:

1. Read `AGENTS.md`.
2. Read the relevant section of `PRODUCTION_EXECUTION_PLAN.md`.
3. For JIRA, Confluence, Email, or decision-source work, read the relevant project-local skill under `.claude/skills/`.
4. Keep implementation aligned with the production plan.

Key reminders:

- This is a production-oriented internal MBSE traceability agent system.
- Do not use removed PRD files as source material.
- Build for feedback-driven improvement, model interchangeability, and detailed debugging from the beginning.
- Do not treat LLM output as approved graph truth without Human-in-the-Loop approval.
- Keep model calls behind the model gateway and preserve run/step/model/prompt traces.
- Keep JIRA, Confluence, and Email access procedures in Claude Code source skills. MCP is allowed, but core application code should only depend on source adapter contracts.

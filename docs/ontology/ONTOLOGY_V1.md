# Ontology V1

This document records the human-readable ontology baseline for the current
implementation. The executable contract is `src/req_tracker/ontology/models.py`.

## Version

- Schema version: `v1`
- Stable ID helpers: `src/req_tracker/ontology/id_factory.py`

## Source Types

- `jira`
- `confluence`
- `email`
- `decision_archive`
- `dummy`

## Data Classifications

- `public_internal`
- `restricted`
- `confidential`
- `no_external_llm`

Model gateway policy must block unmasked confidential content from leaving the
approved boundary. Source adapters and source skills must preserve source
snapshot and evidence references so later graph items can be audited.

## Node Types

- `Requirement`
- `Architecture_Block`
- `Design_Spec`
- `Verification`
- `Issue`
- `Decision`
- `Component`
- `Risk`

Each graph node requires at least one evidence span and records whether it was
created by `source`, `ai`, or `human`.

## Edge Relations

- `satisfies`
- `verifies`
- `derives`
- `implements`
- `affects`
- `blocks`
- `conflicts_with`
- `supersedes`
- `decides`

AI-generated edges remain proposals until approved. Approved graph data and
pending AI proposals must stay logically separate.

## Finding Types

- `orphan_node`
- `missing_verification`
- `missing_implementation`
- `conflict`
- `cross_domain_hidden`
- `stale_trace`
- `weak_evidence`
- `policy_violation`

Findings must reference affected nodes or edges and preserve evidence when
available.

## Change Rule

Ontology changes require the Pydantic contract, contract tests, graph
projection behavior, and relevant docs to change together. Production changes
that affect prompt, rule, retrieval, scoring, or model behavior must go through
the feedback/eval/review/canary path before activation.

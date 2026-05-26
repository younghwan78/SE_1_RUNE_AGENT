# T002 Judge Decision

## Decision

Approved the next Worker slice: add a skip-safe SoC Claude Code quality gate.

## Rationale

The gap report identifies live Claude Code quality acceptance as a remaining D7-D9 gap. The current implementation already has a Claude Code subprocess provider behind the model gateway, prompt/model registry entries, and a dry-run provider smoke. What is missing is a PoC-specific acceptance gate that validates the actual SoC query stages: slice planning, typed tool planning, and answer assembly.

This slice is the best next local work package because it:

- moves the design closer to the "Claude Code only" policy without direct subprocess calls outside the model gateway;
- strengthens D7-D9 quality acceptance while preserving production traceability boundaries;
- is verifiable without external credentials through dry-run behavior and fake-gateway unit tests;
- leaves actual `--live` Claude execution as an explicit environment-dependent gate rather than pretending it passed.

## Worker Objective

Implement `ops/evals/run_soc_claude_quality_gate.py` with:

- default dry-run skip-safe output that reports required live Claude Code quality checks;
- live path that validates schema-valid outputs for SoC slice planning, typed query tool planning, and answer assembly through the model gateway boundary;
- fake-gateway unit tests proving the live evaluation logic can pass without invoking a real Claude subprocess;
- Stage A/D YAML and gap report updates so this gate becomes part of the acceptance surface.

## Allowed Files

- `ops/evals/run_soc_claude_quality_gate.py`
- `tests/unit/ops/test_soc_claude_quality_gate.py`
- `eval/stages/A.yaml`
- `eval/stages/D.yaml`
- `tests/unit/ops/test_soc_stage_a_foundation.py`
- `tests/unit/ops/test_soc_stage_d_foundation.py`
- `docs/implementation/12_SOC_KNOWLEDGE_POC_GAP_REPORT.md`

## Verify

- RED: `uv run pytest tests/unit/ops/test_soc_claude_quality_gate.py -q`
- GREEN targeted: `uv run pytest tests/unit/ops/test_soc_claude_quality_gate.py tests/unit/ops/test_soc_stage_a_foundation.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_claude_code_provider_smoke.py tests/unit/query/test_soc_query_planner.py tests/unit/query/test_soc_orchestration.py -q`
- Dry-run CLI: `uv run python ops/evals/run_soc_claude_quality_gate.py --dry-run --format json`
- Hygiene: `uv run ruff check .`
- Typing: `uv run mypy src`

## Stop If

- Any required change falls outside the allowed files.
- The implementation would call Claude Code directly instead of through model gateway components.
- The live gate requires credentials or real Claude invocation in default mode.
- Structured validation cannot cover slice planning, tool planning, and answer assembly.
- Verification fails twice for different root causes.

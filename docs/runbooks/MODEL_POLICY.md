# Model Policy

This runbook defines how model profiles, prompts, and model-gateway behavior are
allowed to change. The executable contracts are in `src/req_tracker/model_gateway/`.

## Required Boundary

All model calls must go through the model gateway. Product code must not call a
provider SDK directly.

Each call must be traceable by:

- `run_id`
- `step_id`
- `model_profile_id`
- `prompt_version_id`
- request hash
- response hash
- validation status
- retry count
- raw response reference when storage policy allows it

## Model Profile Rules

Each `ModelProfile` must define:

- provider and model name
- endpoint alias, not raw secret material
- allowed data classifications
- JSON schema/tool support flags
- context limit
- temperature default
- timeout
- active state

`ModelPolicy` blocks calls when the request data classification is not listed in
the active model profile's `allowed_data_classes`.

## Prompt Version Rules

Prompt versions are versioned release artifacts. Production prompt changes must
not become active directly from reviewer feedback.

Promotion path:

1. draft
2. eval ready
3. review ready
4. canary
5. active

Any prompt/model/rule/retrieval/scoring change that fails security eval or
regression thresholds must remain blocked or be rolled back.

## Model Change Checklist

Before changing an active model profile or prompt:

- run deterministic unit and contract tests
- run masking policy rehearsal
- run model gateway smoke or company sandbox rehearsal
- run replay or diff comparison for representative fixed inputs
- compare node, edge, finding, confidence, validation error, latency, and
  fallback behavior
- record reviewer approval and canary decision
- keep rollback information for the previous active profile or prompt

## Local Commands

```bash
uv run pytest
uv run python ops/security/rehearse_masking_policy.py
uv run python ops/model_gateway/smoke_model_gateway.py
uv run python ops/evals/run_feedback_eval_rehearsal.py
```

For a company-approved sandbox endpoint:

```bash
export MODEL_GATEWAY_ENDPOINT_URL=https://models.example.com/v1/complete
export MODEL_GATEWAY_API_KEY=<from-secret-store>
export MODEL_GATEWAY_PROFILE_ID=company-sandbox
uv run python ops/model_gateway/rehearse_model_gateway.py
```

Do not commit real endpoint URLs, tokens, raw model payloads, or company
evidence files.

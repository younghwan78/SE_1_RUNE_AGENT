"""Shared final validation commands for company/staging handoff evidence."""

FINAL_VALIDATION_COMMANDS: tuple[str, ...] = (
    (
        "uv run python ops/rehearsal/check_production_readiness.py "
        "--run-local-gates --env-file <staging.env> "
        "--evidence-file <reviewed-evidence.json>"
    ),
    (
        "uv run python ops/rehearsal/check_goal_completion.py "
        "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
        "--run-local-gates"
    ),
    (
        "uv run python ops/rehearsal/build_handoff_bundle.py "
        "--env-file <staging.env> --evidence-file <reviewed-evidence.json> "
        "--run-local-gates --output-dir <handoff-bundle-dir>"
    ),
    "uv run python ops/rehearsal/validate_handoff_bundle.py <handoff-bundle-dir>",
)

# Replay Tests

Replay-specific reproducibility tests should live here once replay fixtures grow
beyond contract and workflow scope.

Current replay coverage is implemented in:

- `tests/contract/test_replay_feedback_api.py`
- `tests/contract/test_debug_api.py`
- `ops/rehearsal/run_full_stack_rehearsal.py`

Add tests here for deterministic replay, model-output diffing, graph-delta
comparison, and restart-restore replay behavior using fixed fixture snapshots.

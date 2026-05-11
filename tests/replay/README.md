# Replay Tests

Replay-specific reproducibility tests should live here once replay fixtures grow
beyond contract and workflow scope.

Current replay coverage is implemented in:

- `tests/contract/test_replay_feedback_api.py`
- `tests/contract/test_debug_api.py`
- `tests/contract/test_persistence_api.py`
- `ops/rehearsal/run_full_stack_rehearsal.py`

Current coverage includes deterministic same-input replay, object-level
node/edge/finding diff shape, compared model/prompt version metadata, graph
delta debug views, and restart-restore replay lookup.

Add tests here when replay fixtures grow into larger fixed-snapshot scenarios
for model-output diffing and graph-delta comparison beyond contract scope.

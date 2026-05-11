# Eval Tests

Eval-specific regression tests should live here once prompt/model/rule
comparison fixtures grow beyond unit scope.

Current eval coverage is implemented in:

- `tests/unit/evals/`
- `tests/unit/ops/test_feedback_eval_rehearsal.py`
- `ops/evals/run_feedback_eval_rehearsal.py`

Move or add tests here when they validate a production eval dataset, canary
promotion rule, rollback rule, or prompt/model regression gate end to end.

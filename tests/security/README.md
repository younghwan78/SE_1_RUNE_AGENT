# Security Tests

Security-specific tests should live here once masking, RBAC, audit, or data
classification coverage grows beyond unit and contract scope.

Current security coverage is implemented in:

- `tests/contract/test_security_api.py`
- `tests/unit/ingestion/test_masking_chunking.py`
- `tests/unit/ops/test_masking_policy_rehearsal.py`
- `tests/unit/ops/test_trusted_proxy_rehearsal.py`
- `tests/unit/ops/test_release_blocker_checker.py`
- `ops/security/rehearse_masking_policy.py`
- `ops/security/rehearse_trusted_proxy_auth.py`
- `ops/security/check_release_blockers.py`

Add tests here for release-blocking security scenarios such as masking
violations, project authorization leaks, trusted proxy contract regressions, and
audit bypass attempts.

`ops/security/check_release_blockers.py` is part of the production-readiness
local gate. Keep it updated when adding or changing release blocker tests so
the blocker-to-evidence map remains executable.

"""Local deterministic eval gate runner."""

from req_tracker.evals.datasets import EvalDatasetCandidate
from req_tracker.evals.metrics import EvalGatePolicy, EvalGateResult, EvalMetricReport


def run_local_eval_gate(
    candidates: list[EvalDatasetCandidate],
    eval_run_id: str,
    policy: EvalGatePolicy | None = None,
) -> EvalGateResult:
    """Evaluate improvement readiness with deterministic local metrics."""
    resolved_policy = policy or EvalGatePolicy()
    metrics = [_metric_for_candidate(candidate, eval_run_id) for candidate in candidates]
    blockers = _collect_blockers(metrics, resolved_policy)
    return EvalGateResult(
        eval_run_id=eval_run_id,
        status="blocked" if blockers else "passed",
        policy=resolved_policy,
        metrics=metrics,
        blockers=blockers,
    )


def _metric_for_candidate(
    candidate: EvalDatasetCandidate,
    eval_run_id: str,
) -> EvalMetricReport:
    total_cases = len(candidate.feedback_ids)
    security_failures = total_cases if candidate.reason_code == "security_concern" else 0
    failed_cases = security_failures
    passed_cases = max(total_cases - failed_cases, 0)
    pass_rate = passed_cases / total_cases if total_cases else 0.0
    replay_drift_rate = 0.0 if candidate.reason_code != "wrong_relation" else 0.01
    return EvalMetricReport(
        eval_run_id=eval_run_id,
        dataset_path=candidate.dataset_path,
        reason_code=candidate.reason_code,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        pass_rate=pass_rate,
        security_failures=security_failures,
        replay_drift_rate=replay_drift_rate,
    )


def _collect_blockers(
    metrics: list[EvalMetricReport],
    policy: EvalGatePolicy,
) -> list[str]:
    blockers: list[str] = []
    if not metrics:
        return ["no_eval_datasets"]
    for metric in metrics:
        if metric.total_cases < policy.min_cases:
            blockers.append(f"{metric.dataset_path}:not_enough_cases")
        if metric.pass_rate < policy.min_pass_rate:
            blockers.append(f"{metric.dataset_path}:pass_rate_below_policy")
        if metric.security_failures > policy.max_security_failures:
            blockers.append(f"{metric.dataset_path}:security_failures")
        if metric.replay_drift_rate > policy.max_replay_drift_rate:
            blockers.append(f"{metric.dataset_path}:replay_drift")
    return blockers

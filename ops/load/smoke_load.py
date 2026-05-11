"""Small HTTP smoke load runner for a running RUNE API server."""

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class SmokeResult:
    """One smoke request result."""

    run_id: str
    status_code: int
    latency_ms: float
    approvals: int


def main() -> int:
    """Run smoke load against a live API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--project-key", default="RUNE_CAM_ALPHA")
    parser.add_argument("--scenario", default="RUNE_MULTI_SOURCE")
    parser.add_argument("--max-p95-ms", type=float, default=2000.0)
    args = parser.parse_args()

    results = run_smoke_load(
        base_url=args.base_url.rstrip("/"),
        runs=args.runs,
        project_key=args.project_key,
        scenario=args.scenario,
    )
    latencies = [result.latency_ms for result in results]
    p95 = percentile(latencies, 95)
    print(
        json.dumps(
            {
                "runs": len(results),
                "p95_ms": p95,
                "max_ms": max(latencies) if latencies else 0,
                "approvals": sum(result.approvals for result in results),
                "passed": p95 <= args.max_p95_ms,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if p95 <= args.max_p95_ms else 1


def run_smoke_load(
    *,
    base_url: str,
    runs: int,
    project_key: str,
    scenario: str,
) -> list[SmokeResult]:
    """Submit repeated analysis runs and collect latency."""
    if runs < 1:
        raise ValueError("runs must be >= 1")
    results: list[SmokeResult] = []
    for index in range(runs):
        run_id = f"smoke_{int(time.time() * 1000)}_{index}"
        payload = {
            "run_id": run_id,
            "project_key": project_key,
            "scenario": scenario,
        }
        started = time.perf_counter()
        response = post_json(f"{base_url}/api/v1/runs/analyze", payload)
        latency_ms = (time.perf_counter() - started) * 1000
        results.append(
            SmokeResult(
                run_id=run_id,
                status_code=200,
                latency_ms=latency_ms,
                approvals=int(response["counts"]["approvals"]),
            )
        )
    return results


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON and return a decoded object."""
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            loaded = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"request failed with HTTP {exc.code}: {url}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeError("response must be a JSON object")
    return loaded


def percentile(values: list[float], percent: int) -> float:
    """Return percentile value for a non-empty sample."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    if percent <= 0:
        return min(values)
    if percent >= 100:
        return max(values)
    return float(statistics.quantiles(values, n=100, method="inclusive")[percent - 1])


if __name__ == "__main__":
    raise SystemExit(main())

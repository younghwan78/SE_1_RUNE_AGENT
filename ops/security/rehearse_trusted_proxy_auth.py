"""Rehearse trusted-proxy RBAC headers against a running RUNE API.

Use this on staging after OIDC/SAML termination is configured to inject or pass
the trusted identity headers expected by AUTH_MODE=trusted_proxy. The script
does not print the shared proxy secret.
"""

import argparse
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Any
from urllib import error, request

HttpGet = Callable[[str, dict[str, str]], tuple[int, Any]]


@dataclass(frozen=True)
class TrustedProxyRehearsalConfig:
    """Trusted proxy rehearsal configuration."""

    base_url: str
    trusted_secret_present: bool
    trusted_secret: str
    project_key: str
    wrong_project_key: str
    viewer_group: str
    developer_group: str
    operator_group: str


def main() -> int:
    """CLI entrypoint."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = run_trusted_proxy_rehearsal(os.environ)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def run_trusted_proxy_rehearsal(
    env: Mapping[str, str],
    *,
    http_get: HttpGet | None = None,
) -> dict[str, Any]:
    """Run non-destructive auth checks against a trusted-proxy configured API."""
    config = _config_from_env(env)
    missing = _missing_config(config)
    if missing:
        return {
            "passed": False,
            "status": "missing_config",
            "missing": missing,
            "config": _safe_config(config),
            "checks": [],
        }
    getter = http_get or _http_get
    checks = [
        _expect_status(
            getter,
            config,
            check_id="health_open",
            path="/api/v1/health",
            headers={},
            expected_status=200,
        ),
        _expect_status(
            getter,
            config,
            check_id="viewer_schedule_allowed",
            path="/api/v1/schedule",
            headers=_trusted_headers(config, "viewer@example.com", config.viewer_group),
            expected_status=200,
        ),
        _expect_status(
            getter,
            config,
            check_id="developer_audit_denied",
            path=f"/api/v1/audit/events?project_key={config.project_key}",
            headers=_trusted_headers(config, "developer@example.com", config.developer_group),
            expected_status=403,
        ),
        _expect_status(
            getter,
            config,
            check_id="operator_audit_allowed",
            path=f"/api/v1/audit/events?project_key={config.project_key}",
            headers=_trusted_headers(config, "operator@example.com", config.operator_group),
            expected_status=200,
        ),
        _expect_status(
            getter,
            config,
            check_id="operator_wrong_project_denied",
            path=f"/api/v1/audit/events?project_key={config.project_key}",
            headers=_trusted_headers(
                config,
                "operator@example.com",
                config.operator_group,
                project_key=config.wrong_project_key,
            ),
            expected_status=403,
        ),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "passed": passed,
        "status": "passed" if passed else "failed",
        "config": _safe_config(config),
        "checks": checks,
        "schema_version": "v1",
    }


def _expect_status(
    getter: HttpGet,
    config: TrustedProxyRehearsalConfig,
    *,
    check_id: str,
    path: str,
    headers: dict[str, str],
    expected_status: int,
) -> dict[str, Any]:
    try:
        status, _payload = getter(f"{config.base_url}{path}", headers)
        error_type = None
    except Exception as exc:  # noqa: BLE001
        status = 0
        error_type = exc.__class__.__name__
    return {
        "check_id": check_id,
        "passed": status == expected_status,
        "expected_status": expected_status,
        "actual_status": status,
        "error_type": error_type,
    }


def _trusted_headers(
    config: TrustedProxyRehearsalConfig,
    user: str,
    group: str,
    *,
    project_key: str | None = None,
) -> dict[str, str]:
    return {
        "x-rune-trusted-secret": config.trusted_secret,
        "x-rune-user": user,
        "x-rune-groups": group,
        "x-rune-projects": project_key or config.project_key,
        "accept": "application/json",
    }


def _http_get(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=30) as response:
            return response.status, _load_json(response.read())
    except error.HTTPError as exc:
        return exc.code, _load_json(exc.read())


def _load_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def _config_from_env(env: Mapping[str, str]) -> TrustedProxyRehearsalConfig:
    secret = env.get("TRUSTED_PROXY_SECRET", "")
    return TrustedProxyRehearsalConfig(
        base_url=env.get("RUNE_API_BASE_URL", env.get("API_BASE_URL", "")).rstrip("/"),
        trusted_secret_present=bool(secret),
        trusted_secret=secret,
        project_key=env.get("RUNE_PROJECT_KEY", "RUNE_CAM_ALPHA"),
        wrong_project_key=env.get("RUNE_WRONG_PROJECT_KEY", "OTHER_PROJECT"),
        viewer_group=env.get("RUNE_VIEWER_GROUP", "rune-viewers"),
        developer_group=env.get("RUNE_DEVELOPER_GROUP", "rune-developers"),
        operator_group=env.get("RUNE_OPERATOR_GROUP", "rune-operators"),
    )


def _missing_config(config: TrustedProxyRehearsalConfig) -> list[str]:
    missing: list[str] = []
    if not config.base_url:
        missing.append("RUNE_API_BASE_URL")
    if not config.trusted_secret_present:
        missing.append("TRUSTED_PROXY_SECRET")
    return missing


def _safe_config(config: TrustedProxyRehearsalConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["base_url"] = "<set>" if config.base_url else "<unset>"
    payload["trusted_secret"] = "<set>" if config.trusted_secret_present else "<unset>"
    return payload


if __name__ == "__main__":
    raise SystemExit(main())

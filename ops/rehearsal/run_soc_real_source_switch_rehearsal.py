"""Check SoC fixture-to-real source switch readiness without fetching live data."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SOURCE_DEFINITIONS: dict[str, dict[str, object]] = {
    "jira": {
        "skill": ".claude/skills/rune-source-jira/SKILL.md",
        "adapter_module": "req_tracker.adapters.jira_rest",
        "adapter_class": "JiraRestSourceAdapter",
        "required": ["JIRA_BASE_URL", "JIRA_TOKEN", "JIRA_PROJECT_KEY"],
        "secret_keys": ["JIRA_TOKEN"],
    },
    "confluence": {
        "skill": ".claude/skills/rune-source-confluence/SKILL.md",
        "adapter_module": "req_tracker.adapters.confluence_rest",
        "adapter_class": "ConfluenceRestSourceAdapter",
        "required": ["CONFLUENCE_BASE_URL", "CONFLUENCE_TOKEN", "CONFLUENCE_SPACE_KEY"],
        "secret_keys": ["CONFLUENCE_TOKEN"],
    },
    "email": {
        "skill": ".claude/skills/rune-source-email/SKILL.md",
        "adapter_module": "req_tracker.adapters.export_file",
        "adapter_class": "DecisionEmailExportSourceAdapter",
        "required": ["DECISION_EMAIL_EXPORT_PATH"],
        "secret_keys": [],
    },
}


def run_soc_real_source_switch_rehearsal(
    env: Mapping[str, str] | None = None,
    *,
    live: bool = False,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Return a readiness report for switching SoC fixtures to approved real sources."""
    source_env = env if env is not None else os.environ
    sources = {
        source: _source_readiness(source, definition, source_env, root=root)
        for source, definition in SOURCE_DEFINITIONS.items()
    }
    checks = {
        "source_skills": _status_from_sources(sources, key="skill_status"),
        "adapter_boundaries": _status_from_sources(sources, key="adapter_status"),
        "database_target": _database_target_check(source_env, live=live),
        "live_source_access": _live_source_access_check(sources, live=live),
    }
    failures = [
        name
        for name, check in checks.items()
        if live and check["status"] == "failed"
    ]
    status = "skipped" if not live else ("passed" if not failures else "failed")
    return {
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "mode": "live" if live else "dry_run",
        "passed": status == "passed",
        "requires_live": True,
        "schema_version": "v1",
        "sources": sources,
        "status": status,
    }


def _source_readiness(
    source: str,
    definition: Mapping[str, object],
    env: Mapping[str, str],
    *,
    root: Path,
) -> dict[str, Any]:
    required = list(definition["required"])  # type: ignore[index]
    secret_keys = list(definition["secret_keys"])  # type: ignore[index]
    skill_path = root / str(definition["skill"])
    missing = _missing_required(required, env)
    return {
        "adapter_class": definition["adapter_class"],
        "adapter_status": _adapter_status(
            str(definition["adapter_module"]),
            str(definition["adapter_class"]),
        ),
        "config": _safe_config(required, secret_keys, env),
        "missing": missing,
        "skill_path": str(definition["skill"]),
        "skill_status": "present" if skill_path.exists() else "missing",
        "source": source,
    }


def _adapter_status(module_name: str, class_name: str) -> str:
    try:
        module = importlib.import_module(module_name)
    except Exception:  # noqa: BLE001
        return "missing"
    return "present" if hasattr(module, class_name) else "missing"


def _missing_required(required: list[str], env: Mapping[str, str]) -> list[str]:
    missing: list[str] = []
    for key in required:
        if key == "JIRA_TOKEN" and (env.get("JIRA_TOKEN") or env.get("JIRA_API_TOKEN")):
            continue
        if key == "CONFLUENCE_TOKEN" and (
            env.get("CONFLUENCE_TOKEN") or env.get("CONFLUENCE_API_TOKEN")
        ):
            continue
        if not env.get(key):
            missing.append(key)
    return missing


def _safe_config(
    required: list[str],
    secret_keys: list[str],
    env: Mapping[str, str],
) -> dict[str, str]:
    config: dict[str, str] = {}
    for key in required:
        aliases = _aliases_for_key(key)
        present = any(env.get(alias) for alias in aliases)
        safe_key = key.lower()
        if key in secret_keys:
            safe_key = "token"
        elif key.endswith("_BASE_URL"):
            safe_key = "base_url"
        elif key.endswith("_PROJECT_KEY"):
            safe_key = "project_key"
        elif key.endswith("_SPACE_KEY"):
            safe_key = "space_key"
        elif key.endswith("_EXPORT_PATH"):
            safe_key = "export_path"
        config[safe_key] = "<set>" if present else "<unset>"
    return config


def _aliases_for_key(key: str) -> list[str]:
    if key == "JIRA_TOKEN":
        return ["JIRA_TOKEN", "JIRA_API_TOKEN"]
    if key == "CONFLUENCE_TOKEN":
        return ["CONFLUENCE_TOKEN", "CONFLUENCE_API_TOKEN"]
    return [key]


def _status_from_sources(sources: Mapping[str, Mapping[str, Any]], *, key: str) -> dict[str, Any]:
    missing = [source for source, payload in sources.items() if payload[key] != "present"]
    return {
        "missing": missing,
        "status": "passed" if not missing else "failed",
    }


def _database_target_check(env: Mapping[str, str], *, live: bool) -> dict[str, Any]:
    dsn_provided = bool(env.get("POSTGRES_TEST_DSN") or env.get("POSTGRES_DSN"))
    if not live:
        return {
            "dsn_provided": dsn_provided,
            "required_env": ["POSTGRES_TEST_DSN"],
            "status": "skipped",
        }
    return {
        "dsn_provided": dsn_provided,
        "required_env": ["POSTGRES_TEST_DSN"],
        "status": "passed" if dsn_provided else "failed",
    }


def _live_source_access_check(
    sources: Mapping[str, Mapping[str, Any]],
    *,
    live: bool,
) -> dict[str, Any]:
    missing = {
        source: payload["missing"]
        for source, payload in sources.items()
        if payload["missing"]
    }
    if not live:
        return {
            "missing": missing,
            "status": "skipped",
        }
    return {
        "missing": missing,
        "status": "passed" if not missing else "failed",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not require live config.")
    parser.add_argument("--live", action="store_true", help="Require live source readiness config.")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Return non-zero when live readiness is not passed.",
    )
    parser.add_argument("--format", choices=["json"], default="json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_soc_real_source_switch_rehearsal(live=args.live and not args.dry_run)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["status"] == "skipped" and not args.require_live:
        return 0
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

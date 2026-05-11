"""Run env-driven JIRA/Confluence source rehearsals against company sandboxes.

This script is intended for staging or a company-approved sandbox. It prints
counts, warnings, and artifact shape summaries only; tokens and endpoint secrets
are never echoed.
"""

import argparse
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

from req_tracker.adapters.base import RawSourceArtifact, SourceFetchResult, SourceScope
from req_tracker.adapters.confluence_rest import ConfluenceRestSourceAdapter
from req_tracker.adapters.jira_rest import JiraRestSourceAdapter

SourceName = Literal["jira", "confluence"]


@dataclass(frozen=True)
class SourceRehearsalConfig:
    """Source rehearsal configuration loaded from environment variables."""

    source: SourceName
    project_key: str
    limit: int
    base_url_present: bool
    token_present: bool
    base_url: str = ""
    token: str = ""
    jira_jql: str | None = None
    confluence_space_key: str | None = None
    confluence_cql: str | None = None


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["all", "jira", "confluence"],
        default="all",
        help="Source to rehearse. Default uses both source configs.",
    )
    args = parser.parse_args()
    result = run_company_source_rehearsal(os.environ, source=args.source)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def run_company_source_rehearsal(
    env: Mapping[str, str],
    *,
    source: Literal["all", "jira", "confluence"] = "all",
) -> dict[str, Any]:
    """Run configured company source rehearsals and return a structured report."""
    configs = _selected_configs(env, source=source)
    results = [_run_one(config) for config in configs]
    return {
        "passed": bool(results) and all(result["passed"] for result in results),
        "source_count": len(results),
        "results": results,
        "schema_version": "v1",
    }


def _selected_configs(
    env: Mapping[str, str],
    *,
    source: Literal["all", "jira", "confluence"],
) -> list[SourceRehearsalConfig]:
    configs: list[SourceRehearsalConfig] = []
    if source in {"all", "jira"}:
        configs.append(_jira_config(env))
    if source in {"all", "confluence"}:
        configs.append(_confluence_config(env))
    return configs


def _jira_config(env: Mapping[str, str]) -> SourceRehearsalConfig:
    base_url = env.get("JIRA_BASE_URL", "")
    token = env.get("JIRA_TOKEN", "") or env.get("JIRA_API_TOKEN", "")
    return SourceRehearsalConfig(
        source="jira",
        project_key=env.get("JIRA_PROJECT_KEY", env.get("RUNE_PROJECT_KEY", "RUNE_CAM_ALPHA")),
        limit=_positive_int(env.get("JIRA_REHEARSAL_LIMIT"), default=10),
        base_url=base_url,
        token=token,
        base_url_present=bool(base_url),
        token_present=bool(token),
        jira_jql=env.get("JIRA_JQL"),
    )


def _confluence_config(env: Mapping[str, str]) -> SourceRehearsalConfig:
    base_url = env.get("CONFLUENCE_BASE_URL", "")
    token = env.get("CONFLUENCE_TOKEN", "") or env.get("CONFLUENCE_API_TOKEN", "")
    return SourceRehearsalConfig(
        source="confluence",
        project_key=env.get(
            "CONFLUENCE_PROJECT_KEY",
            env.get("RUNE_PROJECT_KEY", "RUNE_CAM_ALPHA"),
        ),
        limit=_positive_int(env.get("CONFLUENCE_REHEARSAL_LIMIT"), default=10),
        base_url=base_url,
        token=token,
        base_url_present=bool(base_url),
        token_present=bool(token),
        confluence_space_key=env.get("CONFLUENCE_SPACE_KEY"),
        confluence_cql=env.get("CONFLUENCE_CQL"),
    )


def _run_one(config: SourceRehearsalConfig) -> dict[str, Any]:
    missing = _missing_config(config)
    if missing:
        return {
            "source": config.source,
            "passed": False,
            "status": "missing_config",
            "missing": missing,
            "config": _safe_config(config),
            "artifacts": [],
            "warnings": [],
        }
    try:
        result = _fetch(config)
    except Exception as exc:  # noqa: BLE001
        return {
            "source": config.source,
            "passed": False,
            "status": "fetch_failed",
            "error_type": exc.__class__.__name__,
            "config": _safe_config(config),
            "artifacts": [],
            "warnings": [],
        }
    artifact_summaries = [_artifact_summary(artifact) for artifact in result.artifacts]
    passed = bool(result.artifacts) and all(summary["shape_ok"] for summary in artifact_summaries)
    return {
        "source": config.source,
        "passed": passed,
        "status": "passed" if passed else "no_valid_artifacts",
        "config": _safe_config(config),
        "artifact_count": len(result.artifacts),
        "artifacts": artifact_summaries,
        "next_cursor_present": result.next_cursor is not None,
        "warnings": result.source_warnings,
        "partial_failure": result.partial_failure,
    }


def _fetch(config: SourceRehearsalConfig) -> SourceFetchResult:
    scope = SourceScope(project_key=config.project_key, limit=config.limit)
    if config.source == "jira":
        return JiraRestSourceAdapter(
            base_url=config.base_url,
            token=config.token,
            jql=config.jira_jql,
        ).fetch_incremental(scope)
    if config.confluence_space_key is None:
        raise ValueError("confluence_space_key is required")
    return ConfluenceRestSourceAdapter(
        base_url=config.base_url,
        token=config.token,
        space_key=config.confluence_space_key,
        cql=config.confluence_cql,
    ).fetch_incremental(scope)


def _missing_config(config: SourceRehearsalConfig) -> list[str]:
    missing: list[str] = []
    if not config.base_url_present:
        missing.append(f"{config.source.upper()}_BASE_URL")
    if not config.token_present:
        missing.append(f"{config.source.upper()}_TOKEN")
    if config.source == "confluence" and not config.confluence_space_key:
        missing.append("CONFLUENCE_SPACE_KEY")
    return missing


def _safe_config(config: SourceRehearsalConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["base_url"] = "<set>" if config.base_url_present else "<unset>"
    payload["token"] = "<set>" if config.token_present else "<unset>"
    return payload


def _artifact_summary(artifact: RawSourceArtifact) -> dict[str, Any]:
    shape_ok = all(
        [
            artifact.external_id,
            artifact.source_type,
            artifact.project_key,
            artifact.title,
            artifact.body_text,
            artifact.created_at,
            artifact.updated_at,
            artifact.data_classification,
        ]
    )
    return {
        "external_id": artifact.external_id,
        "source_type": artifact.source_type,
        "project_key": artifact.project_key,
        "title_present": bool(artifact.title),
        "body_length": len(artifact.body_text),
        "links": artifact.links[:10],
        "classification": artifact.data_classification,
        "access_scope": artifact.access_scope,
        "shape_ok": bool(shape_ok),
    }


def _positive_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


if __name__ == "__main__":
    raise SystemExit(main())

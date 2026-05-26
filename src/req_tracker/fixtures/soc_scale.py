"""Deterministic generator for SoC Knowledge scale fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.ontology.models import SourceType
from req_tracker.ontology.soc_models import SocGroundTruthQuery, SocSlice, VModelLevel
from req_tracker.ontology.soc_schema import SOC_SCHEMA_ROOT, load_soc_schema, validate_soc_schema

PROJECTS = (("SOC-N-1", "SOC1"), ("SOC-N-2", "SOC2"))
SOURCE_SHAPES: tuple[tuple[SourceType, str, int], ...] = (
    ("jira", "JIRA", 100),
    ("confluence", "CONF", 50),
    ("email", "MAIL", 50),
)


def generate_soc_scale_artifacts() -> list[RawSourceArtifact]:
    """Generate the Phase 1 target mix: 200 JIRA, 100 Confluence, 100 Email."""
    schema = load_soc_schema(SOC_SCHEMA_ROOT)
    validate_soc_schema(schema)

    concerns = [
        (item.name, _label_token(item.aliases[0] if item.aliases else item.name))
        for item in schema.concerns
    ]
    components = [
        (item.name, _label_token(item.aliases[0] if item.aliases else item.name))
        for item in schema.components
    ]
    v_levels = [item.name for item in schema.v_levels]

    artifacts: list[RawSourceArtifact] = []
    start = datetime(2026, 2, 1, tzinfo=UTC)
    source_offsets: dict[SourceType, int] = {"jira": 0, "confluence": 2, "email": 4}

    for project_index, (project_key, project_prefix) in enumerate(PROJECTS):
        for source_type, source_label, count in SOURCE_SHAPES:
            for local_index in range(count):
                ordinal = local_index + 101
                concern, concern_label = concerns[
                    (local_index + source_offsets[source_type] + project_index) % len(concerns)
                ]
                component, component_label = components[
                    (local_index * 3 + source_offsets[source_type] + project_index)
                    % len(components)
                ]
                v_level = v_levels[(local_index + project_index) % len(v_levels)]
                external_id = f"{project_prefix}-{source_label}-{ordinal:03d}"
                created_at = start + timedelta(days=len(artifacts))
                artifacts.append(
                    RawSourceArtifact(
                        external_id=external_id,
                        source_type=source_type,
                        source_url=_source_url(source_type=source_type, external_id=external_id),
                        project_key=project_key,
                        title=f"{project_key} {component} {concern} {source_label} L{v_level[-1]}",
                        body_text=_body_text(
                            source_type=source_type,
                            project_key=project_key,
                            component=component,
                            concern=concern,
                            v_level=v_level,
                            local_index=local_index,
                        ),
                        author_id=f"{source_type}_author_{(local_index % 9) + 1}",
                        created_at=created_at.isoformat(),
                        updated_at=(created_at + timedelta(days=1)).isoformat(),
                        labels=[
                            source_type,
                            f"level/{v_level}",
                            f"concern/{concern_label}",
                            f"component/{component_label}",
                        ],
                        links=_links(
                            project_prefix=project_prefix,
                            source_type=source_type,
                            local_index=local_index,
                        ),
                        metadata={
                            "soc_fixture_scale": True,
                            "soc_axes": {
                                "v_level": v_level,
                                "concerns": [concern],
                                "components": [component],
                            },
                        },
                    )
                )
    return artifacts


def write_soc_scale_fixture(path: Path) -> None:
    """Write generated scale fixture artifacts to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "artifacts": [
            artifact.model_dump(mode="json", exclude_none=True)
            for artifact in generate_soc_scale_artifacts()
        ]
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, width=120),
        encoding="utf-8",
    )


def generate_soc_scale_queries(
    artifacts: list[RawSourceArtifact] | None = None,
) -> list[SocGroundTruthQuery]:
    """Generate deterministic query annotations against the scale fixture."""
    resolved_artifacts = artifacts or generate_soc_scale_artifacts()
    queries: list[SocGroundTruthQuery] = []

    concerns = sorted(
        {
            concern
            for artifact in resolved_artifacts
            for concern in artifact.metadata["soc_axes"]["concerns"]
        }
    )
    for index, concern in enumerate(concerns):
        project_key = PROJECTS[index % len(PROJECTS)][0]
        query_slice = SocSlice(
            pattern="concern_slice",
            project_keys=[project_key],
            concerns=[concern],
        )
        _append_query(
            queries,
            artifacts=resolved_artifacts,
            q_id=f"SQ{len(queries) + 1:03d}",
            question=f"{project_key}에서 {concern} 관련 scale fixture 항목은?",
            query_slice=query_slice,
        )

    for project_key, v_level, concern, component in _axis_groups(
        resolved_artifacts,
        fields=("project", "v_level", "concern", "component"),
    )[:10]:
        query_slice = SocSlice(
            pattern="topic_intersection",
            project_keys=[project_key],
            v_levels=[_v_level(v_level)],
            concerns=[concern],
            components=[component],
        )
        _append_query(
            queries,
            artifacts=resolved_artifacts,
            q_id=f"SQ{len(queries) + 1:03d}",
            question=f"{project_key} {v_level} {component} {concern} 교차 항목은?",
            query_slice=query_slice,
        )

    for project_key, v_level, concern in _axis_groups(
        resolved_artifacts,
        fields=("project", "v_level", "concern"),
    )[:6]:
        query_slice = SocSlice(
            pattern="timeline_slice",
            project_keys=[project_key],
            v_levels=[_v_level(v_level)],
            concerns=[concern],
        )
        _append_query(
            queries,
            artifacts=resolved_artifacts,
            q_id=f"SQ{len(queries) + 1:03d}",
            question=f"{project_key} {v_level} {concern} 일정 흐름은?",
            query_slice=query_slice,
        )

    lifecycle_ids = [
        "SOC1-JIRA-101",
        "SOC1-CONF-101",
        "SOC2-JIRA-101",
        "SOC2-MAIL-101",
    ]
    for artifact_id in lifecycle_ids:
        query_slice = SocSlice(pattern="lifecycle_trace", artifact_id=artifact_id)
        _append_query(
            queries,
            artifacts=resolved_artifacts,
            q_id=f"SQ{len(queries) + 1:03d}",
            question=f"{artifact_id} lifecycle trace는?",
            query_slice=query_slice,
        )

    for topic in ("Bluetooth", "PCIe PHY"):
        queries.append(
            SocGroundTruthQuery(
                q_id=f"SQ{len(queries) + 1:03d}",
                question=f"{topic} 관련 scale fixture 항목은?",
                slice=SocSlice(pattern="unknown"),
                expected_artifact_ids=[],
                expected_source_urls=[],
            )
        )
    return queries


def write_soc_scale_queries(path: Path) -> None:
    """Write generated scale query annotations to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "queries": [
            query.model_dump(mode="json", exclude_none=True)
            for query in generate_soc_scale_queries()
        ]
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, width=120),
        encoding="utf-8",
    )


def _body_text(
    *,
    source_type: SourceType,
    project_key: str,
    component: str,
    concern: str,
    v_level: str,
    local_index: int,
) -> str:
    source_phrase = {
        "jira": "tracking issue",
        "confluence": "architecture note",
        "email": "customer discussion thread",
    }[source_type]
    return (
        f"{source_phrase} for {project_key} records {component} {concern} evidence "
        f"at {v_level}. The item preserves source links, axis labels, and review context "
        f"for fixture-scale query validation batch {local_index // 10}."
    )


def _links(*, project_prefix: str, source_type: SourceType, local_index: int) -> list[str]:
    jira_id = f"{project_prefix}-JIRA-{(local_index % 100) + 101:03d}"
    conf_id = f"{project_prefix}-CONF-{(local_index % 50) + 101:03d}"
    if source_type == "jira":
        return [conf_id]
    return [jira_id]


def _source_url(*, source_type: SourceType, external_id: str) -> str:
    if source_type == "jira":
        return f"https://jira.example/browse/{external_id}"
    if source_type == "confluence":
        return f"https://confluence.example/display/SOC/{external_id}"
    return f"https://mail.example/thread/{external_id}"


def _label_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _v_level(value: str) -> VModelLevel:
    return cast(VModelLevel, value)


def _append_query(
    queries: list[SocGroundTruthQuery],
    *,
    artifacts: list[RawSourceArtifact],
    q_id: str,
    question: str,
    query_slice: SocSlice,
) -> None:
    expected_ids = [
        artifact.external_id
        for artifact in artifacts
        if _artifact_matches_slice(artifact=artifact, query_slice=query_slice)
    ]
    if not expected_ids:
        return
    queries.append(
        SocGroundTruthQuery(
            q_id=q_id,
            question=question,
            slice=query_slice,
            expected_artifact_ids=expected_ids,
            expected_source_urls=[],
        )
    )


def _axis_groups(
    artifacts: list[RawSourceArtifact],
    *,
    fields: tuple[str, ...],
) -> list[tuple[str, ...]]:
    groups: set[tuple[str, ...]] = set()
    for artifact in artifacts:
        axes = artifact.metadata["soc_axes"]
        values = {
            "project": artifact.project_key,
            "v_level": axes["v_level"],
            "concern": axes["concerns"][0],
            "component": axes["components"][0],
        }
        groups.add(tuple(str(values[field]) for field in fields))
    return sorted(groups)


def _artifact_matches_slice(*, artifact: RawSourceArtifact, query_slice: SocSlice) -> bool:
    axes = artifact.metadata["soc_axes"]
    concerns = set(axes["concerns"])
    components = set(axes["components"])
    if query_slice.pattern == "unknown":
        return False
    if query_slice.pattern == "lifecycle_trace":
        return artifact.external_id == query_slice.artifact_id
    if query_slice.project_keys and artifact.project_key not in query_slice.project_keys:
        return False
    if query_slice.v_levels and axes["v_level"] not in query_slice.v_levels:
        return False
    if query_slice.concerns and not (set(query_slice.concerns) & concerns):
        return False
    if query_slice.components and not (set(query_slice.components) & components):
        return False
    return True

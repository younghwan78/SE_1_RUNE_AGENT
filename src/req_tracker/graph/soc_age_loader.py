"""Load SoC artifact axis relations into the Apache AGE graph profile."""

import json
from collections.abc import Callable, Sequence
from typing import Any, TypedDict

import psycopg

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.ontology.soc_models import SocAxisClassification, SocSemanticRelation


class SocAgeArtifactRow(TypedDict):
    """Payload row sent to the AGE graph load Cypher."""

    external_id: str
    source_type: str
    source_url: str
    project_key: str
    title: str
    updated_at: str
    project_keys: list[str]
    v_levels: list[str]
    concerns: list[str]
    components: list[str]


class SocAgeSemanticRelationRow(TypedDict):
    """Semantic relation payload row sent to AGE."""

    relation_id: str
    relation_type: str
    source_entity_id: str
    target_entity_id: str
    source_entity_type: str
    target_entity_type: str


class SocAgeGraphPayload(TypedDict):
    """Full AGE graph load payload."""

    artifacts: list[SocAgeArtifactRow]
    semantic_relations: list[SocAgeSemanticRelationRow]


class SocAgeGraphLoader:
    """Write SoC artifact and axis nodes into the AGE graph."""

    def __init__(
        self,
        dsn: str = "",
        *,
        graph_name: str = "soc_graph",
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        if not dsn and connection_factory is None:
            raise ValueError("postgres dsn is required when connection_factory is not provided")
        self._dsn = dsn
        self._graph_name = graph_name
        self._connection_factory = connection_factory

    def upsert_artifact_graph(
        self,
        *,
        artifacts: Sequence[RawSourceArtifact],
        classifications: Sequence[SocAxisClassification],
        semantic_relations: Sequence[SocSemanticRelation] = (),
    ) -> dict[str, int]:
        """Upsert artifact nodes, axis relations, and optional semantic relations."""
        payload = _graph_payload(
            artifacts=artifacts,
            classifications=classifications,
            semantic_relations=semantic_relations,
        )
        cypher = (
            _UPSERT_ARTIFACT_GRAPH_WITH_SEMANTICS_CYPHER
            if payload["semantic_relations"]
            else _UPSERT_ARTIFACT_GRAPH_CYPHER
        )
        with self._connect() as connection:
            _prepare_age_session(connection)
            connection.execute(
                """
                SELECT *
                FROM ag_catalog.cypher(%s, %s, %s::agtype) AS graph_load(updated agtype)
                """,
                (
                    self._graph_name,
                    cypher,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
        return {
            "artifact_nodes": len(payload["artifacts"]),
            "project_nodes": len(
                {project for item in payload["artifacts"] for project in item["project_keys"]}
            ),
            "v_level_nodes": len(
                {v_level for item in payload["artifacts"] for v_level in item["v_levels"]}
            ),
            "concern_nodes": len(
                {concern for item in payload["artifacts"] for concern in item["concerns"]}
            ),
            "component_nodes": len(
                {component for item in payload["artifacts"] for component in item["components"]}
            ),
            "axis_relations": sum(
                len(item["project_keys"])
                + len(item["v_levels"])
                + len(item["concerns"])
                + len(item["components"])
                for item in payload["artifacts"]
            ),
            "semantic_relations": len(payload["semantic_relations"]),
            "mention_relations": sum(
                1
                for item in payload["semantic_relations"]
                if item["relation_type"] == "mentions"
            ),
            "authored_by_relations": sum(
                1
                for item in payload["semantic_relations"]
                if item["relation_type"] == "authoredBy"
            ),
        }

    def _connect(self) -> Any:
        if self._connection_factory is not None:
            return self._connection_factory()
        return psycopg.connect(self._dsn)


def _prepare_age_session(connection: Any) -> None:
    connection.execute("LOAD 'age'")
    connection.execute('SET search_path = ag_catalog, "$user", public')


_UPSERT_ARTIFACT_GRAPH_CYPHER = """
UNWIND $artifacts AS row
MERGE (artifact:Artifact {external_id: row.external_id})
SET artifact.source_type = row.source_type,
    artifact.source_url = row.source_url,
    artifact.project_key = row.project_key,
    artifact.title = row.title,
    artifact.updated_at = row.updated_at
WITH artifact, row
UNWIND row.project_keys AS project_key
MERGE (project:Project {name: project_key})
MERGE (artifact)-[:BELONGS_TO_PROJECT]->(project)
WITH artifact, row
UNWIND row.v_levels AS v_level
MERGE (level:VLevel {name: v_level})
MERGE (artifact)-[:AT_LEVEL]->(level)
WITH artifact, row
UNWIND row.concerns AS concern_name
MERGE (concern:Concern {name: concern_name})
MERGE (artifact)-[:ADDRESSES]->(concern)
WITH artifact, row
UNWIND row.components AS component_name
MERGE (component:Component {name: component_name})
MERGE (artifact)-[:INVOLVES]->(component)
RETURN count(artifact) AS updated
"""

_UPSERT_ARTIFACT_GRAPH_WITH_SEMANTICS_CYPHER = (
    _UPSERT_ARTIFACT_GRAPH_CYPHER
    + """
WITH updated
UNWIND $semantic_relations AS rel
WITH updated, rel
WHERE rel.relation_type = 'mentions'
MERGE (source:Artifact {external_id: rel.source_entity_id})
MERGE (target:Artifact {external_id: rel.target_entity_id})
MERGE (source)-[:MENTIONS {relation_id: rel.relation_id}]->(target)
WITH updated, count(rel) AS mentions_updated
UNWIND $semantic_relations AS rel
WITH updated, mentions_updated, rel
WHERE rel.relation_type = 'authoredBy'
MERGE (source:Artifact {external_id: rel.source_entity_id})
MERGE (person:Person {entity_id: rel.target_entity_id})
MERGE (source)-[:AUTHORED_BY {relation_id: rel.relation_id}]->(person)
RETURN updated + mentions_updated + count(rel) AS updated
"""
)


def _graph_payload(
    *,
    artifacts: Sequence[RawSourceArtifact],
    classifications: Sequence[SocAxisClassification],
    semantic_relations: Sequence[SocSemanticRelation] = (),
) -> SocAgeGraphPayload:
    axes_by_artifact = _axes_by_artifact(classifications)
    rows: list[SocAgeArtifactRow] = []
    for artifact in artifacts:
        axes = axes_by_artifact.get(artifact.external_id, _empty_axes())
        project_keys = axes["project"] or [artifact.project_key]
        rows.append(
            {
                "external_id": artifact.external_id,
                "source_type": str(artifact.source_type),
                "source_url": artifact.source_url,
                "project_key": artifact.project_key,
                "title": artifact.title,
                "updated_at": artifact.updated_at,
                "project_keys": sorted(set(project_keys)),
                "v_levels": sorted(set(axes["v_level"])),
                "concerns": sorted(set(axes["concern"])),
                "components": sorted(set(axes["component"])),
            }
        )
    return {
        "artifacts": rows,
        "semantic_relations": _semantic_relation_rows(semantic_relations),
    }


def _semantic_relation_rows(
    semantic_relations: Sequence[SocSemanticRelation],
) -> list[SocAgeSemanticRelationRow]:
    return [
        {
            "relation_id": relation.relation_id,
            "relation_type": relation.relation_type,
            "source_entity_id": relation.source_entity_id,
            "target_entity_id": relation.target_entity_id,
            "source_entity_type": relation.source_entity_type,
            "target_entity_type": relation.target_entity_type,
        }
        for relation in semantic_relations
        if relation.relation_type in {"mentions", "authoredBy"}
    ]


def _axes_by_artifact(
    classifications: Sequence[SocAxisClassification],
) -> dict[str, dict[str, list[str]]]:
    grouped: dict[str, dict[str, list[str]]] = {}
    for classification in classifications:
        axes = grouped.setdefault(classification.entity_id, _empty_axes())
        axes[classification.axis].append(classification.value)
    return grouped


def _empty_axes() -> dict[str, list[str]]:
    return {"project": [], "v_level": [], "concern": [], "component": []}

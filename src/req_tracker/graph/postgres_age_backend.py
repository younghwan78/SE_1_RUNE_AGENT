"""Apache AGE query builder for SoC slice graph retrieval."""

import json

from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.storage_sql import StorageQuery


class PostgresAgeGraphBackend:
    """Build parameterized AGE Cypher wrapper queries for SoC graph slices."""

    def __init__(self, *, graph_name: str = "soc_graph") -> None:
        self.graph_name = graph_name

    def build_slice_query(self, *, query_slice: SocSlice, limit: int = 50) -> StorageQuery:
        """Return a parameterized Cypher wrapper query for one SoC slice."""
        cypher = """
            MATCH (artifact:Artifact)
            OPTIONAL MATCH (artifact)-[:BELONGS_TO_PROJECT]->(project:Project)
            OPTIONAL MATCH (artifact)-[:AT_LEVEL]->(level:VLevel)
            OPTIONAL MATCH (artifact)-[:ADDRESSES]->(concern:Concern)
            OPTIONAL MATCH (artifact)-[:INVOLVES]->(component:Component)
            WITH artifact,
                 collect(DISTINCT project.name) AS artifact_project_keys,
                 collect(DISTINCT level.name) AS artifact_v_levels,
                 collect(DISTINCT concern.name) AS artifact_concerns,
                 collect(DISTINCT component.name) AS artifact_components
            WHERE ($artifact_id IS NULL OR artifact.external_id = $artifact_id)
              AND (
                  $project_keys IS NULL
                  OR any(value IN artifact_project_keys WHERE value IN $project_keys)
              )
              AND (
                  $v_levels IS NULL
                  OR any(value IN artifact_v_levels WHERE value IN $v_levels)
              )
              AND (
                  $concerns IS NULL
                  OR any(value IN artifact_concerns WHERE value IN $concerns)
              )
              AND (
                  $components IS NULL
                  OR any(value IN artifact_components WHERE value IN $components)
              )
            RETURN artifact.external_id AS external_id
            LIMIT $limit
        """
        params = {
            "project_keys": query_slice.project_keys or None,
            "artifact_id": query_slice.artifact_id,
            "concerns": query_slice.concerns or None,
            "components": query_slice.components or None,
            "v_levels": [str(item) for item in query_slice.v_levels] or None,
            "limit": limit,
        }
        sql = """
            SELECT
                a.external_id,
                a.source_type,
                a.source_url,
                a.project_key,
                a.title,
                a.body_text,
                a.created_at,
                a.updated_at,
                a.labels,
                a.links,
                a.metadata
            FROM ag_catalog.cypher(%s, %s, %s::agtype) AS graph_hit(external_id agtype)
            JOIN soc_artifacts a
              ON a.external_id = trim(both '"' from graph_hit.external_id::text)
            LIMIT %s
        """
        return StorageQuery(
            tool="graph_query",
            sql=sql,
            params=(self.graph_name, cypher, json.dumps(params, ensure_ascii=False), limit),
        )

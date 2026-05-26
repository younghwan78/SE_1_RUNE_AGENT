"""Tests for loading SoC artifacts into the AGE graph profile."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.fixtures.soc_knowledge import (
    classifications_for_artifacts,
    load_soc_seed_artifacts,
)
from req_tracker.graph.soc_age_loader import SocAgeGraphLoader
from req_tracker.ingestion.soc_entity_extraction import extract_soc_entities_for_artifacts


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        self.executed.append((" ".join(sql.lower().split()), params))


def test_soc_age_graph_loader_upserts_artifact_axis_nodes_and_relations() -> None:
    connection = FakeConnection()
    artifacts = load_soc_seed_artifacts()[:2]
    classifications = classifications_for_artifacts(
        artifacts,
        run_id="fixture_age_run",
        step_id="fixture_age_step",
    )
    loader = SocAgeGraphLoader(connection_factory=lambda: connection)

    counts = loader.upsert_artifact_graph(
        artifacts=artifacts,
        classifications=classifications,
    )

    assert counts["artifact_nodes"] == 2
    assert counts["project_nodes"] == 1
    assert counts["v_level_nodes"] >= 1
    assert counts["concern_nodes"] >= 1
    assert counts["component_nodes"] >= 1
    assert counts["axis_relations"] == len(classifications)
    setup_sql = " ".join(sql for sql, _params in connection.executed[:2])
    assert "load 'age'" in setup_sql
    assert "set search_path" in setup_sql
    sql, params = connection.executed[-1]
    assert "ag_catalog.cypher(%s, %s, %s::agtype)" in sql
    assert params[0] == "soc_graph"
    cypher = params[1]
    assert isinstance(cypher, str)
    assert "MERGE (artifact:Artifact" in cypher
    assert "BELONGS_TO_PROJECT" in cypher
    assert "AT_LEVEL" in cypher
    assert "ADDRESSES" in cypher
    assert "INVOLVES" in cypher
    payload = params[2]
    assert isinstance(payload, str)
    assert f'"external_id": "{artifacts[0].external_id}"' in payload
    assert artifacts[0].external_id not in cypher


def test_soc_age_graph_loader_projects_semantic_relations_to_graph_edges() -> None:
    connection = FakeConnection()
    seed_artifacts = load_soc_seed_artifacts()
    linked_artifacts = [
        next(artifact for artifact in seed_artifacts if artifact.external_id == "SOC1-JIRA-001"),
        next(artifact for artifact in seed_artifacts if artifact.external_id == "SOC2-JIRA-001"),
        RawSourceArtifact(
            external_id="SOC1-JIRA-AUTHOR",
            source_type="jira",
            source_url="https://jira.example/browse/SOC1-JIRA-AUTHOR",
            project_key="SOC-N-1",
            title="Author projection",
            body_text="Author relation smoke.",
            author_id="alice@example.com",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
            labels=[],
        ),
    ]
    classifications = classifications_for_artifacts(
        linked_artifacts[:2],
        run_id="fixture_age_run",
        step_id="fixture_age_step",
    )
    extraction = extract_soc_entities_for_artifacts(
        linked_artifacts,
        run_id="fixture_age_run",
        step_id="entity_extract_step",
    )
    loader = SocAgeGraphLoader(connection_factory=lambda: connection)

    counts = loader.upsert_artifact_graph(
        artifacts=linked_artifacts,
        classifications=classifications,
        semantic_relations=extraction.relations,
    )

    assert counts["semantic_relations"] == len(extraction.relations)
    _sql, params = connection.executed[-1]
    cypher = params[1]
    payload = params[2]
    assert isinstance(cypher, str)
    assert isinstance(payload, str)
    assert "MENTIONS" in cypher
    assert "AUTHORED_BY" in cypher
    assert '"relation_type": "mentions"' in payload
    assert '"relation_type": "authoredBy"' in payload
    assert "SOC2-JIRA-001" not in cypher

"""Tests for rule-only SoC entity and relation extraction."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.fixtures.soc_knowledge import load_soc_seed_artifacts
from req_tracker.ingestion.soc_entity_extraction import extract_soc_entities_for_artifacts


def test_soc_entity_extractor_projects_explicit_links_to_mentions_relations() -> None:
    artifacts = load_soc_seed_artifacts()

    result = extract_soc_entities_for_artifacts(
        artifacts,
        run_id="entity_extract_run",
        step_id="entity_extract_step",
    )

    relation = next(
        item
        for item in result.relations
        if item.source_entity_id == "SOC2-JIRA-001"
        and item.target_entity_id == "SOC1-JIRA-001"
    )
    assert relation.relation_type == "mentions"
    assert relation.source == "rule"
    assert relation.status == "baseline"
    assert relation.evidence_ref == "links"
    assert relation.source_entity_type == "Artifact"
    assert relation.target_entity_type == "Artifact"


def test_soc_entity_extractor_finds_jira_key_mentions_in_body_text() -> None:
    artifacts = load_soc_seed_artifacts()
    source = RawSourceArtifact(
        external_id="SOC1-CONF-XREF",
        source_type="confluence",
        source_url="https://confluence.example/pages/SOC1-CONF-XREF",
        project_key="SOC-N-1",
        title="Camera follow-up",
        body_text="This page follows up SOC1-JIRA-001 and SOC1-JIRA-002.",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        labels=[],
    )

    result = extract_soc_entities_for_artifacts(
        [*artifacts, source],
        run_id="entity_extract_run",
        step_id="entity_extract_step",
    )

    body_mentions = {
        relation.target_entity_id
        for relation in result.relations
        if relation.source_entity_id == "SOC1-CONF-XREF"
        and relation.evidence_ref == "body_text"
    }
    assert body_mentions == {"SOC1-JIRA-001", "SOC1-JIRA-002"}


def test_soc_entity_extractor_projects_author_to_person_relation() -> None:
    artifact = RawSourceArtifact(
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
    )

    result = extract_soc_entities_for_artifacts(
        [artifact],
        run_id="entity_extract_run",
        step_id="entity_extract_step",
    )

    person = next(entity for entity in result.entities if entity.entity_type == "Person")
    authored_by = next(
        relation for relation in result.relations if relation.relation_type == "authoredBy"
    )
    assert person.value == "alice@example.com"
    assert authored_by.source_entity_id == "SOC1-JIRA-AUTHOR"
    assert authored_by.target_entity_id == person.entity_id
    assert authored_by.target_entity_type == "Person"

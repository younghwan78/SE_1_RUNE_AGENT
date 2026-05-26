"""Rule-only SoC entity and semantic relation extraction."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.soc_models import (
    SocExtractedEntity,
    SocSemanticRelation,
)

_ARTIFACT_KEY_RE = re.compile(r"\b[A-Z0-9]+-(?:JIRA|CONF|MAIL)-\d{3,}\b")


@dataclass(frozen=True)
class SocEntityExtractionResult:
    """Extracted side-car entities and relations for a fixture/source batch."""

    entities: list[SocExtractedEntity] = field(default_factory=list)
    relations: list[SocSemanticRelation] = field(default_factory=list)


def extract_soc_entities_for_artifacts(
    artifacts: Sequence[RawSourceArtifact],
    *,
    run_id: str,
    step_id: str,
) -> SocEntityExtractionResult:
    """Extract Artifact/Person entities and deterministic semantic relations."""
    known_artifact_ids = {artifact.external_id for artifact in artifacts}
    entities: list[SocExtractedEntity] = []
    relations: list[SocSemanticRelation] = []
    seen_entities: set[tuple[str, str]] = set()
    seen_relations: set[tuple[str, str, str, str]] = set()

    for artifact in artifacts:
        _append_entity(
            entities,
            seen_entities,
            entity_id=artifact.external_id,
            entity_type="Artifact",
            value=artifact.external_id,
            source_artifact_id=artifact.external_id,
            evidence_ref="artifact",
            run_id=run_id,
            step_id=step_id,
        )
        for target_id in _explicit_artifact_links(artifact, known_artifact_ids):
            _append_relation(
                relations,
                seen_relations,
                relation_type="mentions",
                source_entity_id=artifact.external_id,
                target_entity_id=target_id,
                source_entity_type="Artifact",
                target_entity_type="Artifact",
                confidence=1.0,
                evidence_ref="links",
                run_id=run_id,
                step_id=step_id,
            )
        for target_id in _body_artifact_mentions(artifact, known_artifact_ids):
            _append_relation(
                relations,
                seen_relations,
                relation_type="mentions",
                source_entity_id=artifact.external_id,
                target_entity_id=target_id,
                source_entity_type="Artifact",
                target_entity_type="Artifact",
                confidence=0.9,
                evidence_ref="body_text",
                run_id=run_id,
                step_id=step_id,
            )
        if artifact.author_id:
            person_id = _person_entity_id(artifact.author_id)
            _append_entity(
                entities,
                seen_entities,
                entity_id=person_id,
                entity_type="Person",
                value=artifact.author_id,
                source_artifact_id=artifact.external_id,
                evidence_ref="author_id",
                run_id=run_id,
                step_id=step_id,
            )
            _append_relation(
                relations,
                seen_relations,
                relation_type="authoredBy",
                source_entity_id=artifact.external_id,
                target_entity_id=person_id,
                source_entity_type="Artifact",
                target_entity_type="Person",
                confidence=1.0,
                evidence_ref="author_id",
                run_id=run_id,
                step_id=step_id,
            )

    return SocEntityExtractionResult(entities=entities, relations=relations)


def _explicit_artifact_links(
    artifact: RawSourceArtifact,
    known_artifact_ids: set[str],
) -> list[str]:
    return sorted(
        {
            link
            for link in artifact.links
            if link in known_artifact_ids and link != artifact.external_id
        }
    )


def _body_artifact_mentions(
    artifact: RawSourceArtifact,
    known_artifact_ids: set[str],
) -> list[str]:
    return sorted(
        {
            mention
            for mention in _ARTIFACT_KEY_RE.findall(artifact.body_text)
            if mention in known_artifact_ids and mention != artifact.external_id
        }
    )


def _append_entity(
    entities: list[SocExtractedEntity],
    seen: set[tuple[str, str]],
    *,
    entity_id: str,
    entity_type: str,
    value: str,
    source_artifact_id: str,
    evidence_ref: str,
    run_id: str,
    step_id: str,
) -> None:
    key = (entity_id, entity_type)
    if key in seen:
        return
    seen.add(key)
    entities.append(
        SocExtractedEntity(
            entity_id=entity_id,
            entity_type=entity_type,  # type: ignore[arg-type]
            value=value,
            source_artifact_id=source_artifact_id,
            evidence_ref=evidence_ref,
            source="rule",
            status="baseline",
            run_id=run_id,
            step_id=step_id,
        )
    )


def _append_relation(
    relations: list[SocSemanticRelation],
    seen: set[tuple[str, str, str, str]],
    *,
    relation_type: str,
    source_entity_id: str,
    target_entity_id: str,
    source_entity_type: str,
    target_entity_type: str,
    confidence: float,
    evidence_ref: str,
    run_id: str,
    step_id: str,
) -> None:
    key = (relation_type, source_entity_id, target_entity_id, evidence_ref)
    if key in seen:
        return
    seen.add(key)
    payload = {
        "relation_type": relation_type,
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "evidence_ref": evidence_ref,
    }
    relations.append(
        SocSemanticRelation(
            relation_id=f"soc_rel_{stable_hash(payload)[:16]}",
            relation_type=relation_type,  # type: ignore[arg-type]
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            source_entity_type=source_entity_type,  # type: ignore[arg-type]
            target_entity_type=target_entity_type,  # type: ignore[arg-type]
            confidence=confidence,
            evidence_ref=evidence_ref,
            source="rule",
            status="baseline",
            run_id=run_id,
            step_id=step_id,
        )
    )


def _person_entity_id(author_id: str) -> str:
    return f"person_{stable_hash(author_id.strip().lower())[:16]}"

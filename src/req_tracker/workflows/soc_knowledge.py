"""SoC Knowledge fixture ingestion workflow."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.debug.models import AgentRun, AgentStepTrace
from req_tracker.fixtures.soc_knowledge import (
    load_soc_scale_artifacts,
    load_soc_seed_artifacts,
)
from req_tracker.ingestion.soc_classification import classify_soc_axes
from req_tracker.ingestion.soc_entity_extraction import extract_soc_entities_for_artifacts
from req_tracker.storage.soc_postgres_loader import lifecycle_events_for_artifacts

CoverageMode = Literal["seed", "scale"]
SOC_INGESTION_WORKFLOW_SCHEMA_VERSION = "soc-ingestion-workflow-v0.1"


class SocKnowledgeIngestionResult(BaseModel):
    """Traceable result for one fixture ingestion rehearsal."""

    model_config = ConfigDict(extra="forbid")

    run: AgentRun
    steps: list[AgentStepTrace] = Field(default_factory=list)
    coverage_mode: CoverageMode
    counts: dict[str, int] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(default_factory=dict)
    storage_projection: dict[str, int] = Field(default_factory=dict)
    idempotency_fingerprint: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = SOC_INGESTION_WORKFLOW_SCHEMA_VERSION


class SocKnowledgeIngestionWorkflow:
    """Deterministic SoC fixture ingestion flow without live storage side effects."""

    def run_fixture_ingestion(
        self,
        *,
        run_id: str,
        coverage_mode: CoverageMode = "seed",
    ) -> SocKnowledgeIngestionResult:
        """Run packaged fixtures through classification and event projection."""
        artifacts = (
            load_soc_scale_artifacts()
            if coverage_mode == "scale"
            else load_soc_seed_artifacts()
        )
        return self.run_artifacts(
            run_id=run_id,
            coverage_mode=coverage_mode,
            artifacts=artifacts,
        )

    def run_artifacts(
        self,
        *,
        run_id: str,
        coverage_mode: CoverageMode,
        artifacts: list[RawSourceArtifact],
    ) -> SocKnowledgeIngestionResult:
        """Run caller-provided artifacts through the SoC fixture ingestion stages."""
        run = AgentRun(
            run_id=run_id,
            run_type="ingestion",
            project_key="soc_knowledge",
            triggered_by="soc_fixture_ingestion_workflow",
            trigger_source="system",
            status="succeeded",
            input_snapshot_ids=[stable_hash([artifact.external_id for artifact in artifacts])],
            completed_at=datetime.now(UTC),
        )
        source_snapshot = _source_snapshot(artifacts)
        steps = [
            _step_trace(
                run_id=run_id,
                stage_name="soc_fixture_source_snapshot",
                input_payload={"coverage_mode": coverage_mode},
                output_payload=source_snapshot,
            )
        ]

        classification_step_id = f"{run_id}_soc_axis_classification"
        classifications = [
            classification
            for artifact in artifacts
            for classification in classify_soc_axes(
                artifact,
                run_id=run_id,
                step_id=classification_step_id,
            )
        ]
        classification_summary = {
            "classifications": len(classifications),
            "axes": sorted({classification.axis for classification in classifications}),
        }
        steps.append(
            _step_trace(
                run_id=run_id,
                stage_name="soc_axis_classification",
                input_payload=source_snapshot,
                output_payload=classification_summary,
            )
        )

        entity_step_id = f"{run_id}_soc_entity_extraction"
        entity_result = extract_soc_entities_for_artifacts(
            artifacts,
            run_id=run_id,
            step_id=entity_step_id,
        )
        entity_summary = {
            "entities": len(entity_result.entities),
            "relations": len(entity_result.relations),
            "relation_types": sorted(
                {relation.relation_type for relation in entity_result.relations}
            ),
        }
        steps.append(
            _step_trace(
                run_id=run_id,
                stage_name="soc_entity_extraction",
                input_payload=source_snapshot,
                output_payload=entity_summary,
            )
        )

        lifecycle_step_id = f"{run_id}_soc_lifecycle_events"
        lifecycle_events = lifecycle_events_for_artifacts(
            artifacts,
            run_id=run_id,
            step_id=lifecycle_step_id,
        )
        lifecycle_summary = {
            "events": len(lifecycle_events),
            "change_types": sorted({event.change_type for event in lifecycle_events}),
        }
        steps.append(
            _step_trace(
                run_id=run_id,
                stage_name="soc_lifecycle_events",
                input_payload=source_snapshot,
                output_payload=lifecycle_summary,
            )
        )

        storage_projection = {
            "artifacts": len(artifacts),
            "classifications": len(classifications),
            "extracted_entities": len(entity_result.entities),
            "semantic_relations": len(entity_result.relations),
            "events": len(lifecycle_events),
            "embeddings": len(artifacts),
            "live_storage_required": 0,
        }
        steps.append(
            _step_trace(
                run_id=run_id,
                stage_name="soc_storage_projection",
                input_payload={
                    "artifacts": len(artifacts),
                    "classifications": len(classifications),
                    "extracted_entities": len(entity_result.entities),
                    "semantic_relations": len(entity_result.relations),
                    "events": len(lifecycle_events),
                },
                output_payload=storage_projection,
            )
        )

        counts = {
            "artifacts": len(artifacts),
            "classifications": len(classifications),
            "entities": len(entity_result.entities),
            "relations": len(entity_result.relations),
            "events": len(lifecycle_events),
            "steps": len(steps),
        }
        idempotency_fingerprint = {
            "artifact_ids": sorted(artifact.external_id for artifact in artifacts),
            "classification_ids": sorted(
                classification.classification_id for classification in classifications
            ),
            "entity_ids": sorted(entity.entity_id for entity in entity_result.entities),
            "relation_ids": sorted(
                relation.relation_id for relation in entity_result.relations
            ),
            "event_ids": sorted(event.event_id for event in lifecycle_events),
            "counts": counts,
            "source_counts": source_snapshot["source_counts"],
            "storage_projection": storage_projection,
            "stage_names": [step.stage_name for step in steps],
        }
        return SocKnowledgeIngestionResult(
            run=run,
            steps=steps,
            coverage_mode=coverage_mode,
            counts=counts,
            source_counts=source_snapshot["source_counts"],
            storage_projection=storage_projection,
            idempotency_fingerprint=idempotency_fingerprint,
        )


def _source_snapshot(artifacts: list[RawSourceArtifact]) -> dict[str, Any]:
    source_counts = Counter(artifact.source_type for artifact in artifacts)
    return {
        "artifact_ids": [artifact.external_id for artifact in artifacts],
        "source_counts": dict(sorted(source_counts.items())),
        "artifacts": len(artifacts),
    }


def _step_trace(
    *,
    run_id: str,
    stage_name: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
) -> AgentStepTrace:
    return AgentStepTrace(
        step_id=f"{run_id}_{stage_name}",
        run_id=run_id,
        stage_name=stage_name,
        status="succeeded",
        input_hash=stable_hash(input_payload),
        output_hash=stable_hash(output_payload),
        validation_status="passed",
        validation_result={
            "output_keys": sorted(output_payload),
        },
        completed_at=datetime.now(UTC),
    )

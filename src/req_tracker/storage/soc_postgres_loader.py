"""Load SoC fixture artifacts into PostgreSQL profile tables."""

import math
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.soc_models import (
    SOC_SCHEMA_VERSION,
    SocAxisClassification,
    SocLifecycleEvent,
)

VectorProvider = Callable[[RawSourceArtifact], list[float]]


class SocPostgresFixtureLoader:
    """Write SoC artifacts, classifications, and deterministic embeddings to PostgreSQL."""

    def __init__(
        self,
        dsn: str = "",
        *,
        connection_factory: Callable[[], Any] | None = None,
        vector_provider: VectorProvider | None = None,
    ) -> None:
        if not dsn and connection_factory is None:
            raise ValueError("postgres dsn is required when connection_factory is not provided")
        self._dsn = dsn
        self._connection_factory = connection_factory
        self._vector_provider = vector_provider or _deterministic_artifact_vector

    def load_fixture(
        self,
        *,
        artifacts: Sequence[RawSourceArtifact],
        classifications: Sequence[SocAxisClassification],
        embedding_model: str = "deterministic-hash-v1",
    ) -> dict[str, int]:
        """Upsert artifacts, classifications, lifecycle events, and embeddings."""
        lifecycle_events = lifecycle_events_for_artifacts(
            artifacts,
            run_id="fixture_load",
            step_id="artifact_sync",
        )
        return {
            "artifacts": self.upsert_artifacts(artifacts),
            "classifications": self.upsert_classifications(classifications),
            "events": self.upsert_lifecycle_events(lifecycle_events),
            "embeddings": self.upsert_embeddings(artifacts, embedding_model=embedding_model),
        }

    def upsert_artifacts(self, artifacts: Sequence[RawSourceArtifact]) -> int:
        """Upsert artifact rows used by FTS/pg_trgm and retrieval result projection."""
        with self._connect() as connection:
            for artifact in artifacts:
                connection.execute(
                    """
                    INSERT INTO soc_artifacts (
                        external_id, source_type, source_url, project_key, title, body_text,
                        created_at, updated_at, labels, links, raw_hash, last_synced_at,
                        metadata, schema_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(external_id) DO UPDATE SET
                        source_type = excluded.source_type,
                        source_url = excluded.source_url,
                        project_key = excluded.project_key,
                        title = excluded.title,
                        body_text = excluded.body_text,
                        updated_at = excluded.updated_at,
                        labels = excluded.labels,
                        links = excluded.links,
                        raw_hash = excluded.raw_hash,
                        last_synced_at = excluded.last_synced_at,
                        metadata = excluded.metadata,
                        schema_version = excluded.schema_version
                    """,
                    (
                        artifact.external_id,
                        artifact.source_type,
                        artifact.source_url,
                        artifact.project_key,
                        artifact.title,
                        artifact.body_text,
                        artifact.created_at,
                        artifact.updated_at,
                        artifact.labels,
                        artifact.links,
                        _artifact_hash(artifact),
                        artifact.updated_at,
                        Jsonb(artifact.metadata),
                        SOC_SCHEMA_VERSION,
                    ),
                )
        return len(artifacts)

    def upsert_classifications(
        self,
        classifications: Sequence[SocAxisClassification],
    ) -> int:
        """Upsert rule or fixture axis classifications used by slice filtering."""
        with self._connect() as connection:
            for classification in classifications:
                connection.execute(
                    """
                    INSERT INTO soc_classifications (
                        artifact_id, axis, value, confidence, source, run_id, step_id,
                        metadata, created_at, schema_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(artifact_id, axis, value, source) DO UPDATE SET
                        confidence = excluded.confidence,
                        run_id = excluded.run_id,
                        step_id = excluded.step_id,
                        metadata = excluded.metadata,
                        created_at = excluded.created_at,
                        schema_version = excluded.schema_version
                    """,
                    (
                        classification.entity_id,
                        classification.axis,
                        classification.value,
                        classification.confidence,
                        classification.source,
                        classification.run_id,
                        classification.step_id,
                        Jsonb(
                            {
                                "classification_id": classification.classification_id,
                                "evidence_ref": classification.evidence_ref,
                                "status": classification.status,
                            }
                        ),
                        classification.created_at,
                        classification.schema_version,
                    ),
                )
        return len(classifications)

    def upsert_lifecycle_events(
        self,
        events: Sequence[SocLifecycleEvent],
    ) -> int:
        """Upsert append-only lifecycle events used by timeline slice queries."""
        with self._connect() as connection:
            for event in events:
                connection.execute(
                    """
                    INSERT INTO soc_event_log (
                        event_id, entity_id, entity_type, ts, change_type,
                        before_state, after_state, source, run_id, step_id,
                        metadata, schema_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(event_id) DO UPDATE SET
                        entity_id = excluded.entity_id,
                        entity_type = excluded.entity_type,
                        ts = excluded.ts,
                        change_type = excluded.change_type,
                        before_state = excluded.before_state,
                        after_state = excluded.after_state,
                        source = excluded.source,
                        run_id = excluded.run_id,
                        step_id = excluded.step_id,
                        metadata = excluded.metadata,
                        schema_version = excluded.schema_version
                    """,
                    (
                        event.event_id,
                        event.entity_id,
                        "artifact",
                        event.timestamp,
                        event.change_type,
                        Jsonb(event.before) if event.before is not None else None,
                        Jsonb(event.after) if event.after is not None else None,
                        event.source,
                        event.run_id,
                        event.step_id,
                        Jsonb({"source_url": event.source_url}),
                        event.schema_version,
                    ),
                )
        return len(events)

    def upsert_embeddings(
        self,
        artifacts: Sequence[RawSourceArtifact],
        *,
        embedding_model: str = "deterministic-hash-v1",
    ) -> int:
        """Upsert one deterministic pgvector-compatible embedding per artifact."""
        with self._connect() as connection:
            for artifact in artifacts:
                chunk_text = _embedding_text(artifact)
                connection.execute(
                    """
                    INSERT INTO soc_artifact_embeddings (
                        artifact_id, chunk_idx, embedding_model, embedding, text_hash,
                        chunk_text, metadata, schema_version
                    )
                    VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s)
                    ON CONFLICT(artifact_id, chunk_idx, embedding_model) DO UPDATE SET
                        embedding = excluded.embedding,
                        text_hash = excluded.text_hash,
                        chunk_text = excluded.chunk_text,
                        metadata = excluded.metadata,
                        schema_version = excluded.schema_version
                    """,
                    (
                        artifact.external_id,
                        0,
                        embedding_model,
                        _vector_literal(self._vector_provider(artifact)),
                        stable_hash(chunk_text),
                        chunk_text,
                        Jsonb(
                            {
                                "project_key": artifact.project_key,
                                "source_type": artifact.source_type,
                                "source_url": artifact.source_url,
                            }
                        ),
                        SOC_SCHEMA_VERSION,
                    ),
                )
        return len(artifacts)

    def _connect(self) -> Any:
        if self._connection_factory is not None:
            return self._connection_factory()
        return psycopg.connect(self._dsn)


def lifecycle_events_for_artifacts(
    artifacts: Sequence[RawSourceArtifact],
    *,
    run_id: str,
    step_id: str,
) -> list[SocLifecycleEvent]:
    """Build source-linked sync events for fixture or target artifact loads."""
    events: list[SocLifecycleEvent] = []
    for artifact in artifacts:
        raw_hash = _artifact_hash(artifact)
        timestamp = _artifact_timestamp(artifact.updated_at)
        event_payload = {
            "entity_id": artifact.external_id,
            "change_type": "artifact_synced",
            "timestamp": timestamp.isoformat(),
            "raw_hash": raw_hash,
        }
        events.append(
            SocLifecycleEvent(
                event_id=f"soc_evt_{stable_hash(event_payload)[:16]}",
                entity_id=artifact.external_id,
                timestamp=timestamp,
                change_type="artifact_synced",
                before=None,
                after={
                    "project_key": artifact.project_key,
                    "source_type": artifact.source_type,
                    "title": artifact.title,
                    "updated_at": timestamp.isoformat(),
                    "raw_hash": raw_hash,
                },
                source=artifact.source_type,
                source_url=artifact.source_url,
                run_id=run_id,
                step_id=step_id,
            )
        )
    return events


def _artifact_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _artifact_hash(artifact: RawSourceArtifact) -> str:
    return stable_hash(
        {
            "body_text": artifact.body_text,
            "external_id": artifact.external_id,
            "source_url": artifact.source_url,
            "title": artifact.title,
            "updated_at": artifact.updated_at,
        }
    )


def _embedding_text(artifact: RawSourceArtifact) -> str:
    return " ".join([artifact.title, artifact.body_text, *artifact.labels])


def _deterministic_artifact_vector(
    artifact: RawSourceArtifact,
    vector_size: int = 1024,
) -> list[float]:
    counts: Counter[int] = Counter()
    for raw in _embedding_text(artifact).lower().split():
        token = "".join(char for char in raw if char.isalnum())
        if not token:
            continue
        counts[int(stable_hash(token)[:8], 16) % vector_size] += 1
    vector = [0.0] * vector_size
    for bucket, count in counts.items():
        vector[bucket] = float(count)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"

"""Rule-only SoC axis classifier for fixture-first validation."""

from collections.abc import Iterable
from functools import cache

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import ModelRequest
from req_tracker.ontology.soc_models import (
    SOC_SCHEMA_VERSION,
    ClassificationSource,
    ClassificationStatus,
    SocAxisClassification,
    SocAxisClassificationBatch,
    SocAxisClassificationSuggestion,
)
from req_tracker.ontology.soc_schema import (
    SOC_SCHEMA_ROOT,
    SocSchema,
    load_soc_schema,
    validate_soc_schema,
)


class GatewaySocAxisClassifier:
    """Use the model gateway to propose pending SoC axis classification enrichments."""

    def __init__(
        self,
        *,
        client: ModelGatewayClient,
        model_profile_id: str,
        prompt_version_id: str,
    ) -> None:
        self._client = client
        self._model_profile_id = model_profile_id
        self._prompt_version_id = prompt_version_id

    def enrich_artifact(
        self,
        artifact: RawSourceArtifact,
        *,
        baseline_classifications: Iterable[SocAxisClassification],
        run_id: str,
        step_id: str = "soc_axis_classification_enrichment",
    ) -> list[SocAxisClassification]:
        """Return Claude/model proposals as pending side-car classifications."""
        baseline = list(baseline_classifications)
        request = ModelRequest(
            model_profile_id=self._model_profile_id,
            prompt_version_id=self._prompt_version_id,
            payload=_enrichment_payload(artifact, baseline),
            data_classification="public_internal",
            masking_applied=bool(
                artifact.metadata.get("masking_applied")
                or artifact.metadata.get("soc_fixture_seed")
            ),
            access_checked=True,
        )
        try:
            _response, parsed, validation = self._client.complete(
                run_id=run_id,
                step_id=step_id,
                request=request,
                response_model=SocAxisClassificationBatch,
            )
        except Exception:
            return []
        if parsed is None or validation.status != "passed":
            return []
        return _proposal_classifications(
            artifact=artifact,
            suggestions=parsed.classifications,
            run_id=run_id,
            step_id=step_id,
        )


def classify_soc_axes(
    artifact: RawSourceArtifact,
    *,
    run_id: str,
    step_id: str,
) -> list[SocAxisClassification]:
    """Classify one artifact across Project, V-Level, Concern, and Component axes."""
    schema = _load_validated_soc_schema()
    text = _classification_text(artifact)

    classifications = [
        _classification(
            entity_id=artifact.external_id,
            axis="project",
            value=artifact.project_key,
            confidence=1.0,
            run_id=run_id,
            step_id=step_id,
        )
    ]
    v_level = _v_level_from_labels(artifact.labels) or _v_level_fallback(artifact)
    classifications.append(
        _classification(
            entity_id=artifact.external_id,
            axis="v_level",
            value=v_level,
            confidence=0.95 if _v_level_from_labels(artifact.labels) else 0.65,
            run_id=run_id,
            step_id=step_id,
        )
    )
    for concern in _matched_vocab_values(
        text=text,
        labels=artifact.labels,
        prefix="concern/",
        records=((item.name, item.aliases) for item in schema.concerns),
    ):
        classifications.append(
            _classification(
                entity_id=artifact.external_id,
                axis="concern",
                value=concern,
                confidence=0.95,
                run_id=run_id,
                step_id=step_id,
            )
        )
    for component in _matched_vocab_values(
        text=text,
        labels=artifact.labels,
        prefix="component/",
        records=((item.name, item.aliases) for item in schema.components),
    ):
        classifications.append(
            _classification(
                entity_id=artifact.external_id,
                axis="component",
                value=component,
                confidence=0.95,
                run_id=run_id,
                step_id=step_id,
            )
        )
    return _dedupe_classifications(classifications)


def _classification(
    *,
    entity_id: str,
    axis: str,
    value: str,
    confidence: float,
    run_id: str,
    step_id: str,
    source: ClassificationSource = "rule",
    status: ClassificationStatus = "baseline",
    evidence_ref: str | None = None,
) -> SocAxisClassification:
    payload = {
        "entity_id": entity_id,
        "axis": axis,
        "value": value,
    }
    if source != "rule":
        payload["source"] = source
    return SocAxisClassification(
        classification_id=f"soc_cls_{stable_hash(payload)[:16]}",
        entity_id=entity_id,
        axis=axis,  # type: ignore[arg-type]
        value=value,
        confidence=confidence,
        source=source,
        status=status,
        evidence_ref=evidence_ref,
        run_id=run_id,
        step_id=step_id,
    )


@cache
def _load_validated_soc_schema() -> SocSchema:
    schema = load_soc_schema(SOC_SCHEMA_ROOT)
    validate_soc_schema(schema)
    return schema


def _classification_text(artifact: RawSourceArtifact) -> str:
    return " ".join([artifact.title, artifact.body_text, *artifact.labels]).lower()


def _enrichment_payload(
    artifact: RawSourceArtifact,
    baseline_classifications: list[SocAxisClassification],
) -> dict[str, object]:
    schema = _load_validated_soc_schema()
    return {
        "task": "soc_axis_classification",
        "schema_version": SOC_SCHEMA_VERSION,
        "artifact": {
            "external_id": artifact.external_id,
            "source_type": artifact.source_type,
            "source_url": artifact.source_url,
            "project_key": artifact.project_key,
            "title": artifact.title,
            "body_preview": artifact.body_text[:1000],
            "labels": artifact.labels,
        },
        "baseline_classifications": [
            classification.model_dump(mode="json") for classification in baseline_classifications
        ],
        "allowed_axes": ["project", "v_level", "concern", "component"],
        "allowed_v_levels": ["L0", "L1", "L2", "L3", "L4", "L5"],
        "allowed_concerns": [item.name for item in schema.concerns],
        "allowed_components": [item.name for item in schema.components],
        "output_contract": (
            "Return ONLY raw JSON for SocAxisClassificationBatch. No prose, no markdown, "
            "no code fences. Include classification suggestions only. Do not mark "
            "proposals approved or baseline."
        ),
        "example_output": {
            "classifications": [
                {
                    "entity_id": artifact.external_id,
                    "axis": "concern",
                    "value": "Performance",
                    "confidence": 0.72,
                    "evidence_ref": "title/body phrase",
                }
            ]
        },
    }


def _proposal_classifications(
    *,
    artifact: RawSourceArtifact,
    suggestions: list[SocAxisClassificationSuggestion],
    run_id: str,
    step_id: str,
) -> list[SocAxisClassification]:
    proposals: list[SocAxisClassification] = []
    for suggestion in suggestions:
        if suggestion.entity_id != artifact.external_id:
            continue
        proposals.append(
            _classification(
                entity_id=suggestion.entity_id,
                axis=suggestion.axis,
                value=suggestion.value,
                confidence=suggestion.confidence,
                run_id=run_id,
                step_id=step_id,
                source="claude",
                status="pending",
                evidence_ref=suggestion.evidence_ref,
            )
        )
    return _dedupe_classifications(proposals)


def _v_level_from_labels(labels: list[str]) -> str | None:
    for label in labels:
        normalized = label.strip().lower()
        if normalized.startswith("level/l") and len(normalized) >= len("level/l0"):
            return normalized.removeprefix("level/").upper()
    return None


def _v_level_fallback(artifact: RawSourceArtifact) -> str:
    text = _classification_text(artifact)
    if artifact.source_type == "email" and "customer" in text:
        return "L0"
    if "system" in text or "requirement" in text:
        return "L1"
    if "architecture" in text:
        return "L2"
    if "subsystem" in text or "ip architecture" in text:
        return "L3"
    if "design" in text:
        return "L4"
    if "rtl" in text or "driver" in text or "unit test" in text:
        return "L5"
    return "L2"


def _matched_vocab_values(
    *,
    text: str,
    labels: list[str],
    prefix: str,
    records: Iterable[tuple[str, list[str]]],
) -> list[str]:
    values: list[str] = []
    label_values = {
        label.strip().lower().removeprefix(prefix)
        for label in labels
        if label.strip().lower().startswith(prefix)
    }
    for name, aliases in records:
        normalized_name = _normalize_token(name)
        normalized_aliases = {_normalize_token(alias) for alias in aliases}
        if normalized_name in label_values or normalized_aliases & label_values:
            values.append(name)
            continue
        if label_values:
            continue
        if any(alias.strip().lower() in text for alias in aliases):
            values.append(name)
    return values


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _dedupe_classifications(
    classifications: list[SocAxisClassification],
) -> list[SocAxisClassification]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[SocAxisClassification] = []
    for classification in classifications:
        key = (classification.entity_id, classification.axis, classification.value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(classification)
    return deduped

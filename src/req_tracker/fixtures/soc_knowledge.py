"""SoC Knowledge PoC seed fixture loader."""

from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.soc_models import (
    SocAxisClassification,
    SocGroundTruthQuery,
    SocSlice,
)

SOC_FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "soc_knowledge"
SOC_SCALE_ARTIFACTS_FILENAME = "scale_artifacts.yaml"
SOC_SCALE_QUERIES_FILENAME = "scale_queries.yaml"


def load_soc_seed_artifacts(fixture_root: Path = SOC_FIXTURE_ROOT) -> list[RawSourceArtifact]:
    """Load seed artifacts for the SoC Knowledge fixture-first loop."""
    payload = _read_yaml_mapping(fixture_root / "artifacts.yaml")
    return _load_artifacts_from_payload(payload, path_name="artifacts.yaml")


def load_soc_scale_artifacts(fixture_root: Path = SOC_FIXTURE_ROOT) -> list[RawSourceArtifact]:
    """Load generated scale artifacts for Phase 1 fixture coverage."""
    payload = _read_yaml_mapping(fixture_root / SOC_SCALE_ARTIFACTS_FILENAME)
    return _load_artifacts_from_payload(payload, path_name=SOC_SCALE_ARTIFACTS_FILENAME)


def classifications_for_artifacts(
    artifacts: list[RawSourceArtifact],
    *,
    run_id: str,
    step_id: str,
) -> list[SocAxisClassification]:
    """Build approved fixture classifications from artifact axis annotations."""
    classifications: list[SocAxisClassification] = []
    for artifact in artifacts:
        axes = artifact.metadata.get("soc_axes")
        if not isinstance(axes, dict):
            raise ValueError(f"artifact {artifact.external_id} missing metadata.soc_axes")
        classifications.append(
            _classification(
                entity_id=artifact.external_id,
                axis="project",
                value=artifact.project_key,
                run_id=run_id,
                step_id=step_id,
            )
        )
        v_level = axes.get("v_level")
        if not isinstance(v_level, str):
            raise ValueError(f"artifact {artifact.external_id} missing v_level")
        classifications.append(
            _classification(
                entity_id=artifact.external_id,
                axis="v_level",
                value=v_level,
                run_id=run_id,
                step_id=step_id,
            )
        )
        for concern in _axis_values(artifact.external_id, axes, "concerns"):
            classifications.append(
                _classification(
                    entity_id=artifact.external_id,
                    axis="concern",
                    value=concern,
                    run_id=run_id,
                    step_id=step_id,
                )
            )
        for component in _axis_values(artifact.external_id, axes, "components"):
            classifications.append(
                _classification(
                    entity_id=artifact.external_id,
                    axis="component",
                    value=component,
                    run_id=run_id,
                    step_id=step_id,
                )
            )
    return classifications


def _load_artifacts_from_payload(
    payload: dict[str, object],
    *,
    path_name: str,
) -> list[RawSourceArtifact]:
    raw_artifacts = payload.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise ValueError(f"{path_name} must contain list key 'artifacts'")
    return [RawSourceArtifact.model_validate(item) for item in raw_artifacts]


def load_soc_ground_truth_classifications(
    fixture_root: Path = SOC_FIXTURE_ROOT,
) -> list[SocAxisClassification]:
    """Load fixture ground-truth classifications from artifact axis annotations."""
    return classifications_for_artifacts(
        load_soc_seed_artifacts(fixture_root),
        run_id="fixture_seed",
        step_id="fixture_ground_truth",
    )


def load_soc_query_set(fixture_root: Path = SOC_FIXTURE_ROOT) -> list[SocGroundTruthQuery]:
    """Load seed ground-truth query cases."""
    payload = _read_yaml_mapping(fixture_root / "queries.yaml")
    return _load_queries_from_payload(payload, path_name="queries.yaml")


def load_soc_scale_query_set(fixture_root: Path = SOC_FIXTURE_ROOT) -> list[SocGroundTruthQuery]:
    """Load generated scale ground-truth query cases."""
    payload = _read_yaml_mapping(fixture_root / SOC_SCALE_QUERIES_FILENAME)
    return _load_queries_from_payload(payload, path_name=SOC_SCALE_QUERIES_FILENAME)


def _load_queries_from_payload(
    payload: dict[str, object],
    *,
    path_name: str,
) -> list[SocGroundTruthQuery]:
    raw_queries = payload.get("queries")
    if not isinstance(raw_queries, list):
        raise ValueError(f"{path_name} must contain list key 'queries'")
    queries: list[SocGroundTruthQuery] = []
    for item in raw_queries:
        if not isinstance(item, dict):
            raise ValueError("query items must be mappings")
        slice_payload = item.get("slice")
        if not isinstance(slice_payload, dict):
            raise ValueError(f"query {item.get('q_id')} missing slice")
        queries.append(
            SocGroundTruthQuery(
                q_id=str(item["q_id"]),
                question=str(item["question"]),
                slice=SocSlice.model_validate(slice_payload),
                expected_artifact_ids=[
                    str(value) for value in item.get("expected_artifact_ids", [])
                ],
                expected_source_urls=[
                    str(value) for value in item.get("expected_source_urls", [])
                ],
            )
        )
    return queries


def _classification(
    *,
    entity_id: str,
    axis: str,
    value: str,
    run_id: str,
    step_id: str,
) -> SocAxisClassification:
    payload = {"entity_id": entity_id, "axis": axis, "value": value}
    return SocAxisClassification(
        classification_id=f"soc_gt_{stable_hash(payload)[:16]}",
        entity_id=entity_id,
        axis=axis,  # type: ignore[arg-type]
        value=value,
        confidence=1.0,
        source="fixture",
        status="approved",
        run_id=run_id,
        step_id=step_id,
    )


def _axis_values(entity_id: str, axes: dict[Any, Any], key: str) -> list[str]:
    raw_values = axes.get(key)
    if not isinstance(raw_values, list) or not raw_values:
        raise ValueError(f"artifact {entity_id} missing {key}")
    return [str(value) for value in raw_values]


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.exists():
        raise ValueError(f"fixture file does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"fixture file must contain a mapping: {path}")
    return cast(dict[str, object], payload)

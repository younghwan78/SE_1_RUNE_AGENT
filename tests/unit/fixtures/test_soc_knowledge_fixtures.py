"""Tests for SoC Knowledge PoC seed fixtures and ground truth."""

from collections import Counter, defaultdict

from req_tracker.fixtures.soc_knowledge import (
    load_soc_ground_truth_classifications,
    load_soc_query_set,
    load_soc_scale_artifacts,
    load_soc_scale_query_set,
    load_soc_seed_artifacts,
)


def test_soc_seed_fixture_has_expected_source_mix_and_project_axis() -> None:
    artifacts = load_soc_seed_artifacts()

    assert len(artifacts) == 40
    assert Counter(artifact.source_type for artifact in artifacts) == {
        "jira": 20,
        "confluence": 10,
        "email": 10,
    }
    assert {artifact.project_key for artifact in artifacts} == {"SOC-N-1", "SOC-N-2"}
    assert all(artifact.source_url for artifact in artifacts)
    assert all(artifact.metadata.get("soc_fixture_seed") is True for artifact in artifacts)


def test_soc_ground_truth_classifications_cover_all_four_axes() -> None:
    artifacts = load_soc_seed_artifacts()
    classifications = load_soc_ground_truth_classifications()
    axes_by_entity: dict[str, set[str]] = defaultdict(set)
    values_by_axis: dict[str, set[str]] = defaultdict(set)
    artifact_ids = {artifact.external_id for artifact in artifacts}

    for classification in classifications:
        axes_by_entity[classification.entity_id].add(classification.axis)
        values_by_axis[classification.axis].add(classification.value)

    assert set(axes_by_entity) == artifact_ids
    required_axes = {"project", "v_level", "concern", "component"}
    assert all(required_axes <= axes for axes in axes_by_entity.values())
    assert values_by_axis["project"] == {"SOC-N-1", "SOC-N-2"}
    assert values_by_axis["v_level"] == {"L0", "L1", "L2", "L3", "L4", "L5"}
    assert {"Power", "Performance", "Memory", "Area", "Thermal", "Latency"} <= values_by_axis[
        "concern"
    ]
    assert {"Camera", "Display", "NPU", "GPU", "MemorySubsystem"} <= values_by_axis[
        "component"
    ]


def test_soc_query_set_covers_four_required_slice_patterns() -> None:
    queries = load_soc_query_set()

    assert len(queries) >= 20
    assert {query.slice.pattern for query in queries} >= {
        "concern_slice",
        "topic_intersection",
        "timeline_slice",
        "lifecycle_trace",
    }
    assert all(query.expected_artifact_ids for query in queries if query.slice.pattern != "unknown")
    assert any(
        query.slice.pattern == "unknown" and not query.expected_artifact_ids
        for query in queries
    )


def test_soc_scale_fixture_reaches_phase_one_source_mix() -> None:
    artifacts = load_soc_scale_artifacts()

    assert len(artifacts) == 400
    assert Counter(artifact.source_type for artifact in artifacts) == {
        "jira": 200,
        "confluence": 100,
        "email": 100,
    }
    assert {artifact.project_key for artifact in artifacts} == {"SOC-N-1", "SOC-N-2"}
    assert all(artifact.source_url for artifact in artifacts)
    assert all(artifact.metadata.get("soc_fixture_scale") is True for artifact in artifacts)


def test_soc_scale_query_set_annotates_scale_fixture_expected_results() -> None:
    artifacts = load_soc_scale_artifacts()
    artifact_ids = {artifact.external_id for artifact in artifacts}
    queries = load_soc_scale_query_set()

    assert len(queries) >= 30
    assert {query.slice.pattern for query in queries} >= {
        "concern_slice",
        "topic_intersection",
        "timeline_slice",
        "lifecycle_trace",
        "unknown",
    }
    assert all(
        expected_id in artifact_ids
        for query in queries
        for expected_id in query.expected_artifact_ids
    )
    assert any(query.slice.pattern == "unknown" for query in queries)

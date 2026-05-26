"""Tests for packaged SoC ontology schema assets."""

from pathlib import Path

import pytest

from req_tracker.ontology.soc_schema import (
    SOC_SCHEMA_ROOT,
    SocSchemaValidationError,
    load_soc_schema,
    validate_soc_schema,
)


def test_packaged_soc_schema_covers_stage_a_axes_and_relations() -> None:
    schema = load_soc_schema(SOC_SCHEMA_ROOT)

    required_entities = {
        "Project",
        "Issue",
        "Page",
        "EmailThread",
        "EmailMessage",
        "Concern",
        "Component",
        "Event",
    }
    required_concerns = {
        "Power",
        "Performance",
        "Memory",
        "Area",
        "Thermal",
        "Latency",
        "Bandwidth",
        "Reliability",
    }
    required_relations = {
        "belongsToProject",
        "atLevel",
        "addresses",
        "involves",
        "hasLifecycleEvent",
        "feedbackTo",
    }

    assert required_entities <= {
        entity.name for entity in schema.entities
    }
    assert [level.name for level in schema.v_levels] == ["L0", "L1", "L2", "L3", "L4", "L5"]
    assert required_concerns <= {
        concern.name for concern in schema.concerns
    }
    assert {"Camera", "Display", "NPU", "GPU", "MemorySubsystem"} <= {
        component.name for component in schema.components
    }
    assert required_relations <= {
        relation.name for relation in schema.relations
    }

    validate_soc_schema(schema)


def test_soc_schema_rejects_relation_with_unknown_entity(tmp_path: Path) -> None:
    schema_root = tmp_path / "schema"
    schema_root.mkdir()
    (schema_root / "entities.yaml").write_text(
        """
entities:
  - name: Artifact
    properties:
      - {name: id, type: string, required: true}
""".strip(),
        encoding="utf-8",
    )
    (schema_root / "relations.yaml").write_text(
        """
relations:
  - name: brokenRelation
    from: Artifact
    to: MissingEntity
    cardinality: many-to-one
""".strip(),
        encoding="utf-8",
    )
    vocab_root = schema_root / "vocab"
    vocab_root.mkdir()
    (vocab_root / "v_levels.yaml").write_text(
        """
v_levels:
  - {name: L0, description: Customer needs}
  - {name: L1, description: System requirements}
  - {name: L2, description: SoC architecture}
  - {name: L3, description: Subsystem architecture}
  - {name: L4, description: IP design}
  - {name: L5, description: Implementation}
""".strip(),
        encoding="utf-8",
    )
    (vocab_root / "concerns.yaml").write_text(
        """
concerns:
  - {name: Power, aliases: [power], units: [mW]}
""".strip(),
        encoding="utf-8",
    )
    (vocab_root / "components.yaml").write_text(
        """
components:
  - {name: Camera, aliases: [camera]}
""".strip(),
        encoding="utf-8",
    )

    schema = load_soc_schema(schema_root)

    with pytest.raises(SocSchemaValidationError, match="MissingEntity"):
        validate_soc_schema(schema)

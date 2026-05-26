"""Loader and validator for SoC ontology YAML schema assets."""

from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

SOC_SCHEMA_ROOT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "ontology"
    / "soc"
    / "schema"
    / "v0.1"
)
EXPECTED_V_LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")


class SocSchemaValidationError(ValueError):
    """Raised when packaged SoC ontology schema assets are internally inconsistent."""


class SocSchemaModel(BaseModel):
    """Base model for SoC schema YAML records."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SocSchemaProperty(SocSchemaModel):
    """Entity or relation property defined in YAML."""

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    required: bool = False
    unique: bool = False
    target: str | None = None
    values: list[str] = Field(default_factory=list)


class SocSchemaEntity(SocSchemaModel):
    """Entity definition from entities.yaml."""

    name: str = Field(min_length=1)
    parent: str | None = None
    properties: list[SocSchemaProperty] = Field(default_factory=list)
    indexes: list[dict[str, str]] = Field(default_factory=list)


class SocSchemaRelation(SocSchemaModel):
    """Relation definition from relations.yaml."""

    name: str = Field(min_length=1)
    from_entity: str = Field(alias="from", min_length=1)
    to_entity: str = Field(alias="to", min_length=1)
    cardinality: str = Field(min_length=1)
    properties: list[SocSchemaProperty] = Field(default_factory=list)


class SocVLevel(SocSchemaModel):
    """V-model level vocabulary record."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    primary_sources: list[str] = Field(default_factory=list)


class SocConcern(SocSchemaModel):
    """Concern vocabulary record."""

    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    definition: str | None = None


class SocComponent(SocSchemaModel):
    """Component vocabulary record."""

    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    parent_component: str | None = None
    definition: str | None = None


class SocSchema(SocSchemaModel):
    """Fully loaded SoC ontology schema bundle."""

    entities: list[SocSchemaEntity]
    relations: list[SocSchemaRelation]
    v_levels: list[SocVLevel]
    concerns: list[SocConcern]
    components: list[SocComponent]


def load_soc_schema(schema_root: Path = SOC_SCHEMA_ROOT) -> SocSchema:
    """Load SoC ontology schema and vocab YAML files from a schema root."""
    return SocSchema(
        entities=_load_records(schema_root / "entities.yaml", "entities", SocSchemaEntity),
        relations=_load_records(schema_root / "relations.yaml", "relations", SocSchemaRelation),
        v_levels=_load_records(schema_root / "vocab" / "v_levels.yaml", "v_levels", SocVLevel),
        concerns=_load_records(schema_root / "vocab" / "concerns.yaml", "concerns", SocConcern),
        components=_load_records(
            schema_root / "vocab" / "components.yaml",
            "components",
            SocComponent,
        ),
    )


def validate_soc_schema(schema: SocSchema) -> None:
    """Validate cross-file references and required Stage A vocabulary coverage."""
    entity_names = _unique_names("entity", [entity.name for entity in schema.entities])
    _unique_names("relation", [relation.name for relation in schema.relations])
    _unique_names("concern", [concern.name for concern in schema.concerns])
    component_names = _unique_names(
        "component",
        [component.name for component in schema.components],
    )

    for entity in schema.entities:
        if entity.parent is not None and entity.parent not in entity_names:
            raise SocSchemaValidationError(
                f"entity {entity.name} references unknown parent {entity.parent}"
            )

    for relation in schema.relations:
        if relation.from_entity not in entity_names:
            raise SocSchemaValidationError(
                f"relation {relation.name} references unknown from entity {relation.from_entity}"
            )
        if relation.to_entity not in entity_names:
            raise SocSchemaValidationError(
                f"relation {relation.name} references unknown to entity {relation.to_entity}"
            )

    for component in schema.components:
        if (
            component.parent_component is not None
            and component.parent_component not in component_names
        ):
            raise SocSchemaValidationError(
                f"component {component.name} references unknown parent {component.parent_component}"
            )

    v_levels = tuple(level.name for level in schema.v_levels)
    if v_levels != EXPECTED_V_LEVELS:
        raise SocSchemaValidationError(
            f"v_levels must be {EXPECTED_V_LEVELS}, got {v_levels}"
        )

    _unique_aliases("concern", [(concern.name, concern.aliases) for concern in schema.concerns])
    _unique_aliases(
        "component",
        [(component.name, component.aliases) for component in schema.components],
    )


def _load_records[TModel: BaseModel](
    path: Path,
    key: str,
    model: type[TModel],
) -> list[TModel]:
    payload = _read_yaml_mapping(path)
    raw_records = payload.get(key)
    if not isinstance(raw_records, list):
        raise SocSchemaValidationError(f"{path} must contain list key {key}")
    return [model.model_validate(item) for item in raw_records]


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SocSchemaValidationError(f"schema file does not exist: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SocSchemaValidationError(f"schema file must contain a mapping: {path}")
    return cast(dict[str, object], loaded)


def _unique_names(kind: str, values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise SocSchemaValidationError(f"duplicate {kind} names: {sorted(duplicates)}")
    return seen


def _unique_aliases(kind: str, values: list[tuple[str, list[str]]]) -> None:
    alias_owner: dict[str, str] = {}
    for owner, aliases in values:
        for alias in aliases:
            normalized = alias.strip().lower()
            if not normalized:
                continue
            existing = alias_owner.get(normalized)
            if existing is not None and existing != owner:
                raise SocSchemaValidationError(
                    f"duplicate {kind} alias {alias!r} used by {existing} and {owner}"
                )
            alias_owner[normalized] = owner

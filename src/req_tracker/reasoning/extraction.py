"""Deterministic node extraction."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.ontology.id_factory import node_id
from req_tracker.ontology.models import EvidenceSpan, NodeType, OntologyNode, SourceArtifact

_KEYWORDS: tuple[tuple[str, NodeType], ...] = (
    ("shall", "Requirement"),
    ("must", "Requirement"),
    ("architecture", "Architecture_Block"),
    ("design", "Design_Spec"),
    ("verification", "Verification"),
    ("test", "Verification"),
    ("issue", "Issue"),
    ("risk", "Risk"),
)


def extract_node(
    raw: RawSourceArtifact,
    artifact: SourceArtifact,
    evidence: EvidenceSpan,
) -> OntologyNode:
    """Extract one node from one normalized source artifact."""
    explicit = raw.metadata.get("mbse_type")
    node_type = explicit if isinstance(explicit, str) else _infer_type(raw)
    return OntologyNode(
        node_id=node_id(artifact.project_key, raw.external_id),
        node_type=node_type,  # type: ignore[arg-type]
        name=raw.title,
        description=raw.body_text,
        project_key=artifact.project_key,
        source_artifact_ids=[artifact.artifact_id],
        evidence=[evidence],
        created_by="source",
        confidence_score=0.95 if explicit else 0.65,
    )


def _infer_type(raw: RawSourceArtifact) -> NodeType:
    text = f"{raw.title} {raw.body_text} {' '.join(raw.labels)}".lower()
    for keyword, node_type in _KEYWORDS:
        if keyword in text:
            return node_type
    return "Design_Spec"


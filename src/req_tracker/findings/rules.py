"""Deterministic graph finding rules."""

from collections import defaultdict
from typing import cast

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import (
    EvidenceSpan,
    Finding,
    FindingType,
    OntologyNode,
    TraceabilityEdge,
)


def analyze_findings(
    nodes: list[OntologyNode],
    edges: list[TraceabilityEdge],
    *,
    source_artifacts: list[RawSourceArtifact] | None = None,
    evidence_by_external_id: dict[str, EvidenceSpan] | None = None,
) -> list[Finding]:
    """Run deterministic finding rules over candidate graph projection."""
    findings: list[Finding] = []
    incoming_by_target: dict[str, list[TraceabilityEdge]] = defaultdict(list)
    outgoing_by_source: dict[str, list[TraceabilityEdge]] = defaultdict(list)
    for edge in edges:
        incoming_by_target[edge.target_node_id].append(edge)
        outgoing_by_source[edge.source_node_id].append(edge)

    for node in nodes:
        if node.node_type == "Requirement":
            has_impl = any(
                edge.relation in {"satisfies", "implements"}
                for edge in incoming_by_target[node.node_id]
            )
            has_ver = any(edge.relation == "verifies" for edge in incoming_by_target[node.node_id])
            if not has_impl:
                findings.append(
                    _finding("REQ_WITHOUT_IMPLEMENTATION", node, "missing_implementation")
                )
            if not has_ver:
                findings.append(_finding("REQ_WITHOUT_VERIFICATION", node, "missing_verification"))
        if node.node_type == "Design_Spec":
            has_parent = any(
                edge.relation in {"implements", "satisfies", "derives"}
                for edge in outgoing_by_source[node.node_id]
            )
            if not has_parent:
                findings.append(_finding("DESIGN_WITHOUT_PARENT", node, "orphan_node"))

    impl_by_target: dict[str, list[TraceabilityEdge]] = defaultdict(list)
    for edge in edges:
        if edge.relation == "implements":
            impl_by_target[edge.target_node_id].append(edge)
    for target_id, impl_edges in impl_by_target.items():
        if len(impl_edges) > 1:
            affected = [target_id, *(edge.source_node_id for edge in impl_edges)]
            finding_hash = stable_hash(
                {"rule": "CONFLICTING_ALTERNATIVES", "ids": affected}
            )
            findings.append(
                Finding(
                    finding_id=f"fdg_{finding_hash[:16]}",
                    finding_type="conflict",
                    severity="high",
                    affected_node_ids=affected,
                    affected_edge_ids=[edge.edge_id for edge in impl_edges],
                    description=(
                        "Multiple implementation alternatives target the same architecture."
                    ),
                    suggested_action=(
                        "Select one implementation or mark alternatives as superseded."
                    ),
                    evidence=impl_edges[0].evidence,
                    detection_method="rule",
                    rule_id="CONFLICTING_ALTERNATIVES",
                )
            )
    findings.extend(
        _confluence_stale_trace_findings(
            nodes=nodes,
            source_artifacts=source_artifacts or [],
            evidence_by_external_id=evidence_by_external_id or {},
        )
    )
    findings.extend(
        _issue_affects_critical_requirement_findings(
            nodes=nodes,
            edges=edges,
            source_artifacts=source_artifacts or [],
        )
    )
    return findings


def _finding(rule_id: str, node: OntologyNode, finding_type: str) -> Finding:
    typed_finding_type = cast(FindingType, finding_type)
    return Finding(
        finding_id=f"fdg_{stable_hash({'rule': rule_id, 'node': node.node_id})[:16]}",
        finding_type=typed_finding_type,
        severity="high" if finding_type == "missing_implementation" else "medium",
        affected_node_ids=[node.node_id],
        affected_edge_ids=[],
        description=f"{node.node_id} triggered {rule_id}.",
        suggested_action="Review traceability links and add missing relation or verification.",
        evidence=node.evidence,
        detection_method="rule",
        rule_id=rule_id,
    )


def _confluence_stale_trace_findings(
    *,
    nodes: list[OntologyNode],
    source_artifacts: list[RawSourceArtifact],
    evidence_by_external_id: dict[str, EvidenceSpan],
) -> list[Finding]:
    node_by_external_id = {_external_id_from_node(node): node for node in nodes}
    findings: list[Finding] = []
    for artifact in source_artifacts:
        if artifact.source_type != "confluence":
            continue
        previous_version = _metadata_int(artifact.metadata.get("previous_version_number"))
        current_version = _metadata_int(artifact.metadata.get("version_number"))
        if previous_version is None or current_version is None:
            continue
        if current_version <= previous_version:
            continue
        node = node_by_external_id.get(artifact.external_id)
        evidence = evidence_by_external_id.get(artifact.external_id)
        if node is None or evidence is None:
            continue
        finding_hash = stable_hash(
            {
                "rule": "CONFLUENCE_PAGE_VERSION_CHANGED",
                "node": node.node_id,
                "previous_version": previous_version,
                "current_version": current_version,
            }
        )
        findings.append(
            Finding(
                finding_id=f"fdg_{finding_hash[:16]}",
                finding_type="stale_trace",
                severity="medium",
                affected_node_ids=[node.node_id],
                affected_edge_ids=[],
                description=(
                    f"{artifact.external_id} changed from Confluence version "
                    f"{previous_version} to {current_version}."
                ),
                suggested_action=(
                    "Review linked requirements, design, verification, and findings for stale "
                    "traceability after the document change."
                ),
                evidence=[evidence],
                detection_method="rule",
                rule_id="CONFLUENCE_PAGE_VERSION_CHANGED",
            )
        )
    return findings


def _issue_affects_critical_requirement_findings(
    *,
    nodes: list[OntologyNode],
    edges: list[TraceabilityEdge],
    source_artifacts: list[RawSourceArtifact],
) -> list[Finding]:
    nodes_by_id = {node.node_id: node for node in nodes}
    artifacts_by_external_id = {artifact.external_id: artifact for artifact in source_artifacts}
    findings: list[Finding] = []
    for edge in edges:
        if edge.relation != "affects":
            continue
        source = nodes_by_id.get(edge.source_node_id)
        target = nodes_by_id.get(edge.target_node_id)
        if source is None or target is None:
            continue
        if source.node_type not in {"Issue", "Risk"} or target.node_type != "Requirement":
            continue
        target_artifact = artifacts_by_external_id.get(_external_id_from_node(target))
        if target_artifact is None or not _is_critical_requirement(target_artifact):
            continue
        finding_hash = stable_hash(
            {
                "rule": "ISSUE_AFFECTS_CRITICAL_REQUIREMENT",
                "edge": edge.edge_id,
                "source": source.node_id,
                "target": target.node_id,
            }
        )
        findings.append(
            Finding(
                finding_id=f"fdg_{finding_hash[:16]}",
                finding_type="cross_domain_hidden",
                severity="critical",
                affected_node_ids=[source.node_id, target.node_id],
                affected_edge_ids=[edge.edge_id],
                description=(
                    f"{source.node_id} affects critical requirement {target.node_id}."
                ),
                suggested_action=(
                    "Escalate the affected critical requirement and review release risk, "
                    "verification coverage, and mitigation owner."
                ),
                evidence=edge.evidence,
                detection_method="rule",
                rule_id="ISSUE_AFFECTS_CRITICAL_REQUIREMENT",
            )
        )
    return findings


def _is_critical_requirement(artifact: RawSourceArtifact) -> bool:
    priority = str(artifact.metadata.get("priority", "")).strip().lower()
    labels = {label.strip().lower() for label in artifact.labels}
    return priority in {"p0", "critical", "blocker"} or bool(
        labels & {"p0", "critical", "blocker"}
    )


def _metadata_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _external_id_from_node(node: OntologyNode) -> str:
    prefix = f"node_{node.project_key}_"
    if node.node_id.startswith(prefix):
        return node.node_id.removeprefix(prefix).replace("_", "-")
    return node.node_id

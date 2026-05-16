"""Finding rule tests."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.findings.rules import analyze_findings
from req_tracker.ontology.models import EvidenceSpan, OntologyNode, TraceabilityEdge


def test_confluence_version_change_creates_stale_trace_finding() -> None:
    evidence = EvidenceSpan(
        artifact_id="src_confluence_CONF-1",
        source_url="https://confluence.example.com/wiki/pages/CONF-1",
        quote_hash="hash_conf_1",
        extracted_text_preview="Design page changed from version 3 to 4.",
        section_path="Camera > Architecture",
    )
    node = OntologyNode(
        node_id="node_RUNE_CAM_ALPHA_CONF-1",
        node_type="Design_Spec",
        name="Camera Architecture",
        description="Design page changed from version 3 to 4.",
        project_key="RUNE_CAM_ALPHA",
        source_artifact_ids=["src_confluence_CONF-1"],
        evidence=[evidence],
        created_by="source",
        confidence_score=0.95,
    )
    raw = RawSourceArtifact(
        external_id="CONF-1",
        source_type="confluence",
        source_url="https://confluence.example.com/wiki/pages/CONF-1",
        project_key="RUNE_CAM_ALPHA",
        title="Camera Architecture",
        body_text="Design page changed from version 3 to 4.",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-04T00:00:00Z",
        metadata={
            "mbse_type": "Design_Spec",
            "version_number": 4,
            "previous_version_number": 3,
        },
    )

    findings = analyze_findings(
        [node],
        [],
        source_artifacts=[raw],
        evidence_by_external_id={"CONF-1": evidence},
    )

    stale = [
        finding
        for finding in findings
        if finding.rule_id == "CONFLUENCE_PAGE_VERSION_CHANGED"
    ]
    assert len(stale) == 1
    assert stale[0].finding_type == "stale_trace"
    assert stale[0].affected_node_ids == [node.node_id]
    assert stale[0].evidence == [evidence]
    assert "version 3 to 4" in stale[0].description


def test_issue_affecting_critical_requirement_creates_critical_finding() -> None:
    req_evidence = EvidenceSpan(
        artifact_id="src_jira_CAM-REQ-001",
        source_url="https://jira.example.com/browse/CAM-REQ-001",
        quote_hash="hash_req_1",
        extracted_text_preview="Critical latency requirement.",
    )
    issue_evidence = EvidenceSpan(
        artifact_id="src_jira_CAM-ISS-060",
        source_url="https://jira.example.com/browse/CAM-ISS-060",
        quote_hash="hash_issue_1",
        extracted_text_preview="Latency spike affects CAM-REQ-001.",
    )
    requirement = OntologyNode(
        node_id="node_RUNE_CAM_ALPHA_CAM_REQ_001",
        node_type="Requirement",
        name="4K60 latency",
        description="Critical latency requirement.",
        project_key="RUNE_CAM_ALPHA",
        source_artifact_ids=["src_jira_CAM-REQ-001"],
        evidence=[req_evidence],
        created_by="source",
        confidence_score=0.95,
    )
    issue = OntologyNode(
        node_id="node_RUNE_CAM_ALPHA_CAM_ISS_060",
        node_type="Issue",
        name="Latency spike",
        description="Latency spike affects CAM-REQ-001.",
        project_key="RUNE_CAM_ALPHA",
        source_artifact_ids=["src_jira_CAM-ISS-060"],
        evidence=[issue_evidence],
        created_by="source",
        confidence_score=0.95,
    )
    edge = TraceabilityEdge(
        edge_id="edge_issue_affects_req",
        source_node_id=issue.node_id,
        target_node_id=requirement.node_id,
        relation="affects",
        reasoning="Issue source link affects critical requirement.",
        evidence=[issue_evidence],
        is_inferred=True,
        confidence_score=0.8,
    )
    req_raw = RawSourceArtifact(
        external_id="CAM-REQ-001",
        source_type="jira",
        source_url="https://jira.example.com/browse/CAM-REQ-001",
        project_key="RUNE_CAM_ALPHA",
        title="4K60 latency",
        body_text="Critical latency requirement.",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        metadata={"mbse_type": "Requirement", "priority": "P0"},
    )
    issue_raw = RawSourceArtifact(
        external_id="CAM-ISS-060",
        source_type="jira",
        source_url="https://jira.example.com/browse/CAM-ISS-060",
        project_key="RUNE_CAM_ALPHA",
        title="Latency spike",
        body_text="Latency spike affects CAM-REQ-001.",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        metadata={"mbse_type": "Issue", "relations": {"CAM-REQ-001": "affects"}},
    )

    findings = analyze_findings(
        [requirement, issue],
        [edge],
        source_artifacts=[req_raw, issue_raw],
        evidence_by_external_id={"CAM-REQ-001": req_evidence, "CAM-ISS-060": issue_evidence},
    )

    critical = [
        finding
        for finding in findings
        if finding.rule_id == "ISSUE_AFFECTS_CRITICAL_REQUIREMENT"
    ]
    assert len(critical) == 1
    assert critical[0].finding_type == "cross_domain_hidden"
    assert critical[0].severity == "critical"
    assert critical[0].affected_node_ids == [issue.node_id, requirement.node_id]
    assert critical[0].affected_edge_ids == [edge.edge_id]
    assert critical[0].evidence == [issue_evidence]


def test_architecture_without_verification_path_creates_finding() -> None:
    arch_evidence = EvidenceSpan(
        artifact_id="src_jira_CAM-ARCH-030",
        source_url="https://jira.example.com/browse/CAM-ARCH-030",
        quote_hash="hash_arch_30",
        extracted_text_preview="Architecture block satisfies CAM-REQ-030.",
    )
    req_evidence = EvidenceSpan(
        artifact_id="src_jira_CAM-REQ-030",
        source_url="https://jira.example.com/browse/CAM-REQ-030",
        quote_hash="hash_req_30",
        extracted_text_preview="Requirement has no verification coverage.",
    )
    architecture = OntologyNode(
        node_id="node_RUNE_CAM_ALPHA_CAM_ARCH_030",
        node_type="Architecture_Block",
        name="Unverified architecture block",
        description="Architecture block satisfies CAM-REQ-030.",
        project_key="RUNE_CAM_ALPHA",
        source_artifact_ids=["src_jira_CAM-ARCH-030"],
        evidence=[arch_evidence],
        created_by="source",
        confidence_score=0.95,
    )
    requirement = OntologyNode(
        node_id="node_RUNE_CAM_ALPHA_CAM_REQ_030",
        node_type="Requirement",
        name="Unverified requirement",
        description="Requirement has no verification coverage.",
        project_key="RUNE_CAM_ALPHA",
        source_artifact_ids=["src_jira_CAM-REQ-030"],
        evidence=[req_evidence],
        created_by="source",
        confidence_score=0.95,
    )
    satisfies_edge = TraceabilityEdge(
        edge_id="edge_arch_satisfies_req",
        source_node_id=architecture.node_id,
        target_node_id=requirement.node_id,
        relation="satisfies",
        reasoning="Architecture satisfies requirement.",
        evidence=[arch_evidence],
        is_inferred=False,
        confidence_score=0.9,
    )

    findings = analyze_findings([architecture, requirement], [satisfies_edge])

    architecture_gaps = [
        finding
        for finding in findings
        if finding.rule_id == "ARCHITECTURE_WITHOUT_VERIFICATION_PATH"
    ]
    assert len(architecture_gaps) == 1
    assert architecture_gaps[0].finding_type == "missing_verification"
    assert architecture_gaps[0].severity == "high"
    assert architecture_gaps[0].affected_node_ids == [architecture.node_id, requirement.node_id]
    assert architecture_gaps[0].affected_edge_ids == [satisfies_edge.edge_id]
    assert architecture_gaps[0].evidence == [arch_evidence]

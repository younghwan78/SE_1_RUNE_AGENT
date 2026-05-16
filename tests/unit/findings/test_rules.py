"""Finding rule tests."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.findings.rules import analyze_findings
from req_tracker.ontology.models import EvidenceSpan, OntologyNode


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

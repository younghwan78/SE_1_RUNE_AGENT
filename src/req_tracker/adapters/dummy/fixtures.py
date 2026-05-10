"""Deterministic dummy fixtures for local validation."""

from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.ontology.models import DataClassification, SourceType


def _raw(
    *,
    external_id: str,
    title: str,
    body_text: str,
    labels: list[str],
    links: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    data_classification: DataClassification = "public_internal",
    source_type: SourceType = "dummy",
    source_url_prefix: str = "dummy://jira",
) -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id=external_id,
        source_type=source_type,
        source_url=f"{source_url_prefix}/{external_id}",
        project_key="RUNE_CAM_ALPHA",
        title=title,
        body_text=body_text,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        labels=labels,
        links=links or [],
        metadata=metadata or {},
        access_scope=["project:RUNE_CAM_ALPHA"],
        data_classification=data_classification,
    )


def rune_cam_alpha() -> list[RawSourceArtifact]:
    """Return a compact camera traceability scenario."""
    return [
        _raw(
            external_id="CAM-REQ-001",
            title="4K60 latency shall be below 100 ms",
            body_text=(
                "Camera pipeline shall support 4K60 video capture with end-to-end latency "
                "below 100 ms for rearview use cases."
            ),
            labels=["requirement", "latency", "p0"],
            metadata={"mbse_type": "Requirement", "priority": "P0"},
        ),
        _raw(
            external_id="CAM-REQ-002",
            title="GDPR local-only face processing",
            body_text=(
                "Face detection and biometric processing must run on-device with no cloud "
                "upload."
            ),
            labels=["requirement", "privacy", "gdpr"],
            metadata={"mbse_type": "Requirement", "priority": "P0"},
        ),
        _raw(
            external_id="CAM-ARCH-010",
            title="ISP tile processing architecture",
            body_text=(
                "Architecture uses four tile processing threads to satisfy CAM-REQ-001 "
                "latency."
            ),
            labels=["architecture", "isp"],
            links=["CAM-REQ-001"],
            metadata={
                "mbse_type": "Architecture_Block",
                "relations": {"CAM-REQ-001": "satisfies"},
            },
        ),
        _raw(
            external_id="CAM-DES-020",
            title="HAL3 ring buffer scheduler",
            body_text="Design implements CAM-ARCH-010 with a 32-entry ring buffer scheduler.",
            labels=["design", "scheduler"],
            links=["CAM-ARCH-010"],
            metadata={
                "mbse_type": "Design_Spec",
                "relations": {"CAM-ARCH-010": "implements"},
            },
        ),
        _raw(
            external_id="CAM-DES-021",
            title="HAL3 lock-free queue scheduler alternative",
            body_text=(
                "Alternative design also implements CAM-ARCH-010 and conflicts with "
                "CAM-DES-020."
            ),
            labels=["design", "scheduler", "alternative"],
            links=["CAM-ARCH-010", "CAM-DES-020"],
            metadata={
                "mbse_type": "Design_Spec",
                "relations": {"CAM-ARCH-010": "implements", "CAM-DES-020": "conflicts_with"},
            },
        ),
        _raw(
            external_id="CAM-DES-022",
            title="ISP DVFS governor",
            body_text=(
                "DVFS design reduces power but introduces a 12-18 ms transition that may "
                "affect CAM-REQ-001 latency during scene transitions."
            ),
            labels=["design", "power", "dvfs"],
            links=["CAM-REQ-001"],
            metadata={"mbse_type": "Design_Spec", "relations": {"CAM-REQ-001": "affects"}},
        ),
        _raw(
            external_id="CAM-DES-028",
            title="3A unified AE/AWB/AF loop",
            body_text=(
                "Design for 3A control loop. No parent requirement or verification is linked."
            ),
            labels=["design", "3a"],
            metadata={"mbse_type": "Design_Spec"},
        ),
        _raw(
            external_id="CAM-VER-040",
            title="4K60 latency benchmark",
            body_text=(
                "Verification plan measures 4K60 end-to-end latency and verifies "
                "CAM-REQ-001."
            ),
            labels=["verification", "latency"],
            links=["CAM-REQ-001"],
            metadata={"mbse_type": "Verification", "relations": {"CAM-REQ-001": "verifies"}},
        ),
        _raw(
            external_id="CAM-ISS-060",
            title="Latency spike during AE convergence",
            body_text="Issue shows 120 ms latency spike and affects CAM-REQ-001.",
            labels=["issue", "latency"],
            links=["CAM-REQ-001"],
            metadata={"mbse_type": "Issue", "relations": {"CAM-REQ-001": "affects"}},
        ),
        _raw(
            external_id="CAM-SEC-001",
            title="Debug log leaked sensor serial",
            body_text="Log contains serial SN-IMX789-SECRET and contact owner@example.com.",
            labels=["security"],
            data_classification="restricted",
            metadata={"mbse_type": "Issue"},
        ),
    ]


def rune_multi_source() -> list[RawSourceArtifact]:
    """Return JIRA, Confluence, Email, and decision archive shaped artifacts."""
    return [
        *rune_cam_alpha(),
        _raw(
            external_id="CONF-CAM-100",
            title="Camera latency architecture decision",
            body_text=(
                "Confluence design page explains why CAM-ARCH-010 satisfies CAM-REQ-001 "
                "and references CAM-DES-020 implementation constraints."
            ),
            labels=["confluence", "architecture", "decision"],
            links=["CAM-ARCH-010", "CAM-REQ-001", "CAM-DES-020"],
            metadata={
                "mbse_type": "Decision",
                "relations": {"CAM-ARCH-010": "decides", "CAM-REQ-001": "satisfies"},
            },
            source_type="confluence",
            source_url_prefix="dummy://confluence/pages",
        ),
        _raw(
            external_id="CONF-CAM-101",
            title="Verification coverage note",
            body_text=(
                "Confluence verification note states CAM-VER-040 must cover CAM-REQ-001 "
                "and privacy requirement CAM-REQ-002 needs a separate test."
            ),
            labels=["confluence", "verification"],
            links=["CAM-VER-040", "CAM-REQ-001", "CAM-REQ-002"],
            metadata={
                "mbse_type": "Verification",
                "relations": {"CAM-REQ-001": "verifies", "CAM-REQ-002": "verifies"},
            },
            source_type="confluence",
            source_url_prefix="dummy://confluence/pages",
        ),
        _raw(
            external_id="MAIL-CAM-200",
            title="Decision mail for local-only biometric processing",
            body_text=(
                "Email decision confirms CAM-REQ-002 must block any cloud upload path "
                "and asks architecture owners to add an explicit design trace."
            ),
            labels=["email", "decision", "privacy"],
            links=["CAM-REQ-002"],
            metadata={"mbse_type": "Decision", "relations": {"CAM-REQ-002": "decides"}},
            source_type="email",
            source_url_prefix="dummy://email/archive",
            data_classification="restricted",
        ),
        _raw(
            external_id="DEC-CAM-300",
            title="Architecture review action record",
            body_text=(
                "Decision archive records that CAM-DES-022 affects CAM-REQ-001 and must "
                "be reviewed before release."
            ),
            labels=["decision_archive", "risk"],
            links=["CAM-DES-022", "CAM-REQ-001"],
            metadata={
                "mbse_type": "Risk",
                "relations": {"CAM-DES-022": "affects", "CAM-REQ-001": "affects"},
            },
            source_type="decision_archive",
            source_url_prefix="dummy://decision/archive",
        ),
    ]


def fixture_by_name(name: str) -> list[RawSourceArtifact]:
    """Return a named fixture scenario."""
    if name == "RUNE_SECURITY":
        return [item for item in rune_cam_alpha() if item.external_id == "CAM-SEC-001"]
    if name == "RUNE_MULTI_SOURCE":
        return rune_multi_source()
    if name in {"RUNE_CAM_ALPHA", "RUNE_CAM_BETA", "RUNE_NOISE"}:
        return rune_cam_alpha()
    raise ValueError(f"unknown dummy scenario: {name}")

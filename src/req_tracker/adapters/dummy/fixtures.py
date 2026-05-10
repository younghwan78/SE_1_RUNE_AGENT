"""Deterministic dummy fixtures for local validation."""

from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.ontology.models import DataClassification


def _raw(
    *,
    external_id: str,
    title: str,
    body_text: str,
    labels: list[str],
    links: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    data_classification: DataClassification = "public_internal",
) -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id=external_id,
        source_type="dummy",
        source_url=f"dummy://jira/{external_id}",
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


def fixture_by_name(name: str) -> list[RawSourceArtifact]:
    """Return a named fixture scenario."""
    if name == "RUNE_SECURITY":
        return [item for item in rune_cam_alpha() if item.external_id == "CAM-SEC-001"]
    if name in {"RUNE_CAM_ALPHA", "RUNE_CAM_BETA", "RUNE_NOISE"}:
        return rune_cam_alpha()
    raise ValueError(f"unknown dummy scenario: {name}")


"""Simple local masking rules."""

import re

from pydantic import BaseModel, ConfigDict


class MaskingResult(BaseModel):
    """Masked text and redaction metadata."""

    model_config = ConfigDict(extra="forbid")

    text: str
    redaction_count: int
    labels: list[str]


class MaskingPolicyViolationError(RuntimeError):
    """Raised when masking leaves policy-forbidden text in an artifact."""

    failure_code = "MASKING_POLICY_VIOLATION"

    def __init__(
        self,
        *,
        artifact_id: str,
        violation_labels: list[str],
        security_review_ref: str | None = None,
    ) -> None:
        self.artifact_id = artifact_id
        self.violation_labels = violation_labels
        self.security_review_ref = security_review_ref
        review_ref = f" ref={security_review_ref}" if security_review_ref else ""
        super().__init__(
            "MASKING_POLICY_VIOLATION: "
            f"{artifact_id} routed to security review{review_ref}; "
            f"violations={','.join(violation_labels)}"
        )


_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]", "email"),
    (r"SN-[A-Za-z0-9-]+", "[DEVICE_SERIAL]", "device_serial"),
    (r"(?i)(token|api_key|password)=\S+", r"\1=[SECRET]", "secret"),
)

_DEFAULT_FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "email"),
    (r"SN-[A-Za-z0-9-]+", "device_serial"),
    (r"(?i)(token|api_key|password)=(?!\[SECRET\])\S+", "secret"),
)


def mask_text(text: str) -> MaskingResult:
    """Mask common sensitive strings in local fixtures."""
    labels: list[str] = []
    redaction_count = 0
    masked = text
    for pattern, replacement, label in _PATTERNS:
        masked, count = re.subn(pattern, replacement, masked)
        if count:
            labels.append(label)
            redaction_count += count
    return MaskingResult(text=masked, redaction_count=redaction_count, labels=labels)


def find_masking_violations(
    masked_text: str,
    *,
    forbidden_patterns: object | None = None,
) -> list[str]:
    """Return policy labels that remain visible after masking."""
    violations: list[str] = []
    for pattern, label in _DEFAULT_FORBIDDEN_PATTERNS:
        if re.search(pattern, masked_text):
            violations.append(label)

    if isinstance(forbidden_patterns, list):
        for index, pattern in enumerate(forbidden_patterns):
            if not isinstance(pattern, str) or not pattern:
                violations.append(f"invalid_forbidden_pattern:{index}")
                continue
            try:
                matched = re.search(pattern, masked_text) is not None
            except re.error:
                violations.append(f"invalid_forbidden_pattern:{index}")
                continue
            if matched:
                violations.append(f"forbidden_pattern:{index}")

    return list(dict.fromkeys(violations))

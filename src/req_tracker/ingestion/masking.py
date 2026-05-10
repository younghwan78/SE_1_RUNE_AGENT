"""Simple local masking rules."""

import re

from pydantic import BaseModel, ConfigDict


class MaskingResult(BaseModel):
    """Masked text and redaction metadata."""

    model_config = ConfigDict(extra="forbid")

    text: str
    redaction_count: int
    labels: list[str]


_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]", "email"),
    (r"SN-[A-Za-z0-9-]+", "[DEVICE_SERIAL]", "device_serial"),
    (r"(?i)(token|api_key|password)=\S+", r"\1=[SECRET]", "secret"),
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


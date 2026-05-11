"""Trace-context helpers for OpenTelemetry-compatible request propagation."""

from dataclasses import dataclass
from secrets import token_hex
from string import hexdigits


@dataclass(frozen=True)
class TraceContext:
    """W3C trace context used for structured logs and response propagation."""

    trace_id: str
    span_id: str
    parent_span_id: str | None
    trace_flags: str

    @property
    def traceparent(self) -> str:
        """Return a W3C traceparent header for this server span."""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags}"


def resolve_trace_context(traceparent: str | None) -> TraceContext:
    """Resolve an incoming W3C traceparent header or create a new trace context."""
    parsed = _parse_traceparent(traceparent)
    if parsed is not None:
        trace_id, parent_span_id, trace_flags = parsed
        return TraceContext(
            trace_id=trace_id,
            span_id=_new_span_id(),
            parent_span_id=parent_span_id,
            trace_flags=trace_flags,
        )
    return TraceContext(
        trace_id=_new_trace_id(),
        span_id=_new_span_id(),
        parent_span_id=None,
        trace_flags="01",
    )


def _parse_traceparent(traceparent: str | None) -> tuple[str, str, str] | None:
    if not traceparent:
        return None
    parts = traceparent.strip().split("-")
    if len(parts) != 4:
        return None
    version, trace_id, span_id, trace_flags = parts
    if version != "00":
        return None
    if not _is_lower_hex(trace_id, 32) or set(trace_id) == {"0"}:
        return None
    if not _is_lower_hex(span_id, 16) or set(span_id) == {"0"}:
        return None
    if not _is_lower_hex(trace_flags, 2):
        return None
    return trace_id, span_id, trace_flags


def _is_lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(char in hexdigits.lower() for char in value)


def _new_trace_id() -> str:
    while True:
        trace_id = token_hex(16)
        if set(trace_id) != {"0"}:
            return trace_id


def _new_span_id() -> str:
    while True:
        span_id = token_hex(8)
        if set(span_id) != {"0"}:
            return span_id

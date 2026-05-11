"""Trace-context helper tests."""

from req_tracker.observability.tracing import resolve_trace_context


def test_resolve_trace_context_preserves_valid_incoming_trace_id() -> None:
    context = resolve_trace_context(
        "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    )

    assert context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert context.parent_span_id == "00f067aa0ba902b7"
    assert context.span_id != "00f067aa0ba902b7"
    assert len(context.span_id) == 16
    assert context.trace_flags == "01"
    assert context.traceparent.startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")


def test_resolve_trace_context_rejects_invalid_headers() -> None:
    context = resolve_trace_context(
        "00-00000000000000000000000000000000-0000000000000000-01"
    )

    assert len(context.trace_id) == 32
    assert set(context.trace_id) != {"0"}
    assert context.parent_span_id is None

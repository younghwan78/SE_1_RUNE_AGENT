"""Retry policy helpers for source adapters."""

from collections.abc import Callable
from typing import Any

from req_tracker.adapters.base import SourceAdapterRequestError

RetrySleep = Callable[[float], None]
SourceRequest = Callable[[], dict[str, Any]]
DEFAULT_BACKOFF_SECONDS = 0.25
MAX_BACKOFF_SECONDS = 2.0


def parse_retry_after(value: str | None) -> float | None:
    """Parse a numeric Retry-After header value."""
    if value is None:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None


def request_with_retry(
    *,
    source_type: str,
    request_call: SourceRequest,
    max_retries: int,
    retry_sleep: RetrySleep | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Run a source request with bounded retry and warning generation."""
    warnings: list[str] = []
    retry_count = 0
    while True:
        try:
            return request_call(), warnings
        except OSError as exc:
            request_error = SourceAdapterRequestError(
                f"{source_type} network request failed: {exc}",
                code="network_error",
            )
            if retry_count >= max_retries:
                warnings.append(
                    f"{source_type}_request_failed_after_retries:{request_error.status_label}"
                )
                return None, warnings
            retry_count += 1
            warnings.append(
                f"{source_type}_request_retry:{request_error.status_label}:attempt_{retry_count}"
            )
            _sleep_before_retry(
                retry_sleep=retry_sleep,
                retry_count=retry_count,
                retry_after_seconds=request_error.retry_after_seconds,
            )
        except SourceAdapterRequestError as exc:
            if exc.is_permission_denied:
                return None, [f"{source_type}_permission_denied:{exc.status_label}"]
            if not exc.is_retryable:
                return None, [f"{source_type}_request_failed:{exc.status_label}"]
            if retry_count >= max_retries:
                warnings.append(f"{source_type}_request_failed_after_retries:{exc.status_label}")
                return None, warnings
            retry_count += 1
            warnings.append(f"{source_type}_request_retry:{exc.status_label}:attempt_{retry_count}")
            _sleep_before_retry(
                retry_sleep=retry_sleep,
                retry_count=retry_count,
                retry_after_seconds=exc.retry_after_seconds,
            )


def _sleep_before_retry(
    *,
    retry_sleep: RetrySleep | None,
    retry_count: int,
    retry_after_seconds: float | None,
) -> None:
    if retry_sleep is None:
        return
    delay = retry_after_seconds
    if delay is None:
        delay = min(DEFAULT_BACKOFF_SECONDS * (2 ** max(retry_count - 1, 0)), MAX_BACKOFF_SECONDS)
    retry_sleep(delay)

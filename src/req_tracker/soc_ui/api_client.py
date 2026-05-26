"""FastAPI client used by the SoC Knowledge Streamlit UI."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from req_tracker.feedback.models import FeedbackAction, FeedbackEvent, FeedbackReasonCode
from req_tracker.ontology.soc_models import SocAnswer, SocQueryRequest


class SocUiApiError(RuntimeError):
    """Raised when the PoC UI cannot complete a backend API call."""


class SocUiTransport(Protocol):
    """Transport seam for tests and future UI adapters."""

    def __call__(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """Perform one API request and return the decoded JSON response."""


class SocKnowledgeApiClient:
    """Small client that keeps Streamlit behind the FastAPI contract."""

    def __init__(
        self,
        *,
        api_base_url: str,
        user_id: str,
        user_role: str = "developer",
        api_key: str = "",
        timeout_seconds: float = 30.0,
        transport: SocUiTransport | None = None,
    ) -> None:
        self._api_base_url = api_base_url.rstrip("/") + "/"
        self._user_id = user_id
        self._user_role = user_role
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._transport = transport or _urllib_transport(self._api_base_url)

    def query(
        self,
        *,
        user_query: str,
        session_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        current_project: str | None = None,
        query_id: str | None = None,
    ) -> SocAnswer:
        """Submit a natural-language SoC knowledge query to FastAPI."""
        request = SocQueryRequest(
            query_id=query_id or _new_ui_id("soc_ui_query"),
            user_query=user_query,
            user_id=self._user_id,
            session_id=session_id,
            current_project=current_project,
            conversation_history=conversation_history or [],
        )
        response = self._request(
            method="POST",
            path="/api/v1/soc/query",
            payload=request.model_dump(mode="json", exclude_none=True),
        )
        return SocAnswer.model_validate(response)

    def record_answer_feedback(
        self,
        *,
        answer: SocAnswer,
        action: FeedbackAction,
        reason_code: FeedbackReasonCode,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Record feedback for a structured SoC answer."""
        event = FeedbackEvent(
            feedback_id=_new_ui_id("fb_soc_ui"),
            target_type="answer",
            target_id=answer.query_id,
            action=action,
            user_id=self._user_id,
            user_role=self._user_role,
            reason_code=reason_code,
            correction_text=comment,
        )
        return self._request(
            method="POST",
            path="/api/v1/feedback",
            payload=event.model_dump(mode="json", exclude_none=True),
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return self._transport(
                method=method,
                path=path,
                payload=payload,
                headers=self._headers(),
                timeout_seconds=self._timeout_seconds,
            )
        except SocUiApiError:
            raise
        except Exception as exc:
            raise SocUiApiError(str(exc)) from exc

    def _headers(self) -> dict[str, str]:
        headers = {
            "content-type": "application/json",
            "x-rune-user": self._user_id,
            "x-rune-role": self._user_role,
        }
        if self._api_key:
            headers["x-rune-api-key"] = self._api_key
        return headers


def _urllib_transport(api_base_url: str) -> SocUiTransport:
    def send(
        *,
        method: str,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            urljoin(api_base_url, path.lstrip("/")),
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SocUiApiError(f"API returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise SocUiApiError(f"API request failed: {exc.reason}") from exc
        if not response_body:
            return {}
        decoded = json.loads(response_body)
        if not isinstance(decoded, dict):
            raise SocUiApiError("API response must be a JSON object")
        return decoded

    return send


def _new_ui_id(prefix: str, new_uuid: Callable[[], uuid.UUID] = uuid.uuid4) -> str:
    return f"{prefix}_{new_uuid().hex[:12]}"

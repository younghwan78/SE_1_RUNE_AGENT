"""Optional model-gateway-backed SoC query slice planning."""

from collections.abc import Callable
from typing import Protocol

from req_tracker.debug.hash import stable_hash
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import ModelRequest
from req_tracker.ontology.soc_models import SOC_SCHEMA_VERSION, SocSlice

SocSliceFallback = Callable[[str], SocSlice]


class SocSlicePlanner(Protocol):
    """Plan a typed SoC slice from user query context."""

    def plan(
        self,
        *,
        user_query: str,
        user_id: str,
        session_id: str,
        current_project: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        run_id: str | None = None,
        step_id: str = "soc_slice_planning",
    ) -> SocSlice:
        """Return a schema-valid query slice."""


class GatewaySocSlicePlanner:
    """Use the model gateway for slice planning with deterministic fallback."""

    def __init__(
        self,
        *,
        client: ModelGatewayClient,
        model_profile_id: str,
        prompt_version_id: str,
        fallback_classifier: SocSliceFallback | None = None,
    ) -> None:
        self._client = client
        self._model_profile_id = model_profile_id
        self._prompt_version_id = prompt_version_id
        self._fallback_classifier = fallback_classifier or _deterministic_fallback

    def plan(
        self,
        *,
        user_query: str,
        user_id: str,
        session_id: str,
        current_project: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        run_id: str | None = None,
        step_id: str = "soc_slice_planning",
    ) -> SocSlice:
        """Return a gateway-planned slice, falling back to rules on any failure."""
        request = ModelRequest(
            model_profile_id=self._model_profile_id,
            prompt_version_id=self._prompt_version_id,
            payload=_planning_payload(
                user_query=user_query,
                user_id=user_id,
                session_id=session_id,
                current_project=current_project,
                conversation_history=conversation_history or [],
            ),
            data_classification="public_internal",
        )
        try:
            _response, parsed, validation = self._client.complete(
                run_id=run_id or f"soc_query_plan_{stable_hash(request.payload)[:12]}",
                step_id=step_id,
                request=request,
                response_model=SocSlice,
            )
        except Exception:
            return self._fallback_classifier(user_query)
        if parsed is None or validation.status == "failed":
            return self._fallback_classifier(user_query)
        return parsed


def _planning_payload(
    *,
    user_query: str,
    user_id: str,
    session_id: str,
    current_project: str | None,
    conversation_history: list[dict[str, str]],
) -> dict[str, object]:
    return {
        "task": "soc_slice_planning",
        "schema_version": SOC_SCHEMA_VERSION,
        "user_query": user_query,
        "user_id": user_id,
        "session_id": session_id,
        "current_project": current_project,
        "conversation_history": conversation_history,
        "allowed_patterns": [
            "concern_slice",
            "topic_intersection",
            "timeline_slice",
            "lifecycle_trace",
            "unknown",
        ],
        "allowed_axes": ["project", "v_level", "concern", "component"],
        "output_contract": "Return exactly one SocSlice JSON object. Do not emit SQL or Cypher.",
    }


def _deterministic_fallback(user_query: str) -> SocSlice:
    from req_tracker.query.soc_service import classify_soc_slice

    return classify_soc_slice(user_query)

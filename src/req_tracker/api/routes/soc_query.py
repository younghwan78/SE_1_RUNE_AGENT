"""SoC Knowledge query APIs."""

from typing import Any

from fastapi import APIRouter, Request

from req_tracker.api.security import require_role
from req_tracker.ontology.soc_models import SocQueryRequest
from req_tracker.query.soc_service import answer_soc_query

router = APIRouter(tags=["soc-query"])


@router.post("/soc/query")
def soc_query(request: Request, payload: SocQueryRequest) -> dict[str, Any]:
    """Return a structured fixture-backed SoC knowledge answer."""
    require_role(request, "viewer")
    answer = answer_soc_query(
        query_id=payload.query_id,
        user_query=payload.user_query,
        user_id=payload.user_id,
        session_id=payload.session_id,
        query_slice=payload.slice,
        current_project=payload.current_project,
        conversation_history=payload.conversation_history,
        slice_planner=request.app.state.runtime.soc_slice_planner,
        tool_planner=request.app.state.runtime.soc_query_tool_planner,
        reranker=request.app.state.runtime.soc_reranker,
        retrieval_backend=request.app.state.runtime.soc_retrieval_backend,
        answer_assembler=request.app.state.runtime.soc_answer_assembler,
        artifact_store=request.app.state.runtime.artifact_store,
        trace_repo=request.app.state.runtime.traces,
    )
    return answer.model_dump(mode="json")

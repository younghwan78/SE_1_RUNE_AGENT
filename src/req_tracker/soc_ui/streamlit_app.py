"""Streamlit entrypoint for the SoC Knowledge PoC UI."""

from __future__ import annotations

import os
import uuid
from importlib import import_module
from typing import Any

from req_tracker.ontology.soc_models import SocAnswer
from req_tracker.soc_ui.api_client import SocKnowledgeApiClient, SocUiApiError
from req_tracker.soc_ui.render_answer import SocAnswerView, build_answer_view

DEFAULT_API_BASE_URL = "http://127.0.0.1:18000"
DEFAULT_TIMEOUT_SECONDS = 30.0


def main() -> None:
    """Run the Streamlit app."""
    st = import_module("streamlit")

    st.set_page_config(page_title="SoC Knowledge", layout="wide")
    _ensure_session_state(st.session_state)

    with st.sidebar:
        st.title("SoC Knowledge")
        user_id = st.text_input("User", value=_default_user_id())
        user_role = st.selectbox("Role", ["developer", "viewer", "operator", "admin"], index=0)
        current_project = st.text_input("Project", value=os.getenv("SOC_UI_DEFAULT_PROJECT", ""))
        show_reasoning = st.toggle("Reasoning log", value=False)

    client = SocKnowledgeApiClient(
        api_base_url=os.getenv("SOC_UI_API_BASE_URL", DEFAULT_API_BASE_URL),
        user_id=user_id,
        user_role=user_role,
        api_key=os.getenv("RUNE_API_KEY", ""),
        timeout_seconds=float(os.getenv("SOC_UI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )

    st.header("SoC Knowledge")
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            answer = message.get("answer")
            if isinstance(answer, SocAnswer):
                _render_answer(st, build_answer_view(answer), show_reasoning=show_reasoning)
                _render_feedback(st, client=client, answer=answer)

    user_query = st.chat_input("Ask about project, V-level, concern, component, or lifecycle")
    if not user_query:
        return

    st.session_state["messages"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Searching"):
            try:
                answer = client.query(
                    user_query=user_query,
                    session_id=st.session_state["session_id"],
                    current_project=current_project or None,
                    conversation_history=_conversation_history(st.session_state["messages"]),
                )
            except SocUiApiError as exc:
                message = f"Query failed: {exc}"
                st.error(message)
                st.session_state["messages"].append({"role": "assistant", "content": message})
                return
        view = build_answer_view(answer)
        st.markdown(view.summary)
        _render_answer(st, view, show_reasoning=show_reasoning)
        _render_feedback(st, client=client, answer=answer)
        st.session_state["messages"].append(
            {"role": "assistant", "content": view.summary, "answer": answer}
        )


def _ensure_session_state(session_state: Any) -> None:
    if "session_id" not in session_state:
        session_state["session_id"] = f"soc_ui_session_{uuid.uuid4().hex[:12]}"
    if "messages" not in session_state:
        session_state["messages"] = []


def _conversation_history(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for message in messages[-8:]:
        role = str(message.get("role", ""))
        content = str(message.get("content", ""))
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


def _render_answer(st: Any, view: SocAnswerView, *, show_reasoning: bool) -> None:
    st.caption(f"Confidence: {view.confidence}")
    if view.quality_signals:
        st.caption("Signals: " + ", ".join(view.quality_signals))
    for item in view.items:
        with st.container(border=True):
            st.subheader(item.title)
            st.write(item.summary)
            tags = [tag for tag in [item.level, *item.concerns, *item.components] if tag]
            if tags:
                st.caption(" / ".join(tags))
            for source in item.source_links:
                st.link_button(source["label"], source["url"])
    with st.expander("Timeline", expanded=False):
        if not view.timeline:
            st.caption("No lifecycle events returned.")
        for event in view.timeline:
            if event.source_url:
                st.markdown(f"- `{event.timestamp}` [{event.label}]({event.source_url})")
            else:
                st.markdown(f"- `{event.timestamp}` {event.label}")
    if show_reasoning:
        st.code(view.reasoning_log_ref)


def _render_feedback(st: Any, *, client: SocKnowledgeApiClient, answer: SocAnswer) -> None:
    with st.form(f"feedback_{answer.query_id}", clear_on_submit=True):
        action = st.radio(
            "Feedback",
            ["approved", "marked_low_quality", "commented"],
            horizontal=True,
        )
        reason_code = st.selectbox(
            "Reason",
            [
                "weak_evidence",
                "missing_context",
                "wrong_relation",
                "wrong_node_type",
                "duplicate",
                "wrong_severity",
                "security_concern",
                "other",
            ],
        )
        comment = st.text_area("Comment", value="")
        submitted = st.form_submit_button("Submit feedback")
    if not submitted:
        return
    try:
        client.record_answer_feedback(
            answer=answer,
            action=action,
            reason_code=reason_code,
            comment=comment or None,
        )
    except SocUiApiError as exc:
        st.error(f"Feedback failed: {exc}")
        return
    st.success("Feedback recorded.")


def _default_user_id() -> str:
    return os.getenv("SOC_UI_USER_ID") or os.getenv("USER") or "architect_01"


if __name__ == "__main__":
    main()

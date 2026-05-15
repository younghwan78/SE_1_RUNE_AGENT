import { api, badge, el, emptyRow, escapeHtml, state, text } from "./core.js";

export const renderDebugSummary = async () => {
  const list = el("debug-steps");
  list.replaceChildren();
  if (!state.currentRunId) {
    text("debug-label", "no run");
    text("debug-counts", "0 artifacts");
    el("debug-detail").textContent = "[]";
    renderDebugDiffView(null);
    list.append(emptyRow("Run an analysis to inspect debug traces"));
    return;
  }
  const [summary, diffView] = await Promise.all([
    api(`/debug/runs/${state.currentRunId}/summary`),
    api(`/debug/runs/${state.currentRunId}/diff-view`),
  ]);
  text("debug-label", state.currentRunId);
  text(
    "debug-counts",
    `${summary.counts.artifact_refs} artifacts / ${summary.counts.graph_deltas} deltas`,
  );
  if (!summary.steps.length) {
    list.append(emptyRow("No debug steps"));
  }
  summary.steps.forEach((step) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(step.stage_name)}</span>${badge(escapeHtml(step.status), step.status !== "succeeded")}
      </div>
      <div class="item-meta">
        ${escapeHtml(step.step_id)}<br>
        input=${escapeHtml(step.input_hash)}<br>
        output=${escapeHtml(step.output_hash || "none")}<br>
        artifact=${escapeHtml(step.output_ref || "none")}<br>
        retrieval=${escapeHtml(step.retrieval_context_ref || "none")}<br>
        validation=${escapeHtml(step.validation_status || "not_applicable")}
      </div>
    `;
    item.addEventListener("click", () => {
      el("debug-detail").textContent = JSON.stringify(step, null, 2);
    });
    list.append(item);
  });
  el("debug-detail").textContent = JSON.stringify(
    {
      run: summary.run,
      counts: summary.counts,
      graph_deltas: summary.graph_deltas,
      llm_calls: summary.llm_calls,
      artifact_refs: summary.artifact_refs,
    },
    null,
    2,
  );
  renderDebugDiffView(diffView);
};

const setJsonPane = (id, value) => {
  el(id).textContent = JSON.stringify(value, null, 2);
};

export const renderDebugDiffView = (diffView) => {
  if (!diffView) {
    text("llm-diff-count", "0 calls");
    text("graph-delta-count", "0 deltas");
    setJsonPane("llm-diff-left", []);
    setJsonPane("llm-diff-right", []);
    setJsonPane("graph-delta-left", []);
    setJsonPane("graph-delta-right", []);
    return;
  }
  text("llm-diff-count", `${diffView.counts.llm_payload_pairs} calls`);
  text("graph-delta-count", `${diffView.counts.graph_delta_previews} deltas`);
  const llmPair = diffView.llm_payload_pairs[0];
  if (llmPair) {
    setJsonPane("llm-diff-left", {
      label: llmPair.left.label,
      artifact_ref: llmPair.left.artifact_ref,
      payload: llmPair.left.payload,
    });
    setJsonPane("llm-diff-right", {
      label: llmPair.right.label,
      artifact_ref: llmPair.right.artifact_ref,
      validation_status: llmPair.validation_status,
      payload: llmPair.right.payload,
      parsed: llmPair.parsed,
    });
  } else {
    setJsonPane("llm-diff-left", []);
    setJsonPane("llm-diff-right", []);
  }
  const delta = diffView.graph_delta_previews[0];
  if (delta) {
    setJsonPane("graph-delta-left", delta.left);
    setJsonPane("graph-delta-right", delta.right);
  } else {
    setJsonPane("graph-delta-left", []);
    setJsonPane("graph-delta-right", []);
  }
};

export const renderAuditEvents = (events) => {
  const list = el("audit-events");
  list.replaceChildren();
  text("audit-count", `${events.length} events`);
  if (!events.length) {
    list.append(emptyRow("No audit events"));
    return;
  }
  events.forEach((event) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(event.action)}</span>${badge(escapeHtml(event.outcome), event.outcome !== "succeeded")}
      </div>
      <div class="item-meta">
        ${escapeHtml(event.audit_id)}<br>
        actor=${escapeHtml(event.actor_id)}${event.actor_role ? ` / ${escapeHtml(event.actor_role)}` : ""}<br>
        target=${escapeHtml(event.target_type)}:${escapeHtml(event.target_id)}<br>
        ${event.reason_code ? `reason=${escapeHtml(event.reason_code)}<br>` : ""}
        ${escapeHtml(event.created_at)}
      </div>
    `;
    list.append(item);
  });
};

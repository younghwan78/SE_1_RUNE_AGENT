import {
  badge,
  el,
  emptyRow,
  escapeHtml,
  healthWarning,
  navigateTo,
  requestRefresh,
  state,
  text,
} from "./core.js";

export const renderSourceHealth = (payload) => {
  state.latestSourceHealth = payload;
  const list = el("source-health");
  const sources = payload.sources || [];
  list.replaceChildren();
  const warningCount = sources.filter((item) => healthWarning(item.status)).length;
  text("source-health-label", warningCount ? `${warningCount} warning` : `${sources.length} sources`);
  if (!sources.length) {
    list.append(emptyRow("No source health evidence"));
    renderSourceHealthFull(payload);
    return;
  }
  sources.forEach((source) => {
    const row = document.createElement("li");
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(source.source_type)}</span>${badge(escapeHtml(source.status), healthWarning(source.status))}
      </div>
      <div class="item-meta">
        artifacts=${source.artifact_count || 0} warnings=${source.warning_count || 0}<br>
        ${escapeHtml(source.cursor_id || "no cursor")}<br>
        ${escapeHtml(source.last_run_id || "no run")}
      </div>
    `;
    row.addEventListener("click", () => navigateTo("source-health", { source: source.source_type }));
    list.append(row);
  });
  renderSourceHealthFull(payload);
};

export const renderRunHealth = (payload) => {
  state.latestRunHealth = payload;
  const list = el("run-health");
  const runs = payload.recent_runs || [];
  list.replaceChildren();
  text("run-health-label", `${payload.total_runs || 0} runs`);
  if (!runs.length) {
    list.append(emptyRow("No run history"));
    renderRunHealthFull(payload);
    return;
  }
  runs.slice(0, 6).forEach((run) => {
    const row = document.createElement("li");
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(run.run_id)}</span>${badge(escapeHtml(run.status), run.status !== "succeeded")}
      </div>
      <div class="item-meta">${escapeHtml(run.run_type)}<br>${escapeHtml(run.completed_at || "not completed")}</div>
    `;
    row.addEventListener("click", () => {
      state.currentRunId = run.run_id;
      navigateTo("debug", { run: run.run_id });
      requestRefresh().catch(console.error);
    });
    list.append(row);
  });
  renderRunHealthFull(payload);
};

export const renderSourceHealthFull = (payload) => {
  const list = el("source-health-full");
  if (!list) return;
  const sources = payload.sources || [];
  list.replaceChildren();
  const warningCount = sources.filter((item) => healthWarning(item.status)).length;
  text("source-health-full-label", warningCount ? `${warningCount} warning` : `${sources.length} sources`);
  if (!sources.length) {
    list.append(emptyRow("No source health evidence"));
    return;
  }
  sources.forEach((source) => {
    const row = document.createElement("li");
    const warnings = source.source_warnings?.length
      ? source.source_warnings.map((warning) => escapeHtml(warning)).join("<br>")
      : "no source warnings";
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(source.source_type)}</span>${badge(escapeHtml(source.status), healthWarning(source.status))}
      </div>
      <div class="item-meta">
        mode=${escapeHtml(source.mode || "not configured")}<br>
        cursor=${escapeHtml(source.cursor_id || "none")}<br>
        last_run=${escapeHtml(source.last_run_id || "none")}<br>
        artifacts=${source.artifact_count || 0} warnings=${source.warning_count || 0}<br>
        last_success=${escapeHtml(source.last_success_at || "none")} stale_after=${source.stale_after_seconds}s<br>
        ${warnings}
      </div>
    `;
    list.append(row);
  });
};

export const renderRunHealthFull = (payload) => {
  const list = el("run-health-full");
  if (!list) return;
  const runs = payload.recent_runs || [];
  list.replaceChildren();
  text("run-health-full-label", `${payload.total_runs || 0} runs / ${payload.failed_runs || 0} failed`);
  if (!runs.length) {
    list.append(emptyRow("No run history"));
    return;
  }
  runs.forEach((run) => {
    const row = document.createElement("li");
    row.className = "queue-row";
    row.classList.toggle("active", state.currentRunId === run.run_id);
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(run.run_id)}</span>${badge(escapeHtml(run.status), run.status !== "succeeded")}
      </div>
      <div class="item-meta">
        type=${escapeHtml(run.run_type)}<br>
        completed=${escapeHtml(run.completed_at || "not completed")}<br>
        failure=${escapeHtml(run.failure_code || run.failure_message || "none")}
      </div>
    `;
    row.addEventListener("click", () => {
      state.currentRunId = run.run_id;
      navigateTo("debug", { run: run.run_id });
      requestRefresh().catch(console.error);
    });
    list.append(row);
  });
};

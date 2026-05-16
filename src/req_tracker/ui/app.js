import {
  api,
  applyHashRoute,
  badge,
  el,
  emptyRow,
  escapeHtml,
  navigateTo,
  safeApi,
  setRefreshHandler,
  state,
  text,
} from "./core.js";
import { renderDashboard } from "./dashboard.js";
import { renderAuditEvents, renderDebugSummary } from "./debug_workbench.js";
import {
  initGraphWorkbench,
  renderEdges,
  renderNodes,
  renderOntologyGraph,
} from "./graph_workbench.js";
import {
  handleQueueAction,
  hydrateWorkQueueBackendState,
  initWorkQueueControls,
  setWorkQueueDecisionHandler,
} from "./work_queue.js";
import {} from "./source_health.js";

const renderFindings = (findings) => {
  const list = el("findings");
  list.replaceChildren();
  if (!findings.length) {
    list.append(emptyRow("No findings"));
    return;
  }
  findings.forEach((finding) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(finding.finding_type)}</span>${badge(escapeHtml(finding.severity), true)}
      </div>
      <div class="item-meta">${escapeHtml(finding.description)}<br>${escapeHtml(finding.suggested_action)}</div>
    `;
    list.append(item);
  });
};

const renderApprovals = (approvals) => {
  const list = el("approvals");
  list.replaceChildren();
  const pending = approvals.filter((approval) => approval.status === "pending");
  text("approval-count", `${pending.length} pending`);
  if (!approvals.length) {
    list.append(emptyRow("No approval items"));
    return;
  }
  approvals.forEach((approval) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(approval.proposal_type)}</span>${badge(escapeHtml(approval.status))}
      </div>
      <div class="item-meta">
        ${escapeHtml(approval.approval_id)}<br>
        risk=${escapeHtml(approval.risk_level)} owner=${escapeHtml(approval.owner_role)}
      </div>
      <div class="review-actions">
        <button data-action="approve" data-id="${escapeHtml(approval.approval_id)}">Approve</button>
        <button data-action="reject" data-id="${escapeHtml(approval.approval_id)}">Reject</button>
      </div>
    `;
    list.append(item);
  });
};

const renderEvalCandidates = (candidates) => {
  const list = el("eval-candidates");
  list.replaceChildren();
  text("eval-count", `${candidates.length} groups`);
  if (!candidates.length) {
    list.append(emptyRow("No eval candidates"));
    return;
  }
  candidates.forEach((candidate) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(candidate.reason_code)}</span>${badge(escapeHtml(candidate.dataset_path))}
      </div>
      <div class="item-meta">${candidate.feedback_ids.length} feedback events</div>
    `;
    list.append(item);
  });
};

const renderImprovements = (improvements) => {
  const list = el("improvements");
  list.replaceChildren();
  text("improvement-count", `${improvements.length} draft`);
  if (!improvements.length) {
    list.append(emptyRow("No improvement candidates"));
    return;
  }
  improvements.forEach((candidate) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(candidate.candidate_type)}</span>${badge(escapeHtml(candidate.status), true)}
      </div>
      <div class="item-meta">
        ${escapeHtml(candidate.candidate_id)}<br>
        ${escapeHtml(candidate.proposed_change_summary)}
      </div>
    `;
    list.append(item);
  });
};

const renderSchedule = (schedule) => {
  text("schedule-label", schedule.running ? "running" : "disabled");
  text("schedule-run-label", schedule.last_run_id || "no run");
  el("schedule-interval").value = schedule.interval_seconds;
  el("schedule-project").value = schedule.project_key;
  el("schedule-scenario").value = schedule.scenario;
  el("schedule-enabled").checked = schedule.enabled;
  el("schedule-status").textContent = JSON.stringify(schedule, null, 2);
};

const refresh = async () => {
  const query = new URLSearchParams({
    mode: state.graphMode,
    edge_filter: state.edgeFilter,
    limit_nodes: "120",
    hops: String(state.hops),
  });
  if (state.searchQuery) {
    query.set("search_query", state.searchQuery);
  }
  if (
    state.selectedNodeId &&
    (state.graphMode === "neighborhood" || state.edgeFilter === "incoming" || state.edgeFilter === "outgoing")
  ) {
    query.set("center_node_id", state.selectedNodeId);
  }
  const [
    projection,
    approvals,
    findings,
    evalCandidates,
    feedbackSummary,
    improvements,
    gate,
    schedule,
    auditEvents,
    dashboardSummary,
    dashboardWorkQueue,
    sourceHealth,
    runHealth,
    riskSummary,
    recentActivity,
    workQueuePreferences,
    workQueueAssignments,
  ] = await Promise.all([
    api(`/graph/projection?${query.toString()}`),
    api("/approvals"),
    api("/findings"),
    api("/eval/candidates"),
    api("/feedback/summary"),
    api("/improvements/candidates"),
    api("/eval/gate"),
    api("/schedule"),
    api("/audit/events?limit=20"),
    safeApi("/dashboard/summary", {
      project_key: "RUNE_CAM_ALPHA",
      traceability_health: "unknown",
      counts: {},
      source_freshness: {},
      eval_gate: { status: "unknown" },
      schedule: {},
    }),
    safeApi("/dashboard/work-queue?limit=200", { items: [], counts: {} }),
    safeApi("/dashboard/source-health", { sources: [] }),
    safeApi("/dashboard/run-health", { recent_runs: [], total_runs: 0, failed_runs: 0 }),
    safeApi("/dashboard/risk-summary", { risk_by_severity: {}, top_findings: [] }),
    safeApi("/dashboard/recent-activity?limit=20", { items: [] }),
    safeApi("/dashboard/work-queue/preferences", { saved_filters: {} }),
    safeApi("/dashboard/work-queue/assignments", { assignments: [] }),
  ]);
  void feedbackSummary;
  state.graphProjection = projection;
  hydrateWorkQueueBackendState(workQueuePreferences, workQueueAssignments);
  renderDashboard({
    summary: dashboardSummary,
    workQueue: dashboardWorkQueue,
    sourceHealth,
    runHealth,
    riskSummary,
    recentActivity,
    projection,
  });
  renderNodes(projection.nodes);
  renderEdges(projection.edges);
  renderOntologyGraph(projection);
  renderApprovals(approvals);
  renderFindings(findings);
  renderEvalCandidates(evalCandidates);
  renderImprovements(improvements);
  renderAuditEvents(auditEvents);
  text("gate-label", gate.eval_run_id);
  el("eval-gate").textContent = JSON.stringify(gate, null, 2);
  renderSchedule(schedule);
  text("finding-count", `${findings.length} open`);
  text(
    "graph-run-label",
    `${projection.mode} | visible ${projection.counts.visible_nodes} | orphan ${projection.counts.orphan_nodes} | pending ${projection.counts.pending_edges}`,
  );
  el("run-replay").disabled = !state.currentRunId;
  await renderDebugSummary();
};

const runAnalysis = async () => {
  text("status-line", "analysis running");
  const result = await api("/runs/analyze", { method: "POST", body: JSON.stringify({}) });
  state.currentRunId = result.run.run_id;
  state.runs.push(result.run.run_id);
  text("status-line", `analysis complete: ${result.run.run_id}`);
  await refresh();
};

const decideApproval = async (approvalId, action) => {
  const reason = action === "reject" ? "wrong_relation" : null;
  await api(`/approvals/${approvalId}/decision`, {
    method: "POST",
    body: JSON.stringify({
      approval_id: approvalId,
      action,
      decided_by: "local_reviewer",
      reason_code: reason,
    }),
  });
  await refresh();
};

const runReplay = async () => {
  if (!state.currentRunId) return;
  text("replay-label", "running");
  const result = await api(`/runs/${state.currentRunId}/replay`, {
    method: "POST",
    body: JSON.stringify({ replay_mode: "same_model_same_prompt" }),
  });
  text("replay-label", result.replay_run_id);
  el("replay-diff").textContent = JSON.stringify(result.diff, null, 2);
  await refresh();
};

const applySchedule = async () => {
  const payload = {
    enabled: el("schedule-enabled").checked,
    interval_seconds: Number(el("schedule-interval").value || 3600),
    project_key: el("schedule-project").value || "RUNE_CAM_ALPHA",
    scenario: el("schedule-scenario").value || "RUNE_MULTI_SOURCE",
    run_id_prefix: "sched",
  };
  await api("/schedule", { method: "PUT", body: JSON.stringify(payload) });
  await refresh();
};

const runScheduleNow = async () => {
  const result = await api("/schedule/run-now", { method: "POST", body: JSON.stringify({}) });
  state.currentRunId = result.run_id;
  state.runs.push(result.run_id);
  text("status-line", `scheduled run complete: ${result.run_id}`);
  navigateTo("debug", { run: result.run_id });
  await refresh();
};

const initWorkspace = () => {
  setRefreshHandler(refresh);
  setWorkQueueDecisionHandler(decideApproval);
  applyHashRoute();
  initWorkQueueControls();
  el("run-analysis").addEventListener("click", () => runAnalysis().catch(console.error));
  el("refresh").addEventListener("click", () => refresh().catch(console.error));
  el("run-replay").addEventListener("click", () => runReplay().catch(console.error));
  el("dashboard-open-workbench").addEventListener("click", () => navigateTo("traceability"));
  el("dashboard-open-debug").addEventListener("click", () => navigateTo("debug"));
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => navigateTo(button.dataset.viewTarget));
  });
  window.addEventListener("hashchange", () => {
    const route = applyHashRoute();
    if (route.params.run || route.params.node || route.params.mode || route.params.layout || route.params.item) {
      refresh().catch(console.error);
    }
  });
  el("approvals").addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) return;
    decideApproval(target.dataset.id, target.dataset.action).catch(console.error);
  });
  el("work-queue-detail").addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) return;
    handleQueueAction(target.dataset.queueAction).catch(console.error);
  });
  el("schedule-form").addEventListener("submit", (event) => {
    event.preventDefault();
    applySchedule().catch(console.error);
  });
  el("schedule-run-now").addEventListener("click", () => runScheduleNow().catch(console.error));
  initGraphWorkbench();
  refresh().catch(console.error);
};

initWorkspace();

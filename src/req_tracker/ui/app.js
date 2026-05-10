const state = {
  runs: [],
  currentRunId: null,
};

const api = async (path, options = {}) => {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
};

const el = (id) => document.getElementById(id);

const text = (id, value) => {
  el(id).textContent = String(value);
};

const emptyRow = (label) => {
  const item = document.createElement("li");
  item.className = "item-meta";
  item.textContent = label;
  return item;
};

const badge = (value, warning = false) =>
  `<span class="badge${warning ? " warning" : ""}">${value}</span>`;

const renderNodes = (nodes) => {
  const list = el("nodes");
  list.replaceChildren();
  if (!nodes.length) {
    list.append(emptyRow("No nodes"));
    return;
  }
  nodes.forEach((node) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title"><span>${node.name}</span>${badge(node.node_type)}</div>
      <div class="item-meta">${node.node_id}<br>${node.description}</div>
    `;
    list.append(item);
  });
};

const renderEdges = (edges) => {
  const list = el("edges");
  list.replaceChildren();
  if (!edges.length) {
    list.append(emptyRow("No approved edges"));
    return;
  }
  edges.forEach((edge) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title"><span>${edge.relation}</span>${badge(edge.approval_status)}</div>
      <div class="item-meta">${edge.source_node_id}<br>${edge.target_node_id}</div>
    `;
    list.append(item);
  });
};

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
        <span>${finding.finding_type}</span>${badge(finding.severity, true)}
      </div>
      <div class="item-meta">${finding.description}<br>${finding.suggested_action}</div>
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
        <span>${approval.proposal_type}</span>${badge(approval.status)}
      </div>
      <div class="item-meta">
        ${approval.approval_id}<br>
        risk=${approval.risk_level} owner=${approval.owner_role}
      </div>
      <div class="review-actions">
        <button data-action="approve" data-id="${approval.approval_id}">Approve</button>
        <button data-action="reject" data-id="${approval.approval_id}">Reject</button>
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
        <span>${candidate.reason_code}</span>${badge(candidate.dataset_path)}
      </div>
      <div class="item-meta">${candidate.feedback_ids.length} feedback events</div>
    `;
    list.append(item);
  });
};

const refresh = async () => {
  const [graph, approvals, findings, evalCandidates, feedbackSummary] = await Promise.all([
    api("/graph/subgraph"),
    api("/approvals"),
    api("/findings"),
    api("/eval/candidates"),
    api("/feedback/summary"),
  ]);
  renderNodes(graph.nodes);
  renderEdges(graph.edges);
  renderApprovals(approvals);
  renderFindings(findings);
  renderEvalCandidates(evalCandidates);
  text("metric-runs", state.runs.length);
  text("metric-nodes", graph.nodes.length);
  text("metric-edges", graph.edges.length);
  text("metric-approvals", approvals.length);
  text("metric-findings", findings.length);
  text(
    "metric-feedback",
    Object.values(feedbackSummary).reduce((sum, count) => sum + count, 0),
  );
  text("finding-count", `${findings.length} open`);
  text("graph-run-label", state.currentRunId || "no run");
  el("run-replay").disabled = !state.currentRunId;
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

el("run-analysis").addEventListener("click", () => runAnalysis().catch(console.error));
el("refresh").addEventListener("click", () => refresh().catch(console.error));
el("run-replay").addEventListener("click", () => runReplay().catch(console.error));
el("approvals").addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  decideApproval(target.dataset.id, target.dataset.action).catch(console.error);
});

refresh().catch(console.error);

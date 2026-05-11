const state = {
  runs: [],
  currentRunId: null,
  nodeFilter: "all",
  graphMode: "overview",
  searchQuery: "",
  edgeFilter: "all",
  hops: 1,
  selectedNodeId: null,
  selectedEdgeId: null,
  graphProjection: {
    nodes: [],
    approved_edges: [],
    pending_edges: [],
    edges: [],
    counts: {},
    groups: [],
  },
  ontologyView: {
    scale: 1,
    x: 0,
    y: 0,
    dragging: false,
    lastX: 0,
    lastY: 0,
  },
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

const nodeColors = {
  Requirement: "#2f6fbb",
  Architecture_Block: "#6b5fb5",
  Design_Spec: "#2f8a65",
  Verification: "#b2762f",
  Issue: "#b54a4a",
  Decision: "#5b7583",
  Component: "#767b35",
  Risk: "#9b5b65",
};

const shortName = (name) => (name.length > 28 ? `${name.slice(0, 25)}...` : name);

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const applyOntologyTransform = () => {
  const viewport = document.getElementById("ontology-viewport");
  if (!viewport) return;
  const { scale, x, y } = state.ontologyView;
  viewport.setAttribute("transform", `translate(${x} ${y}) scale(${scale})`);
};

const resetOntologyView = () => {
  state.ontologyView.scale = 1;
  state.ontologyView.x = 0;
  state.ontologyView.y = 0;
  applyOntologyTransform();
};

const zoomOntology = (factor, anchorX = 640, anchorY = 360) => {
  const current = state.ontologyView.scale;
  const next = clamp(current * factor, 0.35, 3.5);
  const ratio = next / current;
  state.ontologyView.x = anchorX - (anchorX - state.ontologyView.x) * ratio;
  state.ontologyView.y = anchorY - (anchorY - state.ontologyView.y) * ratio;
  state.ontologyView.scale = next;
  applyOntologyTransform();
};

const svgPointFromEvent = (svg, event) => {
  const matrix = svg.getScreenCTM();
  if (!matrix) return { x: 640, y: 360 };
  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  return point.matrixTransform(matrix.inverse());
};

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
    list.append(emptyRow("No visible edges"));
    return;
  }
  edges.forEach((edge) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title">
        <span>${edge.relation}</span>${badge(edge.view_status, edge.view_status === "pending")}
      </div>
      <div class="item-meta">
        ${edge.source_node_name || edge.source_node_id}<br>
        ${edge.target_node_name || edge.target_node_id}
      </div>
    `;
    item.addEventListener("click", () => renderEdgeDetail(edge));
    list.append(item);
  });
};

const renderOntologyGraph = (projection) => {
  const svg = el("ontology-graph");
  svg.replaceChildren();
  const width = 1280;
  const height = 720;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const nodes = projection.nodes.filter(
    (node) => state.nodeFilter === "all" || node.node_type === state.nodeFilter,
  );
  const nodeIds = new Set(nodes.map((node) => node.node_id));
  const edges = projection.edges.filter(
    (edge) => nodeIds.has(edge.source_node_id) && nodeIds.has(edge.target_node_id),
  );
  const levels = [
    ["Requirement"],
    ["Architecture_Block", "Component"],
    ["Design_Spec", "Decision", "Risk"],
    ["Verification", "Issue"],
  ];
  const positions = new Map();
  const viewport = document.createElementNS("http://www.w3.org/2000/svg", "g");
  viewport.setAttribute("id", "ontology-viewport");
  const orphanNodes = nodes.filter((node) => node.is_orphan);
  orphanNodes.forEach((node, index) => {
    const y = 70 + index * 62;
    positions.set(node.node_id, { x: 1180, y });
  });

  levels.forEach((types, column) => {
    const group = nodes.filter((node) => types.includes(node.node_type) && !node.is_orphan);
    const x = 110 + column * 340;
    group.forEach((node, index) => {
      const spacing = Math.max(58, Math.min(108, 560 / Math.max(group.length, 1)));
      const y = 70 + index * spacing;
      positions.set(node.node_id, { x, y });
    });
  });

  const missing = nodes.filter((node) => !positions.has(node.node_id));
  missing.forEach((node, index) => positions.set(node.node_id, { x: 1180, y: 80 + index * 70 }));

  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  defs.innerHTML = `
    <marker id="arrow-approved" markerWidth="8" markerHeight="8" refX="7" refY="4"
      orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L8,4 L0,8 z" fill="#77858d"></path>
    </marker>
    <marker id="arrow-pending" markerWidth="8" markerHeight="8" refX="7" refY="4"
      orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L8,4 L0,8 z" fill="#8a5a19"></path>
    </marker>
  `;
  svg.append(defs);
  svg.append(viewport);

  edges.forEach((edge) => {
    const source = positions.get(edge.source_node_id);
    const target = positions.get(edge.target_node_id);
    if (!source || !target) return;
    const midX = (source.x + target.x) / 2;
    const pathData = `M${source.x + 22},${source.y} C${midX},${source.y} ${midX},${target.y} ${
      target.x - 22
    },${target.y}`;
    const pending = edge.approval_status !== "approved";
    const selected = state.selectedEdgeId === edge.edge_id;
    const selectEdge = (event) => {
      event.stopPropagation();
      renderEdgeDetail(edge);
      renderOntologyGraph(state.graphProjection);
    };
    const hitPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    hitPath.setAttribute("d", pathData);
    hitPath.setAttribute("class", "ontology-edge-hit");
    hitPath.setAttribute("role", "button");
    hitPath.setAttribute("tabindex", "0");
    hitPath.setAttribute(
      "aria-label",
      `${edge.relation} ${edge.source_node_id} to ${edge.target_node_id}`,
    );
    hitPath.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
    });
    hitPath.addEventListener("click", selectEdge);
    hitPath.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectEdge(event);
      }
    });
    viewport.append(hitPath);

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathData);
    path.setAttribute(
      "class",
      `ontology-edge${pending ? " pending" : ""}${selected ? " selected" : ""}`,
    );
    path.setAttribute("marker-end", pending ? "url(#arrow-pending)" : "url(#arrow-approved)");
    viewport.append(path);
  });

  nodes.forEach((node) => {
    const position = positions.get(node.node_id);
    if (!position) return;
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const statusClasses = [
      "ontology-node",
      node.is_orphan ? "orphan" : "",
      node.has_pending_edges ? "pending" : "",
      node.finding_count > 0 ? "finding" : "",
    ]
      .filter(Boolean)
      .join(" ");
    group.setAttribute("class", statusClasses);
    group.setAttribute("tabindex", "0");
    group.setAttribute("role", "button");
    group.setAttribute("aria-label", node.name);
    group.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
    });
    group.addEventListener("click", (event) => {
      event.stopPropagation();
      renderOntologyDetail(node);
      if (state.graphMode === "neighborhood") {
        refresh().catch(console.error);
      }
    });
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        renderOntologyDetail(node);
        if (state.graphMode === "neighborhood") {
          refresh().catch(console.error);
        }
      }
    });

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", position.x);
    circle.setAttribute("cy", position.y);
    circle.setAttribute("r", "18");
    circle.setAttribute("fill", nodeColors[node.node_type] || "#5b7583");
    group.append(circle);

    const title = document.createElementNS("http://www.w3.org/2000/svg", "text");
    title.setAttribute("x", position.x + 26);
    title.setAttribute("y", position.y + 4);
    title.textContent = shortName(node.name);
    group.append(title);

    viewport.append(group);
  });
  applyOntologyTransform();
};

const renderOntologyDetail = (node) => {
  state.selectedNodeId = node.node_id;
  state.selectedEdgeId = null;
  el("ontology-detail").innerHTML = `
    <strong>${node.name}</strong>
    ${badge(node.node_type)}
    ${node.is_orphan ? badge("orphan", true) : ""}
    ${node.has_pending_edges ? badge("pending", true) : ""}
    <div class="item-meta">
      ${node.node_id}<br>
      confidence=${node.confidence_score}<br>
      risk=${node.risk_level} findings=${node.finding_count}<br>
      approved in/out=${node.approved_in_degree}/${node.approved_out_degree}<br>
      pending in/out=${node.pending_in_degree}/${node.pending_out_degree}<br>
      source=${node.source_artifact_ids.join(", ")}<br><br>
      ${node.description}
    </div>
    <div class="review-actions">
      <button id="focus-neighborhood" type="button">Focus Neighborhood</button>
    </div>
    <div class="chain-detail">
      <h3>Traceability Chain</h3>
      <div id="chain-detail">Loading chain</div>
    </div>
  `;
  el("focus-neighborhood").addEventListener("click", () => {
    state.graphMode = "neighborhood";
    document.querySelectorAll("[data-graph-mode]").forEach((item) => {
      item.classList.toggle("active", item.dataset.graphMode === "neighborhood");
    });
    refresh().catch(console.error);
  });
  loadTraceabilityChain(node.node_id).catch((error) => {
    el("chain-detail").textContent = error.message;
  });
};

const renderEdgeDetail = (edge) => {
  state.selectedEdgeId = edge.edge_id;
  const evidence = edge.evidence?.length ? JSON.stringify(edge.evidence, null, 2) : "[]";
  el("ontology-detail").innerHTML = `
    <strong>${edge.relation}</strong>
    ${badge(edge.view_status, edge.view_status === "pending")}
    <div class="item-meta">
      ${edge.edge_id}<br>
      source=${edge.source_node_name || edge.source_node_id}<br>
      target=${edge.target_node_name || edge.target_node_id}<br>
      confidence=${edge.confidence_score}<br>
      approval=${edge.approval_status}${edge.approval_id ? ` / ${edge.approval_id}` : ""}<br><br>
      ${edge.reasoning}
    </div>
    <pre class="detail-pre">${evidence}</pre>
  `;
};

const loadTraceabilityChain = async (nodeId) => {
  const query = new URLSearchParams({
    depth: "3",
    include_pending: "true",
    direction: "both",
  });
  const chain = await api(`/traceability/chain/${encodeURIComponent(nodeId)}?${query.toString()}`);
  if (state.selectedNodeId !== nodeId) return;
  renderTraceabilityChain(chain);
};

const renderTraceabilityChain = (chain) => {
  const target = el("chain-detail");
  if (!chain.nodes.length) {
    target.textContent = "No chain nodes";
    return;
  }
  const nodes = chain.nodes
    .map(
      (node) => `
        <li>
          <span>${node.depth}</span>
          <strong>${node.name}</strong>
          ${badge(node.node_type)}
          ${node.is_center ? badge("center", true) : ""}
        </li>
      `,
    )
    .join("");
  const edges = chain.edges
    .map(
      (edge) => `
        <li>
          <span>${edge.relation}</span>
          ${badge(edge.view_status, edge.view_status === "pending")}
          <div>${edge.source_node_name || edge.source_node_id}<br>${edge.target_node_name || edge.target_node_id}</div>
        </li>
      `,
    )
    .join("");
  target.innerHTML = `
    <div class="chain-summary">${chain.nodes.length} nodes / ${chain.edges.length} edges</div>
    <ul class="chain-list">${nodes}</ul>
    <ul class="chain-list edge-chain">${edges || "<li>No visible edges</li>"}</ul>
  `;
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
        <span>${candidate.candidate_type}</span>${badge(candidate.status, true)}
      </div>
      <div class="item-meta">
        ${candidate.candidate_id}<br>
        ${candidate.proposed_change_summary}
      </div>
    `;
    list.append(item);
  });
};

const renderDebugSummary = async () => {
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
        <span>${step.stage_name}</span>${badge(step.status, step.status !== "succeeded")}
      </div>
      <div class="item-meta">
        ${step.step_id}<br>
        input=${step.input_hash}<br>
        output=${step.output_hash || "none"}<br>
        artifact=${step.output_ref || "none"}<br>
        retrieval=${step.retrieval_context_ref || "none"}<br>
        validation=${step.validation_status || "not_applicable"}
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

const renderDebugDiffView = (diffView) => {
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

const renderAuditEvents = (events) => {
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
        <span>${event.action}</span>${badge(event.outcome, event.outcome !== "succeeded")}
      </div>
      <div class="item-meta">
        ${event.audit_id}<br>
        actor=${event.actor_id}${event.actor_role ? ` / ${event.actor_role}` : ""}<br>
        target=${event.target_type}:${event.target_id}<br>
        ${event.reason_code ? `reason=${event.reason_code}<br>` : ""}
        ${event.created_at}
      </div>
    `;
    list.append(item);
  });
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
  const [projection, approvals, findings, evalCandidates, feedbackSummary, improvements, gate, schedule, auditEvents] =
    await Promise.all([
      api(`/graph/projection?${query.toString()}`),
      api("/approvals"),
      api("/findings"),
      api("/eval/candidates"),
      api("/feedback/summary"),
      api("/improvements/candidates"),
      api("/eval/gate"),
      api("/schedule"),
      api("/audit/events?limit=20"),
    ]);
  state.graphProjection = projection;
  renderNodes(projection.nodes);
  renderEdges(projection.edges);
  renderOntologyGraph(projection);
  renderApprovals(approvals);
  renderFindings(findings);
  renderEvalCandidates(evalCandidates);
  renderImprovements(improvements);
  renderAuditEvents(auditEvents);
  text("metric-runs", state.runs.length);
  text("metric-nodes", `${projection.counts.visible_nodes}/${projection.counts.total_nodes}`);
  text(
    "metric-edges",
    `${projection.counts.visible_approved_edges}/${projection.counts.visible_pending_edges}`,
  );
  text("metric-approvals", approvals.length);
  text("metric-findings", findings.length);
  text(
    "metric-feedback",
    Object.values(feedbackSummary).reduce((sum, count) => sum + count, 0),
  );
  text("metric-gate", gate.status);
  text("metric-schedule", schedule.enabled ? "on" : "off");
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

const renderSchedule = (schedule) => {
  text("schedule-label", schedule.running ? "running" : "disabled");
  text("schedule-run-label", schedule.last_run_id || "no run");
  el("schedule-interval").value = schedule.interval_seconds;
  el("schedule-project").value = schedule.project_key;
  el("schedule-scenario").value = schedule.scenario;
  el("schedule-enabled").checked = schedule.enabled;
  el("schedule-status").textContent = JSON.stringify(schedule, null, 2);
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
el("schedule-form").addEventListener("submit", (event) => {
  event.preventDefault();
  applySchedule().catch(console.error);
});
el("schedule-run-now").addEventListener("click", () => runScheduleNow().catch(console.error));
el("ontology-zoom-in").addEventListener("click", () => zoomOntology(1.2));
el("ontology-zoom-out").addEventListener("click", () => zoomOntology(1 / 1.2));
el("ontology-reset").addEventListener("click", resetOntologyView);
el("graph-search-apply").addEventListener("click", () => {
  state.searchQuery = el("graph-search").value.trim();
  refresh().catch(console.error);
});
el("graph-search-clear").addEventListener("click", () => {
  state.searchQuery = "";
  el("graph-search").value = "";
  refresh().catch(console.error);
});
el("graph-search").addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  state.searchQuery = el("graph-search").value.trim();
  refresh().catch(console.error);
});
el("graph-hops").addEventListener("change", () => {
  state.hops = Number(el("graph-hops").value || 1);
  if (state.graphMode === "neighborhood") {
    refresh().catch(console.error);
  }
});
el("edge-filter").addEventListener("change", () => {
  state.edgeFilter = el("edge-filter").value;
  refresh().catch(console.error);
});
el("ontology-graph").addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    const point = svgPointFromEvent(el("ontology-graph"), event);
    zoomOntology(event.deltaY < 0 ? 1.12 : 1 / 1.12, point.x, point.y);
  },
  { passive: false },
);
el("ontology-graph").addEventListener("pointerdown", (event) => {
  state.ontologyView.dragging = true;
  state.ontologyView.lastX = event.clientX;
  state.ontologyView.lastY = event.clientY;
  el("ontology-graph").classList.add("is-panning");
  el("ontology-graph").setPointerCapture(event.pointerId);
});
el("ontology-graph").addEventListener("pointermove", (event) => {
  if (!state.ontologyView.dragging) return;
  const svg = el("ontology-graph");
  const rect = svg.getBoundingClientRect();
  const scaleX = 1280 / rect.width;
  const scaleY = 720 / rect.height;
  state.ontologyView.x += (event.clientX - state.ontologyView.lastX) * scaleX;
  state.ontologyView.y += (event.clientY - state.ontologyView.lastY) * scaleY;
  state.ontologyView.lastX = event.clientX;
  state.ontologyView.lastY = event.clientY;
  applyOntologyTransform();
});
el("ontology-graph").addEventListener("pointerup", (event) => {
  state.ontologyView.dragging = false;
  el("ontology-graph").classList.remove("is-panning");
  el("ontology-graph").releasePointerCapture(event.pointerId);
});
document.querySelectorAll("[data-node-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-node-filter]").forEach((item) => {
      item.classList.remove("active");
    });
    button.classList.add("active");
    state.nodeFilter = button.dataset.nodeFilter;
    renderOntologyGraph(state.graphProjection);
  });
});
document.querySelectorAll("[data-graph-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-graph-mode]").forEach((item) => {
      item.classList.remove("active");
    });
    button.classList.add("active");
    state.graphMode = button.dataset.graphMode;
    refresh().catch(console.error);
  });
});

refresh().catch(console.error);

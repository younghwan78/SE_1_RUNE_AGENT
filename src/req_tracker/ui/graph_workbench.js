import {
  api,
  badge,
  clamp,
  el,
  emptyRow,
  escapeHtml,
  requestRefresh,
  setActiveGraphMode,
  state,
} from "./core.js";

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

export const zoomOntology = (factor, anchorX = 640, anchorY = 360) => {
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

export const renderNodes = (nodes) => {
  const list = el("nodes");
  list.replaceChildren();
  if (!nodes.length) {
    list.append(emptyRow("No nodes"));
    return;
  }
  nodes.forEach((node) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <div class="item-title"><span>${escapeHtml(node.name)}</span>${badge(escapeHtml(node.node_type))}</div>
      <div class="item-meta">${escapeHtml(node.node_id)}<br>${escapeHtml(node.description)}</div>
    `;
    list.append(item);
  });
};

export const renderEdges = (edges) => {
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
        <span>${escapeHtml(edge.relation)}</span>${badge(escapeHtml(edge.view_status), edge.view_status === "pending")}
      </div>
      <div class="item-meta">
        ${escapeHtml(edge.source_node_name || edge.source_node_id)}<br>
        ${escapeHtml(edge.target_node_name || edge.target_node_id)}
      </div>
    `;
    item.addEventListener("click", () => renderEdgeDetail(edge));
    list.append(item);
  });
};

export const renderOntologyGraph = (projection) => {
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
        requestRefresh().catch(console.error);
      }
    });
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        renderOntologyDetail(node);
        if (state.graphMode === "neighborhood") {
          requestRefresh().catch(console.error);
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

export const renderOntologyDetail = (node) => {
  state.selectedNodeId = node.node_id;
  state.selectedEdgeId = null;
  el("ontology-detail").innerHTML = `
    <strong>${escapeHtml(node.name)}</strong>
    ${badge(escapeHtml(node.node_type))}
    ${node.is_orphan ? badge("orphan", true) : ""}
    ${node.has_pending_edges ? badge("pending", true) : ""}
    <div class="item-meta">
      ${escapeHtml(node.node_id)}<br>
      confidence=${node.confidence_score}<br>
      risk=${escapeHtml(node.risk_level)} findings=${node.finding_count}<br>
      approved in/out=${node.approved_in_degree}/${node.approved_out_degree}<br>
      pending in/out=${node.pending_in_degree}/${node.pending_out_degree}<br>
      source=${node.source_artifact_ids.map((item) => escapeHtml(item)).join(", ")}<br><br>
      ${escapeHtml(node.description)}
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
    setActiveGraphMode("neighborhood");
    requestRefresh().catch(console.error);
  });
  loadTraceabilityChain(node.node_id).catch((error) => {
    el("chain-detail").textContent = error.message;
  });
};

const renderEdgeDetail = (edge) => {
  state.selectedEdgeId = edge.edge_id;
  const evidence = edge.evidence?.length ? JSON.stringify(edge.evidence, null, 2) : "[]";
  el("ontology-detail").innerHTML = `
    <strong>${escapeHtml(edge.relation)}</strong>
    ${badge(escapeHtml(edge.view_status), edge.view_status === "pending")}
    <div class="item-meta">
      ${escapeHtml(edge.edge_id)}<br>
      source=${escapeHtml(edge.source_node_name || edge.source_node_id)}<br>
      target=${escapeHtml(edge.target_node_name || edge.target_node_id)}<br>
      confidence=${edge.confidence_score}<br>
      approval=${escapeHtml(edge.approval_status)}${edge.approval_id ? ` / ${escapeHtml(edge.approval_id)}` : ""}<br><br>
      ${escapeHtml(edge.reasoning)}
    </div>
    <pre class="detail-pre">${escapeHtml(evidence)}</pre>
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
          <strong>${escapeHtml(node.name)}</strong>
          ${badge(escapeHtml(node.node_type))}
          ${node.is_center ? badge("center", true) : ""}
        </li>
      `,
    )
    .join("");
  const edges = chain.edges
    .map(
      (edge) => `
        <li>
          <span>${escapeHtml(edge.relation)}</span>
          ${badge(escapeHtml(edge.view_status), edge.view_status === "pending")}
          <div>${escapeHtml(edge.source_node_name || edge.source_node_id)}<br>${escapeHtml(edge.target_node_name || edge.target_node_id)}</div>
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

export const initGraphWorkbench = () => {
  el("ontology-zoom-in").addEventListener("click", () => zoomOntology(1.2));
  el("ontology-zoom-out").addEventListener("click", () => zoomOntology(1 / 1.2));
  el("ontology-reset").addEventListener("click", resetOntologyView);
  el("graph-search-apply").addEventListener("click", () => {
    state.searchQuery = el("graph-search").value.trim();
    requestRefresh().catch(console.error);
  });
  el("graph-search-clear").addEventListener("click", () => {
    state.searchQuery = "";
    el("graph-search").value = "";
    requestRefresh().catch(console.error);
  });
  el("graph-search").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    state.searchQuery = el("graph-search").value.trim();
    requestRefresh().catch(console.error);
  });
  el("graph-hops").addEventListener("change", () => {
    state.hops = Number(el("graph-hops").value || 1);
    if (state.graphMode === "neighborhood") {
      requestRefresh().catch(console.error);
    }
  });
  el("edge-filter").addEventListener("change", () => {
    state.edgeFilter = el("edge-filter").value;
    requestRefresh().catch(console.error);
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
      setActiveGraphMode(button.dataset.graphMode);
      requestRefresh().catch(console.error);
    });
  });
};

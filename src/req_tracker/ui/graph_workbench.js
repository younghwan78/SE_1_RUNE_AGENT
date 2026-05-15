import {
  api,
  badge,
  clamp,
  el,
  emptyRow,
  escapeHtml,
  requestRefresh,
  setActiveGraphLayout,
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
  relationshipPinnedPositions.clear();
  applyOntologyTransform();
  if (state.graphLayout === "relationship") {
    renderRelationshipGraph(state.graphProjection);
  }
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

const graphPointFromEvent = (svg, event) => {
  const point = svgPointFromEvent(svg, event);
  const { scale, x, y } = state.ontologyView;
  return {
    x: (point.x - x) / scale,
    y: (point.y - y) / scale,
  };
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

const typeRank = {
  Requirement: 1,
  Architecture_Block: 2,
  Component: 3,
  Design_Spec: 4,
  Decision: 5,
  Risk: 6,
  Verification: 7,
  Issue: 8,
};

const sortNodesForLayout = (left, right) => {
  const leftRank = typeRank[left.node_type] || 99;
  const rightRank = typeRank[right.node_type] || 99;
  if (leftRank !== rightRank) return leftRank - rightRank;
  return `${left.name}${left.node_id}`.localeCompare(`${right.name}${right.node_id}`);
};

const buildGraphMaps = (nodes, edges) => {
  const degree = new Map(nodes.map((node) => [node.node_id, 0]));
  const adjacency = new Map(nodes.map((node) => [node.node_id, []]));
  edges.forEach((edge) => {
    if (!degree.has(edge.source_node_id) || !degree.has(edge.target_node_id)) return;
    degree.set(edge.source_node_id, degree.get(edge.source_node_id) + 1);
    degree.set(edge.target_node_id, degree.get(edge.target_node_id) + 1);
    adjacency.get(edge.source_node_id).push(edge.target_node_id);
    adjacency.get(edge.target_node_id).push(edge.source_node_id);
  });
  return { degree, adjacency };
};

const selectRelationshipCenter = (nodes, degree) => {
  const selected = nodes.find((node) => node.node_id === state.selectedNodeId);
  if (selected) return selected;
  return [...nodes]
    .sort((left, right) => {
      const requirementBias =
        (right.node_type === "Requirement" ? 1000 : 0) - (left.node_type === "Requirement" ? 1000 : 0);
      if (requirementBias !== 0) return requirementBias;
      return (degree.get(right.node_id) || 0) - (degree.get(left.node_id) || 0) || sortNodesForLayout(left, right);
    })
    .at(0);
};

const shortestDistances = (centerId, adjacency) => {
  const distances = new Map([[centerId, 0]]);
  const queue = [centerId];
  while (queue.length) {
    const current = queue.shift();
    const nextDistance = distances.get(current) + 1;
    adjacency.get(current).forEach((neighborId) => {
      if (distances.has(neighborId)) return;
      distances.set(neighborId, nextDistance);
      queue.push(neighborId);
    });
  }
  return distances;
};

const placeRing = (positions, nodes, centerX, centerY, radius, startAngle = -Math.PI / 2) => {
  const ordered = [...nodes].sort(sortNodesForLayout);
  ordered.forEach((node, index) => {
    const angle = startAngle + (Math.PI * 2 * index) / Math.max(ordered.length, 1);
    positions.set(node.node_id, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    });
  });
};

const placeIslandBand = (positions, nodes, x, y, columns = 4) => {
  [...nodes].sort(sortNodesForLayout).forEach((node, index) => {
    positions.set(node.node_id, {
      x: x + (index % columns) * 112,
      y: y + Math.floor(index / columns) * 68,
    });
  });
};

export const relationshipPinnedPositions = new Map();
let relationshipNodeDrag = null;
let suppressRelationshipClickNodeId = null;

const connectedComponents = (nodes, adjacency) => {
  const nodeById = new Map(nodes.map((node) => [node.node_id, node]));
  const visited = new Set();
  const components = [];
  [...nodes].sort(sortNodesForLayout).forEach((node) => {
    if (visited.has(node.node_id)) return;
    const queue = [node.node_id];
    const members = [];
    visited.add(node.node_id);
    while (queue.length) {
      const current = queue.shift();
      const currentNode = nodeById.get(current);
      if (currentNode) members.push(currentNode);
      adjacency.get(current).forEach((neighborId) => {
        if (visited.has(neighborId)) return;
        visited.add(neighborId);
        queue.push(neighborId);
      });
    }
    components.push(members);
  });
  return components;
};

const selectedComponentFirst = (components, degree) =>
  [...components].sort((left, right) => {
    const leftSelected = left.some((node) => node.node_id === state.selectedNodeId) ? 1 : 0;
    const rightSelected = right.some((node) => node.node_id === state.selectedNodeId) ? 1 : 0;
    if (leftSelected !== rightSelected) return rightSelected - leftSelected;
    const sizeDelta = right.length - left.length;
    if (sizeDelta !== 0) return sizeDelta;
    const degreeDelta =
      Math.max(...right.map((node) => degree.get(node.node_id) || 0)) -
      Math.max(...left.map((node) => degree.get(node.node_id) || 0));
    if (degreeDelta !== 0) return degreeDelta;
    return sortNodesForLayout(left[0], right[0]);
  });

const selectComponentCenter = (component, degree) => {
  const selected = component.find((node) => node.node_id === state.selectedNodeId);
  if (selected) return selected;
  return [...component]
    .sort((left, right) => {
      const requirementBias =
        (right.node_type === "Requirement" ? 1000 : 0) - (left.node_type === "Requirement" ? 1000 : 0);
      if (requirementBias !== 0) return requirementBias;
      return (degree.get(right.node_id) || 0) - (degree.get(left.node_id) || 0) || sortNodesForLayout(left, right);
    })
    .at(0);
};

const componentNodeAngle = (node, index, total) => {
  const baseAngles = {
    Architecture_Block: -Math.PI * 0.82,
    Component: -Math.PI * 0.62,
    Design_Spec: 0,
    Verification: Math.PI * 0.55,
    Issue: Math.PI * 0.72,
    Decision: -Math.PI * 0.1,
    Risk: Math.PI,
    Requirement: -Math.PI / 2,
  };
  const base = baseAngles[node.node_type] ?? -Math.PI / 2;
  const spread = Math.min(Math.PI * 0.75, Math.max(Math.PI * 0.2, total * 0.12));
  const offset = total <= 1 ? 0 : -spread / 2 + (spread * index) / (total - 1);
  return base + offset;
};

const placeComponent = (positions, component, degree, centerX, centerY, cellWidth, cellHeight) => {
  const center = selectComponentCenter(component, degree);
  positions.set(center.node_id, { x: centerX, y: centerY });
  const rest = component.filter((node) => node.node_id !== center.node_id).sort(sortNodesForLayout);
  rest.forEach((node, index) => {
    const angle = componentNodeAngle(node, index, rest.length);
    const radius = Math.min(cellWidth * 0.34, cellHeight * 0.36, 58 + rest.length * 4);
    positions.set(node.node_id, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    });
  });
};

const relationshipComponentPositions = (nodes, edges, width, height, degree, adjacency) => {
  const positions = new Map();
  const components = connectedComponents(nodes, adjacency);
  const linkedComponents = selectedComponentFirst(
    components.filter((component) => component.some((node) => (degree.get(node.node_id) || 0) > 0)),
    degree,
  );
  const isolatedNodes = components
    .filter((component) => component.every((node) => (degree.get(node.node_id) || 0) === 0))
    .flat()
    .sort(sortNodesForLayout);

  const columns = linkedComponents.length > 12 ? 5 : linkedComponents.length > 6 ? 4 : 3;
  const cellWidth = (width - 120) / columns;
  const cellHeight = 145;
  linkedComponents.forEach((component, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const centerX = 60 + column * cellWidth + cellWidth / 2;
    const centerY = 80 + row * cellHeight + cellHeight / 2;
    placeComponent(positions, component, degree, centerX, centerY, cellWidth, cellHeight);
  });

  const linkedRows = Math.max(1, Math.ceil(linkedComponents.length / columns));
  const shelfY = Math.min(height - 118, 92 + linkedRows * cellHeight);
  const shelfColumns = 9;
  isolatedNodes.forEach((node, index) => {
    positions.set(node.node_id, {
      x: 58 + (index % shelfColumns) * 132,
      y: shelfY + Math.floor(index / shelfColumns) * 48,
    });
  });
  return positions;
};

const relationshipRadialPositions = (nodes, edges, width, height, degree, adjacency) => {
  const positions = new Map();
  const center = selectRelationshipCenter(nodes, degree);
  const centerX = width * 0.5;
  const centerY = height * 0.46;
  positions.set(center.node_id, { x: centerX, y: centerY });

  const distances = shortestDistances(center.node_id, adjacency);
  const connected = nodes.filter((node) => node.node_id !== center.node_id && distances.has(node.node_id));
  const oneHop = connected.filter((node) => distances.get(node.node_id) === 1);
  const twoHop = connected.filter((node) => distances.get(node.node_id) === 2);
  const outer = connected.filter((node) => distances.get(node.node_id) > 2);
  const disconnected = nodes.filter((node) => node.node_id !== center.node_id && !distances.has(node.node_id));
  const orphans = disconnected.filter((node) => node.is_orphan || (degree.get(node.node_id) || 0) === 0);
  const islands = disconnected.filter((node) => !orphans.includes(node));

  placeRing(positions, oneHop, centerX, centerY, 170);
  placeRing(positions, twoHop, centerX, centerY, 294, -Math.PI / 2 + Math.PI / Math.max(twoHop.length, 1));
  placeRing(positions, outer, centerX, centerY, 410, -Math.PI / 3);
  placeIslandBand(positions, islands, width - 400, 84, 3);
  placeIslandBand(positions, orphans, 72, height - 178, 5);
  return positions;
};

export const relationshipLayoutPositions = (nodes, edges, width = 1280, height = 720) => {
  if (!nodes.length) return new Map();
  const { degree, adjacency } = buildGraphMaps(nodes, edges);
  const components = connectedComponents(nodes, adjacency);
  const multiComponent = components.filter((component) => component.some((node) => (degree.get(node.node_id) || 0) > 0));
  if (nodes.length > 45 || multiComponent.length > 4) {
    const positions = relationshipComponentPositions(nodes, edges, width, height, degree, adjacency);
    nodes.forEach((node) => {
      if (relationshipPinnedPositions.has(node.node_id)) {
        positions.set(node.node_id, relationshipPinnedPositions.get(node.node_id));
      }
    });
    return positions;
  }
  const positions = relationshipRadialPositions(nodes, edges, width, height, degree, adjacency);
  nodes.forEach((node) => {
    if (relationshipPinnedPositions.has(node.node_id)) {
      positions.set(node.node_id, relationshipPinnedPositions.get(node.node_id));
    }
  });
  return positions;
};

const appendGraphMarkers = (svg) => {
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
};

const appendEdge = (viewport, edge, pathData) => {
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
  hitPath.setAttribute("data-edge-id", edge.edge_id);
  hitPath.setAttribute("role", "button");
  hitPath.setAttribute("tabindex", "0");
  hitPath.setAttribute("aria-label", `${edge.relation} ${edge.source_node_id} to ${edge.target_node_id}`);
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
  path.setAttribute("data-edge-id", edge.edge_id);
  path.setAttribute(
    "class",
    `ontology-edge${pending ? " pending" : ""}${selected ? " selected" : ""}`,
  );
  path.setAttribute("marker-end", pending ? "url(#arrow-pending)" : "url(#arrow-approved)");
  viewport.append(path);
};

const rerenderRelationshipGraph = () => {
  if (state.graphLayout !== "relationship") return;
  renderRelationshipGraph(state.graphProjection);
};

export const updateRelationshipNodeDrag = (event) => {
  if (!relationshipNodeDrag) return;
  event.preventDefault();
  const point = graphPointFromEvent(el("ontology-graph"), event);
  const nextPosition = {
    x: clamp(point.x + relationshipNodeDrag.offsetX, 32, 1248),
    y: clamp(point.y + relationshipNodeDrag.offsetY, 32, 688),
  };
  const deltaX = nextPosition.x - relationshipNodeDrag.startX;
  const deltaY = nextPosition.y - relationshipNodeDrag.startY;
  if (Math.hypot(deltaX, deltaY) > 3) {
    relationshipNodeDrag.moved = true;
  }
  relationshipPinnedPositions.set(relationshipNodeDrag.nodeId, nextPosition);
  rerenderRelationshipGraph();
};

const endRelationshipNodeDrag = (event) => {
  if (!relationshipNodeDrag) return;
  event.preventDefault();
  if (relationshipNodeDrag.moved) {
    suppressRelationshipClickNodeId = relationshipNodeDrag.nodeId;
  }
  document.removeEventListener("pointermove", updateRelationshipNodeDrag);
  document.removeEventListener("pointerup", endRelationshipNodeDrag);
  relationshipNodeDrag = null;
};

export const startRelationshipNodeDrag = (node, position, event) => {
  if (state.graphLayout !== "relationship") return;
  event.preventDefault();
  event.stopPropagation();
  const point = graphPointFromEvent(el("ontology-graph"), event);
  relationshipNodeDrag = {
    nodeId: node.node_id,
    offsetX: position.x - point.x,
    offsetY: position.y - point.y,
    startX: position.x,
    startY: position.y,
    moved: false,
  };
  relationshipPinnedPositions.set(node.node_id, position);
  document.addEventListener("pointermove", updateRelationshipNodeDrag);
  document.addEventListener("pointerup", endRelationshipNodeDrag);
};

const appendNode = (viewport, node, position, options = {}) => {
  const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
  const statusClasses = [
    "ontology-node",
    options.center ? "relationship-center" : "",
    options.relationship ? "relationship-node" : "",
    node.is_orphan ? "orphan relationship-orphan" : "",
    node.has_pending_edges ? "pending" : "",
    node.finding_count > 0 ? "finding" : "",
  ]
    .filter(Boolean)
    .join(" ");
  group.setAttribute("class", statusClasses);
  group.setAttribute("tabindex", "0");
  group.setAttribute("role", "button");
  group.setAttribute("aria-label", node.name);
  const tooltip = document.createElementNS("http://www.w3.org/2000/svg", "title");
  tooltip.textContent = `${node.name} (${node.node_type})`;
  group.append(tooltip);
  group.addEventListener("pointerdown", (event) => {
    if (options.relationship) {
      startRelationshipNodeDrag(node, position, event);
      return;
    }
    event.stopPropagation();
  });
  group.addEventListener("click", (event) => {
    event.stopPropagation();
    if (suppressRelationshipClickNodeId === node.node_id) {
      suppressRelationshipClickNodeId = null;
      return;
    }
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
  circle.setAttribute("cx", "0");
  circle.setAttribute("cy", "0");
  circle.setAttribute("r", options.center ? "24" : "18");
  circle.setAttribute("fill", nodeColors[node.node_type] || "#5b7583");
  group.append(circle);

  if (!options.hideLabel) {
    const title = document.createElementNS("http://www.w3.org/2000/svg", "text");
    if (options.captionLabel) {
      title.setAttribute("class", "relationship-caption");
      title.setAttribute("text-anchor", "middle");
      title.setAttribute("x", "0");
      title.setAttribute("y", node.is_orphan ? "28" : "60");
    } else {
      title.setAttribute("x", options.center ? "32" : "26");
      title.setAttribute("y", "4");
    }
    title.textContent = shortName(node.name);
    group.append(title);
  }

  group.setAttribute("transform", `translate(${position.x} ${position.y})`);
  viewport.append(group);
};

const relationshipVisibleLabels = (nodes, edges) => {
  if (nodes.length <= 60) return new Set(nodes.map((node) => node.node_id));
  const { degree, adjacency } = buildGraphMaps(nodes, edges);
  const labels = new Set();
  connectedComponents(nodes, adjacency)
    .filter((component) => component.some((node) => (degree.get(node.node_id) || 0) > 0))
    .forEach((component) => {
      labels.add(selectComponentCenter(component, degree).node_id);
    });
  const selected = nodes.find((node) => node.node_id === state.selectedNodeId);
  if (selected) labels.add(selected.node_id);
  nodes
    .filter((node) => node.is_orphan && node.finding_count > 0)
    .slice(0, 8)
    .forEach((node) => labels.add(node.node_id));
  return labels;
};

export const renderRelationshipGraph = (projection) => {
  const svg = el("ontology-graph");
  svg.replaceChildren();
  const width = 1280;
  const height = 720;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("data-layout", "relationship");

  const nodes = projection.nodes.filter(
    (node) => state.nodeFilter === "all" || node.node_type === state.nodeFilter,
  );
  const nodeIds = new Set(nodes.map((node) => node.node_id));
  const edges = projection.edges.filter(
    (edge) => nodeIds.has(edge.source_node_id) && nodeIds.has(edge.target_node_id),
  );
  const positions = relationshipLayoutPositions(nodes, edges, width, height);
  const visibleLabels = relationshipVisibleLabels(nodes, edges);
  const viewport = document.createElementNS("http://www.w3.org/2000/svg", "g");
  viewport.setAttribute("id", "ontology-viewport");
  appendGraphMarkers(svg);
  svg.append(viewport);

  edges.forEach((edge) => {
    const source = positions.get(edge.source_node_id);
    const target = positions.get(edge.target_node_id);
    if (!source || !target) return;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const distance = Math.max(Math.hypot(dx, dy), 1);
    const offsetX = (dx / distance) * 24;
    const offsetY = (dy / distance) * 24;
    const curve = Math.min(48, Math.max(-48, (source.y - target.y) * 0.12));
    const midX = (source.x + target.x) / 2;
    const midY = (source.y + target.y) / 2 + curve;
    const pathData = `M${source.x + offsetX},${source.y + offsetY} Q${midX},${midY} ${
      target.x - offsetX
    },${target.y - offsetY}`;
    appendEdge(viewport, edge, pathData);
  });

  const { degree } = buildGraphMaps(nodes, edges);
  const center = selectRelationshipCenter(nodes, degree);
  nodes.forEach((node) => {
    const position = positions.get(node.node_id);
    if (!position) return;
    appendNode(viewport, node, position, {
      center: node.node_id === center.node_id,
      captionLabel: nodes.length > 60 && visibleLabels.has(node.node_id),
      hideLabel: !visibleLabels.has(node.node_id),
      relationship: true,
    });
  });
  applyOntologyTransform();
};

const renderOntologyLaneGraph = (projection) => {
  const svg = el("ontology-graph");
  svg.replaceChildren();
  const width = 1280;
  const height = 720;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("data-layout", "ontology");

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

  appendGraphMarkers(svg);
  svg.append(viewport);

  edges.forEach((edge) => {
    const source = positions.get(edge.source_node_id);
    const target = positions.get(edge.target_node_id);
    if (!source || !target) return;
    const midX = (source.x + target.x) / 2;
    const pathData = `M${source.x + 22},${source.y} C${midX},${source.y} ${midX},${target.y} ${
      target.x - 22
    },${target.y}`;
    appendEdge(viewport, edge, pathData);
  });

  nodes.forEach((node) => {
    const position = positions.get(node.node_id);
    if (!position) return;
    appendNode(viewport, node, position);
  });
  applyOntologyTransform();
};

export const renderOntologyGraph = (projection) => {
  if (state.graphLayout === "relationship") {
    renderRelationshipGraph(projection);
    return;
  }
  renderOntologyLaneGraph(projection);
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
  document.querySelectorAll("[data-graph-layout]").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveGraphLayout(button.dataset.graphLayout);
      renderOntologyGraph(state.graphProjection);
    });
  });
};

import {
  badge,
  el,
  emptyRow,
  escapeHtml,
  healthWarning,
  navigateTo,
  requestRefresh,
  setActiveGraphMode,
  showView,
  state,
  text,
} from "./core.js";

let decisionHandler = null;
const FILTER_STORAGE_KEY = "rune.workQueue.filters.v1";
const ASSIGNMENT_STORAGE_KEY = "rune.workQueue.assignments.v1";
const LOCAL_USER_ID = "local_reviewer";
const defaultFilters = {
  itemType: "all",
  priority: "all",
  owner: "all",
  search: "",
};
let activeFilters = { ...defaultFilters };
let savedFilters = {};
let queueAssignments = {};

export const setWorkQueueDecisionHandler = (handler) => {
  decisionHandler = handler;
};

const readStorageJson = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    console.warn(`work queue localStorage read failed: ${key}`, error);
    return fallback;
  }
};

const writeStorageJson = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn(`work queue localStorage write failed: ${key}`, error);
  }
};

const assignedUser = (queueId) => queueAssignments[queueId] || null;

export const applyWorkQueueFilters = (items) => {
  const query = activeFilters.search.trim().toLowerCase();
  return items.filter((item) => {
    if (activeFilters.itemType !== "all" && item.item_type !== activeFilters.itemType) return false;
    if (activeFilters.priority !== "all" && item.priority !== activeFilters.priority) return false;
    if (activeFilters.owner === "assigned_to_me" && assignedUser(item.queue_id) !== LOCAL_USER_ID) return false;
    if (activeFilters.owner === "unassigned" && assignedUser(item.queue_id)) return false;
    if (
      !["all", "assigned_to_me", "unassigned"].includes(activeFilters.owner) &&
      item.owner_role !== activeFilters.owner
    ) {
      return false;
    }
    if (!query) return true;
    const haystack = [
      item.queue_id,
      item.title,
      item.summary,
      item.item_type,
      item.priority,
      item.owner_role,
      item.source_type,
      item.related_run_id,
      item.related_approval_id,
      item.related_finding_id,
      ...(item.related_node_ids || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
};

const syncFilterControls = () => {
  const type = el("queue-filter-type");
  if (!type) return;
  type.value = activeFilters.itemType;
  el("queue-filter-priority").value = activeFilters.priority;
  el("queue-filter-owner").value = activeFilters.owner;
  el("queue-filter-search").value = activeFilters.search;
  const saved = el("queue-filter-saved");
  const current = saved.value;
  saved.replaceChildren();
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "No saved filter";
  saved.append(none);
  Object.keys(savedFilters)
    .sort()
    .forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      saved.append(option);
    });
  saved.value = current && savedFilters[current] ? current : "";
};

export const saveCurrentFilter = () => {
  const name = el("queue-filter-save-name").value.trim();
  if (!name) return;
  savedFilters = {
    ...savedFilters,
    [name]: { ...activeFilters },
  };
  writeStorageJson(FILTER_STORAGE_KEY, savedFilters);
  el("queue-filter-save-name").value = "";
  syncFilterControls();
};

const setActiveFiltersFromControls = () => {
  activeFilters = {
    itemType: el("queue-filter-type").value,
    priority: el("queue-filter-priority").value,
    owner: el("queue-filter-owner").value,
    search: el("queue-filter-search").value,
  };
};

const renderFilteredQueue = () => {
  const items = state.latestWorkQueue.items || [];
  renderWorkQueueList("work-queue-full", applyWorkQueueFilters(items), 200);
  text("work-queue-full-count", `${applyWorkQueueFilters(items).length}/${items.length} visible`);
};

export const assignSelectedWorkItem = (assignee = LOCAL_USER_ID) => {
  if (!state.selectedWorkItem) return;
  queueAssignments = {
    ...queueAssignments,
    [state.selectedWorkItem.queue_id]: assignee,
  };
  writeStorageJson(ASSIGNMENT_STORAGE_KEY, queueAssignments);
  renderWorkQueue(state.latestWorkQueue);
};

const clearSelectedAssignment = () => {
  if (!state.selectedWorkItem) return;
  const next = { ...queueAssignments };
  delete next[state.selectedWorkItem.queue_id];
  queueAssignments = next;
  writeStorageJson(ASSIGNMENT_STORAGE_KEY, queueAssignments);
  renderWorkQueue(state.latestWorkQueue);
};

export const initWorkQueueControls = () => {
  savedFilters = readStorageJson(FILTER_STORAGE_KEY, {});
  queueAssignments = readStorageJson(ASSIGNMENT_STORAGE_KEY, {});
  syncFilterControls();
  [
    "queue-filter-type",
    "queue-filter-priority",
    "queue-filter-owner",
    "queue-filter-search",
  ].forEach((id) => {
    const control = el(id);
    if (!control) return;
    control.addEventListener("input", () => {
      setActiveFiltersFromControls();
      renderFilteredQueue();
    });
    control.addEventListener("change", () => {
      setActiveFiltersFromControls();
      renderFilteredQueue();
    });
  });
  el("queue-filter-save").addEventListener("click", saveCurrentFilter);
  el("queue-filter-clear").addEventListener("click", () => {
    activeFilters = { ...defaultFilters };
    syncFilterControls();
    renderFilteredQueue();
  });
  el("queue-filter-saved").addEventListener("change", () => {
    const name = el("queue-filter-saved").value;
    if (!name || !savedFilters[name]) return;
    activeFilters = { ...defaultFilters, ...savedFilters[name] };
    syncFilterControls();
    renderFilteredQueue();
  });
};

const setSelectedItemContext = (item) => {
  state.selectedWorkItem = item;
  if (item.related_node_ids?.[0]) {
    state.selectedNodeId = item.related_node_ids[0];
  }
  if (item.related_run_id) {
    state.currentRunId = item.related_run_id;
  }
};

export const renderWorkQueue = (payload) => {
  const items = payload.items || [];
  const counts = payload.counts || {};
  state.latestWorkQueue = payload;
  const routedItem = state.routeParams.item
    ? items.find((item) => item.queue_id === state.routeParams.item)
    : null;
  if (routedItem && state.selectedWorkItem?.queue_id !== routedItem.queue_id) {
    setSelectedItemContext(routedItem);
  }
  text("work-queue-count", `${counts.open || 0} open`);
  renderWorkQueueList("work-queue", items, 12);
  const filtered = applyWorkQueueFilters(items);
  text("work-queue-full-count", `${filtered.length}/${items.length} visible`);
  renderWorkQueueList("work-queue-full", filtered, 200);
  renderWorkQueueDetail(state.selectedWorkItem);
};

const renderWorkQueueList = (targetId, items, limit) => {
  const list = el(targetId);
  if (!list) return;
  list.replaceChildren();
  if (!items.length) {
    list.append(emptyRow("No open dashboard work items"));
    return;
  }
  items.slice(0, limit).forEach((item) => {
    const row = document.createElement("li");
    row.className = "queue-row";
    row.classList.toggle("active", state.selectedWorkItem?.queue_id === item.queue_id);
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(item.title)}</span>${badge(escapeHtml(item.priority), healthWarning(item.priority))}
      </div>
      <div class="item-meta">
        ${escapeHtml(item.item_type)} / ${escapeHtml(item.status)}${
          item.owner_role ? ` / ${escapeHtml(item.owner_role)}` : ""
        }<br>
        ${escapeHtml(item.summary)}<br>
        ${item.related_run_id ? `run=${escapeHtml(item.related_run_id)}<br>` : ""}
        ${item.related_finding_id ? `finding=${escapeHtml(item.related_finding_id)}<br>` : ""}
        ${item.related_approval_id ? `approval=${escapeHtml(item.related_approval_id)}` : ""}
        ${assignedUser(item.queue_id) ? `<br>assigned=${escapeHtml(assignedUser(item.queue_id))}` : ""}
      </div>
    `;
    row.addEventListener("click", () => selectWorkItem(item));
    list.append(row);
  });
};

export const selectWorkItem = (item, { openView = true, updateHash = true } = {}) => {
  setSelectedItemContext(item);
  renderWorkQueue(state.latestWorkQueue);
  renderWorkQueueDetail(item);
  if (!openView) return;
  if (updateHash) {
    navigateTo("work-queue", { item: item.queue_id });
  } else {
    showView("work-queue");
  }
};

export const renderWorkQueueDetail = (item) => {
  const target = el("work-queue-detail");
  if (!target) return;
  if (!item) {
    text("work-queue-detail-label", "not selected");
    target.textContent = "Select a work item";
    return;
  }
  text("work-queue-detail-label", item.queue_id);
  const evidence = item.evidence_refs?.length
    ? item.evidence_refs.map((ref) => `<span>${escapeHtml(ref)}</span>`).join("")
    : "<span>no evidence ref</span>";
  const relatedNodes = item.related_node_ids?.length ? item.related_node_ids.join(", ") : "none";
  const relatedEdges = item.related_edge_ids?.length ? item.related_edge_ids.join(", ") : "none";
  const assignment = assignedUser(item.queue_id) || "unassigned";
  const supportedActions = [
    item.related_node_ids?.length || item.related_edge_ids?.length ? "open_graph" : null,
    item.related_run_id ? "open_debug" : null,
    item.item_type === "source_warning" ? "inspect_source" : null,
    item.item_type === "eval_gate" ? "open_eval" : null,
    item.related_approval_id ? "approve" : null,
    item.related_approval_id ? "reject" : null,
  ].filter(Boolean);
  target.innerHTML = `
    <div>
      <h3>${escapeHtml(item.title)}</h3>
      ${badge(escapeHtml(item.item_type))}
      ${badge(escapeHtml(item.priority), healthWarning(item.priority))}
      ${badge(escapeHtml(item.status), healthWarning(item.status))}
    </div>
    <div class="item-meta">${escapeHtml(item.summary)}</div>
    <div class="detail-grid">
      <div class="detail-cell"><span>Queue</span><strong>${escapeHtml(item.queue_id)}</strong></div>
      <div class="detail-cell"><span>Owner</span><strong>${escapeHtml(item.owner_role || "unassigned")}</strong></div>
      <div class="detail-cell"><span>Run</span><strong>${escapeHtml(item.related_run_id || "none")}</strong></div>
      <div class="detail-cell"><span>Approval</span><strong>${escapeHtml(item.related_approval_id || "none")}</strong></div>
      <div class="detail-cell"><span>Finding</span><strong>${escapeHtml(item.related_finding_id || "none")}</strong></div>
      <div class="detail-cell"><span>Source</span><strong>${escapeHtml(item.source_type || "none")}</strong></div>
      <div class="detail-cell"><span>Nodes</span><strong>${escapeHtml(relatedNodes)}</strong></div>
      <div class="detail-cell"><span>Edges</span><strong>${escapeHtml(relatedEdges)}</strong></div>
      <div class="detail-cell"><span>Local Assignment</span><strong>${escapeHtml(assignment)}</strong></div>
    </div>
    <div>
      <h3>Evidence</h3>
      <div class="evidence-list">${evidence}</div>
    </div>
    <div>
      <h3>Available Actions</h3>
      <div class="evidence-list">${
        item.actions?.length
          ? item.actions.map((action) => `<span>${escapeHtml(action)}</span>`).join("")
          : "<span>none</span>"
      }</div>
    </div>
    <div class="review-actions">
      <button data-queue-action="assign_to_me" type="button">Assign to me</button>
      <button data-queue-action="clear_assignment" type="button">Clear assignment</button>
      ${supportedActions
        .map((action) => `<button data-queue-action="${escapeHtml(action)}" type="button">${escapeHtml(action)}</button>`)
        .join("")}
    </div>
  `;
};

export const handleQueueAction = async (action) => {
  const item = state.selectedWorkItem;
  if (!item) return;
  if (action === "open_graph") {
    if (item.related_node_ids?.[0]) {
      state.selectedNodeId = item.related_node_ids[0];
      setActiveGraphMode("neighborhood");
      navigateTo("traceability", { node: item.related_node_ids[0], mode: "neighborhood" });
    } else {
      navigateTo("traceability");
    }
    await requestRefresh();
    return;
  }
  if (action === "assign_to_me") {
    assignSelectedWorkItem();
    return;
  }
  if (action === "clear_assignment") {
    clearSelectedAssignment();
    return;
  }
  if (action === "open_debug") {
    const params = item.related_run_id ? { run: item.related_run_id } : {};
    if (item.related_run_id) state.currentRunId = item.related_run_id;
    navigateTo("debug", params);
    await requestRefresh();
    return;
  }
  if (action === "inspect_source") {
    navigateTo("source-health", item.source_type ? { source: item.source_type } : {});
    return;
  }
  if (action === "open_eval") {
    navigateTo("eval");
    return;
  }
  if ((action === "approve" || action === "reject") && item.related_approval_id && decisionHandler) {
    await decisionHandler(item.related_approval_id, action);
  }
};

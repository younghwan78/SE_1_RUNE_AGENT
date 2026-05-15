export const state = {
  runs: [],
  currentRunId: null,
  activeView: "dashboard",
  routeParams: {},
  nodeFilter: "all",
  graphMode: "overview",
  graphLayout: "ontology",
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
  latestWorkQueue: { items: [], counts: {} },
  selectedWorkItem: null,
  latestSourceHealth: { sources: [] },
  latestRunHealth: { recent_runs: [], total_runs: 0, failed_runs: 0 },
};

let refreshHandler = null;

export const setRefreshHandler = (handler) => {
  refreshHandler = handler;
};

export const requestRefresh = () => {
  if (!refreshHandler) return Promise.resolve();
  return refreshHandler();
};

export const api = async (path, options = {}) => {
  const response = await fetch(`/api/v1${path}`, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
};

export const safeApi = async (path, fallback, options = {}) => {
  try {
    return await api(path, options);
  } catch (error) {
    console.warn(`dashboard optional request failed: ${path}`, error);
    return fallback;
  }
};

export const el = (id) => document.getElementById(id);

export const text = (id, value) => {
  el(id).textContent = String(value);
};

export const emptyRow = (label) => {
  const item = document.createElement("li");
  item.className = "item-meta";
  item.textContent = label;
  return item;
};

export const badge = (value, warning = false) =>
  `<span class="badge${warning ? " warning" : ""}">${value}</span>`;

export const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

export const healthWarning = (value) =>
  ["attention", "attention_required", "blocked", "critical", "high", "failed", "stale", "warning"].includes(
    String(value),
  );

export const displayStatus = (value) => {
  if (value === "attention_required") return "attention";
  if (!value) return "unknown";
  return String(value).replaceAll("_", " ");
};

export const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const encodeRoute = (viewName, params = {}) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const suffix = query.toString();
  return suffix ? `${viewName}?${suffix}` : viewName;
};

const parseHash = () => {
  const raw = window.location.hash.replace(/^#/, "");
  if (!raw) return { view: "dashboard", params: {} };
  const [viewPart, queryPart = ""] = raw.split("?");
  const params = Object.fromEntries(new URLSearchParams(queryPart).entries());
  return { view: viewPart || "dashboard", params };
};

export const showView = (
  viewName,
  { updateHash = false, params = state.routeParams, scroll = true } = {},
) => {
  state.activeView = viewName;
  state.routeParams = params || {};
  document.querySelectorAll("[data-app-view]").forEach((section) => {
    section.classList.toggle("active", section.dataset.appView === viewName);
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.viewTarget === viewName);
  });
  if (updateHash) {
    const nextHash = `#${encodeRoute(viewName, state.routeParams)}`;
    if (window.location.hash !== nextHash) {
      history.replaceState(null, "", nextHash);
    }
  }
  if (scroll) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
};

export const navigateTo = (viewName, params = {}) => {
  showView(viewName, { updateHash: true, params });
};

export const setActiveGraphMode = (mode) => {
  state.graphMode = mode;
  document.querySelectorAll("[data-graph-mode]").forEach((item) => {
    item.classList.toggle("active", item.dataset.graphMode === mode);
  });
};

export const setActiveGraphLayout = (layout) => {
  state.graphLayout = layout;
  document.querySelectorAll("[data-graph-layout]").forEach((item) => {
    item.classList.toggle("active", item.dataset.graphLayout === layout);
  });
};

export const applyHashRoute = () => {
  const route = parseHash();
  state.routeParams = route.params;
  if (route.params.run) {
    state.currentRunId = route.params.run;
  }
  if (route.params.node) {
    state.selectedNodeId = route.params.node;
  }
  if (route.params.mode) {
    setActiveGraphMode(route.params.mode);
  }
  if (route.params.layout) {
    setActiveGraphLayout(route.params.layout);
  }
  showView(route.view, { updateHash: false, params: route.params, scroll: false });
  return route;
};

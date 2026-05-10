# Graph View Scalability Plan

## 1. Problem Statement

The current Ontology View is useful only as a smoke-test visualization. It draws all returned nodes into fixed ontology lanes. That breaks down when real projects have 100+ nodes, many pending edges, disconnected source items, duplicated concepts, and noisy evidence.

Graph View must become an investigation surface, not a decorative full graph.

Core requirement:

- show traceability structure without overwhelming the reviewer
- make missing links and orphan nodes obvious
- support 100+ nodes in dummy validation and later thousands through API-side filtering
- keep graph rendering independent from JIRA, Confluence, Email, MCP, or model provider details
- preserve approval/debug/evidence workflow context

## 2. Research Notes

React Flow remains a strong option for a future React implementation because it documents large graph performance tactics such as memoized components and rendering only visible elements. Its API includes `onlyRenderVisibleElements`, but that optimization has tradeoffs and should not replace data reduction.

Cytoscape.js is more graph-analysis oriented and has documented performance options for larger interactive graphs, including renderer hints such as hiding edges during pan/zoom. It is a better candidate if we later need advanced graph algorithms, compound nodes, and analysis-heavy interaction.

Dagre-style hierarchical layout fits MBSE traceability better than force-directed layout because requirements, architecture, design, verification, issues, and decisions have directional semantics. Force-directed graphs may be useful for local neighborhoods, but not as the default traceability view.

Decision for current repo stage:

- keep zero-build static UI for now
- move complexity into a graph projection API
- use SVG only for the current milestone
- design API contracts so React Flow or Cytoscape.js can replace the renderer later

References:

- React Flow performance: https://reactflow.dev/learn/advanced-use/performance
- React Flow `onlyRenderVisibleElements`: https://reactflow.dev/api-reference/react-flow
- Cytoscape.js performance guidance: https://js.cytoscape.org/index.html
- Dagre directed layout: https://github.com/dagrejs/dagre

## 3. Design Principles

### 3.1 Do Not Render The Whole Graph By Default

For 100+ nodes, the default should be `overview`, not `full`.

Modes:

| Mode | Purpose | Default Limit |
| --- | --- | --- |
| `overview` | show representative graph, risky/orphan/pending nodes first | 120 nodes |
| `neighborhood` | inspect 1-2 hop context around selected node | configurable |
| `orphans` | focus on disconnected or weakly connected nodes | 200 nodes |
| `pending` | review proposed graph changes before approval | 200 nodes |
| `full` | debug-only full projection | server-capped |

### 3.2 Orphans Are Findings, Not Visual Noise

Disconnected nodes must be visually distinct.

Required representation:

- warning border
- `orphan` badge in detail panel
- separate count in graph summary
- `orphans` mode
- optional orphan bucket/lane when the graph is large

Definition:

```text
is_orphan = approved_in_degree + approved_out_degree + pending_in_degree + pending_out_degree == 0
```

Later, this should be refined by ontology type. For example, top-level requirements may have no parent but should still require implementation and verification.

### 3.3 API Owns Graph Semantics

UI should not infer graph status by counting raw edges every time. The API must return view metadata.

Required node view fields:

```json
{
  "node_id": "node_RUNE_CAM_ALPHA_CAM_REQ_001",
  "node_type": "Requirement",
  "name": "4K60 latency shall be below 100 ms",
  "risk_level": "high",
  "approved_in_degree": 0,
  "approved_out_degree": 0,
  "pending_in_degree": 2,
  "pending_out_degree": 0,
  "finding_count": 1,
  "is_orphan": false,
  "has_pending_edges": true
}
```

Required graph projection fields:

```json
{
  "mode": "overview",
  "nodes": [],
  "approved_edges": [],
  "pending_edges": [],
  "edges": [],
  "groups": [],
  "counts": {
    "total_nodes": 150,
    "visible_nodes": 120,
    "orphan_nodes": 18,
    "pending_edges": 144,
    "approved_edges": 0,
    "findings": 52
  }
}
```

### 3.4 Layout Is A Product Contract

Default layout should be ontology lanes:

1. Requirement
2. Architecture / Component
3. Design / Decision / Risk
4. Verification / Issue
5. Orphan bucket when needed

This is intentionally not a generic network layout. MBSE review depends on direction and layer semantics.

### 3.5 Rendering Must Be Progressive

Initial target:

- 100-200 visible nodes with SVG
- API-side mode filtering
- no animation for large projections
- labels trimmed
- detail panel on click

Later target:

- React Flow with viewport rendering, minimap, edge toggles, search
- or Cytoscape.js if analysis operations dominate
- server-side graph projection from Neo4j

## 4. API Plan

### 4.1 Endpoint

```http
GET /api/v1/graph/projection?project_key=RUNE_CAM_ALPHA&mode=overview&center_node_id=...&hops=1&limit_nodes=120
```

Parameters:

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `project_key` | string | `RUNE_CAM_ALPHA` | project scope |
| `mode` | enum | `overview` | `overview`, `neighborhood`, `orphans`, `pending`, `full` |
| `center_node_id` | string | null | required by neighborhood for targeted view |
| `hops` | int | 1 | max 3 initially |
| `limit_nodes` | int | 120 | hard cap for SVG renderer |

### 4.2 Projection Service Responsibilities

- collect approved graph nodes/edges
- collect pending graph delta edges
- compute node degree
- attach finding count and risk level
- filter by mode
- cap visible nodes deterministically
- return stable summary counts

## 5. UI Plan

### Phase UI-1: Scalable SVG Contract

Implement immediately:

- Graph mode control
- node degree/status fields from API
- orphan highlighting
- pending/approved edge distinction
- large dummy fixture validation

### Phase UI-2: Search and Focus

Add:

- search by node name/id
- click node -> switch to neighborhood mode
- 1-hop / 2-hop toggle
- incoming/outgoing edge filters

### Phase UI-3: Review Workbench Overlay

Add:

- pending-only mode
- approval item linkage
- edge click detail
- finding severity filter
- graph delta preview before approval commit

### Phase UI-4: Renderer Migration Decision

Choose one:

- React Flow if app becomes React-based and review UI is component-heavy
- Cytoscape.js if graph analysis, compound nodes, and graph algorithms dominate
- Keep SVG only if graph view stays bounded and mode-filtered

## 6. Validation Plan

Dummy fixtures:

| Fixture | Purpose |
| --- | --- |
| `RUNE_CAM_ALPHA` | compact baseline |
| `RUNE_MULTI_SOURCE` | multi-source cross-link validation |
| `RUNE_SCALE_150` | 100+ node rendering and mode filtering |

Required checks:

- `overview` returns capped visible nodes and accurate total counts
- `orphans` returns disconnected nodes with `is_orphan=true`
- `pending` returns nodes attached to pending edges
- `neighborhood` returns only hop-limited local context
- UI remains usable after `RUNE_SCALE_150` run

## 7. Implementation Sequence

1. Add graph projection contract and projection service.
2. Add `RUNE_SCALE_150` dummy fixture.
3. Update graph API with mode parameters.
4. Update static UI with graph modes and orphan highlighting.
5. Add tests for projection counts, orphan status, and scale fixture.
6. Reassess renderer choice after real data shape is known.

## 8. Implemented Scope

Current implementation keeps the zero-build static UI but moves graph semantics into the API.

Implemented:

- `/api/v1/graph/projection` with `overview`, `neighborhood`, `orphans`, `pending`, and `full` modes
- API-side `search_query`, `edge_filter`, `center_node_id`, `hops`, and `limit_nodes`
- node metadata for approved/pending degree, finding count, risk level, orphan state, and pending-edge state
- edge metadata for source/target display names, pending/approved view status, and pending approval id
- scalable `RUNE_SCALE_150` fixture with 150 nodes, connected edges, orphan nodes, findings, and pending approvals
- UI controls for mode selection, node type filtering, search, hop count, edge filtering, zoom, pan, and reset
- node click detail with focus-neighborhood action
- edge click detail with approval id, evidence, confidence, source, target, and reasoning
- wider invisible SVG edge hit targets so graph edge click remains usable at large scale

Validated:

- contract test coverage for scale mode, orphan mode, pending mode, search, neighborhood, and pending edge metadata
- `RUNE_SCALE_150` API smoke with 150 nodes, 103 pending candidate edges, 47 findings, and 103 approval items
- browser smoke for 120-node overview, search result narrowing to one node, node detail, and edge detail click

Next renderer decision point:

- keep SVG while visible graph is capped under a few hundred nodes
- migrate to React Flow when the operator UI becomes component-heavy
- migrate to Cytoscape.js if graph algorithms, compound groups, and larger local analysis become first-class workflows

# Graph Relationship View Plan

이 문서는 `Ontology_graph_sample.jpg`가 의도한 관계 중심 graph view를 상용 dashboard에 반영하기 위한 별도 구현 계획이다. 기준 계획은 `PRODUCTION_EXECUTION_PLAN.md`와 `10_DASHBOARD_PRODUCTION_PLAN.md`이며, graph view는 승인 graph와 pending proposal을 동시에 관찰하되 둘을 시각적으로 구분해야 한다.

## 1. 현재 Gap

현재 `Traceability Workbench`의 SVG graph는 `Ontology Lane`에 가깝다.

- node type별 column에 배치되어 requirement -> architecture -> design -> verification 흐름을 빠르게 확인할 수 있다.
- 100개 이상 node에서 stage별 누락과 orphan을 파악하기 쉽다.
- 그러나 requirement 간 연결 관계, requirement와 다른 node type의 cross-link, hub node, isolated cluster를 직관적으로 보기 어렵다.

`Ontology_graph_sample.jpg`의 핵심 의도는 stage lane이 아니라 관계 topology다. 사용자는 특정 요구사항이 어떤 요구사항, 설계, 검증, 이슈와 연결되는지 공간적으로 파악해야 한다.

## 2. Target View Modes

상용 dashboard에는 projection mode와 layout mode를 분리한다.

### 2.1 Projection Mode

서버가 어떤 graph subset을 내려줄지 결정한다.

- `overview`: 운영자가 전체 상태를 빠르게 보는 기본 projection
- `pending`: 승인 대기 relation 중심 projection
- `orphans`: 연결 없는 node와 연결 취약 node 중심 projection
- `neighborhood`: 선택 node 기준 N-hop projection
- `full`: 검증용 full projection. 100개 이상 node에서는 검색/필터와 함께 사용한다.

### 2.2 Layout Mode

동일한 projection 데이터를 화면에서 어떻게 배치할지 결정한다.

- `Ontology Lane`: 기존 column/lane layout. node type과 traceability stage를 읽기 쉽다.
- `Relationship Graph`: 관계 중심 radial topology layout. hub, cluster, cross-link, disconnected island를 읽기 쉽다.
- `Requirement Neighborhood`: 선택된 requirement를 중심으로 1-hop/2-hop relation을 강조하는 specialized view. 초기 구현에서는 `neighborhood` projection + `Relationship Graph` layout 조합으로 제공하고, 이후 전용 evidence panel을 붙인다.

## 3. Relationship Graph Rendering Strategy

초기 구현은 외부 graph library 없이 deterministic SVG layout으로 진행한다. 이유는 다음과 같다.

- 현재 dashboard는 정적 FastAPI UI로 운영되고 있어 dependency blast radius가 작아야 한다.
- dummy fixture와 regression test에서 node 위치가 흔들리지 않아야 한다.
- node click, edge click, zoom, pan, reset은 이미 SVG control로 구현되어 있다.

배치 규칙:

- selected node가 있으면 center node로 사용한다.
- selected node가 없으면 degree가 높은 `Requirement`를 우선 center로 선택한다.
- 1-hop node는 inner ring, 2-hop node는 outer ring에 배치한다.
- 3-hop 이상 또는 disconnected cluster는 outer band에 배치한다.
- orphan node는 graph에서 숨기지 않고 별도 island band에 배치한다.
- approved edge는 solid line, pending proposal edge는 dashed amber line으로 표시한다.
- finding/pending/orphan 상태는 node stroke로 유지한다.

## 4. Scale Plan

`RUNE_SCALE_150` fixture를 기준으로 단계적으로 검증한다.

1. 30개 이하: 모든 node label 표시, node/edge click detail 검증
2. 100개 이상: 검색, node type filter, projection mode로 표시량 제어
3. 150개 이상: orphan island, pending edge 강조, zoom/pan/reset 회귀 검증
4. 300개 이상 후보: label thinning, edge bundling, Cytoscape.js 또는 WebGL renderer 도입 여부 재검토

초기 production 기준에서는 100개 이상 graph를 full view 하나로 억지로 읽히게 하지 않는다. 운영 workflow는 `overview -> search/filter -> Requirement Neighborhood -> approval/debug detail` 순서로 설계한다.

## 5. Implementation Steps

### Phase G1: Plan and Static Relationship Layout

- 이 문서를 추가한다.
- `Traceability Workbench`에 `Ontology Lane` / `Relationship Graph` layout toggle을 추가한다.
- `renderRelationshipGraph`와 `relationshipLayoutPositions`를 추가한다.
- 기존 projection API와 approval/debug contract는 변경하지 않는다.
- fixture 기반 UI smoke와 contract test를 업데이트한다.

### Phase G2: Requirement Neighborhood UX

- selected requirement를 center로 고정한다.
- N-hop selector와 search 결과가 같은 center selection을 공유하게 한다.
- node detail에 direct relation summary와 evidence count를 추가한다.
- edge detail에서 source evidence와 pending approval lineage를 더 빠르게 볼 수 있게 한다.

### Phase G3: 100+ Node 운영성

- `RUNE_SCALE_150` dummy data로 regression screenshot을 만든다.
- isolated cluster count, visible edge count, hidden-by-filter count를 workbench summary에 노출한다.
- label density와 edge opacity를 scale에 따라 조정한다.

### Phase G4: Renderer Decision Gate

다음 조건 중 2개 이상이 충족되면 dedicated graph library 도입을 검토한다.

- 300개 이상 node를 한 화면에서 반복 분석해야 한다.
- edge crossing을 layout algorithm으로 줄여야 한다.
- cluster collapse/expand가 핵심 workflow가 된다.
- graph edit interaction이 단순 proposal approval을 넘어선다.

후보:

- Cytoscape.js: graph topology, style rule, layout plugin에 강하다.
- React Flow: workflow diagram과 node editor에 강하지만 topology 분석 graph에는 상대적으로 부적합하다.
- Sigma.js/WebGL: very large graph에는 강하지만 dashboard 도입 비용이 크다.

## 6. Verification

필수 검증:

- `uv run pytest tests/contract/test_ui_route.py tests/unit/ops/test_operator_ui_smoke.py`
- `uv run python ops/ui/smoke_operator_ui.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy src`

시각 검증:

- `RUNE_CAM_ALPHA`에서 기본 overview와 neighborhood를 확인한다.
- `RUNE_SCALE_150`에서 100개 이상 node, orphan island, pending edge, zoom/pan/reset을 확인한다.
- node click 시 detail panel과 `Requirement Neighborhood` 흐름이 동작해야 한다.
- edge click 시 relation, confidence, approval status, evidence가 표시되어야 한다.

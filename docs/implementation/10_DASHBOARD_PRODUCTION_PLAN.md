# Dashboard Production Plan

## 1. Purpose

이 문서는 현재 local operator UI를 상용 수준의 dashboard/workbench로 올리기 위한
단계별 설계이다. 기준 source of truth는 `PRODUCTION_EXECUTION_PLAN.md`이며,
특히 Step 10 `Graph UI, Findings UI, Debug Workbench`와 Step 11 `Feedback Store와
Eval Gate`를 사용자 업무 화면으로 구체화한다.

현재 UI는 기능 확인용으로는 충분하지만, 상용 dashboard로는 부족하다.

- graph, approval, finding, debug, replay, eval, audit이 한 화면에 같은 무게로 나열된다.
- 사용자가 먼저 알아야 할 "지금 무엇을 처리해야 하는가"가 첫 화면에서 명확하지 않다.
- reviewer, operator, developer, admin의 업무 흐름이 분리되지 않았다.
- source freshness, run health, model/eval gate, approval backlog, high-risk finding이
  하나의 상황판으로 통합되지 않았다.
- 100개 이상 node graph를 보여줄 수는 있지만, 의사결정 중심으로 축약해서 보여주는
  dashboard 구조가 약하다.

목표는 graph 시각화를 더 크게 만드는 것이 아니라, 다음 질문에 빠르게 답하는
production control surface를 만드는 것이다.

1. 현재 traceability 상태는 정상인가?
2. 사람이 처리해야 할 가장 중요한 item은 무엇인가?
3. 어떤 source, run, model, prompt, rule 때문에 결과 품질이 흔들렸는가?
4. approval 없이 graph가 변경되지 않았는가?
5. 다음 action은 approve, reject, investigate, rerun, replay, eval 중 무엇인가?

## 2. Scope

### 2.1 In Scope

- dashboard-first information architecture
- role별 화면 구조와 navigation
- dashboard 전용 read model/API 설계
- work queue 중심 approval/finding/run/source/eval 통합
- graph workbench와 dashboard의 책임 분리
- debug/replay/eval entry point 정리
- dummy fixture 기반 검증 전략
- UI smoke 및 screenshot 검증 기준
- 단계별 구현 순서와 acceptance criteria

### 2.2 Out of Scope

- 실제 사내 JIRA, Confluence, Email 연결 검증
- SSO/OIDC provider 실연동
- React migration의 즉시 수행
- React Flow/Cytoscape.js 도입의 즉시 확정
- Grafana 운영 dashboard 대체

Grafana dashboard는 runtime/ops observability 용도이고, 이 문서의 dashboard는
application/product workflow dashboard이다. 둘은 보완 관계이며 서로 대체하지 않는다.

## 3. Product Principles

### 3.1 Dashboard Is Not A Full Graph

Dashboard는 전체 graph를 보여주는 화면이 아니다. Dashboard는 상태, 위험, 작업
우선순위, 최근 변화, gate 상태를 보여준다. 전체 graph 탐색은 Traceability Workbench로
분리한다.

### 3.2 Work Queue First

사용자는 대부분 "무엇을 처리해야 하는지"를 먼저 본다. 따라서 dashboard의 중심은
metric card가 아니라 prioritized work queue이다.

Work queue item 예:

```text
HIGH | missing_verification | CAM-REQ-002 has no approved verification
Action: inspect evidence / open neighborhood / acknowledge / create follow-up
```

### 3.3 Evidence And Debug Are One Click Away

각 dashboard item은 evidence, related graph neighborhood, approval lineage,
debug run trace로 이어져야 한다. 요약만 있고 원인을 확인할 수 없으면 production
dashboard가 아니다.

### 3.4 Role-Based Views

같은 데이터라도 role마다 필요한 첫 화면이 다르다.

| Role | Primary Question | Default View |
| --- | --- | --- |
| Reviewer | 내가 승인/거부/수정해야 할 proposal은 무엇인가? | Work Queue + Approval Detail |
| Operator | 시스템이 정상적으로 돌고 있고 backlog가 통제 가능한가? | Run/Source/Queue Health |
| Developer | agent가 어디서 틀렸고 재현 가능한가? | Debug Workbench |
| Admin | prompt/model/rule 변경이 안전하게 승격 가능한가? | Eval/Improvement Gate |
| Viewer | 현재 project traceability 상태는 어떤가? | Read-only Summary + Graph Preview |

### 3.5 Dummy Data Must Prove UX Shape

사내 데이터가 없어도 dashboard 품질은 검증 가능해야 한다. `RUNE_CAM_ALPHA`,
`RUNE_MULTI_SOURCE`, `RUNE_SCALE_150`, source export rehearsal fixture를 사용해
empty/normal/large/backlog/stale-like 상태를 재현한다.

## 4. Target Information Architecture

상용 UI는 하나의 긴 page가 아니라 다음 view로 나눈다.

```text
/
  Dashboard
  Work Queue
  Traceability Workbench
  Run Debug
  Source Health
  Eval & Improvement
  Admin
```

### 4.1 Dashboard

첫 화면. 사용자가 현재 상태와 최우선 action을 판단한다.

필수 영역:

- project/environment selector
- last updated / last run / next scheduled run
- health summary cards
- prioritized work queue
- critical/high finding summary
- approval backlog summary
- source freshness summary
- run health summary
- eval gate summary
- compact graph preview
- recent activity

### 4.2 Work Queue

approval, finding, source warning, failed run, eval regression candidate를 통합한다.

필수 기능:

- severity/risk/status/source/owner/type filter
- queue item detail drawer
- approve/reject/modify/hold/comment
- finding acknowledge/resolve/dismiss
- related evidence link
- graph neighborhood link
- debug trace link
- idempotent action handling

### 4.3 Traceability Workbench

graph 탐색과 evidence 기반 검토 화면이다. 기존 `07_GRAPH_VIEW_SCALABILITY_PLAN.md`의
graph projection 원칙을 따른다.

필수 기능:

- overview/risk/orphans/pending/neighborhood/full mode
- server-side projection
- selected node/edge detail
- evidence panel
- approval panel
- finding panel
- graph delta preview
- chain view

### 4.4 Run Debug

developer/operator가 agent run을 재현하고 stage별 실패를 조사한다.

필수 기능:

- run list
- step timeline
- input/output hash
- artifact refs
- prompt/model/retrieval context
- LLM request/response summary
- validation result
- graph delta preview
- replay diff

### 4.5 Source Health

JIRA/Confluence/Email/Decision Archive 연결 품질을 보여준다.

필수 기능:

- last successful sync
- cursor id
- artifact count
- source warnings
- stale threshold
- permission/filter warning
- masked/rejected artifact count
- source skill/export rehearsal status

### 4.6 Eval & Improvement

feedback 기반 개선 후보와 gate 상태를 보여준다.

필수 기능:

- feedback summary
- improvement candidates
- eval dataset candidates
- active/canary/review-required status
- rollback availability
- regression threshold result

### 4.7 Admin

초기 production release에서는 최소화한다.

필수 기능:

- model profile registry read
- prompt version registry read
- activation/rollback audit
- release readiness link

## 5. Dashboard Read Model

프론트엔드가 여러 endpoint를 조합해 dashboard 상태를 추론하지 않도록 dashboard 전용
read API를 만든다. 이 API는 이미 존재하는 run, approval, finding, feedback, graph,
source cursor, eval 데이터를 product-view에 맞게 요약한다.

### 5.1 Endpoint Set

```http
GET /api/v1/dashboard/summary?project_key=RUNE_CAM_ALPHA
GET /api/v1/dashboard/work-queue?project_key=RUNE_CAM_ALPHA&status=open&limit=50
GET /api/v1/dashboard/source-health?project_key=RUNE_CAM_ALPHA
GET /api/v1/dashboard/run-health?project_key=RUNE_CAM_ALPHA
GET /api/v1/dashboard/risk-summary?project_key=RUNE_CAM_ALPHA
GET /api/v1/dashboard/recent-activity?project_key=RUNE_CAM_ALPHA&limit=20
```

### 5.2 Summary Contract

```json
{
  "schema_version": "v1",
  "project_key": "RUNE_CAM_ALPHA",
  "generated_at": "2026-05-12T00:00:00Z",
  "traceability_health": "attention_required",
  "last_run": {
    "run_id": "run_123",
    "run_type": "analysis",
    "status": "succeeded",
    "completed_at": "2026-05-12T00:00:00Z"
  },
  "counts": {
    "total_nodes": 150,
    "approved_edges": 0,
    "pending_edges": 103,
    "orphan_nodes": 9,
    "open_findings": 48,
    "critical_findings": 0,
    "high_findings": 41,
    "pending_approvals": 103,
    "feedback_events": 0
  },
  "source_freshness": {
    "jira": "fresh",
    "confluence": "unknown",
    "decision_archive": "fresh",
    "email": "disabled"
  },
  "eval_gate": {
    "status": "blocked",
    "reason": "no reviewed production evidence"
  },
  "schedule": {
    "enabled": false,
    "last_run_id": null,
    "next_run_at": null
  }
}
```

### 5.3 Work Queue Contract

```json
{
  "schema_version": "v1",
  "items": [
    {
      "queue_id": "wq_finding_fdg_123",
      "item_type": "finding",
      "priority": "high",
      "status": "open",
      "title": "Requirement has no approved verification",
      "summary": "CAM-REQ-002 is not covered by an approved verification edge.",
      "project_key": "RUNE_CAM_ALPHA",
      "source_type": "dummy",
      "owner_role": "System Architect",
      "related_run_id": "run_123",
      "related_node_ids": ["node_RUNE_CAM_ALPHA_CAM_REQ_002"],
      "related_approval_id": null,
      "related_finding_id": "fdg_123",
      "evidence_refs": ["artifact://..."],
      "actions": ["inspect", "acknowledge", "open_graph", "open_debug"]
    }
  ],
  "counts": {
    "open": 25,
    "high": 12,
    "approval": 103,
    "finding": 47,
    "source_warning": 0,
    "failed_run": 0
  }
}
```

### 5.4 Source Health Contract

```json
{
  "schema_version": "v1",
  "sources": [
    {
      "source_type": "jira",
      "status": "fresh",
      "mode": "jira_export",
      "last_run_id": "run_jira_export",
      "cursor_id": "src_cursor_jira_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA",
      "artifact_count": 1,
      "warning_count": 0,
      "last_success_at": "2026-05-12T00:00:00Z",
      "stale_after_seconds": 86400
    }
  ]
}
```

### 5.5 Health Status Semantics

| Status | Meaning |
| --- | --- |
| `healthy` | no high-risk open work and latest run/source/eval state is acceptable |
| `attention_required` | high finding, approval backlog, stale source, or eval warning exists |
| `blocked` | release blocker, failed latest run, masking violation, or required gate failure |
| `unknown` | no run/source/eval evidence is available |

## 6. Frontend Structure

현재 zero-build static UI는 빠른 검증에 유리하다. 그러나 dashboard가 component-heavy가 되면
React migration을 검토해야 한다.

### 6.1 Near-Term Structure

초기에는 build system을 추가하지 않고 파일만 분리한다.

```text
src/req_tracker/ui/
  index.html
  styles.css
  app.js
  dashboard.js
  work_queue.js
  graph_workbench.js
  debug_workbench.js
  source_health.js
```

이 단계의 목적은 UI build 도구를 도입하는 것이 아니라 책임을 분리하는 것이다.

### 6.2 React Migration Decision Gate

다음 조건 중 2개 이상이 충족되면 React + React Flow migration을 검토한다.

- dashboard/workbench state가 static JS에서 유지보수하기 어려워진다.
- graph detail, approval drawer, evidence panel, debug panes가 재사용 component를 요구한다.
- browser screenshot test에서 layout regression이 잦아진다.
- role별 route/view guard가 복잡해진다.
- real graph에서 SVG renderer 한계가 명확해진다.

그 전까지는 API contract와 UX 구조를 먼저 안정화한다.

## 7. Visual Design Direction

상용 dashboard는 marketing page가 아니라 반복 사용 업무 도구이다.

디자인 원칙:

- dense but readable
- high information hierarchy
- muted enterprise palette
- first viewport에서 summary와 action queue를 동시에 노출
- graph는 첫 화면의 보조 preview로 제한
- 위험/상태 색상은 의미를 고정한다
- card를 과도하게 중첩하지 않는다
- long IDs와 long titles가 layout을 깨지 않게 한다
- mobile은 full feature보다 readable triage를 우선한다

권장 첫 화면 layout:

```text
Top Bar
  Project selector | Environment | Last updated | Run now | Refresh

Health Row
  Traceability Health | Pending Approvals | High Findings | Last Run | Source Health | Eval Gate

Main Row
  Work Queue                         | Risk / Coverage Snapshot
  Recent Critical Items              | Compact Graph Preview

Bottom Row
  Source Health Table                | Recent Activity
```

## 8. Implementation Phases

### Phase D1: Plan And Contract Freeze

목표: dashboard를 UI 추론이 아니라 read model contract로 고정한다.

작업:

1. `10_DASHBOARD_PRODUCTION_PLAN.md` 추가
2. dashboard endpoint contract 작성
3. Pydantic response model 초안 작성
4. fixture별 expected summary 작성
5. OpenAPI route 목록에 dashboard API 반영

산출물:

- dashboard production plan
- dashboard response models
- contract tests

검증:

```powershell
uv run pytest tests/contract/test_dashboard_api.py
uv run ruff check .
uv run mypy src
```

완료 기준:

- `RUNE_CAM_ALPHA`와 `RUNE_SCALE_150`에서 deterministic summary가 생성된다.
- empty state가 500 error 없이 `unknown` 상태로 표현된다.
- project authorization이 기존 API와 동일하게 적용된다.

### Phase D2: Dashboard Summary API

목표: 첫 화면에 필요한 상태를 API에서 한 번에 가져온다.

작업:

1. `src/req_tracker/dashboard/models.py` 추가
2. `src/req_tracker/dashboard/service.py` 추가
3. `src/req_tracker/api/routes/dashboard.py` 추가
4. app route 등록
5. source cursor, run, approval, finding, graph projection, eval gate 요약 연결

검증:

- latest run 없음
- ingestion-only run
- analysis run
- approval 후 pending count 감소
- `RUNE_SCALE_150` 150 node summary
- source export rehearsal 후 source health summary

완료 기준:

- frontend가 첫 화면 metric을 계산하지 않는다.
- dashboard API response가 schema version을 가진다.
- 모든 count는 기존 상세 endpoint와 모순되지 않는다.

### Phase D3: Work Queue API

목표: 사람이 처리해야 할 일을 하나의 queue로 통합한다.

작업:

1. finding -> work queue item 변환
2. pending approval -> work queue item 변환
3. failed run -> work queue item 변환
4. source warning/stale cursor -> work queue item 변환
5. eval gate warning -> work queue item 변환
6. priority sort 정책 구현

Priority sort:

```text
blocked release item
critical finding
high finding
stale/failed source
pending approval high risk
failed run
medium finding
normal approval
eval candidate
informational activity
```

검증:

- high finding이 normal approval보다 위에 온다.
- pending approval이 stale/rejected 상태와 섞이지 않는다.
- action 목록이 role과 item type에 맞게 나온다.

완료 기준:

- reviewer가 dashboard에서 바로 처리할 item을 찾을 수 있다.
- work queue item이 evidence/debug/graph 관련 id를 가진다.

### Phase D4: Dashboard-First UI

목표: `/` 첫 화면을 summary/work queue 중심으로 재구성한다.

작업:

1. current operator UI section을 view 단위로 분리
2. 첫 화면을 dashboard layout으로 교체
3. health row 구현
4. work queue panel 구현
5. compact graph preview 구현
6. recent activity/source health panel 구현
7. 기존 graph/debug/eval/audit section은 workbench view로 이동

검증:

- 0 data state
- `RUNE_CAM_ALPHA`
- `RUNE_SCALE_150`
- long title/long id
- approval action 후 count 갱신

완료 기준:

- 첫 viewport에서 핵심 상태와 최우선 action이 보인다.
- graph가 dashboard를 압도하지 않는다.
- 기존 approval/debug/replay 기능이 사라지지 않는다.

### Phase D5: Traceability Workbench Split

목표: graph view를 dashboard에서 분리하고 investigation surface로 만든다.

작업:

1. graph workbench route/view
2. left filter rail
3. center graph canvas
4. right node/edge/evidence panel
5. approval/finding/debug link
6. mode별 preset button

검증:

- overview/pending/orphans/neighborhood/full mode 유지
- node click detail 유지
- edge click detail 유지
- evidence와 approval id 노출 유지

완료 기준:

- dashboard는 summary, workbench는 investigation으로 책임이 분리된다.

### Phase D6: Debug And Eval Views

목표: developer/admin용 화면을 product dashboard에서 분리한다.

작업:

1. Run Debug view
2. LLM payload diff view
3. graph delta preview view
4. replay diff view
5. Eval & Improvement view
6. Admin registry read view

검증:

- developer 권한이 필요한 API는 viewer에게 보이지 않는다.
- replay diff와 graph delta preview가 기존 contract와 일치한다.

완료 기준:

- reviewer 화면과 developer debug 화면이 섞이지 않는다.
- model/prompt/rule 개선 후보가 eval gate와 연결되어 보인다.

### Phase D7: UI Quality Gate

목표: dashboard 품질을 release gate로 만든다.

작업:

1. 기존 `ops/ui/smoke_operator_ui.py`를 dashboard smoke로 확장
2. dashboard API smoke 추가
3. screenshot-based smoke 추가 검토
4. CI gate에 dashboard smoke 포함
5. README/MEMORY/current audit 갱신

검증 command:

```powershell
uv run python ops/ui/smoke_operator_ui.py
uv run pytest tests/contract/test_dashboard_api.py tests/unit/ops/test_operator_ui_smoke.py
uv run ruff check .
uv run mypy src
uv run pytest
```

완료 기준:

- CI에서 dashboard API와 UI asset smoke가 실행된다.
- 150-node fixture에서 dashboard가 usable state를 반환한다.
- 주요 UI control 누락이 smoke에서 잡힌다.

## 9. Dummy Fixture Coverage

| Fixture | Dashboard Purpose |
| --- | --- |
| `RUNE_CAM_ALPHA` | compact normal project, 10 nodes, findings, approvals |
| `RUNE_MULTI_SOURCE` | source diversity, Confluence/Email/Decision Archive shape |
| `RUNE_SCALE_150` | large graph, backlog, orphan summary, truncation |
| `RUNE_SECURITY` | restricted/masking/security finding path |
| source export rehearsal | JIRA/Confluence/decision-email source health without company systems |

추가로 필요한 synthetic states:

| State | Purpose |
| --- | --- |
| no runs | first install empty dashboard |
| ingestion-only | source exists but graph reasoning not yet run |
| failed run | run health blocked item |
| stale cursor | source health warning |
| approved edge present | approval count and graph status after reviewer action |
| rejected/modified approval | feedback/improvement queue path |

## 10. RBAC Requirements

| View | Minimum Role |
| --- | --- |
| Dashboard summary | viewer |
| Compact graph preview | viewer |
| Work queue read | developer |
| Approval decision | operator |
| Finding status update | operator |
| Run debug | developer |
| Source cursor/debug health | developer |
| Audit events | operator |
| Eval candidates | developer |
| Registry activation/rollback | admin |

Dashboard API must not bypass existing `require_project` and `require_role` rules.

## 11. Non-Negotiable Safety Rules

- dashboard must not show pending AI edges as approved graph edges
- approval action must use existing idempotency and stale guard
- dashboard summary must never infer approval by visual state alone
- source health must not expose secrets, tokens, MCP tool names, or internal endpoints
- debug views must respect raw artifact access policy
- masked/restricted data policy must remain enforced before model/debug display
- frontend must not own authorization decisions

## 12. Test Strategy

### 12.1 Contract Tests

Add:

```text
tests/contract/test_dashboard_api.py
```

Required cases:

- empty summary
- summary after `RUNE_CAM_ALPHA`
- summary after `RUNE_SCALE_150`
- work queue priority ordering
- source health after skill export rehearsal
- approval decision updates summary
- RBAC project filtering

### 12.2 Unit Tests

Add:

```text
tests/unit/dashboard/test_summary_service.py
tests/unit/dashboard/test_work_queue.py
```

Required cases:

- health status derivation
- priority sort
- stale source classification
- finding severity count
- eval gate status mapping

### 12.3 UI Smoke

Extend:

```text
ops/ui/smoke_operator_ui.py
tests/unit/ops/test_operator_ui_smoke.py
```

Required checks:

- dashboard static asset includes summary/work queue view hooks
- dashboard API returns first viewport data
- graph workbench controls remain present
- 150-node projection still passes
- dashboard does not require company endpoints

### 12.4 Visual Smoke

Preferred after dashboard-first UI lands:

- desktop 1440 x 900
- desktop 1920 x 1080
- tablet 1024 x 768
- mobile 390 x 844 sanity

Required visual assertions:

- no blank first viewport
- health row visible
- work queue visible
- no text overlap in cards/buttons
- graph preview does not dominate dashboard
- long id/title truncation does not break layout

## 13. Release Acceptance Criteria

Dashboard production uplift is complete when:

1. dashboard-first screen exists at `/`
2. dashboard summary API is covered by contract tests
3. work queue API combines findings, approvals, source warnings, failed runs, and eval items
4. graph workbench is separated from dashboard
5. debug workbench is separated from reviewer workflow
6. source health is visible without leaking secrets
7. `RUNE_SCALE_150` fixture validates large graph dashboard behavior
8. CI runs dashboard smoke
9. current audit document records dashboard readiness status
10. docs explain which company/staging UI checks remain manual

## 14. Backlog After First Dashboard Release

- React + React Flow migration decision
- saved dashboard filters
- per-user queue assignment
- SLA/age threshold configuration
- dashboard trend history
- source-specific drill-down pages
- graph clustering/grouping API
- browser screenshot baseline artifacts
- accessibility pass
- keyboard navigation for approval queue
- bulk review for supervised autonomy later phase

## 15. Recommended Next Implementation Slice

Do not start with a full frontend rewrite. Start with the read model.

Next slice:

1. Add `src/req_tracker/dashboard/models.py`
2. Add `src/req_tracker/dashboard/service.py`
3. Add `src/req_tracker/api/routes/dashboard.py`
4. Add `tests/contract/test_dashboard_api.py`
5. Add dashboard summary and work queue smoke to `ops/ui/smoke_operator_ui.py`
6. Then restructure `/` into dashboard-first layout

This keeps the blast radius low while correcting the product architecture.

## 16. Implemented Scope

Current local implementation has completed the first and second production dashboard
slices.

Implemented:

- `src/req_tracker/dashboard/models.py`
- `src/req_tracker/dashboard/service.py`
- `src/req_tracker/api/routes/dashboard.py`
- `/api/v1/dashboard/summary`
- `/api/v1/dashboard/work-queue`
- `/api/v1/dashboard/source-health`
- `/api/v1/dashboard/run-health`
- `/api/v1/dashboard/risk-summary`
- `/api/v1/dashboard/recent-activity`
- dashboard-first `/` layout with:
  - health summary row
  - prioritized work queue
  - risk snapshot
  - source health
  - run health
  - recent activity
  - compact graph preview
- static UI view split:
  - Dashboard
  - Work Queue
  - Traceability
  - Run Debug
  - Source Health
  - Eval
  - Admin
- work queue detail panel with item metadata, related run/approval/finding/node
  identifiers, evidence refs, available action display, graph/debug/source/eval
  routing, and approval approve/reject routing where applicable
- Work Queue operator controls:
  - type, priority, owner, and text filters
  - saved filter presets stored through backend user preference API with
    browser `localStorage` fallback
  - assignment state stored through backend work queue assignment API with
    browser `localStorage` fallback
  - assign-to-me and clear-assignment actions in the queue detail panel
  - filtered count display for the full queue view
- static JS split into focused browser modules:
  - `core.js`
  - `dashboard.js`
  - `work_queue.js`
  - `graph_workbench.js`
  - `debug_workbench.js`
  - `source_health.js`
- hash-based deep links:
  - `#dashboard`
  - `#work-queue?item=...`
  - `#traceability?node=...&mode=neighborhood`
  - `#debug?run=...`
  - `#source-health?source=...`
- source health detail view with source mode, cursor id, latest run, artifact
  count, warning count, stale threshold, and warning text
- run health detail view with recent run status and debug routing
- existing traceability graph/debug/eval/audit/admin functionality retained in
  separated views
- OpenAPI surface guard for dashboard routes
- RBAC alignment:
  - summary/run-health/risk-summary: viewer
  - work-queue/source-health: developer
  - recent-activity: operator

Validated:

- empty dashboard state returns `traceability_health=unknown`
- `RUNE_CAM_ALPHA` summary returns 10 nodes, 7 pending edges, 7 pending
  approvals, and 6 open findings
- `RUNE_SCALE_150` summary returns 150 nodes, 103 pending edges, 103 pending
  approvals, 48 findings, and 9 orphan nodes
- approval commit updates approved/pending dashboard counts
- source export adapter path appears in source health without company systems
- dashboard project/RBAC filtering is enforced
- operator UI smoke validates dashboard static hooks and dashboard read models
- focused dashboard UI 2 tests validate `data-app-view` hooks, work queue detail
  hooks, and source/run health detail hooks
- static UI module contract tests validate module asset serving and module
  entrypoint imports
- work queue static contract tests validate saved filter and local assignment
  hooks
- backend work queue preference and assignment API contract tests validate
  project/user scoping, idempotent assignment writes, assignment clearing, and
  SQLite restart restore
- operator UI smoke validates backend preference/assignment routes and UI
  module hooks
- Playwright CLI screenshot validates that `#work-queue?item=...` opens the
  selected work item detail view in a browser
- Playwright CLI screenshot validates that the dashboard view renders in a real
  browser viewport after `RUNE_SCALE_150` analysis

Next implementation slices:

1. Add browser screenshot smoke to CI once the local browser dependency policy is
   settled.
2. Reassess React + React Flow after real graph shape and reviewer workflow
   complexity are known.

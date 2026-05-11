# Module Design

## 1. 목표

이 문서는 `src/req_tracker/` 아래에 구현할 주요 module의 책임과 경계를 정의한다. 목표는 실제 데이터 없이 dummy data로 먼저 검증하더라도, 나중에 실제 JIRA/Confluence/model을 연결할 때 module 경계를 다시 뜯어고치지 않게 하는 것이다.

## 2. 최상위 패키지 구조

```text
src/req_tracker/
  adapters/
  api/
  approvals/
  audit/
  config/
  debug/
  evidence/
  feedback/
  findings/
  graph/
  ingestion/
  model_gateway/
  ontology/
  reasoning/
  workflows/
  vector/
  evals/
```

각 module은 아래 방향의 의존성만 허용한다.

```text
api -> services -> domain modules -> persistence abstractions
workflows -> domain modules -> persistence abstractions
domain modules -> contracts/models
persistence implementations -> external systems
```

금지:

- `reasoning`이 FastAPI request object를 import
- `findings`가 특정 Neo4j driver를 직접 import
- `adapters`가 approval commit을 직접 수행
- `model_gateway` 외부에서 model SDK를 직접 호출
- UI/API response model이 DB ORM model을 그대로 노출

## 3. Core Contracts Layer

권장 위치:

```text
src/req_tracker/ontology/models.py
src/req_tracker/debug/models.py
src/req_tracker/feedback/models.py
src/req_tracker/approvals/models.py
src/req_tracker/model_gateway/models.py
```

역할:

- `SourceArtifact`, `EvidenceSpan`
- `OntologyNode`, `TraceabilityEdge`, `Finding`
- `AgentRun`, `AgentStepTrace`, `LLMCallTrace`
- `ApprovalItem`, `GraphDelta`
- `FeedbackEvent`, `ImprovementCandidate`
- `ModelProfile`, `PromptVersion`, `RetrievalPolicy`

설계 규칙:

- Pydantic model은 API, workflow, tests에서 공통 사용한다.
- external source 원본 구조는 그대로 전파하지 않는다.
- 모든 id는 deterministic id 생성 정책을 가진다.
- schema version field를 둬서 dummy fixture와 migration test가 깨졌는지 확인할 수 있게 한다.

## 4. Config Module

권장 위치:

```text
src/req_tracker/config/settings.py
src/req_tracker/config/constants.py
src/req_tracker/config/logging.py
```

책임:

- 환경 변수 로딩
- datasource mode: `dummy`, `jira`
- graph backend mode: `memory`, `neo4j`
- vector mode: `memory`, `qdrant`
- model mode: `dummy`, `local`, `internal`, `external`
- data classification policy path
- debug artifact retention

초기 구현에서는 모든 외부 dependency를 dummy/in-memory fallback으로 실행 가능하게 둔다.

필수 설정 예시:

```text
REQ_TRACKER_ENV=local
DATASOURCE_MODE=dummy
GRAPH_BACKEND=memory
VECTOR_BACKEND=memory
MODEL_GATEWAY_MODE=dummy
ARTIFACT_STORE=local
```

## 5. Adapters Module

권장 위치:

```text
src/req_tracker/adapters/base.py
src/req_tracker/adapters/dummy/
src/req_tracker/adapters/jira/
src/req_tracker/adapters/confluence/
src/req_tracker/adapters/email/
```

Claude Code source skills:

```text
.claude/skills/rune-source-jira/
.claude/skills/rune-source-confluence/
.claude/skills/rune-source-email/
.claude/skills/rune-source-skill-pattern/
```

역할 분리:

- Claude Code skill: 사내 환경에서 source에 접근하는 절차, MCP/REST/export/dummy transport 선택, local configuration 규칙을 관리한다.
- Python adapter: 이미 접근 가능한 source payload를 production contract로 정규화하고 pipeline에 전달한다.
- Core workflow: source가 MCP인지 REST인지 알지 않는다.

핵심 interface:

```python
class SourceAdapter(Protocol):
    source_type: SourceType

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None,
    ) -> SourceFetchResult:
        ...
```

`SourceFetchResult`는 다음을 포함한다.

- `artifacts: list[RawSourceArtifact]`
- `next_cursor`
- `source_warnings`
- `partial_failure`
- `fetch_started_at`
- `fetch_completed_at`

Dummy adapter 요구:

- production JIRA connector와 같은 interface를 사용한다.
- deterministic fixture를 반환한다.
- pagination, deleted item, moved item, permission-denied item, malformed item을 옵션으로 재현할 수 있어야 한다.
- Claude Code source skill에서 export한 fixture와 같은 schema를 사용해야 한다.

POC 참고:

- POC의 `DummyAdapter`와 `RawDocument` 개념은 참고 가능하다.
- 다만 새 시스템에서는 `SourceArtifact`와 stage trace를 중심으로 다시 구현한다.

## 6. Ingestion Module

권장 위치:

```text
src/req_tracker/ingestion/sync.py
src/req_tracker/ingestion/normalization.py
src/req_tracker/ingestion/masking.py
src/req_tracker/ingestion/chunking.py
src/req_tracker/ingestion/classification.py
```

책임:

- raw source artifact를 normalized artifact로 변환
- content hash 계산
- data classification 부여
- PII/secret masking
- chunk 생성
- evidence span 생성
- vector upsert 요청 생성

중요:

- ingestion은 LLM 추론보다 재현성이 우선이다.
- 동일 raw snapshot, 동일 policy version이면 동일 masked artifact와 chunk set이 나와야 한다.
- masking violation은 분석 workflow를 중단시킬 수 있어야 한다.

## 7. Evidence Module

권장 위치:

```text
src/req_tracker/evidence/spans.py
src/req_tracker/evidence/hash.py
src/req_tracker/evidence/preview.py
```

책임:

- 원문 offset, section path, table cell ref를 evidence span으로 변환
- quote hash 생성
- UI/API용 preview 생성
- evidence가 raw artifact로 역추적 가능한지 검증

Dummy data에서도 evidence span은 생략하지 않는다. 실제 데이터 없이도 evidence-first 구조를 검증하기 위해서다.

## 8. Model Gateway Module

권장 위치:

```text
src/req_tracker/model_gateway/client.py
src/req_tracker/model_gateway/providers.py
src/req_tracker/model_gateway/policy.py
src/req_tracker/model_gateway/structured_output.py
src/req_tracker/model_gateway/dummy_provider.py
```

책임:

- model provider별 호출 방식 캡슐화
- model profile policy 검사
- prompt version 로딩
- structured output validation
- repair retry
- LLM call trace 저장
- dummy response fixture 실행

초기 provider:

- `DummyModelProvider`: JSON fixture를 반환하거나 오류 fixture를 재현
- `EchoModelProvider`: prompt와 input 일부를 deterministic output으로 변환
- 실제 provider는 후순위

핵심 원칙:

- `reasoning`, `workflows`, `api`는 Anthropic/OpenAI/내부 SDK를 직접 import하지 않는다.
- 모델 교체 검증을 위해 같은 prompt를 여러 model profile로 실행할 수 있어야 한다.

## 9. Reasoning Module

권장 위치:

```text
src/req_tracker/reasoning/extraction.py
src/req_tracker/reasoning/linking.py
src/req_tracker/reasoning/scoring.py
src/req_tracker/reasoning/prompts/
```

책임:

- candidate node extraction
- entity resolution 입력 생성
- candidate edge generation
- retrieval context 구성
- confidence/risk scoring
- counter-evidence 필드 구성

단계:

1. deterministic extraction: source type, labels, links, issue hierarchy 사용
2. dummy LLM extraction: fixture 기반 schema validation 검증
3. 실제 LLM extraction: model gateway 뒤에서만 연결

## 10. Ontology Module

권장 위치:

```text
src/req_tracker/ontology/models.py
src/req_tracker/ontology/normalization.py
src/req_tracker/ontology/resolver.py
src/req_tracker/ontology/id_factory.py
```

책임:

- node/edge type normalization
- deterministic id 생성
- duplicate node/edge 탐지
- merge/create decision 생성

Entity resolver 출력:

```text
ResolvedEntityOperation
  - operation: create | merge | ignore | needs_review
  - candidate_node_id
  - resolved_node_id
  - confidence_score
  - evidence
  - reasoning
```

## 11. Findings Module

권장 위치:

```text
src/req_tracker/findings/rules.py
src/req_tracker/findings/analyzer.py
src/req_tracker/findings/severity.py
```

Rule은 LLM 없이 동작해야 한다.

초기 rule:

- `REQ_WITHOUT_IMPLEMENTATION`
- `REQ_WITHOUT_VERIFICATION`
- `DESIGN_WITHOUT_PARENT`
- `ARCH_WITHOUT_VERIFICATION_PATH`
- `CONFLICTING_ALTERNATIVES`
- `ISSUE_AFFECTS_CRITICAL_REQUIREMENT`
- `STALE_TRACE_FROM_SOURCE_UPDATE`
- `WEAK_EVIDENCE`

각 finding은 반드시 다음을 가진다.

- `rule_id`
- `finding_type`
- `severity`
- affected nodes/edges
- graph path 또는 source evidence
- suggested action

## 12. Graph Module

권장 위치:

```text
src/req_tracker/graph/base.py
src/req_tracker/graph/memory_backend.py
src/req_tracker/graph/neo4j_backend.py
src/req_tracker/graph/projection.py
src/req_tracker/graph/delta.py
```

책임:

- approved graph query
- pending proposal과 approved graph 분리
- graph delta validation
- idempotent commit
- traceability chain query
- project-scoped subgraph query

초기 구현:

- `MemoryGraphBackend`로 contract와 rule을 검증한다.
- Neo4j는 같은 backend interface로 후속 구현한다.

주의:

- Memory backend는 POC의 NetworkX 아이디어를 참고할 수 있지만, 운영 계약은 `GraphBackend` interface가 기준이다.
- pending AI edge가 approved query에 섞이면 안 된다.

## 13. Approvals Module

권장 위치:

```text
src/req_tracker/approvals/models.py
src/req_tracker/approvals/service.py
src/req_tracker/approvals/routing.py
```

책임:

- approval item 생성
- owner/reviewer routing
- approve/reject/modify/hold 상태 전이
- stale item 감지
- graph delta preview 생성
- feedback event 생성

승인 상태 전이:

```text
pending -> approved
pending -> rejected
pending -> modified_approved
pending -> held
pending -> stale
held -> approved | rejected | modified_approved | stale
```

## 14. Debug Module

권장 위치:

```text
src/req_tracker/debug/traces.py
src/req_tracker/debug/artifacts.py
src/req_tracker/debug/replay.py
src/req_tracker/debug/diff.py
```

책임:

- `AgentRun`, `AgentStepTrace`, `LLMCallTrace` 기록
- stage output artifact 저장
- replay 입력 복원
- old/new stage output diff
- graph delta diff

Debug module은 첫 구현부터 필요하다. 나중에 붙이면 agent 품질 문제를 추적하기 어렵다.

## 15. Workflows Module

권장 위치:

```text
src/req_tracker/workflows/ingestion_graph.py
src/req_tracker/workflows/analysis_graph.py
src/req_tracker/workflows/approval_graph.py
src/req_tracker/workflows/replay_graph.py
src/req_tracker/workflows/improvement_graph.py
```

초기에는 LangGraph를 쓰지 않고 service 함수로 workflow shape를 검증해도 된다. 단, public workflow step 이름과 trace contract는 LangGraph 전환 후에도 유지한다.

필수 stage 이름:

- `source_fetch`
- `normalize`
- `mask`
- `chunk`
- `embed`
- `extract_nodes`
- `resolve_entities`
- `link_edges`
- `detect_findings`
- `enrich_reasoning`
- `stage_approval`
- `commit_graph_delta`
- `record_feedback`

## 16. API Module

권장 위치:

```text
src/req_tracker/api/app.py
src/req_tracker/api/routes/
src/req_tracker/api/schemas/
src/req_tracker/api/auth.py
```

초기 API group:

- `/api/v1/runs`
- `/api/v1/graph`
- `/api/v1/findings`
- `/api/v1/approvals`
- `/api/v1/feedback`
- `/api/v1/debug`
- `/api/v1/admin/model-profiles`
- `/api/v1/admin/prompt-versions`

API는 UI 전용 shortcut을 먼저 만들지 않는다. UI도 같은 API contract를 사용한다.

## 17. Eval Module

권장 위치:

```text
src/req_tracker/evals/datasets.py
src/req_tracker/evals/runner.py
src/req_tracker/evals/metrics.py
src/req_tracker/evals/reports.py
```

책임:

- dummy/golden dataset 로딩
- model/prompt comparison
- regression threshold 판단
- replay drift 계산
- eval report 생성

Eval은 실제 model 연결 전에도 dummy model fixture로 돌아야 한다.

# PRODUCTION_EXECUTION_PLAN: MBSE 기반 자율 개선형 Traceability Agent System

## 0. 문서의 역할

이 문서는 사내에서 사용할 MBSE 기반 자율형 traceability agent system의 단일 기준 문서이다. 이전 기획 문서는 혼선을 줄이기 위해 유지하지 않는다. 앞으로 개발, 리뷰, 구현 지시, 테스트 기준은 이 문서를 중심으로 맞춘다.

핵심 방향은 다음과 같다.

- 처음부터 완벽한 agent를 목표로 하지 않는다. 낮은 신뢰도의 초기 agent를 만들고, 사용자 피드백과 평가 데이터로 점진적으로 개선한다.
- 자체 모델, 사내 LLM, 외부 API 모델이 모두 가능하다는 전제로 model-agnostic gateway를 먼저 만든다.
- 모든 agent 판단은 단계별 중간 결과, 근거, prompt/model version, retrieval context, graph delta를 남겨 디버깅 가능해야 한다.
- AI 제안은 승인 전까지 운영 graph 원장에 반영하지 않는다.
- 자율 개선은 무통제 자동 변경이 아니라 feedback -> eval -> improvement candidate -> review -> canary -> release -> rollback 가능한 통제 루프이다.

## 1. 시스템 목표

사내 JIRA, Confluence, Email 또는 decision archive에 흩어진 요구사항, 아키텍처, 설계, 검증, 이슈, 의사결정 정보를 수집하여 MBSE 관점의 지식 그래프로 통합한다. Agent는 이 그래프 위에서 traceability chain, gap, conflict, 변경 영향 후보를 찾아내고 사용자의 승인과 수정을 통해 점진적으로 더 나은 추론 패턴을 갖게 된다.

### 1.1 핵심 사용자 가치

- 요구사항부터 설계, 구현, 검증까지 연결된 chain을 빠르게 확인한다.
- 누락된 검증, 고아 설계, 충돌 가능성이 있는 설계 대안, 변경 영향 범위를 조기에 발견한다.
- AI가 제안한 관계와 finding의 근거를 원문 evidence까지 추적한다.
- 사용자가 승인/수정/거부한 이력이 다음 분석 품질 개선에 반영된다.
- 모델이 바뀌어도 같은 입력에 대해 어느 단계에서 결과가 달라졌는지 비교할 수 있다.

### 1.2 운영 원칙

- Evidence first: node, edge, finding, answer는 반드시 원본 artifact 또는 graph 근거를 가진다.
- Human-in-the-loop: 신규 AI 추론 edge, high 이상 finding, 삭제/무효화 제안은 승인 전 pending 상태로 유지한다.
- Deterministic core: 권한, 승인 상태 전이, graph commit, audit, 기본 gap rule은 LLM이 아니라 코드와 DB constraint가 수행한다.
- Debuggable by design: agent workflow의 모든 단계는 저장 가능한 중간 산출물을 만든다.
- Model interchangeable: 모델 provider, model id, prompt version, structured output parser를 분리한다.
- Controlled self-improvement: 운영 prompt/rule/retrieval/scoring 변경은 평가와 리뷰를 통과한 버전만 활성화한다.

### 1.3 명시적 비범위

- 승인 없는 AI 자동 graph commit
- AI의 원본 JIRA/Confluence 자동 수정
- Email 전체 본문 무제한 수집
- 사용자 피드백을 즉시 운영 prompt에 반영하는 online self-mutation
- 근거 없는 요구사항/검증 항목 생성

## 2. 자율 개선형 Agent의 현실적 성숙도 모델

처음부터 높은 정확도를 기대하면 운영 시스템으로 실패하기 쉽다. 이 시스템은 agent autonomy를 단계적으로 올린다.

| Level | 이름 | Agent 역할 | 운영 반영 | 필요한 안전장치 |
| --- | --- | --- | --- | --- |
| L0 | Deterministic Baseline | JIRA link, issue type, rule 기반 graph 후보 생성 | 승인 후 반영 | schema, audit, idempotency |
| L1 | Assisted Suggestion | LLM이 node/edge/finding 후보와 reasoning 제안 | 승인 후 반영 | evidence, confidence, debug trace |
| L2 | Feedback-Aware | 사용자 승인/수정/거부 이력을 eval dataset으로 축적 | 변경 없음 | feedback taxonomy, eval gate |
| L3 | Controlled Improvement | prompt/rule/retrieval/scoring 개선 후보 생성 | reviewer 승인 후 canary | regression eval, rollback |
| L4 | Supervised Autonomy | 낮은 risk/high confidence 항목 bulk approval 지원 | 정책 범위 내 반영 | policy engine, sampling audit |

초기 상용 릴리스는 L1을 안정적으로 운영하고 L2 기반을 완성하는 것을 목표로 한다. L3는 실제 피드백 데이터가 충분히 쌓인 뒤 활성화한다. L4는 조직의 신뢰와 audit 지표가 확보된 뒤 제한적으로 검토한다.

## 3. 전체 아키텍처

```text
Source Systems
  ├─ JIRA
  ├─ Confluence
  └─ Email / Decision Archive

Connector Layer
  ├─ Source adapters
  ├─ Incremental sync cursor
  ├─ Raw snapshot store
  └─ Source permission mapping

Ingestion & Evidence Layer
  ├─ Normalizer
  ├─ PII / secret masking
  ├─ Chunker
  ├─ Evidence span builder
  └─ Embedding writer

Agent Workflow Layer
  ├─ LangGraph workflows
  ├─ Tool registry
  ├─ Model gateway
  ├─ Structured output validator
  ├─ Traceability linker
  ├─ Gap / conflict analyzer
  └─ Step result recorder

Human Review Layer
  ├─ Approval queue
  ├─ Graph delta preview
  ├─ Feedback capture
  └─ Reviewer routing

Persistence Layer
  ├─ PostgreSQL: runs, approvals, audit, feedback, policies
  ├─ Graph DB: approved traceability graph
  ├─ Vector DB: chunks, embeddings, semantic memory
  ├─ Object/File Store: raw snapshots, debug artifacts
  └─ Prompt/Model Registry

Service & UI Layer
  ├─ FastAPI
  ├─ React Flow graph UI
  ├─ Approval workbench
  ├─ Debug workbench
  ├─ Eval dashboard
  └─ Admin console

Observability Layer
  ├─ Structured logs
  ├─ OpenTelemetry traces
  ├─ Metrics
  └─ Replay tools
```

## 4. 기술 선택 기준

| 영역 | 권장 선택 | 이유 |
| --- | --- | --- |
| Language | Python 3.12+ | FastAPI, LangGraph, Pydantic 생태계와 운영 안정성 |
| Package Manager | uv | lock 기반 재현성과 빠른 설치 |
| API | FastAPI | OpenAPI contract, auth middleware, async job 연동 |
| Agent Workflow | LangGraph | 단계별 상태 저장, 분기, retry, replay 설계에 적합 |
| App DB | PostgreSQL | run, approval, feedback, audit, policy의 신뢰성 있는 저장 |
| Graph DB | Neo4j 우선 | 운영 성숙도, constraint, query tooling |
| Graph Algorithm Engine | Memgraph 후보 | 대규모 실시간 graph algorithm 필요 시 별도 검증 |
| Vector DB | Qdrant | metadata filtering, on-prem 운영, embedding version 관리 |
| LLM Gateway | LiteLLM 또는 사내 gateway wrapper | 자체 모델/외부 모델 교체, 공통 logging과 policy 적용 |
| Structured Output | Pydantic + Instructor | LLM output validation, retry, schema evolution |
| UI | React + React Flow | 복잡한 graph 조작, delta preview, debug UI 구현 |
| Auth | OIDC/SAML SSO | 사내 계정과 group 기반 RBAC |
| Observability | OpenTelemetry + Prometheus/Grafana | run/step/model call 추적 |

## 5. Model-Agnostic 설계

사내 환경에서는 자체 모델, 폐쇄망 모델, 외부 API 모델이 바뀔 수 있다. 따라서 agent 코드는 특정 모델 SDK에 직접 결합하지 않는다.

### 5.1 Model Gateway 책임

- model provider별 호출 방식 캡슐화
- prompt template과 model parameter 분리
- 모델별 허용 데이터 등급 검사
- request/response metadata logging
- timeout, retry, rate limit, fallback 처리
- structured output validation과 repair retry
- cost/token/latency metric 수집
- 동일 입력에 대해 모델별 비교 실행 지원

### 5.2 ModelProfile

```python
class ModelProfile(BaseModel):
    model_profile_id: str
    provider: Literal["internal", "openai", "anthropic", "azure", "local"]
    model_name: str
    endpoint_alias: str
    allowed_data_classes: list[str]
    supports_json_schema: bool
    supports_tool_calling: bool
    max_context_tokens: int
    default_temperature: float
    timeout_seconds: int
    is_active: bool
```

### 5.3 PromptVersion

```python
class PromptVersion(BaseModel):
    prompt_version_id: str
    task_name: Literal[
        "node_extraction",
        "edge_linking",
        "finding_reasoning",
        "impact_analysis",
        "answer_generation",
    ]
    template: str
    schema_version: str
    retrieval_policy_id: str
    created_by: str
    created_at: datetime
    status: Literal["draft", "eval_ready", "canary", "active", "retired"]
```

### 5.4 모델 교체 시 필수 비교

모델 변경은 다음 결과를 비교해야 한다.

- node extraction 개수와 type 분포
- edge suggestion precision
- finding severity 분포
- structured output validation failure rate
- latency와 timeout rate
- token/cost 지표
- reviewer reject/modify rate
- masking policy 위반 여부

## 6. 단계별 중간 결과 계약

디버깅 가능한 agent를 만들려면 각 단계가 사람이 확인할 수 있는 산출물을 남겨야 한다.

| Stage | 입력 | 출력 | 디버그 확인 포인트 |
| --- | --- | --- | --- |
| S1 Source Fetch | source config, cursor | raw artifact snapshot | 누락 ticket, 권한 오류, cursor |
| S2 Normalize | raw artifact | normalized artifact | field mapping, content hash |
| S3 Mask | normalized artifact | masked artifact | masking rule, redaction count |
| S4 Chunk | masked artifact | chunks | chunk boundary, section path |
| S5 Embed | chunks | vector records | embedding model/version, metadata |
| S6 Extract Nodes | chunks, source fields | candidate nodes | prompt, raw output, parsed output, evidence |
| S7 Resolve Entities | candidate nodes, graph | resolved node operations | merge/create decision, similarity score |
| S8 Link Edges | nodes, graph, retrieval | candidate edges | retrieval context, relation score |
| S9 Detect Findings | graph projection, candidates | findings | rule id, graph path, severity reason |
| S10 Enrich Reasoning | candidates, findings | reasoning text, confidence | model id, prompt version, counter-evidence |
| S11 Stage Approval | scored proposals | approval items | owner routing, risk level |
| S12 Commit | approval decision | graph delta | before/after, idempotency key |
| S13 Feedback | user decision | feedback events | reason code, correction text |

각 stage output은 `run_id`, `step_id`, `input_hash`, `output_hash`, `schema_version`, `created_at`을 가져야 한다.

## 7. 핵심 데이터 모델

### 7.1 SourceArtifact

```python
class SourceArtifact(BaseModel):
    artifact_id: str
    source_type: Literal["jira", "confluence", "email", "decision_archive"]
    source_url: str
    external_id: str
    project_key: str
    title: str
    body_text_ref: str
    author_id: str | None
    created_at: datetime
    updated_at: datetime
    ingested_at: datetime
    content_hash: str
    access_scope: list[str]
    data_classification: Literal["public_internal", "restricted", "confidential", "no_external_llm"]
```

### 7.2 EvidenceSpan

```python
class EvidenceSpan(BaseModel):
    artifact_id: str
    source_url: str
    quote_hash: str
    extracted_text_preview: str
    start_offset: int | None = None
    end_offset: int | None = None
    section_path: str | None = None
    table_cell_ref: str | None = None
```

### 7.3 OntologyNode

```python
class OntologyNode(BaseModel):
    node_id: str
    node_type: Literal[
        "Requirement",
        "Architecture_Block",
        "Design_Spec",
        "Verification",
        "Issue",
        "Decision",
        "Component",
        "Risk",
    ]
    name: str
    description: str
    project_key: str
    domain: str | None = None
    lifecycle_state: Literal["draft", "active", "deprecated", "superseded"] = "active"
    source_artifact_ids: list[str]
    evidence: list[EvidenceSpan]
    created_by: Literal["source", "ai", "human"]
    confidence_score: float
    version: int
```

### 7.4 TraceabilityEdge

```python
class TraceabilityEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation: Literal[
        "satisfies",
        "verifies",
        "derives",
        "implements",
        "affects",
        "blocks",
        "conflicts_with",
        "supersedes",
        "decides",
    ]
    reasoning: str
    evidence: list[EvidenceSpan]
    is_inferred: bool
    confidence_score: float
    approval_status: Literal["pending", "approved", "rejected", "modified", "expired"]
    approved_by: str | None = None
    approved_at: datetime | None = None
    version: int
```

### 7.5 Finding

```python
class Finding(BaseModel):
    finding_id: str
    finding_type: Literal[
        "orphan_node",
        "missing_verification",
        "missing_implementation",
        "conflict",
        "cross_domain_hidden",
        "stale_trace",
        "weak_evidence",
        "policy_violation",
    ]
    severity: Literal["critical", "high", "medium", "low"]
    affected_node_ids: list[str]
    affected_edge_ids: list[str]
    description: str
    suggested_action: str
    evidence: list[EvidenceSpan]
    detection_method: Literal["rule", "llm", "hybrid"]
    approval_status: Literal["open", "acknowledged", "resolved", "dismissed"]
```

### 7.6 AgentRun

```python
class AgentRun(BaseModel):
    run_id: str
    run_type: Literal["ingestion", "analysis", "approval_commit", "eval", "replay", "improvement"]
    project_key: str
    triggered_by: str
    trigger_source: Literal["manual", "schedule", "api", "system"]
    status: Literal["queued", "running", "succeeded", "failed", "cancelled", "partial"]
    model_profile_id: str | None
    prompt_version_ids: list[str]
    input_snapshot_ids: list[str]
    started_at: datetime
    completed_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None
```

### 7.7 AgentStepTrace

```python
class AgentStepTrace(BaseModel):
    step_id: str
    run_id: str
    stage_name: str
    status: Literal["running", "succeeded", "failed", "skipped"]
    input_hash: str
    output_hash: str | None
    output_ref: str | None
    started_at: datetime
    completed_at: datetime | None
    retry_count: int
    error_class: str | None = None
    error_message: str | None = None
```

### 7.8 LLMCallTrace

```python
class LLMCallTrace(BaseModel):
    llm_call_id: str
    run_id: str
    step_id: str
    model_profile_id: str
    prompt_version_id: str
    request_hash: str
    response_hash: str | None
    masked_payload_ref: str
    raw_response_ref: str | None
    parsed_output_ref: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    validation_status: Literal["not_applicable", "passed", "failed", "repaired"]
    retry_count: int
    error_message: str | None = None
```

### 7.9 FeedbackEvent

```python
class FeedbackEvent(BaseModel):
    feedback_id: str
    target_type: Literal["node", "edge", "finding", "answer", "run_step"]
    target_id: str
    action: Literal["approved", "rejected", "modified", "commented", "marked_low_quality"]
    user_id: str
    user_role: str
    reason_code: Literal[
        "wrong_relation",
        "weak_evidence",
        "wrong_node_type",
        "duplicate",
        "missing_context",
        "wrong_severity",
        "security_concern",
        "other",
    ] | None
    correction_text: str | None
    created_at: datetime
    model_profile_id: str | None
    prompt_version_id: str | None
```

### 7.10 ImprovementCandidate

```python
class ImprovementCandidate(BaseModel):
    candidate_id: str
    candidate_type: Literal["prompt", "rule", "retrieval_policy", "scoring_threshold", "model_profile"]
    source_feedback_ids: list[str]
    proposed_change_summary: str
    before_version_id: str
    after_version_ref: str
    eval_run_id: str | None
    status: Literal["draft", "eval_running", "review_ready", "approved", "rejected", "canary", "active", "rolled_back"]
    created_at: datetime
    reviewed_by: str | None = None
```

## 8. LangGraph Workflow 설계

### 8.1 Ingestion Workflow

```text
START
  -> load_source_policy
  -> fetch_incremental_artifacts
  -> persist_raw_snapshot
  -> normalize_artifacts
  -> classify_data
  -> mask_sensitive_data
  -> build_evidence_spans
  -> chunk_artifacts
  -> embed_chunks
  -> record_stage_outputs
END
```

중요한 점은 ingestion 단계에서 분석 품질보다 재현성을 우선한다는 것이다. 같은 snapshot과 같은 policy version이면 같은 masked artifact와 chunk set을 다시 만들 수 있어야 한다.

### 8.2 Analysis Workflow

```text
START
  -> select_ready_artifacts
  -> load_existing_graph_projection
  -> extract_candidate_nodes
  -> validate_node_schema
  -> resolve_entities
  -> retrieve_related_context
  -> generate_candidate_edges
  -> validate_edge_schema
  -> run_graph_rules
  -> generate_findings
  -> enrich_reasoning_with_llm
  -> score_confidence_and_risk
  -> stage_approval_items
  -> record_run_summary
END
```

LLM 호출이 실패해도 가능한 deterministic 결과는 보존한다. 예를 들어 JIRA link 기반 edge는 생성하되, reasoning enrichment가 실패하면 해당 proposal을 `needs_reasoning_retry` 상태로 둔다.

### 8.3 Approval Commit Workflow

```text
START
  -> validate_reviewer_permission
  -> validate_approval_item_version
  -> apply_reviewer_modification
  -> build_graph_delta
  -> validate_graph_constraints
  -> commit_approved_delta
  -> write_feedback_event
  -> refresh_dependent_findings
  -> write_audit_event
END
```

승인 item은 optimistic locking을 사용한다. 검토 중 원본 artifact, graph node, edge, prompt version이 바뀌면 stale 상태로 전환하고 재분석을 요구한다.

### 8.4 Debug Replay Workflow

```text
START
  -> select_previous_run
  -> load_input_snapshot
  -> load_prompt_and_model_profile
  -> choose_replay_mode
       ├─ same_model_same_prompt
       ├─ new_model_same_prompt
       ├─ same_model_new_prompt
       └─ new_model_new_prompt
  -> execute_selected_steps
  -> compare_stage_outputs
  -> compare_graph_delta
  -> write_replay_report
END
```

Replay는 모델 교체, prompt 변경, bug fix 이후 품질 차이를 확인하는 핵심 기능이다.

### 8.5 Self-Improvement Workflow

```text
START
  -> collect_feedback_events
  -> group_feedback_by_failure_pattern
  -> build_or_update_eval_dataset
  -> propose_improvement_candidate
  -> run_regression_eval
  -> run_security_eval
  -> human_review_candidate
  -> canary_activate
  -> monitor_canary_metrics
  -> promote_or_rollback
END
```

이 workflow는 운영 graph를 직접 수정하지 않는다. prompt, rule, retrieval policy, scoring threshold, model profile 개선 후보를 만들고, 평가와 리뷰를 거친 뒤 활성화한다.

## 9. Debuggability 필수 요구사항

이 시스템은 agent가 틀릴 것을 전제로 설계한다. 따라서 "왜 틀렸는지"를 빠르게 찾을 수 있어야 한다.

### 9.1 Run Debug 화면에서 보여야 할 것

- run status, trigger, project, source snapshot
- stage별 성공/실패/skip 상태
- 각 stage의 input/output hash와 schema version
- masked payload preview
- retrieval query와 top-k context
- LLM prompt version, model profile, raw response, parsed output
- structured output validation error
- retry/repair 횟수
- candidate node/edge/finding 목록
- confidence 산정 근거
- graph delta preview
- approval item 연결
- feedback event 연결

### 9.2 디버그 API

| Method | Path | 목적 |
| --- | --- | --- |
| `GET` | `/api/v1/runs` | run 목록과 상태 조회 |
| `GET` | `/api/v1/runs/{run_id}` | run summary |
| `GET` | `/api/v1/runs/{run_id}/steps` | stage별 trace |
| `GET` | `/api/v1/runs/{run_id}/llm-calls` | 모델 호출 이력 |
| `GET` | `/api/v1/runs/{run_id}/artifacts` | 중간 산출물 목록 |
| `GET` | `/api/v1/runs/{run_id}/graph-delta` | graph 변경 후보 |
| `POST` | `/api/v1/runs/{run_id}/replay` | replay 실행 |
| `GET` | `/api/v1/replays/{replay_id}/diff` | replay 비교 결과 |
| `GET` | `/api/v1/debug/approvals/{approval_id}/lineage` | approval 생성 경로 |

### 9.3 오류 분류

| Error Class | 예시 | 처리 |
| --- | --- | --- |
| `SOURCE_AUTH_ERROR` | JIRA 권한 부족 | run failed, admin action 필요 |
| `SOURCE_RATE_LIMIT` | API rate limit | backoff retry |
| `MASKING_POLICY_VIOLATION` | 금지 데이터 미마스킹 | 분석 중단, security review |
| `LLM_TIMEOUT` | 모델 응답 지연 | retry/fallback |
| `STRUCTURED_OUTPUT_INVALID` | schema validation 실패 | repair retry, 실패 시 manual review |
| `RETRIEVAL_EMPTY` | 관련 context 없음 | 낮은 confidence로 진행 또는 skip |
| `GRAPH_CONSTRAINT_ERROR` | 중복 edge, 잘못된 relation | commit 차단 |
| `APPROVAL_STALE` | 검토 중 원본 변경 | 재분석 요구 |

### 9.4 비교 디버깅

모델 또는 prompt 변경 시 다음 diff를 자동 생성한다.

- extracted node diff
- resolved entity diff
- candidate edge diff
- finding diff
- severity diff
- confidence diff
- approval routing diff
- final graph delta diff

이 diff는 reviewer가 "새 모델이 더 좋아졌는지"를 정성/정량으로 판단하는 근거가 된다.

## 10. Feedback 기반 개선 설계

### 10.1 피드백 수집 위치

피드백은 UI 버튼 하나가 아니라 여러 작업에서 자연스럽게 발생해야 한다.

- edge approve/reject/modify
- finding acknowledge/dismiss/resolve
- node type correction
- duplicate merge correction
- severity correction
- evidence 부족 표시
- answer 품질 낮음 표시
- run step 실패에 대한 admin annotation

### 10.2 피드백 taxonomy

| Reason Code | 의미 | 개선 대상 |
| --- | --- | --- |
| `wrong_relation` | relation type 또는 방향이 틀림 | edge linker, prompt |
| `weak_evidence` | 근거가 부족함 | retrieval policy, evidence builder |
| `wrong_node_type` | node type 분류 오류 | node extraction prompt/rule |
| `duplicate` | 중복 node/edge 생성 | entity resolver |
| `missing_context` | 중요한 source를 못 찾음 | connector, retrieval |
| `wrong_severity` | finding 심각도 오류 | scoring rule |
| `security_concern` | 민감 데이터 처리 우려 | masking/policy |
| `other` | reviewer free text 필요 | manual triage |

### 10.3 개선 후보 생성 방식

피드백이 쌓이면 시스템은 다음 후보를 만든다.

- prompt wording 변경
- few-shot example 추가/삭제
- graph rule 추가/수정
- retrieval top-k, filter, reranking 변경
- confidence threshold 조정
- model profile 변경
- ontology normalization rule 추가

중요한 제한:

- feedback 1건으로 즉시 운영 동작을 바꾸지 않는다.
- 변경 후보는 eval dataset으로 회귀 테스트한다.
- security eval을 통과하지 못하면 활성화하지 않는다.
- canary 결과가 나쁘면 자동 rollback한다.

### 10.4 Eval Dataset 구성

```text
eval_datasets/
  node_extraction/
    approved_nodes.jsonl
    rejected_nodes.jsonl
  edge_linking/
    approved_edges.jsonl
    modified_edges.jsonl
    rejected_edges.jsonl
  findings/
    useful_findings.jsonl
    dismissed_findings.jsonl
  security/
    masking_cases.jsonl
  replay/
    representative_runs.jsonl
```

### 10.5 품질 지표

| Metric | 의미 |
| --- | --- |
| Edge Approval Precision | 제안 edge 중 승인 또는 수정 승인된 비율 |
| Edge Modification Rate | 제안 edge 중 사용자가 수정한 비율 |
| Finding Useful Rate | finding 중 acknowledged/resolved 비율 |
| False Positive Rate | reject/dismiss 비율 |
| Evidence Sufficiency Rate | weak_evidence 피드백이 없는 비율 |
| Structured Output Failure Rate | schema validation 실패율 |
| Replay Drift | 같은 입력에서 버전 변경으로 달라진 결과 비율 |
| Masking Violation Count | 보안상 릴리스 차단 지표 |

## 11. API 설계

### 11.1 Read API

| Method | Path | 목적 |
| --- | --- | --- |
| `GET` | `/api/v1/projects` | 접근 가능한 프로젝트 |
| `GET` | `/api/v1/graph/nodes` | node 목록 |
| `GET` | `/api/v1/graph/edges` | edge 목록 |
| `GET` | `/api/v1/graph/subgraph` | 특정 node 주변 graph |
| `GET` | `/api/v1/traceability/chain/{node_id}` | traceability chain |
| `GET` | `/api/v1/findings` | finding 목록 |
| `GET` | `/api/v1/findings/{finding_id}` | finding 상세 |
| `GET` | `/api/v1/approvals` | 승인 대기 목록 |
| `GET` | `/api/v1/audit/events` | 감사 이벤트 |

### 11.2 Command API

| Method | Path | 목적 |
| --- | --- | --- |
| `POST` | `/api/v1/runs/ingest` | source 수집 시작 |
| `POST` | `/api/v1/runs/analyze` | 분석 시작 |
| `POST` | `/api/v1/approvals/{approval_id}/decision` | 승인/수정/거부 |
| `POST` | `/api/v1/findings/{finding_id}/status` | finding 상태 변경 |
| `POST` | `/api/v1/feedback` | 명시적 피드백 기록 |
| `POST` | `/api/v1/admin/prompt-versions/{id}/activate` | prompt version 활성화 |
| `POST` | `/api/v1/admin/model-profiles/{id}/activate` | model profile 활성화 |

Command API는 idempotency key를 지원해야 한다.

## 12. Repository 구조

```text
src/req_tracker/
  adapters/
    jira/
    confluence/
    email/
  api/
    routes/
    schemas/
    auth.py
  approvals/
  audit/
  config/
  debug/
    traces.py
    replay.py
    diff.py
  evidence/
  feedback/
  findings/
    rules.py
    analyzer.py
  graph/
    backend.py
    neo4j_backend.py
    queries/
  ingestion/
    chunking.py
    masking.py
    normalization.py
    sync.py
  model_gateway/
    profiles.py
    client.py
    policy.py
    structured_output.py
  ontology/
    models.py
    resolver.py
  reasoning/
    prompts/
    extraction.py
    linking.py
    scoring.py
  workflows/
    ingestion_graph.py
    analysis_graph.py
    approval_graph.py
    replay_graph.py
    improvement_graph.py
  vector/
  evals/
  ui/
tests/
  contract/
  integration/
  evals/
  security/
  replay/
docs/
  api/
  ontology/
  security/
  runbooks/
ops/
  docker-compose.local.yml
  migrations/
  helm/
```

## 13. 단계별 개발 계획

### Step 1. 단일 기준 문서와 운영 정책 확정

목표: 개발 전 ontology, 데이터 정책, 승인 정책, 모델 정책을 고정한다.

작업:

- node/edge ontology v1 확정
- 데이터 등급과 모델 전송 허용 범위 정의
- approval 권한 matrix 정의
- audit retention과 raw snapshot retention 정의
- model profile 운영 정책 정의
- feedback reason code 확정

산출물:

- `docs/ontology/ONTOLOGY_V1.md`
- `docs/security/DATA_POLICY.md`
- `docs/security/RBAC_MATRIX.md`
- `docs/runbooks/MODEL_POLICY.md`

완료 기준:

- 어떤 데이터가 어떤 모델로 갈 수 있는지 명확하다.
- 승인 전 AI 제안이 운영 graph에 반영되지 않는 정책이 명확하다.
- feedback이 어떤 개선 대상으로 연결되는지 reason code가 정의되어 있다.

### Step 2. 공통 계약, API skeleton, CI 구축

목표: 모든 기능이 같은 Pydantic schema와 test gate 위에서 개발되게 한다.

작업:

- `uv` 기반 Python 프로젝트 구성
- FastAPI skeleton 작성
- Pydantic 모델 구현
- OpenAPI schema 생성
- lint/type check/unit test CI 구성
- correlation id, run id logging middleware 구현

완료 기준:

- API server가 local에서 실행된다.
- schema 변경 시 contract test가 실패한다.
- 모든 request log에 correlation id와 user id가 남는다.

### Step 3. Model Gateway와 Debug Trace 기반 먼저 구현

목표: agent 기능을 만들기 전에 모델 호출과 디버깅 기반을 먼저 만든다.

작업:

- `ModelProfile`, `PromptVersion`, `LLMCallTrace` 구현
- provider wrapper interface 구현
- masked payload logging
- structured output validation과 retry
- prompt/model version registry
- run/step trace 저장
- replay skeleton 구현

완료 기준:

- 동일 prompt를 두 모델에 실행해 결과와 latency를 비교할 수 있다.
- LLM 호출 실패와 schema validation 실패가 trace에 남는다.
- debug API로 raw response와 parsed output을 조회할 수 있다.

### Step 4. Persistence Layer 구축

목표: app state, graph, vector, debug artifact를 분리 저장한다.

작업:

- PostgreSQL schema: runs, steps, llm_calls, artifacts, approvals, feedback, audit
- Neo4j constraint와 index
- Qdrant collection과 embedding metadata
- object/file store abstraction
- migration과 rollback strategy

완료 기준:

- run 하나의 모든 stage output이 추적 가능하다.
- graph commit은 idempotent하다.
- debug artifact가 원본 artifact와 연결된다.

### Step 5. JIRA Production Connector

목표: 실제 JIRA 데이터를 incremental하게 수집한다.

작업:

- JIRA auth 방식 구현
- JQL 기반 project/component/release scope
- pagination, retry, rate limit 처리
- issue, link, comment, history 수집
- sync cursor와 content hash 저장
- permission mapping

완료 기준:

- 같은 sync를 재실행해도 중복 artifact가 생기지 않는다.
- 권한 오류, rate limit, partial failure가 명확히 기록된다.
- source snapshot을 기준으로 replay 가능한 입력이 저장된다.

### Step 6. Ingestion, Masking, Evidence Pipeline

목표: 원본 데이터를 안전하고 재현 가능한 분석 입력으로 만든다.

작업:

- source artifact normalization
- data classification
- PII/secret masking
- chunking
- evidence span 생성
- embedding upsert
- stage output 저장

완료 기준:

- LLM payload에는 금지 데이터가 포함되지 않는다.
- 모든 chunk와 evidence는 원본 source로 역추적 가능하다.
- masking violation은 분석을 차단하고 security review로 보낸다.

### Step 7. Deterministic Traceability Baseline

목표: LLM 없이도 최소한의 graph 후보와 gap rule을 동작시킨다.

작업:

- JIRA issue type, labels, components 기반 node 후보 생성
- JIRA link 기반 edge 후보 생성
- 기본 entity resolver
- 기본 graph rules:
  - requirement without implementation
  - requirement without verification
  - design without parent requirement
  - architecture without verification path
  - conflicting alternatives
  - issue affects critical requirement

완료 기준:

- LLM 장애 상황에서도 baseline findings를 생성한다.
- rule id와 graph path가 finding에 기록된다.
- deterministic 결과와 LLM-assisted 결과가 구분된다.

### Step 8. LLM 기반 Extraction, Linking, Reasoning

목표: baseline 위에 LLM 보조 추론을 추가한다.

작업:

- node extraction prompt v1
- edge linking prompt v1
- finding reasoning prompt v1
- retrieval context 구성
- structured output parser
- confidence scoring
- counter-evidence 필드 추가

완료 기준:

- 모든 LLM 후보는 prompt version, model profile, evidence를 가진다.
- schema validation 실패 시 repair retry 후 trace에 남는다.
- 낮은 confidence 후보는 자동 승인되지 않는다.

### Step 9. Approval Workbench와 Graph Commit

목표: 사용자가 AI 제안을 검토하고 승인된 것만 graph에 반영한다.

작업:

- approval item versioning
- approve/reject/modify/hold 상태 전이
- graph delta preview
- stale approval detection
- approval permission check
- feedback event 저장
- audit event 저장

완료 기준:

- 승인되지 않은 AI edge는 approved graph API에 나타나지 않는다.
- 수정 승인 시 원 제안과 수정 결과가 모두 audit 가능하다.
- stale approval은 commit되지 않는다.

### Step 10. Graph UI, Findings UI, Debug Workbench

목표: 실사용자와 개발자가 각각 필요한 수준으로 결과를 검토할 수 있게 한다.

작업:

- React Flow graph view
- node/edge detail panel
- traceability chain view
- finding list/detail
- approval queue
- debug run detail
- LLM call viewer
- graph delta diff
- replay diff viewer

완료 기준:

- 사용자는 요구사항 하나에서 관련 설계/검증/이슈 chain을 볼 수 있다.
- reviewer는 evidence와 reasoning을 보고 승인 판단을 할 수 있다.
- 개발자는 같은 run에서 어느 stage가 틀렸는지 확인할 수 있다.

### Step 11. Feedback Store와 Eval Gate

목표: 사용자 피드백을 품질 개선 데이터로 축적하고 버전 변경을 평가한다.

작업:

- feedback event 저장
- feedback reason code UI
- eval dataset builder
- golden eval runner
- regression threshold
- prompt/model comparison report
- canary metric dashboard

완료 기준:

- reject/modify 피드백이 eval dataset 후보로 자동 적재된다.
- prompt/model 변경은 eval gate 없이 active가 될 수 없다.
- replay drift와 approval precision 변화가 report로 나온다.

### Step 12. Controlled Self-Improvement

목표: 피드백 기반 개선 후보를 만들고 통제된 방식으로 운영에 반영한다.

작업:

- failure pattern clustering
- prompt improvement candidate 생성
- rule/retrieval/scoring candidate 생성
- eval run 자동 실행
- reviewer approval
- canary activation
- rollback

완료 기준:

- 시스템은 개선 후보를 제안하지만 스스로 active 운영 버전을 바꾸지 않는다.
- canary에서 reject rate가 악화되면 rollback할 수 있다.
- 개선 전후의 품질 차이가 수치와 sample diff로 제공된다.

### Step 13. Confluence 확장

목표: 설계 문서, 표, 회의록을 traceability graph에 연결한다.

작업:

- Confluence page sync
- section hierarchy 보존
- table parser
- page version diff
- JIRA link와 mention 연결
- document evidence viewer

완료 기준:

- 문서 section/table cell에서 생성된 node/edge가 원문 위치로 역추적된다.
- 문서 변경이 기존 traceability를 stale 후보로 만든다.
- JIRA requirement와 Confluence design spec 간 후보 edge가 생성된다.

### Step 14. Decision/Email 제한 확장

목표: Email 전체 수집이 아니라 승인된 decision source만 graph에 반영한다.

작업:

- decision archive 범위 확정
- thread metadata masking
- decision node extraction
- JIRA/Confluence reference linking
- sensitive thread manual review

완료 기준:

- decision node는 원문 evidence와 source policy를 가진다.
- 개인정보/비업무 본문이 vector store나 LLM payload로 유입되지 않는다.
- decision이 어떤 requirement/design/finding에 영향을 주는지 표시된다.

### Step 15. 운영 배포와 보안 강화

목표: 사내 사용자에게 안정적으로 제공할 수 있는 운영 체계를 만든다.

작업:

- dev/stage/prod 환경 분리
- SSO/OIDC 연동
- RBAC과 project-level authorization
- secret manager 연동
- audit log retention
- backup/restore rehearsal
- load test
- incident response runbook

완료 기준:

- 사용자는 권한 있는 project 데이터만 볼 수 있다.
- 장애 시 run 재시도/중단/복구 절차가 명확하다.
- backup에서 app DB, graph DB, vector metadata를 복구할 수 있다.

## 14. 첫 상용 릴리스 범위

첫 릴리스는 기능을 넓히기보다 traceability agent의 안전한 운영 루프를 완성하는 데 집중한다.

필수 포함:

- 실제 JIRA incremental sync
- source snapshot, masking, evidence, chunking
- model gateway와 prompt/model registry
- run/step/LLM call trace
- deterministic baseline rules
- LLM-assisted node/edge/finding suggestion
- approval queue와 graph delta preview
- approved graph commit
- feedback event store
- debug workbench
- replay skeleton
- graph/chain/finding read API
- React Flow graph UI
- SSO/RBAC 기본 연동
- audit log

첫 릴리스 제외:

- Email ingestion
- AI의 원본 시스템 write-back
- 승인 없는 자동 graph 변경
- 자동 prompt active 변경
- 전사 전체 rollout
- high-risk item bulk auto approval

## 15. 보안 요구사항

### 15.1 LLM 데이터 정책

- 외부 모델에는 raw secret, 개인정보, 고객 식별자, 미승인 기밀 문서를 보내지 않는다.
- model gateway는 `allowed_data_classes`를 검사한다.
- masking 전 raw artifact는 LLM gateway로 직접 전달할 수 없다.
- 모든 LLM request는 request hash와 masked payload ref만 운영 로그에 남긴다.
- raw response는 접근 권한이 있는 debug 사용자만 볼 수 있다.

### 15.2 RBAC

- project 단위 read 권한
- domain 단위 approval 권한
- admin policy 변경 권한
- debug artifact 조회 권한
- audit 조회 권한

### 15.3 Release 차단 조건

- masking violation 1건 이상
- 승인 없는 graph commit 가능성 발견
- project 권한 밖 node/edge 노출
- prompt/model 변경 후 eval 핵심 지표 하락
- graph migration rollback 불가
- LLM raw payload에 금지 데이터 포함

## 16. 운영 KPI

| KPI | 의미 |
| --- | --- |
| Traceability Coverage | active requirement 중 approved implementation/verification chain이 있는 비율 |
| Open Critical/High Findings | 미해결 critical/high finding 수 |
| Edge Approval Precision | AI 제안 edge 중 승인 또는 수정 승인 비율 |
| Edge Modification Rate | 사용자가 edge를 수정한 비율 |
| Finding Useful Rate | acknowledged/resolved 처리된 finding 비율 |
| Evidence Sufficiency Rate | weak_evidence 피드백이 없는 비율 |
| Mean Approval Time | pending item 처리 평균 시간 |
| Structured Output Failure Rate | LLM schema validation 실패율 |
| Replay Drift | 버전 변경으로 결과가 달라진 비율 |
| Masking Violation Count | 보안 차단 지표 |
| Model Timeout Rate | 모델 응답 실패율 |
| Sync Freshness | 원본 변경이 분석 후보에 반영되기까지 시간 |

## 17. 주요 리스크와 대응

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| 초기 agent 품질이 낮음 | 사용자 신뢰 저하 | L0 baseline, evidence, approval, debug trace |
| 모델 교체로 결과가 흔들림 | 운영 일관성 저하 | model profile, replay diff, eval gate |
| prompt 개선이 회귀를 만듦 | 품질 저하 | golden eval, canary, rollback |
| 피드백이 쌓이지 않음 | 개선 루프 정체 | approval UI에서 reason code를 자연스럽게 수집 |
| JIRA 데이터 품질이 낮음 | graph 품질 저하 | source link 우선, missing metadata finding |
| 근거 없는 LLM 추론 | 잘못된 edge 생성 | evidence 필수, confidence threshold, HITL |
| 보안 데이터 유출 | 릴리스 불가 | masking gate, model data policy, audit |
| debug artifact 과다 저장 | 비용 증가 | retention policy, artifact compression, access control |
| approval queue 적체 | 운영 정체 | severity routing, owner assignment, bulk review 후보 |

## 18. 최종 개발 순서 요약

1. 단일 기준 문서, ontology, 데이터/모델/승인 정책을 확정한다.
2. Pydantic 계약, FastAPI skeleton, CI를 만든다.
3. agent보다 먼저 model gateway와 debug trace 기반을 만든다.
4. PostgreSQL, Neo4j, Qdrant, artifact store를 구성한다.
5. JIRA connector와 source snapshot/replay 입력을 안정화한다.
6. masking, evidence, chunking, embedding pipeline을 만든다.
7. LLM 없는 deterministic baseline graph/finding을 만든다.
8. LLM extraction/linking/reasoning을 붙인다.
9. approval workbench와 graph commit을 완성한다.
10. graph UI와 debug workbench를 연결한다.
11. feedback store와 eval gate를 만든다.
12. controlled self-improvement loop를 활성화한다.
13. Confluence를 확장한다.
14. decision/email source는 보안 정책 검증 후 제한적으로 도입한다.
15. 운영 배포, SSO/RBAC, backup/restore, load test를 완료한다.

## 19. 설계상 가장 중요한 판단

- agent가 틀리는 것은 예외가 아니라 기본 가정이다. 그래서 debug trace와 feedback loop가 핵심 기능이다.
- 모델은 바뀐다. 따라서 prompt, model, retrieval, structured parser, scoring은 모두 versioned component로 관리한다.
- 사용자 피드백은 단순 로그가 아니라 eval dataset과 improvement candidate의 원천 데이터다.
- 자율 개선은 운영 안전장치를 가진 release process다. 시스템이 스스로 개선 후보를 만들 수는 있지만, 운영 active 버전 변경은 eval과 reviewer 승인이 필요하다.
- 승인되지 않은 AI 후보와 승인된 graph 원장은 물리적/논리적으로 분리한다.
- 상용 품질의 첫 기준은 "정답을 항상 맞히는 agent"가 아니라 "틀렸을 때 원인과 수정 경로가 명확한 agent"이다.


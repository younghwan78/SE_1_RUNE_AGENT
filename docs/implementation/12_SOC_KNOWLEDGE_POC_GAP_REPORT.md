# SoC Knowledge PoC v4.0 Gap Report

작성일: 2026-05-25

## 1. 분석 기준

이 문서는 `SoC_Knowledge_PoC_Design_v4.0.md`를 기준으로, 현재 `E:\51_Codex_MBSE_Agent` 구현에 무엇을 추가하거나 수정해야 하는지 정리한 gap report다.

우선순위는 다음과 같이 둔다.

1. `PRODUCTION_EXECUTION_PLAN.md`: repository의 단일 source of truth.
2. `AGENTS.md`: 구현/운영 guardrail.
3. `SoC_Knowledge_PoC_Design_v4.0.md`: 새 PoC 방향과 acceptance criteria.
4. 현재 코드와 `docs/implementation/*`: 이미 구현된 production-shaped 기반.

중요한 결론은 하나다. 새 PoC 설계는 현재 구현을 폐기하기보다, 현재의 `Pydantic contract + source adapter + masking/evidence + model_gateway trace + approval/feedback + FastAPI/API/test` 기반 위에 SoC domain ontology, fixture-first query loop, Claude Code subprocess provider, hybrid retrieval, query/chat UI를 얹는 방향이 가장 안전하다.

## 2. 현재 구현 요약

현재 저장소는 단순 PoC보다 production skeleton이 훨씬 많이 진행된 상태다.

| 영역 | 현재 구현 상태 | 재사용 판단 |
| --- | --- | --- |
| 언어/패키지 | Python 3.12+, `uv`, Pydantic v2, FastAPI | 그대로 사용 |
| API | `/api/v1/runs/*`, graph, approval, feedback, debug, dashboard, audit, scheduler route, `/api/v1/soc/query` seed route | Streamlit seed UI는 API client로 연결됨. local live UI smoke와 feedback persistence는 확인됐고, target 환경 반복 evidence가 남음 |
| Source adapter | dummy, JIRA export, Confluence export, decision/email export, JIRA REST, Confluence REST | PoC connector 추상화의 기반으로 사용 |
| Source skill | `.claude/skills/rune-source-jira`, `rune-source-confluence`, `rune-source-email` 존재, Stage G readiness gate가 source skill 존재를 검증 | Stage G real switch에 재사용. 실제 source sample fetch evidence는 남음 |
| Ingestion | source fetch, normalize, mask, chunk, evidence span, vector upsert, rule-only SoC classification seed, rule entity/semantic relation extractor seed, lifecycle event writer seed, skip-safe SoC fixture ingestion workflow rehearsal | real-source entity/event extraction and live storage ingestion evidence 필요 |
| Workflow | `LocalAnalysisWorkflow`: fetch -> normalize -> mask/chunk -> extract node -> link edge -> LLM reasoning -> finding -> approval; `SocKnowledgeIngestionWorkflow` seed: fixture source snapshot -> rule classification -> entity/relation extraction -> lifecycle events -> storage projection | real source adapters, masking/chunking, graph/vector writes, and debug artifact persistence integration 필요 |
| Ontology | MBSE v1 + SoC seed Pydantic/YAML schema: Project/V-Level/Concern/Component, lifecycle, query answer contracts | storage schema와 approved/proposed relation persistence 확장 필요 |
| Graph | memory backend, Neo4j backend, projection/chain API, AGE Cypher wrapper seed, relation-based SoC AGE query, SoC AGE graph loader seed, optional AGE `MENTIONS`/`AUTHORED_BY` semantic relation projection, SoC AGE graph migration/static readiness, live storage rehearsal entrypoint | target DB에서의 passing live AGE execution evidence와 company DB rehearsal 필요 |
| Vector | memory lexical backend, Qdrant backend, deterministic hash vector, optional bge-m3/e5 local embedding loader seed, pgvector query builder/table migration seed, seed lexical/gateway/cross-encoder reranker, live storage rehearsal entrypoint, local model quality gate | target DB에서의 pgvector retrieval evidence와 실제 live model 실행 evidence가 남음 |
| Model | model gateway, dummy/HTTP/Claude Code provider, prompt/model registry, LLM call trace, SoC Claude Code classifier/slice/tool/answer quality gates, live Claude Code structured-output evidence | model profile 운영 승격과 target 환경 반복 evidence 필요 |
| UI | FastAPI static operator UI, dashboard/work queue/traceability/debug, SoC Streamlit seed UI support, SoC UI runbook | Streamlit live browser smoke는 two-session/source-link/feedback까지 확인됨. target 환경 반복 evidence 필요 |
| Feedback/eval | feedback events, improvement candidates, eval/canary promotion skeleton, 20-Q SoC seed eval/comparer, generated 400-fixture query eval, storage-backed query eval gate, `soc_eval_runs` persistence rehearsal, eval-run metric diff report | scale query manual curation과 사용자 feedback loop 확장, target DSN live evidence 필요 |
| Persistence | PostgreSQL state tables, rollback scripts, typed mirrors, core-vs-SoC migration profile split, SoC AGE/pgvector/FTS query adapter seed, 011~013 SoC table/pgvector/AGE migrations, fixture-to-Postgres artifact/classification/event writer seed, AGE graph loader seed, live SoC DB validator, live storage rehearsal gate | target DSN 기반 passing live DB execution and company DB rehearsal 필요 |
| Ops/tests | CI gates, readiness/backup/helm/rehearsal scripts, `eval/stages/A-G.yaml`, SoC schema/fixture/query/UI/source-switch eval tests, SoC Postgres profile validator, live storage rehearsal smoke, storage-backed query eval gate, real-source switch readiness gate | live target DB/source acceptance evidence 추가 필요 |

## 3. PoC 설계가 요구하는 핵심 변화

`SoC_Knowledge_PoC_Design_v4.0.md`는 기존 traceability agent를 다음 방향으로 특화한다.

| PoC 핵심 | 의미 | 현재와의 차이 |
| --- | --- | --- |
| 4축 ontology | Project x V-Level x Concern x Component | 현재는 node type 중심 MBSE ontology |
| Slice query | 자연어를 4가지 query pattern으로 라우팅 | seed classifier/query API, storage-backed hybrid query adapter, storage-backed query eval gate는 있음. target DSN과 target UI 반복 evidence는 미완 |
| Fixture-first | 2개 과제, JIRA 200, Conf 100, Email 100, ground truth Q 20~30 | 40개 seed fixture, 20-Q set, generated 400 fixture, generated 30-Q scale set은 있음. manual review/curation은 미완 |
| Single Postgres | Postgres + Apache AGE + pgvector + pg_trgm | Postgres hybrid query adapter와 live storage rehearsal gate는 있음. target DB 통과 evidence는 미완 |
| Claude Code only | LLM 추론은 Claude Code subprocess | gateway 뒤 Claude Code provider와 slice/plan/answer quality gate는 있음. 실제 live 품질 실행 evidence는 미완 |
| Local embedding/rerank | bge-m3, cross-encoder reranker | optional bge-m3/e5 embedding loader seed + lexical/gateway/cross-encoder rerank seed + explicit quality gate는 있음. 실제 live model 통과 evidence는 미완 |
| Streamlit UI | chat, source link, timeline, feedback, reasoning toggle | API-only Streamlit seed UI support, local live browser acceptance, usage guide는 있음. target 환경 반복 evidence는 미완 |
| Stage A-G autonomy | acceptance YAML과 regression loop로 agent 자율 완료 | Stage A-G seed YAML은 있음. Stage G full live source acceptance는 미완 |

## 4. 가장 큰 설계 충돌과 권장 해소 방식

### 4.1 Claude Code subprocess vs model gateway

PoC는 모든 LLM 작업을 Claude Code subprocess로 실행하라고 정의한다. 반면 production plan은 model-specific call을 model gateway 뒤에 숨기고, 모든 LLM call을 `run_id`, `step_id`, `model_profile_id`, `prompt_version_id`, request/response hash, validation status로 추적하라고 요구한다.

권장 해소:

- `subprocess.run(["claude-code", ...])`를 UI나 query code에서 직접 부르지 않는다.
- `src/req_tracker/model_gateway/claude_code_provider.py`를 추가해 `ModelProvider` 구현체로 감싼다.
- `ModelProfile.provider`에 `claude_code` 또는 기존 Literal 확장이 어렵다면 `local` provider의 endpoint alias로 먼저 표현한다.
- 모든 Claude Code 호출은 `ModelGatewayClient.complete()`를 통과시켜 masking policy, prompt version, structured output validation, `LLMCallTrace`를 유지한다.
- PoC의 "Claude Code only" 원칙은 `MODEL_GATEWAY_MODE=claude_code_subprocess` profile로 충족한다.

이 방식이면 PoC의 self-contained 실행과 production의 traceability non-negotiable을 동시에 만족한다.

### 4.2 Postgres AGE/pgvector vs Neo4j/Qdrant

PoC는 단일 Postgres에 AGE, pgvector, pg_trgm을 얹는 구조를 요구한다. 현재 구현은 production plan에 맞게 Postgres state, Neo4j graph, Qdrant vector를 분리했다.

권장 해소:

- 기존 Neo4j/Qdrant backend를 제거하지 않는다.
- Stage A에서 `GRAPH_BACKEND=postgres_age`, `VECTOR_BACKEND=pgvector`, `KEYWORD_BACKEND=postgres_fts`를 선택할 수 있는 새 backend profile을 추가한다.
- SoC PoC query service는 backend protocol에 의존하게 만들고, 실제 저장소 선택은 설정으로 둔다.
- AGE 설치가 사내 DB에서 불확실하면 Stage B-F는 memory/Neo4j/Qdrant로 functional acceptance를 먼저 통과시키고, Stage G 전 `postgres_age/pgvector` profile을 검증한다.

즉, PoC의 단일 Postgres 요구는 새 운영 profile로 구현하되, 현재 production-shaped backend를 되돌리지 않는다.

### 4.3 Streamlit UI vs FastAPI static UI

PoC는 Streamlit chat UI를 요구하지만, production plan과 현재 docs는 FastAPI static UI를 첫 release UI로 둔다.

권장 해소:

- 빠른 PoC 검증용으로 `src/req_tracker/soc_ui/streamlit_app.py`를 별도 entrypoint로 둔다.
- Streamlit은 DB와 workflow를 직접 만지지 않고, FastAPI의 `/api/v1/soc/query`와 `/api/v1/feedback`만 호출한다.
- production UI에는 같은 API를 사용하는 "SoC Knowledge" tab을 나중에 추가한다.

이렇게 하면 PoC 사용성 검증 속도를 얻으면서 core application boundary를 유지할 수 있다.

### 4.4 AI classification을 바로 graph truth로 저장하는 문제

PoC는 classifier가 V-Level/Concern/Component를 부여하고 graph relation으로 적재하는 흐름을 제안한다. 하지만 production guardrail은 AI output을 승인 전 운영 graph 원장에 반영하지 말라고 한다.

권장 해소:

- Fixture ground truth와 rule high-confidence classification은 `baseline` 또는 `approved_seed`로 저장할 수 있다.
- Claude Code가 보강한 classification은 `source=claude`, `approval_status=pending` 또는 `is_proposal=true`로 분리한다.
- Query response에는 낮은 confidence와 pending/proposed classification을 "추정"으로 표시한다.
- graph commit이 필요한 relation은 기존 approval workflow를 통과시킨다.

## 5. Architecture Layer별 Gap Matrix

### 5.1 Ontology와 schema

| 요구 | 현재 | Gap | 추가/수정 |
| --- | --- | --- | --- |
| Project axis | `project_key` 문자열만 존재 | Project entity와 project metadata 없음 | `SocProject` 또는 `Project` axis registry 추가 |
| V-Level L0-L5 | 없음 | V-model level field/classification 없음 | `VModelLevel` enum, classification axis 추가 |
| Concern axis | 없음 | Power/Performance/Memory 등 vocab 없음 | concern vocab YAML과 alias matcher 추가 |
| Component axis | `NodeType=Component`만 있음 | Component hierarchy/vocab 없음 | component vocab YAML, parent_component 지원 |
| Artifact superclass | `SourceArtifact` 있음 | Issue/Page/EmailThread/EmailMessage subtype 구분은 metadata 중심 | artifact subtype 모델 또는 source-specific normalized detail 추가 |
| Event | run/audit events + `SocLifecycleEvent` model + `soc_event_log` table + fixture lifecycle event upsert seed | real-source lifecycle extraction and target DB evidence 없음 | source adapter event extraction과 live event query 검증 추가 |
| Relation set | satisfies/verifies/derives/implements/affects/... | addresses/involves/atLevel/belongsToProject/replyTo/partOf 등 없음 | classification side-car와 semantic relation model 추가 |
| YAML schema | `docs/ontology/ONTOLOGY_V1.md`와 Pydantic | PoC `ontology/schema/v0.1/*.yaml` 없음 | `docs/ontology/soc/schema/v0.1/entities.yaml`, `relations.yaml`, validator 추가 |

권장 구현:

- core `OntologyNode`를 바로 크게 확장하기보다, 먼저 side-car domain model을 둔다.
- 후보 경로:
  - `src/req_tracker/ontology/soc_models.py`
  - `src/req_tracker/ontology/soc_schema.py`
  - `docs/ontology/soc/schema/v0.1/entities.yaml`
  - `docs/ontology/soc/schema/v0.1/relations.yaml`
  - `docs/ontology/SOC_ONTOLOGY_V0_1.md`

필수 Pydantic 계약 후보:

```python
AxisType = Literal["project", "v_level", "concern", "component"]
ClassificationSource = Literal["rule", "claude", "manual", "fixture"]
ClassificationStatus = Literal["baseline", "pending", "approved", "rejected"]

class SocAxisClassification(BaseModel):
    classification_id: str
    entity_id: str
    axis: AxisType
    value: str
    confidence: float
    source: ClassificationSource
    status: ClassificationStatus
    evidence_ref: str | None
    run_id: str
    step_id: str
    schema_version: str = "soc-v0.1"

class SocLifecycleEvent(BaseModel):
    event_id: str
    entity_id: str
    timestamp: datetime
    change_type: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    source: str
    source_url: str | None
    schema_version: str = "soc-v0.1"
```

### 5.2 Ingestion pipeline

| PoC 단계 | 현재 구현 | Gap | 구현 방향 |
| --- | --- | --- | --- |
| Fetch | `SourceAdapter.fetch_incremental()` | PoC `Connector.fetch/normalize`와 이름 다름 | 기존 adapter protocol 유지, PoC connector는 adapter wrapper로 해석 |
| Normalize | `normalize_raw_artifact()` | source별 subtype detail 부족 | JIRA/Conf/Email metadata normalization 보강 |
| Mask | `mask_text()`, violation block | 재사용 가능 | Claude Code provider 호출 전에도 재사용 |
| Classify | rule-only 4축 classifier + fixture ingestion workflow classification stage + `GatewaySocAxisClassifier` pending proposal path + skip-safe/live classifier enrichment gate | low-confidence review loop 운영 evidence 없음 | classifier proposal review workflow 연결 |
| Extract entities | `extract_node()`는 MBSE node 1개 생성; `ingestion/soc_entity_extraction.py`가 Artifact/Person side-car entity와 explicit link/body JIRA-key `mentions`, author `authoredBy` relation을 생성하고 AGE loader가 `MENTIONS`/`AUTHORED_BY` edge payload를 만들 수 있음 | Claude Code-assisted semantic extraction, live AGE execution, real-source mention evidence 없음 | live relation load evidence와 semantic enrichment gate 추가 |
| Embed | `vector.upsert(chunks)` + optional `LocalSentenceTransformerEmbedder` seed + local model quality gate | live bge-m3/e5 model load evidence and pgvector write/read target evidence 없음 | live smoke와 storage-backed eval 추가 |
| Persist graph/vector | memory/Neo4j/Qdrant + SoC AGE/pgvector/FTS query builders + SoC Postgres migrations + artifact/classification/event/embedding writer seed + AGE graph loader seed + optional semantic relation graph edge payload + live storage rehearsal gate + fixture storage projection workflow | target DB에서의 passing live SoC storage execution evidence 없음 | company/staging live adapter execution 추가 |
| Log event | audit/run step + `soc_event_log` table seed + fixture `artifact_synced` lifecycle event writer | real-source lifecycle extraction과 query/replay integration 부족 | source-derived event extraction과 target DB event query 검증 추가 |
| Idempotent re-ingestion | cursor/hash 기반 일부 존재 + SoC stable classification/entity/relation/event IDs + scale fixture idempotency rehearsal | live storage upsert idempotency evidence 없음 | target DB 반복 적재 evidence 추가 |

새 pipeline은 기존 `LocalAnalysisWorkflow`를 무리하게 비대화하지 않는 편이 낫다. 후보 구조:

```text
src/req_tracker/workflows/soc_knowledge.py
  SocKnowledgeIngestionWorkflow
    source_fetch
    normalize
    mask_chunk
    classify_axes
    extract_entities
    embed
    build_semantic_links
    persist_soc_index
    log_lifecycle_events
```

현재 seed workflow는 `src/req_tracker/workflows/soc_knowledge.py`에 추가됐고, fixture source snapshot, axis classification, lifecycle event, storage projection 단계를 `AgentRun`/`AgentStepTrace`로 남긴다. 다음 확장에서는 기존 `LocalAnalysisWorkflow`의 artifact/debug persistence 패턴을 따라 source adapter, masking/chunking, graph/vector write 단계까지 연결해야 한다. Claude Code classification 단계는 추가 시 `LLMCallTrace`를 남긴다.

### 5.3 Fixture와 ground truth

| 요구 | 현재 | Gap |
| --- | --- | --- |
| JIRA fixture 200 | generated SoC scale fixture 200개 | curated/natural review 필요 |
| Confluence fixture 100 | generated SoC scale fixture 100개 | architecture/design page naturalness review 필요 |
| Email fixture 100 | generated SoC scale fixture 100개 | thread reconstruction/quote fixture realism 보강 필요 |
| 2개 project 분포 | `SOC-N-1`, `SOC-N-2` seed/scale fixture | longitudinal scenario quality review 필요 |
| V-Level 분포 | 없음 | L0-L5 coverage 없음 |
| Concern/Component 분포 | labels 일부 | Power/Performance/Memory/Camera 등 axis ground truth 없음 |
| Cross-source/cross-project | 일부 links | PoC 의도 case 대량 부족 |
| Q set 20~30 | 없음 | slice query ground truth 없음 |

권장 경로:

```text
fixtures/soc_knowledge/
  spec.md
  projects.yaml
  vocab/
    concerns.yaml
    components.yaml
  jira/*.yaml
  confluence/*.yaml
  email/*.yaml
  ground_truth/
    classifications.yaml
    relations.yaml
    events.yaml
  queries.yaml
```

현재 repository에는 root `fixtures/`가 없지만, PoC 설계가 fixture-first를 강하게 요구하므로 새 root fixture directory를 두는 것이 자연스럽다. 단, 실제 회사 데이터 export나 민감 샘플은 넣지 않는다.

### 5.4 Storage

PoC storage 요구는 현재 storage와 가장 크게 다르다.

| PoC storage | 현재 storage | Gap | 권장 구현 |
| --- | --- | --- | --- |
| Postgres + AGE graph | Neo4j graph backend + `graph/postgres_age_backend.py` relation query builder + `graph/soc_age_loader.py` + `013_soc_age_schema.sql` + live profile validator + live storage rehearsal | target DB에서의 passing live AGE graph execution evidence 없음 | company/staging integration test 추가 |
| pgvector embedding | Qdrant backend + `vector/pgvector_backend.py` query builder + `012_soc_pgvector_tables.sql` + deterministic fixture embedding writer + live profile validator + live storage rehearsal | target DB에서의 passing live embedding storage execution evidence 없음 | embedder와 integration test 추가 |
| pg_trgm/FTS | `query/postgres_keyword_backend.py` query builder + `011_soc_knowledge_tables.sql` + `soc_artifacts` writer + live profile validator + live storage rehearsal | target DB에서의 passing live typed table execution evidence 없음 | company/staging integration test 추가 |
| `artifact_meta` | `source_artifacts`, state mirrors, `soc_artifacts` | storage table seed 추가됨 | source adapter loader와 upsert repository 추가 |
| `event_log` | audit events, run steps, `soc_event_log`, fixture `artifact_synced` event writer | target/live source-derived lifecycle event evidence 없음 | source-derived event extraction과 live event query 검증 추가 |
| `classification` | `soc_classifications` | classifier write path 없음 | rule classifier result upsert 추가 |
| `sync_state` | `source_sync_cursors` | 재사용 가능 | 기존 cursor table 우선 사용 |
| `user_feedback` | `feedback_events` | 재사용 가능 | answer feedback target 추가 |
| `eval_run` | improvement/eval skeleton + `soc_eval_runs` table + state-store persistence/reload rehearsal + local eval-run metric diff report | local seed persistence/diff는 있음. target Postgres live persistence, artifact report retention, promotion-gate integration은 미완 | `soc_eval_runs` live gate와 eval promotion review 연결 |

권장 migration:

```text
src/req_tracker/storage/migrations/postgres/
  011_soc_knowledge_tables.sql
  012_soc_pgvector_tables.sql       # pgvector 사용 시
  013_soc_age_schema.sql            # AGE 사용 시, extension availability gate 필요
rollback/
  011_soc_knowledge_tables.sql
  012_soc_pgvector_tables.sql
  013_soc_age_schema.sql
```

중요한 주의:

- `CREATE EXTENSION age`, `CREATE EXTENSION vector`, `CREATE EXTENSION pg_trgm`는 target DB 권한에 따라 실패할 수 있다.
- migration은 extension missing을 조용히 무시하면 안 된다. `readiness`와 Stage A acceptance에서 명확히 실패해야 한다.
- 기존 PostgreSQL state store가 JSONB typed mirror 중심이므로, SoC query 성능을 위해 classification/event/embedding은 별도 typed table로 가야 한다.

### 5.5 Query 처리

현재 구현은 graph projection과 traceability chain 위에 seed SoC query layer를 추가했다. 자연어 query는 deterministic/optional gateway slice plan으로 라우팅되고, fixture-backed retrieval과 structured answer JSON은 동작한다. storage-backed hybrid backend와 그 query eval gate도 추가됐으므로, 남은 작업은 target DSN live evidence와 production UI/feedback 확장이다.

필요하거나 이미 seed로 들어간 query 모듈:

```text
src/req_tracker/query/
  __init__.py
  models.py              # SocQueryRequest, SocSlice, SocAnswer; 현재는 ontology/soc_models.py 중심
  slice_classifier.py    # natural language -> slice pattern; 현재는 query/soc_planner.py seed
  templates.py           # Pattern A-D whitelisted query templates; 현재는 query/soc_orchestration.py seed
  retrieval.py           # graph + vector + keyword orchestration; storage-backed backend seed 구현됨
  reranking.py           # lexical/model-gateway/cross-encoder seed
  answering.py           # context -> structured answer; 현재는 soc_service.py + optional gateway assembler seed
  tools.py               # graph_query/vector_search/keyword_search/event_log facade; AGE/pgvector/FTS facade pending
```

API 후보:

```text
POST /api/v1/soc/query
GET  /api/v1/soc/query/{query_run_id}
GET  /api/v1/soc/artifacts/{artifact_id}/timeline
POST /api/v1/soc/query/{query_run_id}/feedback
```

답변 schema는 PoC 13.3을 Pydantic으로 고정한다.

```python
class SocAnswerSource(BaseModel):
    type: Literal["jira", "confluence", "email", "decision_archive", "dummy"]
    key: str | None
    url: str

class SocAnswerItem(BaseModel):
    title: str
    summary: str
    sources: list[SocAnswerSource]
    level: str | None
    concern: list[str]
    component: list[str]

class SocAnswer(BaseModel):
    summary: str
    items: list[SocAnswerItem]
    timeline: list[SocLifecycleEvent]
    confidence: Literal["low", "medium", "high"]
    reasoning_log_ref: str
```

보안상 Claude Code가 임의 Cypher/SQL을 생성해 바로 실행하는 구조는 피해야 한다. 권장 방식은 Claude Code가 `slice_plan`을 제안하고, deterministic query service가 whitelisted template만 실행하는 것이다.

### 5.6 Retrieval와 reranking

PoC 목표는 graph + vector + keyword + rerank hybrid다. 현재는 fixture-backed slice filter, deterministic keyword matching, typed query orchestration, optional bge-m3/e5 local embedding loader seed, lexical/gateway/cross-encoder rerank seed, local model quality gate, parameterized AGE/pgvector/Postgres FTS adapter seed, relation-based AGE graph query, 011~013 SoC Postgres table/pgvector/AGE migrations, static profile validator, live DB profile validator, artifact/classification/deterministic embedding writer seed, AGE artifact-axis graph loader seed, `ops/rehearsal/run_soc_live_storage_rehearsal.py`, 그리고 `ops/evals/run_soc_storage_backed_query_eval.py`까지 들어갔다. 다만 target DB에서의 passing live DB execution evidence와 실제 live local model execution evidence는 아직 없다.

추가 항목:

- `KeywordSearchBackend` live execution against a real Postgres profile.
- Postgres FTS/pg_trgm table/index readiness는 static validator까지 완료, company DB rehearsal 필요.
- `HybridRetrievalResult` schema: candidate id, source, score components, matched axis, evidence refs.
- score 합산 기본값: graph_match, vector_similarity, keyword_score, recency/lifecycle boost.
- live local embedding and cross-encoder quality acceptance. Embedding/cross-encoder loader는 optional dependency와 dry-run smoke로 seed 구현됐고, `ops/evals/run_soc_local_model_quality_gate.py`가 explicit `--live` recall@k 품질 gate를 제공한다.
- Claude Code reranking은 이미 `ModelGatewayClient`를 통과하는 seed wrapper가 있으므로, live 품질 acceptance와 fallback 기준을 추가한다.

현재 `QdrantVectorBackend`의 deterministic `_embed_text()`는 test baseline으로는 유용하지만, PoC quality gate에는 부족하다. `LocalSentenceTransformerEmbedder`는 bge-m3/e5-style 모델을 lazy-load하고 1024-dimension vector를 검증한다. `run_soc_local_model_quality_gate.py`는 seed Q2 기준 embedding/reranker recall@k를 확인한다. `run_soc_storage_backed_query_eval.py`는 target DSN에서 Postgres hybrid retrieval 기준 query quality를 확인하지만, 실제 live model download/load와 target DB live eval은 기본 CI에 포함하지 않는다.

### 5.7 UI

PoC가 원하는 UI는 "operator가 승인/디버그하는 UI"가 아니라 "architect가 자연어로 묻는 knowledge UI"다.

현재 static UI에 없는 것:

- chat input/output.
- 답변 카드의 source deep link.
- event timeline panel.
- user/session 분리된 conversation history.
- query response feedback widget.
- reasoning log toggle.
- Claude Code timeout/DB 장애에 대한 사용자 친화 error.

권장 구현 1차:

```text
src/req_tracker/soc_ui/
  streamlit_app.py
  api_client.py
  render_answer.py
```

Streamlit은 다음 원칙을 지킨다.

- 직접 DB 접속 금지.
- 직접 Claude Code subprocess 호출 금지.
- FastAPI query/feedback/debug endpoint만 호출.
- `session_state`에는 conversation UI state만 저장.
- `user_id`는 env 또는 reverse proxy header를 API로 전달.

권장 구현 2차:

- 기존 static UI에 `SoC Knowledge` tab 추가.
- 같은 `/api/v1/soc/query` endpoint를 사용해 Streamlit과 결과 shape를 공유.

### 5.8 Eval loop와 autonomous Stage A-G

현재 eval/feedback/canary skeleton은 production improvement loop 중심이다. PoC가 요구하는 fixture Q-set recall/source accuracy loop는 별도로 추가해야 한다.

필요한 파일:

```text
eval/stages/
  A.yaml
  B.yaml
  C.yaml
  D.yaml
  E.yaml
  F.yaml
  G.yaml
ops/evals/
  run_soc_query_eval.py
  compare_soc_answer.py
  diagnose_soc_failures.py
tests/evals/
  test_soc_stage_acceptance.py
  test_soc_query_ground_truth.py
```

평가 지표:

- classification axis accuracy.
- query recall.
- source URL accuracy.
- answer JSON schema pass.
- graceful "찾지 못함" pass.
- regression count.
- response time for fixture scale.

PoC의 `logs/iteration_<n>.yaml`는 repository에 계속 쌓는 방식보다 debug artifact store에 저장하는 것이 낫다. 필요하면 `.local_artifacts`에 생성하고, report summary만 `ops/evals` output으로 남긴다.

## 6. Stage별 Gap Assessment

### Stage A. Foundation

현재 충족:

- Python 3.12+, uv, Pydantic, FastAPI, tests/CI 기반.
- source adapter boundary와 source skills.
- PostgreSQL migration loader와 rollback validation.
- model gateway, prompt/model registry, LLM trace skeleton.
- debug artifact store와 trace repository.
- SoC Pydantic contract, schema/vocab YAML, schema validator.
- Claude Code subprocess provider와 dry-run smoke.
- `eval/stages/A.yaml`.

부족:

- Postgres AGE/pgvector/pg_trgm live company DB execution.
- bge-m3/e5 embedding live model load and quality acceptance.
- cross-encoder reranker live model load and quality acceptance.
- `make db-init`, `make schema-apply`에 해당하는 repo command. 현재 repo는 PowerShell/uv 중심이라 `ops/soc/*.py` entrypoint가 더 적합할 수 있다.

권장 작업:

1. `docs/ontology/soc/schema/v0.1`와 validator부터 추가.
2. `SocAxisClassification`, `SocLifecycleEvent`, `SocQuery*` contracts 추가.
3. `ClaudeCodeSubprocessProvider`를 model gateway 뒤에 추가.
4. `PgVectorBackend`와 `PostgresKeywordBackend`를 먼저 구현하고, AGE는 extension availability gate 후 추가.
5. Stage acceptance YAML과 runner skeleton 추가.

### Stage B. Fixture & Data Model

현재 충족:

- dummy fixture 패턴과 scale fixture 경험.
- source contract로 fixture를 읽는 adapter 기반.
- test로 dummy pipeline 검증 가능.
- 40개 SoC seed fixture.
- generated 400개 SoC scale fixture: JIRA 200, Confluence 100, Email 100.
- 20개 ground-truth query set.
- fixture loader와 validator.
- `eval/stages/B.yaml`.

부족:

- manually curated 400-fixture query expected annotation.
- longitudinal scenario와 source naturalness manual review loop.
- scale fixture query/eval regression promotion.

권장 작업:

1. fixture spec를 먼저 작성한다.
2. 수량을 한 번에 400개 만들기보다 40개 seed fixture로 schema/query loop를 검증한 뒤 generator로 확장한다.
3. `fixtures/soc_knowledge/queries.yaml`에서 4가지 slice pattern을 강제한다.
4. architect manual review 항목은 "실데이터 리뷰"가 아니라 "fixture 자연스러움 리뷰"로 분리한다.

### Stage C. Ingestion Fixture Mode

현재 충족:

- fetch/normalize/mask/chunk/evidence/vector upsert.
- idempotent source cursor 기반 일부.
- JIRA/Confluence metadata preservation 일부.
- rule-only Project/V-Level/Concern/Component classifier.
- classification confidence/source 기록 contract.
- classification recall validator.
- stable classification/entity/relation/event IDs and scale fixture idempotency rehearsal.
- `eval/stages/C.yaml`.

부족:

- rule + Claude Code hybrid classification.
- live AGE graph `MENTIONS` / `AUTHORED_BY` semantic relation execution evidence.
- email thread/reply/quote removal.
- real-source lifecycle event extraction.
- live AGE graph builder 또는 semantic index builder execution evidence.
- target DB 반복 적재 idempotency evidence.

권장 작업:

1. classification을 graph relation보다 먼저 side-car table로 구현한다.
2. fixture ground truth로 rule classifier를 먼저 측정한다.
3. low confidence와 random sampling만 Claude Code provider로 보내 trace를 남긴다.
4. JIRA changelog metadata를 `SocLifecycleEvent`로 변환한다.
5. email은 Stage C fixture에서 L1-L3 처리만 구현하고, broad mailbox access는 Stage G 승인 전까지 막는다.

### Stage D. Retrieval & Query

현재 충족:

- vector search protocol.
- graph projection/traceability chain.
- model gateway structured output validation.
- debug trace.
- deterministic natural-language slice classification.
- Pattern A-D seed query paths plus graceful unknown.
- typed `SocQueryPlan` / whitelisted tool calls.
- seed keyword matching and lexical/model-gateway/cross-encoder rerank wrapper.
- injectable Postgres hybrid retrieval profile seed.
- parameterized AGE Cypher, pgvector, and Postgres FTS/pg_trgm query builders.
- AGE graph loader seed for `Artifact` -> `Project`/`VLevel`/`Concern`/`Component` relations.
- SoC Postgres profile migrations: `011_soc_knowledge_tables.sql`, `012_soc_pgvector_tables.sql`, `013_soc_age_schema.sql` and rollback scripts.
- static profile validator: `ops/rehearsal/validate_soc_postgres_profile.py`.
- live profile validator: `ops/rehearsal/validate_soc_live_postgres.py`.
- standard `SocAnswer` JSON with source URL validation.
- query reasoning log and `AgentRun`/`AgentStepTrace` lineage.
- `/api/v1/soc/query` and seed eval runner.
- skip-safe storage-backed query eval gate for seed/scale Q sets.

부족:

- live DB integration/data load for AGE/pgvector/FTS and company/staging rehearsal.
- live cross-encoder quality acceptance.
- live Claude Code quality acceptance for planner/reranker/answer assembly.
- target DSN에서의 storage-backed query eval passing evidence.
- storage-backed query reasoning persistence and replay diff UI.

추가 완화:

- `ops/rehearsal/run_soc_live_storage_rehearsal.py`가 target DSN에서 profile validation, fixture artifact/classification/embedding load, AGE graph load, hybrid AGE/FTS/pgvector retrieval, source URL provenance를 한 번에 확인하는 gate로 추가됐다.
- 기본 local/CI에서는 DSN이 없으면 `status=skipped`로 끝나며, target DB에서는 `--require-live --apply-migrations`로 non-zero failure gate가 된다.
- `ops/evals/run_soc_storage_backed_query_eval.py`는 live storage rehearsal 이후 seed/scale Q set을 `PostgresHybridSocRetrievalBackend`로 실행해 recall/source/schema/regression metric을 보고한다. 이 gate도 기본은 skip-safe이고, `--live --require-live`에서만 target DB 실패를 non-zero로 만든다.

권장 작업:

1. deterministic slice parser baseline을 먼저 만든다.
2. Claude Code slice planner는 baseline fallback 또는 reviewer로 붙인다.
3. query execution은 whitelisted template만 허용한다.
4. answer generation은 Pydantic schema validation 실패 시 retry하고 trace에 남긴다.
5. `POST /api/v1/soc/query` contract test를 먼저 만든다.

### Stage E. UI

현재 충족:

- static operator UI, dashboard, work queue, debug panes.
- feedback API와 reason-code normalization.

추가 충족:

- API-only Streamlit seed entrypoint: `src/req_tracker/soc_ui/streamlit_app.py`.
- FastAPI client boundary: `src/req_tracker/soc_ui/api_client.py`.
- answer card/source/timeline view helper: `src/req_tracker/soc_ui/render_answer.py`.
- query-specific answer feedback payload path to `/api/v1/feedback`.
- session-scoped conversation state and reasoning log toggle seed.
- dry-run smoke: `ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json`.
- local live smoke: FastAPI `127.0.0.1:18080` + Streamlit `127.0.0.1:18580`에서 query answer card와 feedback submit을 확인.
- PostgreSQL-backed feedback persistence: `ops/rehearsal/run_full_stack_rehearsal.py`가 answer feedback을 `/api/v1/feedback`으로 기록하고 API restart 후 `/api/v1/feedback/summary`에서 복원 count를 확인한다.
- explicit live UI acceptance smoke: `ops/ui/smoke_soc_streamlit_ui.py --live --ui-url ...`가 두 개의 독립 browser context, session isolation, source link presence/actionability, feedback form availability를 검증한다. 2026-05-25 local run은 FastAPI `127.0.0.1:18082` + Streamlit `127.0.0.1:18582`에서 `status=passed`, session A source link 8개, session B source link 16개를 확인했다.

남은 부족:

- target 환경에서의 반복 live UI acceptance evidence.
- target environment usage evidence using the runbook.

다음 권장 작업:

1. target 실행 환경에서 `ops/ui/smoke_soc_streamlit_ui.py --live --ui-url ...`를 반복 실행해 Stage E acceptance evidence를 축적한다.
2. architect용 실행/장애 대응 usage guide는 `docs/runbooks/SOC_KNOWLEDGE_UI_GUIDE.md`에 추가됐다. 남은 작업은 target 환경에서 guide 기반 반복 evidence를 축적하는 것이다.
3. 기존 FastAPI static UI는 나중에 같은 API를 쓰는 tab으로 확장한다.

### Stage F. E2E Validation Loop

현재 충족:

- feedback/eval/canary rehearsal.
- replay diff and debug foundation.
- CI gate 확장 패턴.
- 20-Q ground truth runner.
- recall/source accuracy/schema/unknown-handling metrics.
- answer-vs-ground-truth comparer.
- failure diagnosis by layer.
- regression guard for packaged passing Q set.
- generated 400-fixture / 30-Q scale eval loop.
- skip-safe storage-backed query eval gate.
- `soc_eval_runs` eval summary persistence/reload rehearsal.
- local eval-run metric/regression diff report.

부족:

- manually curated scale query review and promotion loop.
- target DSN에서 storage-backed retrieval 기준의 scale query recall/source accuracy passing evidence.
- target Postgres-backed eval-run persistence evidence and promotion gate integration.

권장 작업:

1. `ops/evals/run_soc_query_eval.py`가 FastAPI test client 또는 service layer를 호출한다.
2. 결과를 `soc_eval_runs`로 저장하고 artifact report를 남긴다.
3. 실패를 classification/retrieval/answer/source-link/schema로 분류한다.
4. Stage F pass 후 통과 Q는 regression set으로 고정한다.

### Stage G. Real Data Switch

현재 충족:

- JIRA REST adapter.
- Confluence REST adapter.
- export-file source adapters.
- source skills.
- restricted decision/email export policy.
- source smoke/rehearsal scripts.

부족:

- JIRA MCP connector wrapper는 skill-level 절차만 있고 app adapter는 REST/export 중심.
- Email live connector는 broad mailbox가 아니라 decision/export 제한.
- SoC-specific JIRA project mapping, Conf whitelist, Email non-personal account config.
- real sample 50개 dry run과 classification accuracy measurement.
- full real-data ingest acceptance.

권장 작업:

1. Stage G 전까지 real source access는 구현하지 않고 fixture loop를 먼저 통과한다.
2. JIRA/Confluence는 existing REST/export adapter를 먼저 사용하고, MCP는 source skill transport로만 둔다.
3. Email은 비실명 계정이라도 approved label/archive scope만 ingest한다.
4. real sample classification은 사람이 검토한 YAML을 ground truth로 저장한다.

### Stage H. User Eval & Iteration

현재 충족:

- feedback API.
- dashboard/work queue.
- improvement candidate infrastructure.

부족:

- 10명 user eval 운영 flow.
- 사전 질문 50개 수집 format.
- query usage analytics.
- user-level qualitative survey.

권장 작업:

- Stage G 완료 후 별도 문서와 runbook으로 분리한다.
- Stage H 결과는 active prompt/rule에 직접 반영하지 말고 improvement candidate로 적재한다.

## 7. 구체적 추가/수정 파일 제안

### 7.1 새 문서

```text
docs/ontology/SOC_ONTOLOGY_V0_1.md
docs/ontology/soc/schema/v0.1/entities.yaml
docs/ontology/soc/schema/v0.1/relations.yaml
docs/implementation/13_SOC_KNOWLEDGE_STAGE_PLAN.md
docs/runbooks/SOC_KNOWLEDGE_POC_RUNBOOK.md
```

### 7.2 새 contracts

```text
src/req_tracker/ontology/soc_models.py
src/req_tracker/query/models.py
src/req_tracker/evals/soc_models.py
```

### 7.3 새 ingestion/query modules

```text
src/req_tracker/ingestion/soc_classification.py
src/req_tracker/ingestion/soc_entity_extraction.py
src/req_tracker/ingestion/soc_events.py
src/req_tracker/workflows/soc_knowledge.py
src/req_tracker/query/slice_classifier.py
src/req_tracker/query/retrieval.py
src/req_tracker/query/templates.py
src/req_tracker/query/reranking.py
src/req_tracker/query/answering.py
src/req_tracker/query/tools.py
```

### 7.4 새 providers/backends

```text
src/req_tracker/model_gateway/claude_code_provider.py
src/req_tracker/vector/pgvector_backend.py
src/req_tracker/query/postgres_keyword_backend.py
src/req_tracker/graph/postgres_age_backend.py
```

AGE는 Stage A에서 extension availability를 확인한 뒤 추가한다. 먼저 typed relational classification/event tables와 pgvector/FTS만으로 Stage B-F를 전진할 수 있다.

### 7.5 새 API route

```text
src/req_tracker/api/routes/soc_query.py
```

`create_app()`에 router를 추가하고, `tests/contract/test_soc_query_api.py`를 함께 작성한다.

### 7.6 새 UI

```text
src/req_tracker/soc_ui/streamlit_app.py
src/req_tracker/soc_ui/api_client.py
src/req_tracker/soc_ui/render_answer.py
```

추가 dependency 후보:

- `streamlit`
- `sentence-transformers`
- `torch` 또는 CPU-only install 정책
- `pgvector`
- `talon` 또는 quote-removal 대체 라이브러리

dependency는 Stage A에서 설치 가능성과 Windows/Ubuntu/사내망 wheel availability를 확인한 뒤 추가한다.

### 7.7 새 fixtures/eval

```text
fixtures/soc_knowledge/
eval/stages/
ops/evals/run_soc_query_eval.py
ops/evals/compare_soc_answer.py
ops/evals/diagnose_soc_failures.py
tests/evals/test_soc_query_ground_truth.py
tests/unit/ingestion/test_soc_classification.py
tests/unit/ingestion/test_soc_events.py
tests/unit/query/test_soc_slice_classifier.py
```

## 8. 권장 구현 순서

### Step 0. Guardrail 정렬

목표: 새 PoC가 production plan을 깨지 않게 경계를 고정한다.

작업:

- 이 gap report를 기준으로 "SoC PoC는 current production skeleton 위의 domain extension"이라고 명시한다.
- raw Claude subprocess direct call 금지.
- unmasked confidential data 금지.
- AI classification proposal과 approved graph truth 분리.
- AGE/pgvector/Streamlit은 optional profile 또는 PoC entrypoint로 격리.

완료 기준:

- `docs/implementation/13_SOC_KNOWLEDGE_STAGE_PLAN.md`에 boundary가 기록된다.

### Step 1. Stage A contracts

목표: SoC 4축 ontology와 query answer contract를 고정한다.

작업:

- `SocAxisClassification`, `SocLifecycleEvent`, `SocQueryRequest`, `SocAnswer` Pydantic 추가.
- YAML schema/vocab 추가.
- schema validator 추가.
- contract tests 추가.

완료 기준:

- `uv run pytest tests/contract/test_soc_models.py tests/unit/ontology/test_soc_schema_validator.py` 통과.

### Step 2. Stage B seed fixture

목표: full 400개 전에 40개 seed fixture로 schema와 query shape를 검증한다.

작업:

- JIRA 20, Conf 10, Email 10 seed.
- 2개 project, L0-L5, 8 concern, 주요 component coverage.
- Q set 최소 8개, pattern A-D 각 2개.

완료 기준:

- fixture validator 통과.
- 모든 fixture가 source contract로 load 가능.

### Step 3. Stage C classification/event ingestion

목표: fixture를 ingest해 SoC axis index와 lifecycle event를 만든다.

작업:

- rule classifier.
- Claude Code provider classification 보강.
- entity extraction.
- lifecycle event extraction.
- classification/event persistence.

완료 기준:

- seed fixture classification accuracy 85% 이상.
- 모든 artifact에 source_url과 최소 1개 axis classification.
- event query가 lifecycle Q를 반환.

### Step 4. Stage D query API

목표: 4가지 slice pattern을 API로 답변한다.

작업:

- deterministic slice classifier.
- hybrid retrieval service.
- answer JSON generator.
- source URL/provenance validator.
- `/api/v1/soc/query`.

완료 기준:

- seed Q set recall 75% 이상.
- answer JSON schema 100%.
- source URL 100%.
- "찾지 못함" graceful case 통과.

### Step 5. Stage E PoC UI

목표: architect가 자연어로 묻고 답변/source/timeline을 본다.

작업:

- Streamlit app.
- query API client.
- answer card/source/timeline/feedback/reasoning toggle.
- timeout/error UI.

완료 기준:

- local manual smoke: query -> answer -> source link -> feedback 저장.

### Step 6. Stage F full fixture expansion and eval loop

목표: 400 fixture와 20~30 Q에서 acceptance threshold를 통과한다.

작업:

- fixture generator/curation.
- eval runner.
- failure diagnosis.
- regression set.
- eval-run persistence/reload rehearsal.
- eval-run diff report.

완료 기준:

- recall 85% 이상.
- source accuracy 95% 이상.
- graceful failure 100%.
- regression 0.

### Step 7. Stage G real data switch

목표: connector 교체로 real data dry run을 수행한다.

작업:

- JIRA/Confluence real/export path mapping.
- Email approved mailbox/export path.
- 50개 dry run.
- human-reviewed sample classification.
- full ingest.

완료 기준:

- connector mode만 바꿔 fixture -> real 전환.
- sample classification 75% 이상.
- source link 실제 도달.
- Stage H handoff package 생성.

## 9. 최소 변경으로 시작하는 "thin slice"

대폭 개선을 시작하되 blast radius를 줄이려면 첫 구현은 다음 thin slice가 적합하다.

1. SoC ontology/vocab YAML과 Pydantic contract.
2. 40개 seed fixture와 20개 Q set.
3. rule-only 4축 classifier.
4. 기존 memory/vector backend를 사용하는 query service.
5. `/api/v1/soc/query`에서 `concern_slice`, `topic_intersection`, `timeline_slice`, `lifecycle_trace`, `unknown` seed path를 먼저 통과.
6. Claude Code subprocess provider는 model gateway 뒤에 두고, slice planning은 optional planner + deterministic fallback으로 붙인다.
7. Streamlit은 query API만 호출.

이 thin slice는 AGE/pgvector/bge-m3/400 fixture/real source를 한꺼번에 열지 않아도 PoC 설계의 핵심인 "다차원 ontology slice query"가 현재 시스템 위에서 성립하는지 빠르게 검증한다.

## 10. 주요 리스크

| 리스크 | 영향 | 완화 |
| --- | --- | --- |
| AGE/pgvector 설치 권한 없음 | Stage A DB acceptance 실패 | backend profile을 optional로 두고 readiness에서 명확히 실패 |
| Claude Code subprocess trace 누락 | production non-negotiable 위반 | model gateway provider로만 호출 |
| AI classification이 approved graph로 섞임 | 감사/승인 원칙 위반 | classification status와 approval boundary 추가 |
| fixture 400개를 너무 일찍 생성 | schema 수정 비용 증가 | 40개 seed -> schema 안정 -> generator 확장 |
| Streamlit이 core logic을 우회 | API/trace/audit 분리 | Streamlit은 FastAPI client만 사용 |
| Email scope 과확장 | 보안 리스크 | approved export/label/archive만 Stage G 허용 |
| local model dependency가 무거움 | Windows/Ubuntu 설치 실패 | Stage A에서 model loading smoke와 fallback 명시 |
| query template이 ad-hoc SQL/Cypher 실행으로 변질 | injection/권한 리스크 | whitelisted templates와 typed slice plan만 실행 |

## 11. 최종 판단

현재 구현은 새 PoC의 기반으로 충분히 쓸 수 있다. 특히 source adapter boundary, masking/evidence, run/step/LLM trace, model gateway, feedback/eval, approval/audit, API/test 구조는 PoC가 새로 만들 필요가 없다.

현재는 SoC shift-left query가 seed baseline으로는 동작한다. 다만 PoC v4.0의 production-quality 목표와 비교하면 가장 큰 남은 gap은 다음 5개다.

1. AGE/pgvector/Postgres FTS live storage-backed hybrid retrieval target evidence.
2. generated 400 fixture/query loop를 curated eval set과 longitudinal scenario review로 승격.
3. live bge-m3/e5 embedding과 live cross-encoder reranker 품질 acceptance.
4. Streamlit live browser/manual acceptance와 feedback persistence 확인.
5. real JIRA/Confluence/Email source switch sample evidence와 target 환경 반복 evidence.

따라서 다음 구현은 기존 seed baseline을 버리지 말고, `live SoC Postgres integration`, `storage-backed query eval live evidence`, 또는 `Stage E live UI/manual acceptance` 중 하나를 선택해 seed 기능을 실제 실행 품질 gate로 승격하는 것이 가장 안전하다.

## 12. 구현 진행 업데이트

업데이트 시점: 2026-05-25

이번 구현으로 Stage A~F의 seed baseline 일부가 현재 코드에 반영됐다.

| Stage | 구현된 항목 | 검증 |
| --- | --- | --- |
| A. Foundation | SoC Pydantic contract, schema/vocab YAML, schema validator, core-vs-SoC Postgres migration profile split, SoC Postgres pg_trgm/pgvector/AGE migration/static readiness seed, live SoC DB validator, optional bge-m3 local embedding loader seed, local model quality gate, Claude Code provider/quality gate, `eval/stages/A.yaml` | `uv run python ops/ontology/validate_soc_schema.py --format json`; `uv run python ops/rehearsal/validate_soc_postgres_profile.py`; `uv run python ops/rehearsal/validate_soc_live_postgres.py`; `uv run python ops/evals/smoke_soc_embedding_model.py --dry-run --format json`; `uv run python ops/evals/run_soc_local_model_quality_gate.py --dry-run --format json`; `uv run python ops/evals/run_soc_claude_quality_gate.py --dry-run --format json` |
| B. Fixture & Data Model | 40개 seed fixture, generated 400 scale fixture, 20개 seed Q, generated 30 scale Q, fixture loader, `eval/stages/B.yaml` | `uv run python ops/fixtures/validate_soc_fixtures.py --format json`; `uv run python ops/fixtures/validate_soc_fixtures.py --coverage-mode scale --format json` |
| C. Ingestion Fixture Mode | rule-only 4축 classifier, rule Artifact/Person entity extractor, side-car `mentions`/`authoredBy` semantic relation projection, classification recall validator, skip-safe fixture ingestion workflow rehearsal, lifecycle event/storage projection counts, stable ID idempotency rehearsal, `eval/stages/C.yaml` | `uv run pytest tests/unit/ingestion/test_soc_classification.py tests/unit/ingestion/test_soc_entity_extraction.py -q`; `uv run python ops/rehearsal/run_soc_fixture_ingestion_workflow.py --coverage-mode scale --format json`; `uv run python ops/rehearsal/run_soc_ingestion_idempotency_check.py --coverage-mode scale --format json` |
| D. Retrieval & Query | deterministic slice classifier, optional model-gateway `SocSlice` planner, typed query tool planner, lexical/model-gateway/cross-encoder rerank seed, local model quality gate, Claude Code slice/plan/answer quality gate, injectable Postgres hybrid retrieval adapter seed, relation-based AGE query/loader seed, optional AGE semantic `MENTIONS`/`AUTHORED_BY` projection, SoC Postgres storage profile migrations/static/live validator, fixture-to-Postgres artifact/classification/lifecycle event writer seed, live storage rehearsal, storage-backed query eval gate, optional answer assembler, fixture-backed query service, `/api/v1/soc/query`, seed query eval runner, `eval/stages/D.yaml` | `uv run python ops/evals/run_soc_query_eval.py --format json`; `uv run python ops/evals/run_soc_storage_backed_query_eval.py --dry-run --format json`; `uv run python ops/evals/run_soc_local_model_quality_gate.py --dry-run --format json`; `uv run python ops/evals/run_soc_claude_quality_gate.py --dry-run --format json`; `uv run python ops/rehearsal/validate_soc_postgres_profile.py`; `uv run python ops/rehearsal/validate_soc_live_postgres.py`; `uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --format json`; `uv run pytest tests/unit/storage/test_soc_postgres_loader.py -q` |
| E. UI | API-only Streamlit seed entrypoint, FastAPI query/feedback client, answer/source/timeline rendering helper, session-state conversation, reasoning toggle, dry-run smoke, single-session live browser query/feedback smoke, explicit two-session/source-link live smoke, PostgreSQL-backed answer feedback restart-restore rehearsal, SoC UI guide, `eval/stages/E.yaml` | `uv run pytest tests/unit/soc_ui/test_soc_ui_client.py tests/unit/ops/test_soc_stage_e_foundation.py -q`; `uv run python ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json`; `uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url http://127.0.0.1:18580 --format json`; local Playwright browser smoke on `127.0.0.1:18580`; `uv run python ops/rehearsal/run_full_stack_rehearsal.py --api-port 18081 --timeout-seconds 180` |
| F. E2E Validation Loop | answer-vs-ground-truth comparer, failure diagnosis by layer, regression detection, generated scale eval, storage-backed query eval acceptance, `soc_eval_runs` persistence/reload rehearsal, eval-run metric diff report, `eval/stages/F.yaml` | `uv run python ops/evals/compare_soc_answer.py --format json`; `uv run python ops/evals/compare_soc_answer.py --coverage-mode scale --format json`; `uv run python ops/evals/run_soc_storage_backed_query_eval.py --dry-run --format json`; `uv run python ops/evals/run_soc_eval_persistence_rehearsal.py --coverage-mode scale --format json`; `uv run python ops/evals/diff_soc_eval_runs.py --coverage-mode scale --format json` |
| G. Real Data Switch | Stage G acceptance YAML, source skill presence check, adapter boundary check, token/DSN-masked real-source readiness rehearsal, explicit live env requirements for JIRA/Confluence/decision-email export and target DB | `uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --dry-run --format json`; `uv run pytest tests/unit/ops/test_soc_stage_g_foundation.py tests/unit/ops/test_soc_real_source_switch_rehearsal.py -q` |

최근 검증 스냅샷:

- `uv run pytest tests/unit/query/test_soc_reranking.py tests/unit/query/test_soc_orchestration.py tests/unit/query/test_soc_runtime_planner.py tests/contract/test_soc_query_api.py tests/unit/ops/test_soc_stage_d_foundation.py -q`: 24 passed.
- `uv run pytest tests/unit/query/test_soc_storage_retrieval.py tests/unit/query/test_soc_query_service.py tests/unit/query/test_soc_runtime_planner.py tests/unit/ops/test_soc_stage_d_foundation.py -q`: 22 passed.
- `uv run pytest tests/unit/storage/test_soc_postgres_loader.py tests/unit/query/test_soc_storage_retrieval.py tests/unit/storage/test_postgres_store.py tests/unit/ops/test_soc_postgres_profile_validator.py tests/unit/ops/test_soc_stage_a_foundation.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_production_readiness_check.py tests/unit/ops/test_postgres_migration_rollback_validator.py -q`: 52 passed.
- `uv run pytest tests/unit/graph/test_soc_age_loader.py tests/unit/query/test_soc_storage_retrieval.py tests/unit/ops/test_soc_stage_d_foundation.py -q`: 8 passed.
- `uv run python ops/rehearsal/validate_soc_postgres_profile.py`: passed, checked `soc_artifacts`, `soc_classifications`, `soc_event_log`, `soc_eval_runs`, `soc_artifact_embeddings`, and `soc_graph`.
- `uv run python ops/rehearsal/validate_soc_live_postgres.py`: skipped without DSN, and now provides an explicit live readiness gate for `pg_trgm`, `vector`, `age`, SoC tables/indexes, and `soc_graph` without printing the DSN.
- `uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --format json`: skipped without DSN, and now provides an explicit target DB gate for profile validation, fixture table load, AGE graph load including semantic relation counts, and hybrid sourced retrieval without printing the DSN.
- `uv run python ops/evals/run_soc_storage_backed_query_eval.py --dry-run --format json`: skipped without DSN, and now provides an explicit target DB query quality gate for seed/scale ground-truth queries, recall, source accuracy, schema, unknown handling, and regression metrics without printing the DSN.
- `uv run python ops/rehearsal/validate_postgres_migration_rollbacks.py`: passed, migration/rollback versions 001~013.
- `uv run python ops/rehearsal/validate_ci_gate_coverage.py`: passed, missing required commands 0, CI command count 39.
- `uv run pytest tests/unit/ops/test_soc_live_storage_rehearsal.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/query/test_soc_storage_retrieval.py tests/unit/graph/test_soc_age_loader.py tests/unit/ops/test_production_readiness_check.py::test_local_gate_commands_include_staging_evidence_plan_smoke -q`: 13 passed.
- `uv run pytest tests/unit/query/test_soc_storage_retrieval.py tests/unit/query/test_soc_query_service.py tests/unit/query/test_soc_runtime_planner.py tests/unit/storage/test_soc_postgres_loader.py tests/unit/graph/test_soc_age_loader.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_soc_live_storage_rehearsal.py tests/unit/ops/test_production_readiness_check.py -q`: 56 passed.
- `uv run python ops/ontology/validate_soc_schema.py --format json`: status passed, schema `soc-v0.1`.
- `uv run python ops/fixtures/validate_soc_fixtures.py --format json`: status passed, 40 artifacts / 20 queries / classification recall 1.0.
- `uv run python ops/fixtures/validate_soc_fixtures.py --coverage-mode scale --format json`: status passed, 400 artifacts / 200 JIRA / 100 Confluence / 100 Email / 30 queries / classification recall 1.0.
- `uv run python ops/evals/compare_soc_answer.py --coverage-mode scale --format json`: status passed, 400 artifacts / 30 queries / recall 1.0 / source accuracy 1.0 / full Stage F ready true.
- `uv run pytest tests/unit/ops/test_soc_storage_backed_query_eval.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_soc_stage_f_foundation.py -q`: initial RED failed because `ops/evals/run_soc_storage_backed_query_eval.py` and ACC-D/F live entries were missing; after implementation 9 passed.
- `uv run pytest tests/unit/evals/test_soc_query_eval.py tests/unit/ops/test_soc_eval_persistence_rehearsal.py tests/unit/storage/test_postgres_store.py::test_postgres_store_typed_soc_eval_run_table tests/unit/ops/test_soc_stage_f_foundation.py -q`: initial RED failed because `build_soc_eval_run_record` was missing; after implementation 13 passed.
- `uv run python ops/evals/run_soc_eval_persistence_rehearsal.py --coverage-mode scale --format json`: status passed, persisted collection `soc_eval_runs`, coverage_mode `scale`, 30 queries / 400 artifacts / regression_count 0, reloaded record matched persisted record.
- `uv run pytest tests/unit/storage/test_postgres_store.py -q`: 15 passed.
- `uv run pytest tests/unit/evals/test_soc_query_eval.py tests/unit/ops/test_soc_eval_diff.py tests/unit/ops/test_soc_stage_f_foundation.py -q`: initial RED failed because `diff_soc_eval_run_records` was missing; after implementation 13 passed.
- `uv run python ops/evals/diff_soc_eval_runs.py --coverage-mode scale --format json`: status passed, coverage_mode `scale`, regression_delta 0, regressed_metrics empty, report_only true.
- `uv run pytest tests/unit/storage/test_soc_postgres_loader.py tests/unit/ops/test_soc_stage_a_foundation.py tests/unit/ops/test_soc_stage_d_foundation.py -q`: initial RED failed because `lifecycle_events_for_artifacts` was missing; after implementation 9 passed.
- `uv run python ops/rehearsal/validate_soc_postgres_profile.py`: passed after lifecycle event writer update; `soc_event_log` table and `idx_soc_event_log_entity_ts` remain covered.
- `uv run pytest tests/unit/workflows/test_soc_knowledge_workflow.py tests/unit/ops/test_soc_fixture_ingestion_workflow.py tests/unit/ops/test_soc_stage_b_c_foundation.py -q`: initial RED failed because `req_tracker.workflows.soc_knowledge` was missing; after implementation 7 passed.
- `uv run python ops/rehearsal/run_soc_fixture_ingestion_workflow.py --coverage-mode scale --format json`: status passed, 400 artifacts / 1600 classifications / 400 events / 4 workflow steps, live_storage_required 0.
- `uv run pytest tests/unit/ingestion/test_soc_entity_extraction.py tests/unit/workflows/test_soc_knowledge_workflow.py tests/unit/ops/test_soc_fixture_ingestion_workflow.py tests/unit/ops/test_soc_stage_b_c_foundation.py -q`: initial RED failed because `req_tracker.ingestion.soc_entity_extraction` was missing; after implementation 10 passed.
- `uv run python ops/rehearsal/run_soc_fixture_ingestion_workflow.py --coverage-mode scale --format json`: status passed after entity extraction; 400 artifacts / 1600 classifications / 427 extracted entities / 800 semantic relations / 400 events / 5 workflow steps.
- `uv run pytest tests/unit/graph/test_soc_age_loader.py tests/unit/ops/test_soc_stage_b_c_foundation.py tests/unit/ops/test_soc_stage_d_foundation.py -q`: initial RED failed because `SocAgeGraphLoader.upsert_artifact_graph(..., semantic_relations=...)` was missing and Stage C did not name `AUTHORED_BY`; after implementation 7 passed.
- `uv run pytest tests/unit/workflows/test_soc_knowledge_workflow.py tests/unit/ops/test_soc_fixture_ingestion_workflow.py tests/unit/ops/test_soc_ingestion_idempotency_check.py tests/unit/ops/test_soc_stage_b_c_foundation.py -q`: initial RED failed because `idempotency_fingerprint`, `run_soc_ingestion_idempotency_check.py`, and ACC-C-SEED-06 were missing; after implementation 10 passed.
- `uv run python ops/rehearsal/run_soc_ingestion_idempotency_check.py --coverage-mode scale --format json`: status passed, fingerprint_match true, duplicate_candidate_count 0, 400 artifacts / 1600 classifications / 427 entities / 800 relations / 400 events.
- `uv run pytest tests/unit/ops/test_soc_live_storage_rehearsal.py tests/unit/ops/test_soc_stage_d_foundation.py -q`: initial RED failed because live storage rehearsal did not pass semantic relations into `SocAgeGraphLoader`; after implementation 5 passed and Stage D live acceptance requires `age_graph_load.counts.semantic_relations > 0`.
- `uv run pytest tests/unit/ingestion/test_soc_classification.py tests/unit/ops/test_soc_classifier_enrichment_gate.py tests/unit/ops/test_soc_stage_b_c_foundation.py tests/unit/model_gateway/test_http_provider_and_registry.py -q`: initial RED failed because `GatewaySocAxisClassifier` and `run_soc_classifier_enrichment_gate.py` were missing; after implementation 17 passed.
- `uv run python ops/evals/run_soc_classifier_enrichment_gate.py --dry-run --format json`: status skipped, requires_live true, prompt `pv_soc_axis_classification_v1`, response model `SocAxisClassificationBatch`.
- `uv run pytest tests/unit/model_gateway/test_claude_code_provider.py tests/unit/ops/test_soc_classifier_enrichment_gate.py tests/unit/ops/test_soc_claude_quality_gate.py -q`: initial RED failed because Claude Code provider lacked JSON-only structured prompt instructions, fenced JSON extraction, and gate example outputs; after implementation 12 passed.
- `uv run python ops/evals/run_soc_classifier_enrichment_gate.py --live --format json`: status passed, `classifier_enrichment.status=passed`, proposal_count 3, pending_count 3, trace_count 1.
- `uv run pytest tests/unit/ops/test_soc_stage_a_foundation.py tests/unit/ops/test_soc_stage_b_c_foundation.py -q`: initial RED failed because A11/C8/C9 acceptance YAML labels were stale; after reconciliation these entries point to existing folder, local embedder, and graph/index builder seed evidence.
- `uv run python ops/evals/smoke_soc_embedding_model.py --dry-run --format json`: status skipped, mode dry_run, model `BAAI/bge-m3`, expected dimensions 1024.
- `uv run python ops/evals/smoke_soc_cross_encoder_reranker.py --dry-run --format json`: status skipped, mode dry_run, model `BAAI/bge-reranker-v2-m3`.
- `uv run python ops/evals/run_soc_local_model_quality_gate.py --dry-run --format json`: status skipped, requires_live true, embedding/reranker quality checks reported.
- `uv run pytest tests/unit/ops/test_soc_local_model_quality_gate.py tests/unit/ops/test_soc_stage_a_foundation.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_soc_embedding_smoke.py tests/unit/ops/test_soc_cross_encoder_smoke.py tests/unit/vector/test_local_embedding.py tests/unit/query/test_soc_reranking.py -q`: 16 passed.
- `uv run python ops/evals/run_soc_claude_quality_gate.py --dry-run --format json`: status skipped, requires_live true, `slice_planning`, `query_tool_planning`, `answer_assembly` checks reported for `claude-code-local`.
- `uv run python ops/evals/run_soc_claude_quality_gate.py --live --format json`: status passed, `slice_planning`, `query_tool_planning`, and `answer_assembly` all schema-validated; answer assembly preserved one source URL; trace_count 3.
- `uv run pytest tests/unit/ops/test_soc_claude_quality_gate.py tests/unit/ops/test_soc_stage_a_foundation.py tests/unit/ops/test_soc_stage_d_foundation.py tests/unit/ops/test_claude_code_provider_smoke.py tests/unit/query/test_soc_query_planner.py tests/unit/query/test_soc_orchestration.py -q`: 18 passed.
- `uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --dry-run --format json`: status skipped, requires_live true, `source_skills.status=passed`, `adapter_boundaries.status=passed`, `live_source_access.status=skipped`, missing live env vars reported without secrets.
- `uv run pytest tests/unit/ops/test_soc_stage_g_foundation.py tests/unit/ops/test_soc_real_source_switch_rehearsal.py -q`: 4 passed.
- `uv run python ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json`: status passed, api_only true, entrypoint `src/req_tracker/soc_ui/streamlit_app.py`.
- `uv run pytest tests/unit/soc_ui/test_soc_ui_client.py tests/unit/ops/test_soc_stage_e_foundation.py -q`: Stage E guide coverage included; current focused Stage E foundation test has 6 passed.
- Local live UI smoke: FastAPI `127.0.0.1:18080` health returned ok; direct `/api/v1/soc/query` returned `soc_ui_live_smoke_001` with confidence high; Playwright submitted a Streamlit query on `127.0.0.1:18580` and rendered answer/source cards; feedback submit rendered `Feedback recorded.` and FastAPI log showed `/api/v1/feedback` 200.
- Explicit two-session live UI smoke: FastAPI `127.0.0.1:18082` + Streamlit `127.0.0.1:18582`; `uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url http://127.0.0.1:18582 --format json --timeout-seconds 45` returned `status=passed`, with `two_browser_sessions`, `session_isolation`, `source_link_present`, `source_link_clickable`, and `feedback_form_available`; session A source link count 8, session B source link count 16.
- `uv run python ops/evals/run_soc_query_eval.py --format json`: status passed, recall 1.0, source accuracy 1.0, schema pass rate 1.0, graceful unknown pass rate 1.0.
- `uv run python ops/evals/compare_soc_answer.py --format json`: status passed, regression count 0, full Stage F ready false.
- `uv run pytest tests/unit/fixtures/test_soc_knowledge_fixtures.py tests/unit/evals/test_soc_query_eval.py tests/unit/ops/test_soc_stage_b_c_foundation.py tests/unit/ops/test_soc_stage_f_foundation.py -q`: 16 passed.
- `uv run ruff check .`: all checks passed.
- `uv run mypy src`: no issues in 133 source files.
- `uv lock --check`: resolved lock is current.
- `uv run pytest`: 425 passed, 3 skipped.
- `uv run python ops/integration/run_backend_integration.py --timeout-seconds 180`: 3 passed against disposable PostgreSQL/Neo4j/Qdrant; the Postgres app state-store path used `POSTGRES_MIGRATION_PROFILE=core`.
- `uv run python ops/rehearsal/run_full_stack_rehearsal.py --api-port 18081 --timeout-seconds 180`: passed, with PostgreSQL state store, Neo4j graph backend, Qdrant vector backend, API restart restore, answer feedback persistence restore, and smoke load all passing.

현재 Stage D seed baseline은 다음을 만족한다.

- Stage C ingestion workflow: `SocKnowledgeIngestionWorkflow`가 seed/scale fixture를 source snapshot, rule classification, entity/relation extraction, lifecycle event generation, storage projection 단계로 통과시키고 각 단계를 `AgentStepTrace`로 남긴다.
- Stage C classifier enrichment seed: `GatewaySocAxisClassifier`가 `ModelGatewayClient.complete(..., response_model=SocAxisClassificationBatch)`를 통해 Claude Code classifier 보강 출력을 구조 검증하고, 결과를 `source=claude`, `status=pending` side-car proposal로만 반환한다. `ops/evals/run_soc_classifier_enrichment_gate.py`는 기본 dry-run에서 비용 없이 prompt/model contract를 보고하고 `--live`에서 실제 Claude 품질 gate를 수행한다.
- Stage C entity extraction: `extract_soc_entities_for_artifacts()`가 explicit `links`와 body text의 JIRA-key-like artifact references를 side-car `mentions` relation으로, `author_id`를 `Person` entity와 `authoredBy` relation으로 projected한다.
- Stage C idempotency: rule classification, semantic relation, and lifecycle event IDs are stable across run IDs, and `run_soc_ingestion_idempotency_check.py` compares repeated scale fixture ingestion by stable IDs/counts/projection without live storage.
- Stage C local embedder and graph/index builder seed: Stage C acceptance now points to existing `LocalSentenceTransformerEmbedder`, dry-run/live local model gates, `SocPostgresFixtureLoader`, `SocAgeGraphLoader`, pgvector/AGE adapters, and live storage rehearsal. These are seed/local gates; target DB and live model evidence remain explicit external gates.
- query pattern: `concern_slice`, `topic_intersection`, `timeline_slice`, `lifecycle_trace`, `unknown`.
- API: `POST /api/v1/soc/query`.
- answer contract: `SocAnswer` schema, source URL, confidence, timeline, persisted `reasoning_log_ref`, graceful unknown.
- optional query planning: `GatewaySocSlicePlanner`가 `ModelGatewayClient.complete(..., response_model=SocSlice)`로 structured validation과 `LLMCallTrace`를 남기고, 실패 시 deterministic `classify_soc_slice()`로 fallback한다.
- runtime wiring: 기본값은 deterministic이지만 `SOC_QUERY_PLANNER_MODE=model_gateway`, `SOC_QUERY_PLANNER_MODEL_PROFILE_ID=...`로 FastAPI runtime에서 planner를 구성할 수 있다.
- typed tool planning: `SocQueryPlan` / `SocQueryToolCall` contract가 추가되어 whitelisted tool call만 허용하고 `sql`, `cypher`, `raw_query` argument를 schema validation 단계에서 거부한다.
- storage retrieval seed: `PostgresHybridSocRetrievalBackend`가 AGE, FTS/pg_trgm, pgvector query adapters를 parameterized SQL로 조합하고, `SOC_RETRIEVAL_BACKEND=postgres_hybrid`로 runtime wiring이 가능하다.
- live storage rehearsal: `ops/rehearsal/run_soc_live_storage_rehearsal.py`가 `POSTGRES_TEST_DSN=<target> ... --require-live --apply-migrations`에서 profile validation, fixture load, AGE graph load, semantic relation count, hybrid retrieval, source URL provenance를 검증한다.
- storage-backed query eval gate: `ops/evals/run_soc_storage_backed_query_eval.py`가 기본 `--dry-run`에서 skip-safe contract를 보고하고, `--live`에서는 target DSN에 seed/scale fixture를 적재한 뒤 `PostgresHybridSocRetrievalBackend`를 통해 query recall/source/schema/regression metric을 계산한다.
- migration safety: `PostgreSQLStateStore` 기본값은 `POSTGRES_MIGRATION_PROFILE=core`라 vanilla PostgreSQL에서 core persistence를 유지하고, `POSTGRES_MIGRATION_PROFILE=soc`를 명시할 때만 011~013 SoC pg_trgm/pgvector/AGE profile을 적용한다.
- storage profile seed: `011_soc_knowledge_tables.sql`, `012_soc_pgvector_tables.sql`, `013_soc_age_schema.sql`이 `soc_artifacts`, `soc_classifications`, `soc_event_log`, `soc_eval_runs`, `soc_artifact_embeddings`, `soc_graph`를 정의하고 rollback과 static validator를 가진다.
- fixture-to-Postgres writer seed: `SocPostgresFixtureLoader`가 artifact, axis classification, source-linked `artifact_synced` lifecycle event, 1024-dimension deterministic embedding을 Postgres profile table에 upsert하는 SQL path를 제공한다.
- AGE graph loader seed: `SocAgeGraphLoader`가 `Artifact`에서 `Project`, `VLevel`, `Concern`, `Component`로 이어지는 `BELONGS_TO_PROJECT`, `AT_LEVEL`, `ADDRESSES`, `INVOLVES` 관계와 `MENTIONS`/`AUTHORED_BY` semantic relations를 parameterized Cypher wrapper로 적재한다. Live storage rehearsal now passes extracted semantic relations into this loader, and `PostgresAgeGraphBackend`의 query Cypher도 axis 관계를 통해 slice를 필터링한다.
- optional answer assembly: `GatewaySocAnswerAssembler`가 `SocAnswer` structured output을 검증하고, 실패하면 deterministic sourced answer로 fallback한다.
- seed reranking: `LexicalSocReranker`가 deterministic fallback을 제공하고, `GatewaySocReranker`가 `SocRerankResult` structured output을 검증해 후보 순서를 재정렬한다. `CrossEncoderSocReranker`는 optional `sentence-transformers` local model을 lazy-load하며 실패 시 lexical fallback으로 돌아간다.
- runtime wiring: 기본값은 deterministic이지만 `SOC_QUERY_PLANNER_MODE`, `SOC_QUERY_TOOL_PLANNER_MODE`, `SOC_RERANKER_MODE`, `SOC_ANSWER_ASSEMBLER_MODE`를 `model_gateway`로 설정하면 각 단계를 registry profile/prompt 기반으로 켤 수 있다.
- debug lineage: `/api/v1/soc/query`는 query 단위 `AgentRun(run_type=query)`과 `soc_query_received`, `soc_slice_planning`, `soc_query_tool_planning`, `soc_seed_retrieval`, `soc_rerank`, `soc_answer_projection` step trace를 남긴다. Gateway planner/reranker/assembler가 켜진 경우 `LLMCallTrace`도 같은 query run에 연결된다.
- seed eval result: 20개 query, recall 1.0, source accuracy 1.0, schema pass rate 1.0, graceful unknown pass rate 1.0.
- Stage F seed comparison: failure layer는 `answer_schema`, `unknown_handling`, `retrieval`, `source_link`, `precision`으로 분류된다.
- Stage F seed regression guard: packaged passing Q set 기준 regression count 0을 확인한다.
- Stage F eval-run persistence: `build_soc_eval_run_record()`와 `persist_soc_eval_run()`이 query eval report를 compact metrics/metadata와 report hash를 포함한 `soc_eval_runs` payload로 저장하고, local rehearsal이 SQLite state store에서 재조회 일치를 검증한다.
- Stage F eval-run diff: `diff_soc_eval_run_records()`와 `ops/evals/diff_soc_eval_runs.py`가 baseline/candidate eval-run의 recall/source/schema/unknown/regression deltas를 report-only JSON으로 비교하고, regression metric을 자동 promotion 없이 표시한다.
- Claude Code subprocess provider: `src/req_tracker/model_gateway/claude_code_provider.py`가 추가되어 직접 subprocess 호출 대신 `ModelGatewayClient` trace/policy/validation 경로를 사용할 수 있다.
- prompt registry: `pv_soc_slice_planning_v1`, `pv_soc_query_tool_planning_v1`, `pv_soc_rerank_v1`, `pv_soc_answer_assembly_v1`이 추가되어 Stage D의 LLM 보조 단계를 registry에서 표현할 수 있다.
- model registry: `claude-code-local` profile이 추가되어 live Claude Code subprocess planner를 설정으로 선택할 수 있다. 현재 로컬 CLI는 `claude -p --output-format json` 형태라 profile endpoint alias도 이 형태로 맞췄다.
- Claude CLI compatibility: provider가 Claude CLI의 `{"type":"result","result":"..."}` wrapper를 provider-neutral `output` JSON으로 정규화한다. `ops/model_gateway/smoke_claude_code_provider.py --dry-run`은 비용 없이 command/profile wiring을 확인하고, `--live`를 명시할 때만 실제 모델 호출을 수행한다.
- Claude structured output hardening: provider payload가 JSON-only 지시와 expected output envelope를 포함하고, Claude CLI `result` 문자열 안의 fenced/prose JSON object를 추출한다.
- Claude Code quality gate: `ops/evals/run_soc_claude_quality_gate.py`가 기본 `--dry-run`에서 비용 없이 slice planning, typed query tool planning, answer assembly check contract를 보고하고, `--live`에서는 model gateway를 통해 `SocSlice`, `SocQueryPlan`, `SocAnswer` structured validation과 source URL 보존을 확인한다. 2026-05-27 현재 환경에서 `--live`가 통과했다.

현재 Stage A local model seed baseline은 다음을 만족한다.

- embedding loader: `LocalSentenceTransformerEmbedder`가 `sentence_transformers.SentenceTransformer`를 lazy-load하고 `embed_text`, `embed_texts`, `embed_artifact`, `warmup`을 제공한다.
- model defaults: `SOC_EMBEDDING_MODEL_NAME=BAAI/bge-m3`, `SOC_EMBEDDING_DIMENSIONS=1024`.
- validation: model output vector count, numeric conversion, expected dimension, optional L2 normalization을 검증한다.
- install boundary: heavy local model dependency는 core dependency가 아니라 `soc-models` optional extra로 둔다.
- dry-run smoke: `ops/evals/smoke_soc_embedding_model.py --dry-run --format json`이 live model download 없이 model/dimension wiring을 확인한다.
- quality gate: `ops/evals/run_soc_local_model_quality_gate.py --live --format json`이 seed Q2 기준 embedding recall@k와 cross-encoder reranker recall@k를 확인한다. 기본 `--dry-run`은 모델을 로드하지 않고 gate contract만 보고한다.

현재 Stage E seed baseline은 다음을 만족한다.

- Streamlit entrypoint: `src/req_tracker/soc_ui/streamlit_app.py`.
- API boundary: UI는 DB/Claude Code subprocess를 직접 호출하지 않고 `SocKnowledgeApiClient`를 통해 `/api/v1/soc/query`, `/api/v1/feedback`만 호출한다.
- answer rendering: `SocAnswer`를 answer card, source link, timeline, reasoning log reference view로 변환한다.
- feedback: 기존 `FeedbackEvent.target_type="answer"`와 reason-code taxonomy를 재사용한다.
- feedback persistence: full-stack rehearsal이 PostgreSQL state store에 answer feedback을 기록하고 API restart 후 summary count를 확인한다.
- session isolation seed: `session_state`에 `session_id`와 message history만 저장한다.
- optional dependency: Streamlit은 core runtime dependency가 아니라 `soc-ui` optional extra로 둔다.
- dry-run smoke: `ops/ui/smoke_soc_streamlit_ui.py --dry-run --format json`이 live backend 없이 import/API boundary를 확인한다.
- live smoke: Playwright CLI로 `http://127.0.0.1:18580`에서 질문 제출, answer/source card 렌더링, feedback submit 성공을 확인했다.
- live acceptance smoke contract: `ops/ui/smoke_soc_streamlit_ui.py --live --ui-url ...`가 two browser sessions, session isolation, source link presence/actionability, feedback form availability를 확인한다. 2026-05-25 local run은 `127.0.0.1:18582`에서 통과했다.
- UI usage guide: `docs/runbooks/SOC_KNOWLEDGE_UI_GUIDE.md`가 local/target run commands, `SOC_UI_API_BASE_URL`, `/api/v1/soc/query`, `/api/v1/feedback`, live smoke, feedback checks, session isolation, and secret-handling rules를 정리한다.

다만 이것은 PoC 설계의 최종 Stage D/E가 아니라 seed deterministic/API-only baseline이다. 아직 남은 gap은 명확하다.

1. `C/D1~D4`: fixture ingestion workflow, classifier enrichment proposal path, entity/relation projection, stable ID idempotency rehearsal, AGE Cypher, pgvector, Postgres FTS/pg_trgm query adapter seed, core-vs-SoC migration profile split, SoC Postgres migrations/static/live readiness validator, fixture artifact/classification/event writer seed, AGE graph loader seed, semantic relation graph projection, live storage rehearsal gate는 있으나 target DB에서의 passing live DB execution, company DB rehearsal evidence는 아직 아니다.
2. `A6/D5`: bge-m3/e5 embedding loader와 lexical/gateway/cross-encoder rerank seed 및 explicit local model quality gate는 있으나 실제 live model execution evidence는 아직 기본 CI에 포함하지 않았다.
3. `D7~D9`: optional slice planning, typed tool-call planning, answer assembly, structured-output hardening, and live SoC Claude quality gate evidence는 확보됐다. 다만 AGE/pgvector/FTS live tool execution은 target DB evidence에 묶여 아직 남아 있다.
4. `D10`: seed query run/step lineage는 추가됐지만, storage-backed persistence와 replay diff까지 포함하는 full production debug workbench 연동은 아직 아니다.
5. `F`: 20개 seed Q loop, generated 400-fixture/30-Q scale loop, skip-safe storage-backed query eval gate, `soc_eval_runs` local persistence rehearsal, eval-run diff report는 있으나, manual curated scale eval, target DSN live storage-backed retrieval acceptance evidence, target Postgres-backed eval-run evidence, promotion-gate integration은 아직 아니다.
6. `E`: Streamlit seed UI는 API-only 경계, single-session live browser query/feedback smoke, explicit two-session/source-link live smoke 실행 통과, PostgreSQL-backed answer feedback restart-restore rehearsal, usage guide까지 확인됐지만, target 환경 반복 evidence는 아직 아니다.
7. `G`: Stage G acceptance YAML과 skip-safe real-source switch readiness gate는 추가됐지만, 실제 JIRA/Confluence/decision-email sample fetch, 사람이 검토한 real sample classification, full ingest, incremental sync evidence는 아직 외부 승인/credential 의존으로 남아 있다.

따라서 다음 gap-minimizing 순서는 target DB를 연결해 `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json`과 `POSTGRES_TEST_DSN=<target> uv run python ops/evals/run_soc_storage_backed_query_eval.py --live --require-live --apply-migrations --coverage-mode scale --format json`을 실제로 통과시키는 것이다. 병렬로 Stage E target 환경 반복 evidence와 Stage G real-source sample evidence를 확보한다.

### 12.1 2026-05-27 T029 Remaining Evidence Recheck

이번 recheck에서는 새 구현을 추가하지 않고, 현재 환경에서 남은 live/manual evidence를 수집할 수 있는지 확인했다. 결론은 명확하다. target DB/source/model/manual 입력이 제공되지 않았으므로 최종 PoC evidence는 아직 닫을 수 없지만, local skip-safe gate들은 의도대로 동작한다.

- Target DB: `POSTGRES_TEST_DSN`/`POSTGRES_DSN`이 없어서 `validate_soc_live_postgres.py`, `run_soc_live_storage_rehearsal.py`, `run_soc_storage_backed_query_eval.py` 모두 `status=skipped`로 종료했다. 실패 이유는 DSN 부재이며 secret 값은 출력하지 않았다.
- Live local model: 현재 uv 환경에 `sentence_transformers`와 `torch`가 없고 `HF_HOME`/`SENTENCE_TRANSFORMERS_HOME`도 없다. `run_soc_local_model_quality_gate.py --dry-run`은 model contract만 보고하고 live model load는 수행하지 않았다.
- Claude Code: Claude CLI는 존재하고, T028에서 classifier enrichment와 slice/tool/answer quality gate의 live structured-output evidence가 이미 통과했다.
- Real source switch: `run_soc_real_source_switch_rehearsal.py --dry-run`은 source skill presence와 adapter boundary를 통과했지만 JIRA/Confluence/decision-email live env와 target DB가 없어 live source access는 skipped다.
- UI: `smoke_soc_streamlit_ui.py --dry-run`은 `status=passed`로 API-only Streamlit boundary를 확인했다. target 환경 반복 live browser evidence는 아직 필요하다.

남은 owner-provided inputs는 target SoC PostgreSQL DSN, approved local model install/cache, approved JIRA/Confluence/decision-email source inputs, target Streamlit URL/running services, manual curation records다. 이 입력이 제공되면 다음 evidence gate를 우선 실행한다.

1. `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/validate_soc_live_postgres.py --require-live`
2. `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_live_storage_rehearsal.py --require-live --apply-migrations --format json`
3. `POSTGRES_TEST_DSN=<target> uv run python ops/evals/run_soc_storage_backed_query_eval.py --live --require-live --apply-migrations --coverage-mode scale --format json`
4. `uv run python ops/evals/run_soc_local_model_quality_gate.py --live --format json`
5. `POSTGRES_TEST_DSN=<target> uv run python ops/rehearsal/run_soc_real_source_switch_rehearsal.py --live --require-live --format json`
6. `uv run python ops/ui/smoke_soc_streamlit_ui.py --live --ui-url <target-streamlit-url> --format json`

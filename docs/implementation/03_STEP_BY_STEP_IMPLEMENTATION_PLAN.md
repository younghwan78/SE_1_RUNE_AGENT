# Step-by-Step Implementation Plan

## 1. 구현 전략

실제 데이터가 없으므로 dummy mode를 first-class implementation으로 둔다. 단, dummy mode는 데모용 shortcut이 아니라 production contract를 검증하는 adapter이다.

각 step은 다음을 가진다.

- 구현 범위
- 주요 파일
- dummy data 검증
- 테스트 기준
- 완료 기준

## 2. Step 0: Repository Baseline

목표: 개발 시작 전 기본 repository shape를 만든다.

구현:

- `pyproject.toml`
- `.python-version`
- `src/req_tracker/__init__.py`
- `tests/`
- `docs/`
- `ops/`
- `README.md`
- `.env.example`

의존성 초안:

```text
fastapi
uvicorn
pydantic
pydantic-settings
sqlalchemy
alembic
httpx
pytest
pytest-cov
ruff
mypy
```

LLM, Neo4j, Qdrant dependency는 interface가 잡힌 뒤 추가한다.

검증:

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

완료 기준:

- 빈 test라도 CI command가 통과한다.
- package import가 가능하다.

## 3. Step 1: Common Contracts

목표: 생산 시스템의 모든 데이터 흐름을 Pydantic contract로 고정한다.

주요 파일:

```text
src/req_tracker/ontology/models.py
src/req_tracker/debug/models.py
src/req_tracker/model_gateway/models.py
src/req_tracker/approvals/models.py
src/req_tracker/feedback/models.py
tests/contract/test_models.py
```

구현:

- `SourceArtifact`
- `EvidenceSpan`
- `ArtifactChunk`
- `OntologyNode`
- `TraceabilityEdge`
- `Finding`
- `AgentRun`
- `AgentStepTrace`
- `LLMCallTrace`
- `ModelProfile`
- `PromptVersion`
- `GraphDelta`
- `ApprovalItem`
- `FeedbackEvent`

Dummy 검증:

- fixture object를 모두 Pydantic validate
- JSON serialization round-trip
- invalid enum, missing evidence, invalid confidence rejection

완료 기준:

- 모든 core contract가 schema export 가능
- schema breaking change가 test로 감지됨

## 4. Step 2: Config, Logging, Health API

목표: local dummy mode를 기본 실행 경로로 만든다.

주요 파일:

```text
src/req_tracker/config/settings.py
src/req_tracker/config/logging.py
src/req_tracker/api/app.py
src/req_tracker/api/routes/health.py
tests/contract/test_health_api.py
```

구현:

- Pydantic settings
- structured logging
- correlation id middleware
- `/api/v1/health`
- `/api/v1/config/runtime`는 admin/debug only로 후순위

Dummy 검증:

- `.env` 없이 `DATASOURCE_MODE=dummy`, `MODEL_GATEWAY_MODE=dummy`로 실행
- health API가 active backend mode를 반환

완료 기준:

- local API 실행 가능
- 모든 request log에 correlation id 존재

## 5. Step 3: Local Artifact Store and Trace Recorder

목표: agent 단계 산출물을 저장하고 디버깅할 수 있는 기반을 먼저 만든다.

주요 파일:

```text
src/req_tracker/debug/artifacts.py
src/req_tracker/debug/traces.py
src/req_tracker/debug/hash.py
tests/unit/debug/test_artifact_store.py
tests/unit/debug/test_trace_recorder.py
```

구현:

- `LocalArtifactStore`
- `InMemoryTraceRepository`
- `create_run`
- `start_step`
- `finish_step`
- `fail_step`
- `record_llm_call`
- hash utility

Dummy 검증:

- stage output 저장 후 ref로 재조회
- input/output hash 안정성 검증
- failed step에 error class 기록

완료 기준:

- 어떤 workflow stage든 trace를 남길 수 있음
- artifact는 git ignored local path에 저장됨

## 6. Step 4: Model Gateway Dummy First

목표: 실제 모델 없이 model-agnostic 호출, schema validation, failure handling을 검증한다.

주요 파일:

```text
src/req_tracker/model_gateway/client.py
src/req_tracker/model_gateway/dummy_provider.py
src/req_tracker/model_gateway/policy.py
src/req_tracker/model_gateway/structured_output.py
src/req_tracker/reasoning/prompts/
tests/unit/model_gateway/
tests/fixtures/dummy/model_responses/
```

구현:

- `ModelGatewayClient`
- `ModelProvider` protocol
- `DummyModelProvider`
- `ModelPolicy`
- structured output validation
- invalid output repair retry simulation

Dummy response cases:

- valid node extraction
- valid edge linking
- invalid JSON
- schema mismatch
- timeout
- hallucinated edge without evidence
- low confidence response

완료 기준:

- 같은 request를 두 dummy model profile로 실행하고 diff 가능
- LLM call trace에 prompt/model/validation status 기록
- failure도 workflow를 완전히 숨기지 않고 trace에 남김

## 7. Step 5: Dummy Source Adapter and Fixture Loader

목표: 실제 JIRA 없이 production source contract를 검증하고, Claude Code source skill이 만든 fixture/export를 같은 adapter contract로 읽게 한다.

주요 파일:

```text
.claude/skills/rune-source-jira/SKILL.md
.claude/skills/rune-source-confluence/SKILL.md
.claude/skills/rune-source-email/SKILL.md
src/req_tracker/adapters/base.py
src/req_tracker/adapters/dummy/adapter.py
src/req_tracker/adapters/dummy/fixtures.py
tests/fixtures/dummy/jira/
tests/unit/adapters/test_dummy_adapter.py
```

구현:

- `SourceAdapter`
- `SourceScope`
- `SyncCursor`
- `SourceFetchResult`
- dummy fixture loader
- pagination simulation
- malformed artifact option
- permission denied artifact option
- source skill에서 MCP/REST/export/dummy transport 선택 원칙 문서화
- `.mcp.example.json` 유지, 실제 `.mcp.json`은 local-only

Dummy dataset:

- `RUNE_CAM_ALPHA`: camera SoC project
- `RUNE_CAM_BETA`: cross-release drift project
- `RUNE_SECURITY`: masking/security cases
- `RUNE_NOISE`: irrelevant docs and ambiguous tickets

완료 기준:

- incremental sync cursor가 동작
- 같은 fixture를 두 번 fetch해도 content hash 동일
- malformed item은 run warning 또는 failed artifact로 분리됨
- MCP tool name이나 사내 endpoint가 Python application code에 등장하지 않음

## 8. Step 6: Ingestion Pipeline

목표: source artifact를 masked chunks와 evidence span으로 변환한다.

주요 파일:

```text
src/req_tracker/ingestion/normalization.py
src/req_tracker/ingestion/masking.py
src/req_tracker/ingestion/chunking.py
src/req_tracker/evidence/spans.py
src/req_tracker/workflows/ingestion_graph.py
tests/unit/ingestion/
tests/security/test_masking.py
```

구현:

- normalize raw dummy artifact
- data classification
- masking rules
- evidence span builder
- chunker
- stage trace

Dummy 검증:

- security fixture에서 email, phone, token, customer code masking
- no-external-llm classification은 model gateway 차단
- evidence preview가 source 위치를 가리킴

완료 기준:

- `POST /api/v1/runs/ingest`가 dummy artifact를 처리
- run step이 `source_fetch -> normalize -> mask -> chunk` 순서로 남음

## 9. Step 7: In-Memory Vector and Retrieval

목표: Qdrant 없이 retrieval context 흐름을 검증한다.

주요 파일:

```text
src/req_tracker/vector/base.py
src/req_tracker/vector/memory_backend.py
src/req_tracker/vector/retrieval.py
tests/unit/vector/
```

구현:

- lexical similarity fallback
- metadata filter
- top-k retrieval
- retrieval trace artifact

Dummy 검증:

- latency requirement 검색 시 DVFS, AE spike, latency bench chunk가 top-k에 포함
- GDPR requirement 검색 시 privacy/security chunks가 포함
- project scope 밖 chunk는 반환되지 않음

완료 기준:

- analysis workflow가 retrieval context ref를 trace에 남김

## 10. Step 8: Ontology Extraction and Entity Resolution

목표: candidate node를 만들고 duplicate/merge 판단을 수행한다.

주요 파일:

```text
src/req_tracker/reasoning/extraction.py
src/req_tracker/ontology/resolver.py
src/req_tracker/ontology/id_factory.py
tests/unit/reasoning/test_extraction.py
tests/unit/ontology/test_resolver.py
```

구현:

- deterministic extraction from source fields
- dummy LLM extraction through gateway
- evidence required validation
- entity resolver
- `needs_review` path

Dummy 검증:

- issue type이 Task여도 내용이 "shall/must"이면 Requirement 후보
- 같은 component가 JIRA와 Confluence에서 반복되면 merge candidate
- ambiguous item은 low confidence + approval review

완료 기준:

- candidate node output이 trace artifact로 저장
- duplicate fixture가 merge operation으로 감지됨

## 11. Step 9: Edge Linking and Findings Rules

목표: relation 후보와 deterministic finding을 생성한다.

주요 파일:

```text
src/req_tracker/reasoning/linking.py
src/req_tracker/findings/rules.py
src/req_tracker/findings/analyzer.py
src/req_tracker/findings/severity.py
tests/unit/findings/
tests/integration/test_dummy_analysis_pipeline.py
```

구현:

- source link edge generation
- semantic candidate edge generation
- relation validation
- graph projection
- finding rules
- severity scoring

Dummy 검증:

- conflicting alternatives 탐지
- requirement without verification 탐지
- design without parent 탐지
- cross-domain hidden impact 후보 생성
- false positive fixture는 finding이 생성되지 않아야 함

완료 기준:

- LLM 없이 baseline finding 생성 가능
- LLM reasoning 실패 시 rule finding은 유지됨

## 12. Step 10: Approval and Graph Commit

목표: pending proposal과 approved graph를 분리하고, 승인된 delta만 commit한다.

주요 파일:

```text
src/req_tracker/approvals/service.py
src/req_tracker/approvals/routing.py
src/req_tracker/graph/base.py
src/req_tracker/graph/memory_backend.py
src/req_tracker/graph/delta.py
src/req_tracker/workflows/approval_graph.py
tests/unit/approvals/
tests/integration/test_approval_commit.py
```

구현:

- approval item 생성
- graph delta preview
- approve/reject/modify/hold
- stale detection
- feedback event 생성
- idempotent memory graph commit

Dummy 검증:

- pending edge가 approved graph query에 나타나지 않음
- approve 후 나타남
- reject 후 feedback event 생성
- modify approve 후 original proposal과 modified delta 둘 다 추적 가능
- 같은 idempotency key로 두 번 commit해도 graph 중복 없음

완료 기준:

- 승인 없는 graph mutation 불가

## 13. Step 11: Debug API and Replay

목표: run 결과를 사람이 추적하고 모델/prompt 변경 전후를 비교한다.

주요 파일:

```text
src/req_tracker/debug/replay.py
src/req_tracker/debug/diff.py
src/req_tracker/api/routes/debug.py
src/req_tracker/api/routes/runs.py
tests/replay/
```

구현:

- run list/detail
- step list
- llm call list
- artifact list
- graph delta view
- replay same_model_same_prompt
- replay new_model_same_prompt
- output diff

Dummy 검증:

- invalid model fixture replay가 validation failure 증가로 표시
- prompt v2 dummy response가 edge count를 바꾸면 diff에 표시
- graph delta diff가 added/removed/changed relation을 보여줌

완료 기준:

- 개발자가 실패 run의 어느 stage가 문제인지 API로 확인 가능

## 14. Step 12: Feedback Store and Eval Gate

목표: 사용자 피드백을 eval dataset 후보와 개선 후보로 연결한다.

주요 파일:

```text
src/req_tracker/feedback/service.py
src/req_tracker/evals/datasets.py
src/req_tracker/evals/runner.py
src/req_tracker/evals/metrics.py
tests/evals/
```

구현:

- feedback event 저장
- reason code validation
- eval dataset builder
- approval precision metric
- modification rate metric
- replay drift metric
- security eval gate

Dummy 검증:

- wrong_relation feedback 5건이 edge_linking eval dataset 후보로 묶임
- weak_evidence feedback이 retrieval policy improvement candidate로 연결됨
- security_concern은 release blocker로 처리됨

완료 기준:

- prompt/model activation은 eval gate 없이 불가능한 구조가 됨

## 15. Step 13: Minimal UI

목표: API가 안정된 뒤 graph/review/debug 확인용 UI를 만든다.

권장:

- React + React Flow
- 초기에는 dense tool UI
- marketing/landing page 금지

필수 화면:

- Graph view
- Findings view
- Approval workbench
- Run debug
- LLM call detail
- Replay diff
- Feedback reason capture

Dummy 검증:

- RUNE_CAM_ALPHA graph 표시
- approval 전후 graph delta 비교
- failed LLM call detail 표시
- replay diff 표시

완료 기준:

- 사용자와 개발자가 같은 dummy run을 두 관점으로 검토 가능

## 16. Step 14: Real Backend Expansion

목표: dummy/in-memory backend를 production backend로 교체한다.

순서:

1. SQLite/in-memory app repo -> PostgreSQL
2. MemoryGraphBackend -> Neo4j
3. MemoryVectorBackend -> Qdrant
4. DummySourceAdapter -> JIRA adapter
5. DummyModelProvider -> 실제 model provider

각 교체는 같은 contract test suite를 통과해야 한다.

완료 기준:

- dummy integration test와 backend integration test가 같은 expected behavior를 검증

## 17. Current Implementation Status

현재 repo는 production backend 교체 전의 local/dummy validation stage에 있다.

완료된 축:

- FastAPI skeleton, health, run analyze, scheduler
- GitHub Actions CI for ruff, mypy, and pytest
- core Pydantic contracts
- local artifact store, trace repository, replay diff skeleton
- SQLite state store for local persistence validation
- PostgreSQL state repository and package migration foundation
- typed PostgreSQL core table migration, mirror upsert, read path, and rollback foundation
- dummy model gateway and dummy source adapter
- model gateway structured validation retry and fallback trace foundation
- generic HTTP JSON model provider, provider factory, and file-backed model/prompt registry
- export-file adapters for JIRA, Confluence, and restricted decision/email sources
- JIRA REST source adapter foundation behind the shared `SourceAdapter` contract
- Confluence REST source adapter foundation behind the shared `SourceAdapter` contract
- JIRA/Confluence REST retry, rate-limit, permission-denied, and warning handling foundation
- ingestion normalization, masking, chunking, evidence span path
- deterministic node extraction, source-link edge candidate generation, findings rules
- graph/vector backend protocols for production backend replacement
- Neo4j graph backend foundation with env-gated integration test
- Qdrant vector backend foundation with env-gated integration test
- pending approval queue and approved graph separation
- approval approve/reject/hold/modify decision path
- feedback summary, eval candidate, improvement candidate, eval gate block
- scalable graph projection for 100+ dummy nodes
- traceability chain API with approved/pending edge separation
- debug summary/artifact API
- debug approval lineage API
- audit event capture/API for run completion, approval decisions, feedback, debug artifact reads, and scheduler operations
- static operator UI for graph, approval, findings, replay, scheduler, node chain review, run debug, and audit events

아직 production 전환 전 남은 축:

- production-grade typed PostgreSQL query repositories and real PostgreSQL integration tests
- Neo4j backend and Qdrant backend
- direct production transport implementations behind the source skill/export boundary
- full debug workbench UX for LLM call payload diff and graph delta side-by-side inspection
- typed production audit event store and RBAC/SSO enforcement
- React/React Flow migration decision after real graph shape validation
- production deployment hardening, migrations, backup/restore, and load tests

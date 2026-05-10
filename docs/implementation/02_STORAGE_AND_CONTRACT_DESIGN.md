# Storage and Contract Design

## 1. 목표

이 문서는 구현 단계에서 먼저 고정해야 할 data contract와 저장소 설계를 정의한다. 실제 source와 model이 없어도 dummy data로 전체 흐름을 검증하려면 저장 계약이 먼저 안정되어야 한다.

## 2. Contract 원칙

- Pydantic model이 API, workflow, test fixture의 공통 계약이다.
- DB row, graph node, API response는 각각 별도 model을 둘 수 있지만 field 의미는 같아야 한다.
- 모든 주요 model은 `schema_version`을 가진다.
- 모든 agent 산출물은 `run_id`와 가능하면 `step_id`를 가진다.
- 모든 AI 산출물은 `model_profile_id`, `prompt_version_id`, `confidence_score`, `evidence`를 가진다.
- 모든 command는 idempotency key를 지원한다.

## 3. ID 정책

| 대상 | 권장 형식 | 생성 기준 |
| --- | --- | --- |
| `artifact_id` | `src_{source_type}_{external_id_hash}` | source type + external id |
| `chunk_id` | `chk_{artifact_id}_{index}` | artifact + chunk index |
| `node_id` | `node_{project_key}_{stable_key}` | source external id 또는 normalized name |
| `edge_id` | `edge_{source}_{relation}_{target}_{hash}` | source node + relation + target node |
| `finding_id` | `fdg_{rule_id}_{hash}` | rule id + affected ids |
| `run_id` | `run_{timestamp}_{short_random}` | run 생성 시 |
| `step_id` | `step_{run_id}_{stage}_{index}` | workflow stage |
| `approval_id` | `apv_{proposal_hash}` | proposal content hash |
| `feedback_id` | `fb_{timestamp}_{short_random}` | feedback 생성 시 |

ID는 dummy fixture에서도 같은 정책을 사용한다. 그래야 실제 connector로 바꿔도 test shape가 유지된다.

## 4. Pydantic Contract Set

초기 구현에서 반드시 필요한 model group:

```text
ontology/
  SourceArtifact
  EvidenceSpan
  ArtifactChunk
  OntologyNode
  TraceabilityEdge
  Finding

debug/
  AgentRun
  AgentStepTrace
  LLMCallTrace
  StageArtifactRef
  ReplayRun
  ReplayDiff

approvals/
  ApprovalItem
  ApprovalDecision
  GraphDelta
  GraphDeltaOperation

feedback/
  FeedbackEvent
  ImprovementCandidate

model_gateway/
  ModelProfile
  PromptVersion
  ModelRequest
  ModelResponse
  StructuredValidationResult
```

## 5. PostgreSQL 설계

PostgreSQL은 app state와 audit 가능한 업무 상태를 저장한다. Graph DB와 vector DB의 metadata reference도 여기서 관리한다.

### 5.1 tables

```text
projects
source_sync_cursors
source_artifacts
artifact_chunks
agent_runs
agent_step_traces
llm_call_traces
stage_artifacts
approval_items
approval_decisions
findings
feedback_events
improvement_candidates
model_profiles
prompt_versions
retrieval_policies
audit_events
idempotency_keys
```

### 5.2 `source_artifacts`

| column | type | note |
| --- | --- | --- |
| `artifact_id` | text pk | stable id |
| `source_type` | text | jira/confluence/email/decision_archive/dummy |
| `external_id` | text | source id |
| `source_url` | text | may be dummy URL |
| `project_key` | text | required |
| `title` | text | normalized title |
| `body_text_ref` | text | raw body artifact ref |
| `content_hash` | text | normalized source hash |
| `data_classification` | text | policy field |
| `access_scope` | jsonb | group/user/project scope |
| `source_updated_at` | timestamptz | source timestamp |
| `ingested_at` | timestamptz | system timestamp |
| `schema_version` | text | contract version |

Unique:

- `(source_type, external_id, content_hash)`

### 5.3 `agent_runs`

| column | type | note |
| --- | --- | --- |
| `run_id` | text pk | run id |
| `run_type` | text | ingestion/analysis/approval_commit/eval/replay/improvement |
| `project_key` | text | scope |
| `triggered_by` | text | user/system |
| `trigger_source` | text | manual/schedule/api/system |
| `status` | text | queued/running/succeeded/failed/cancelled/partial |
| `model_profile_id` | text nullable | active model |
| `prompt_version_ids` | jsonb | versions used |
| `input_snapshot_ids` | jsonb | source snapshot ids |
| `started_at` | timestamptz | |
| `completed_at` | timestamptz nullable | |
| `failure_code` | text nullable | |
| `failure_message` | text nullable | |

### 5.4 `agent_step_traces`

| column | type | note |
| --- | --- | --- |
| `step_id` | text pk | |
| `run_id` | text fk | |
| `stage_name` | text | fixed stage name |
| `status` | text | running/succeeded/failed/skipped |
| `input_hash` | text | |
| `output_hash` | text nullable | |
| `output_ref` | text nullable | artifact reference |
| `schema_version` | text | |
| `retry_count` | int | |
| `error_class` | text nullable | |
| `error_message` | text nullable | |
| `started_at` | timestamptz | |
| `completed_at` | timestamptz nullable | |

Index:

- `(run_id, stage_name)`
- `(run_id, status)`

### 5.5 `llm_call_traces`

| column | type | note |
| --- | --- | --- |
| `llm_call_id` | text pk | |
| `run_id` | text fk | |
| `step_id` | text fk | |
| `model_profile_id` | text fk | |
| `prompt_version_id` | text fk | |
| `request_hash` | text | no raw secret in logs |
| `response_hash` | text nullable | |
| `masked_payload_ref` | text | stored artifact ref |
| `raw_response_ref` | text nullable | restricted access |
| `parsed_output_ref` | text nullable | |
| `input_tokens` | int nullable | |
| `output_tokens` | int nullable | |
| `latency_ms` | int | |
| `validation_status` | text | passed/failed/repaired |
| `retry_count` | int | |
| `error_message` | text nullable | |

### 5.6 `approval_items`

| column | type | note |
| --- | --- | --- |
| `approval_id` | text pk | |
| `project_key` | text | |
| `proposal_type` | text | node/edge/finding/graph_delta |
| `proposal_ref` | text | artifact ref |
| `graph_delta_ref` | text nullable | |
| `status` | text | pending/approved/rejected/modified_approved/held/stale |
| `risk_level` | text | critical/high/medium/low |
| `owner_role` | text | routing |
| `created_from_run_id` | text fk | |
| `created_from_step_id` | text fk | |
| `proposal_hash` | text | stale detection |
| `version` | int | optimistic locking |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### 5.7 `feedback_events`

Feedback event는 단순 로그가 아니라 eval dataset 후보의 원천이다.

| column | type | note |
| --- | --- | --- |
| `feedback_id` | text pk | |
| `target_type` | text | node/edge/finding/answer/run_step |
| `target_id` | text | |
| `action` | text | approved/rejected/modified/commented/marked_low_quality |
| `reason_code` | text nullable | taxonomy |
| `correction_text` | text nullable | |
| `user_id` | text | |
| `user_role` | text | |
| `model_profile_id` | text nullable | |
| `prompt_version_id` | text nullable | |
| `created_at` | timestamptz | |

## 6. Graph DB 설계

Graph DB는 approved traceability graph 원장이다. Pending proposal은 PostgreSQL approval table과 artifact store에 남긴다.

### 6.1 Node labels

공통 label:

```text
:TraceNode
```

type별 label:

```text
:Requirement
:ArchitectureBlock
:DesignSpec
:Verification
:Issue
:Decision
:Component
:Risk
```

공통 properties:

```text
node_id
node_type
project_key
name
description
lifecycle_state
source_artifact_ids
evidence_refs
created_by
confidence_score
version
created_at
updated_at
```

### 6.2 Edge relation types

```text
:SATISFIES
:VERIFIES
:DERIVES
:IMPLEMENTS
:AFFECTS
:BLOCKS
:CONFLICTS_WITH
:SUPERSEDES
:DECIDES
```

공통 properties:

```text
edge_id
relation
reasoning
evidence_refs
is_inferred
confidence_score
approval_id
approved_by
approved_at
version
created_at
updated_at
```

### 6.3 Constraints

```cypher
CREATE CONSTRAINT trace_node_id IF NOT EXISTS
FOR (n:TraceNode) REQUIRE n.node_id IS UNIQUE;

CREATE CONSTRAINT trace_edge_id IF NOT EXISTS
FOR ()-[r:TRACE_RELATION]-() REQUIRE r.edge_id IS UNIQUE;
```

Neo4j version에 따라 relationship property unique constraint 지원 여부를 확인하고, 지원하지 않으면 app DB에서 edge uniqueness를 보장한다.

### 6.4 Required Queries

| query | 목적 |
| --- | --- |
| `get_node(node_id)` | node 상세 |
| `get_subgraph(project_key, filters)` | graph UI |
| `get_traceability_chain(node_id)` | requirement chain |
| `find_orphan_nodes(project_key)` | rule |
| `find_missing_verification(project_key)` | rule |
| `find_conflicting_alternatives(project_key)` | rule |
| `apply_graph_delta(delta, idempotency_key)` | approved commit |

## 7. Vector DB 설계

Vector DB는 semantic retrieval memory이다. 운영 graph truth가 아니다.

Collection:

```text
artifact_chunks_v1
```

Payload fields:

```text
chunk_id
artifact_id
project_key
source_type
external_id
section_path
data_classification
access_scope
embedding_model
embedding_version
content_hash
created_at
```

Search는 항상 다음 filter를 포함한다.

- `project_key`
- `access_scope`
- `data_classification`
- source type 또는 domain filter

Dummy mode에서는 in-memory vector 또는 lexical search fallback을 먼저 구현한다.

## 8. Artifact Store 설계

Artifact store는 raw snapshot, masked payload, stage output, raw LLM response, parsed output, replay report를 저장한다.

초기 local path:

```text
.local_artifacts/
  runs/
    {run_id}/
      source_fetch.json
      normalize.json
      mask.json
      chunks.json
      extract_nodes.json
      link_edges.json
      findings.json
      reasoning.json
      approval_items.json
      llm_calls/
```

`.local_artifacts/`는 git에 commit하지 않는다.

보안:

- raw source와 raw LLM response는 debug 권한 필요
- masked payload와 parsed output은 일반 developer debug 권한에서 조회 가능
- artifact ref와 hash는 PostgreSQL에 저장

## 9. API Contract 우선순위

초기 API는 다음 순서로 구현한다.

1. `GET /api/v1/health`
2. `POST /api/v1/runs/ingest`
3. `POST /api/v1/runs/analyze`
4. `GET /api/v1/runs/{run_id}`
5. `GET /api/v1/runs/{run_id}/steps`
6. `GET /api/v1/runs/{run_id}/graph-delta`
7. `GET /api/v1/approvals`
8. `POST /api/v1/approvals/{approval_id}/decision`
9. `GET /api/v1/graph/subgraph`
10. `GET /api/v1/findings`
11. `POST /api/v1/runs/{run_id}/replay`
12. `GET /api/v1/replays/{replay_id}/diff`

## 10. Dummy Mode Storage Strategy

실제 PostgreSQL/Neo4j/Qdrant가 없어도 step 검증이 가능해야 한다.

초기 backend mapping:

| production abstraction | dummy/local implementation |
| --- | --- |
| PostgreSQL repositories | SQLite or in-memory repository |
| Neo4j backend | MemoryGraphBackend |
| Qdrant backend | MemoryVectorBackend |
| Object store | LocalArtifactStore |
| Model gateway | DummyModelProvider |
| JIRA connector | DummySourceAdapter |

단, public interface와 Pydantic contract는 production과 동일하게 유지한다.


# Debug, Replay, and Feedback Design

## 1. 목표

Agent는 초기부터 틀릴 수 있다. 이 시스템의 상용 품질은 "항상 맞히는 agent"가 아니라 "틀렸을 때 원인을 찾고 개선 루프로 연결할 수 있는 agent"에서 나온다.

이 문서는 다음을 설계한다.

- run/step level debug trace
- model call trace
- stage artifact storage
- replay and diff
- reviewer feedback capture
- feedback to eval dataset
- controlled improvement candidate

## 2. Debug Trace 원칙

모든 workflow stage는 다음 metadata를 남긴다.

```text
run_id
step_id
stage_name
status
input_hash
output_hash
output_ref
retrieval_context_ref
validation_status
validation_result
schema_version
started_at
completed_at
retry_count
error_class
error_message
```

LLM call은 추가로 다음을 남긴다.

```text
model_profile_id
prompt_version_id
request_hash
response_hash
masked_payload_ref
raw_response_ref
parsed_output_ref
validation_status
latency_ms
token counts
```

## 3. Stage Artifact 종류

| stage | artifact |
| --- | --- |
| source_fetch | raw artifact list, source warnings |
| normalize | normalized artifact list |
| mask | masked artifact list, redaction report |
| chunk | chunks, evidence spans |
| retrieve | retrieval query, top-k chunk ids |
| extract_nodes | candidate nodes, raw model response |
| resolve_entities | create/merge/needs_review operations |
| link_edges | candidate edges, retrieval context |
| detect_findings | findings, rule paths |
| enrich_reasoning | reasoning, confidence, counter-evidence |
| stage_approval | approval items, graph delta previews |
| commit_graph_delta | committed operations, skipped duplicates |
| record_feedback | feedback events |

## 4. Debug API

초기 API:

| Method | Path | 목적 |
| --- | --- | --- |
| `GET` | `/api/v1/runs` | run 목록 |
| `GET` | `/api/v1/runs/{run_id}` | run summary |
| `GET` | `/api/v1/runs/{run_id}/steps` | step trace |
| `GET` | `/api/v1/runs/{run_id}/artifacts` | artifact refs |
| `GET` | `/api/v1/runs/{run_id}/llm-calls` | model call trace |
| `GET` | `/api/v1/runs/{run_id}/graph-delta` | proposed graph delta |
| `GET` | `/api/v1/debug/approvals/{approval_id}/lineage` | approval lineage |
| `POST` | `/api/v1/runs/{run_id}/replay` | replay 시작 |
| `GET` | `/api/v1/replays/{replay_id}/diff` | replay diff |

## 5. Error Classes

| Error | 의미 | 처리 |
| --- | --- | --- |
| `SOURCE_AUTH_ERROR` | source 접근 실패 | run failed, admin action |
| `SOURCE_RATE_LIMIT` | rate limit | retry/backoff |
| `SOURCE_MALFORMED_ARTIFACT` | source item schema 문제 | artifact skipped or manual review |
| `MASKING_POLICY_VIOLATION` | 민감 데이터 미마스킹 | analysis blocked |
| `MODEL_POLICY_BLOCKED` | data class가 model에 허용되지 않음 | model call skipped |
| `LLM_TIMEOUT` | model timeout | retry/fallback |
| `STRUCTURED_OUTPUT_INVALID` | schema validation 실패 | repair retry or manual review |
| `RETRIEVAL_EMPTY` | context 없음 | low confidence |
| `GRAPH_CONSTRAINT_ERROR` | invalid graph delta | commit blocked |
| `APPROVAL_STALE` | approval 생성 후 source/graph 변경 | re-analysis required |

## 6. Replay 설계

Replay는 저장된 run input과 version metadata를 사용해 일부 또는 전체 stage를 다시 실행한다.

Replay mode:

| mode | 목적 |
| --- | --- |
| `same_model_same_prompt` | 재현성 확인 |
| `new_model_same_prompt` | 모델 교체 영향 확인 |
| `same_model_new_prompt` | prompt 변경 영향 확인 |
| `new_model_new_prompt` | release candidate 전체 비교 |
| `source_update_same_versions` | source 변경 영향 확인 |
| `selected_stage_only` | 특정 stage bug fix 검증 |

Replay output:

```text
ReplayRun
  replay_id
  source_run_id
  replay_mode
  compared_model_profile_ids
  compared_prompt_version_ids
  status
  diff_ref
```

## 7. Diff 종류

| diff | 비교 대상 |
| --- | --- |
| source diff | artifact count, content hash, changed fields |
| chunk diff | chunk boundary, evidence span |
| retrieval diff | top-k context ids and scores |
| node diff | added/removed/changed node candidates |
| entity resolution diff | create/merge/needs_review decisions |
| edge diff | added/removed/changed relation candidates |
| finding diff | added/removed/changed finding |
| severity diff | severity and score change |
| confidence diff | confidence score change |
| approval routing diff | owner/risk routing change |
| graph delta diff | final proposed graph mutation |

Diff는 단순 text diff가 아니라 object-level diff여야 한다.

## 8. Feedback Capture 설계

피드백은 approval UI, finding UI, debug UI에서 모두 생성될 수 있다.

피드백 entry point:

- approval decision
- edge relation correction
- node type correction
- finding severity correction
- evidence insufficient marker
- duplicate marker
- debug run annotation
- model output low quality marker

필수 reason code:

```text
wrong_relation
weak_evidence
wrong_node_type
duplicate
missing_context
wrong_severity
security_concern
other
```

## 9. Feedback to Eval Dataset

피드백은 다음 mapping으로 eval dataset 후보가 된다.

| reason_code | eval dataset |
| --- | --- |
| `wrong_relation` | edge_linking/rejected_edges.jsonl |
| `weak_evidence` | retrieval/evidence_sufficiency.jsonl |
| `wrong_node_type` | node_extraction/corrections.jsonl |
| `duplicate` | entity_resolution/duplicates.jsonl |
| `missing_context` | retrieval/missed_context.jsonl |
| `wrong_severity` | findings/severity_corrections.jsonl |
| `security_concern` | security/blockers.jsonl |
| `other` | manual_triage/unclassified.jsonl |

Dataset promotion rule:

- raw feedback -> candidate eval case
- candidate eval case -> curated eval case after reviewer/admin confirmation
- curated eval case만 release gate에 사용

## 10. Improvement Candidate 생성

Improvement candidate 종류:

- prompt change
- few-shot example change
- graph rule change
- retrieval policy change
- scoring threshold change
- model profile change
- ontology normalization change

생성 조건 예시:

| pattern | candidate |
| --- | --- |
| same relation type repeatedly rejected | edge linking prompt/rule candidate |
| many weak evidence feedbacks | retrieval top-k/rerank policy candidate |
| duplicate feedback cluster | entity resolver threshold candidate |
| wrong node type feedback cluster | ontology normalization candidate |
| wrong severity on same rule | severity scoring candidate |
| schema failures on one model | model profile or parser candidate |

## 11. Improvement Release Gate

개선 후보는 다음 gate를 통과해야 한다.

1. unit/contract tests
2. golden eval
3. replay drift report
4. security eval
5. reviewer approval
6. canary activation
7. canary metric monitoring
8. promote or rollback

차단 조건:

- masking violation
- approval precision 하락이 threshold 초과
- false positive rate 증가
- structured output failure rate 증가
- critical/high finding miss 증가
- reviewer가 sample diff에서 회귀 확인

## 12. Debug UI 설계

Debug UI는 운영 사용자용 graph UI와 구분한다.

화면:

- Run List
- Run Detail
- Stage Timeline
- Stage Artifact Viewer
- LLM Call Detail
- Retrieval Context Viewer
- Graph Delta Preview
- Replay Launcher
- Replay Diff Viewer
- Feedback/Eval Linkage

Run Detail에서 바로 확인해야 할 것:

- 실패 stage
- 실패 error class
- model profile/prompt version
- validation failure message
- affected approval/finding
- replay 가능 여부

## 13. Dummy 검증 시나리오

| scenario | 기대 결과 |
| --- | --- |
| invalid model output | validation failed trace and repair retry |
| model timeout | `LLM_TIMEOUT` trace and fallback/partial run |
| hallucinated edge | validation or weak evidence finding |
| prompt v2 changes edge direction | replay edge diff |
| source latency target changes | stale trace finding |
| reviewer rejects relation | feedback -> eval candidate |
| security fixture uses external model | `MODEL_POLICY_BLOCKED` |

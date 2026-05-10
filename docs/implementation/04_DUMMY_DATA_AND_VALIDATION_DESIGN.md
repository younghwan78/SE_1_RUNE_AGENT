# Dummy Data and Validation Design

## 1. 목표

실제 사내 데이터를 사용할 수 없으므로 dummy data는 단순 데모 데이터가 아니라 구현 검증의 핵심 자산이다. Dummy data는 다음을 검증해야 한다.

- source adapter
- ingestion/masking/evidence
- retrieval
- node extraction
- entity resolution
- edge linking
- graph rule finding
- approval and graph commit
- debug trace
- replay diff
- feedback and eval gate

## 2. POC 참고와 확장 방향

기존 POC의 `Ulysses Camera HAL` 18개 ticket은 좋은 seed dataset이다. 특히 다음 gap은 유지할 가치가 있다.

- scheduler design alternative conflict
- DVFS latency impact
- MIPI parent requirement missing
- 3A algorithm orphan
- architecture verification missing
- GDPR implementation missing
- memory bandwidth bug causing latency impact

다만 새 dummy dataset은 다음을 추가해야 한다.

- JIRA issue type이 MBSE type과 맞지 않는 경우
- Confluence-like design document
- decision archive
- duplicate entity
- stale source update
- masking/security cases
- malformed source artifact
- invalid LLM output
- reviewer feedback history
- model/prompt version comparison

## 3. Fixture 위치

권장 위치:

```text
tests/fixtures/dummy/
  scenarios/
    rune_cam_alpha/
      source_artifacts.jsonl
      expected_nodes.jsonl
      expected_edges.jsonl
      expected_findings.jsonl
      expected_approvals.jsonl
      expected_metrics.json
    rune_cam_beta/
    rune_security/
    rune_noise/
  model_responses/
    node_extraction/
    edge_linking/
    finding_reasoning/
  feedback/
    reviewer_events.jsonl
  replay/
    run_snapshots/
    expected_diffs/
```

Fixture는 production contract와 같은 schema를 사용한다. 별도 demo-only schema를 만들지 않는다.

Claude Code source skill 검증용 export 위치:

```text
tests/fixtures/dummy/source_exports/
  jira/
  confluence/
  decision_archive/
```

이 export는 `.claude/skills/rune-source-*`가 live source 대신 사용할 수 있는 형태여야 한다. MCP가 없어도 같은 변환 절차를 검증하기 위해서다.

## 4. Scenario A: `RUNE_CAM_ALPHA`

목적: Camera SoC traceability의 정상/오류/누락/충돌을 모두 검증한다.

권장 규모:

| artifact type | count |
| --- | ---: |
| JIRA-like Requirement | 8 |
| JIRA-like Architecture | 7 |
| JIRA-like Design Spec | 12 |
| JIRA-like Verification | 8 |
| JIRA-like Issue/Risk | 8 |
| Confluence-like pages | 6 |
| Decision archive entries | 5 |
| Noise/irrelevant artifacts | 6 |
| Total | 60 |

### 4.1 핵심 요구사항

| ID | Type | 목적 |
| --- | --- | --- |
| `CAM-REQ-001` | Requirement | 4K60 end-to-end latency < 100ms |
| `CAM-REQ-002` | Requirement | HDR10 still capture |
| `CAM-REQ-003` | Requirement | 1080p30 preview power < 2.5W |
| `CAM-REQ-004` | Requirement | MIPI virtual channel RGB+IR support |
| `CAM-REQ-005` | Requirement | GDPR local-only face processing |
| `CAM-REQ-006` | Requirement | cold start camera preview < 700ms |
| `CAM-REQ-007` | Requirement | thermal throttling policy |
| `CAM-REQ-008` | Requirement | secure debug log redaction |

### 4.2 아키텍처 후보

| ID | Type | 목적 |
| --- | --- | --- |
| `CAM-ARCH-010` | Architecture_Block | ISP tile pipeline |
| `CAM-ARCH-011` | Architecture_Block | LPDDR5 dual-channel camera memory |
| `CAM-ARCH-012` | Architecture_Block | HDR TME hardware block |
| `CAM-ARCH-013` | Architecture_Block | NPU face processing path |
| `CAM-ARCH-014` | Architecture_Block | Sensor CSI receiver |
| `CAM-ARCH-015` | Architecture_Block | Thermal governor integration |
| `CAM-ARCH-016` | Architecture_Block | Secure diagnostic log path |

### 4.3 설계 후보

| ID | Type | 목적 |
| --- | --- | --- |
| `CAM-DES-020` | Design_Spec | HAL3 ring buffer scheduler |
| `CAM-DES-021` | Design_Spec | HAL3 lock-free queue alternative |
| `CAM-DES-022` | Design_Spec | ISP DVFS governor |
| `CAM-DES-023` | Design_Spec | MIPI CSI-2 4-lane IMX789 driver |
| `CAM-DES-024` | Design_Spec | Face detection NPU service |
| `CAM-DES-025` | Design_Spec | Camera cold-start prewarm cache |
| `CAM-DES-026` | Design_Spec | Thermal backoff frame-drop policy |
| `CAM-DES-027` | Design_Spec | Secure log redaction filter |
| `CAM-DES-028` | Design_Spec | 3A unified AE/AWB/AF loop |
| `CAM-DES-029` | Design_Spec | HDR offline queue implementation |
| `CAM-DES-030` | Design_Spec | Memory QoS arbitration |
| `CAM-DES-031` | Design_Spec | Sensor calibration blob loader |

### 4.4 검증 후보

| ID | Type | 목적 |
| --- | --- | --- |
| `CAM-VER-040` | Verification | 4K60 latency bench |
| `CAM-VER-041` | Verification | HDR DisplayHDR compliance |
| `CAM-VER-042` | Verification | 1080p30 power measurement |
| `CAM-VER-043` | Verification | GDPR local-only audit |
| `CAM-VER-044` | Verification | cold-start timing test |
| `CAM-VER-045` | Verification | thermal policy soak test |
| `CAM-VER-046` | Verification | secure log redaction test |
| `CAM-VER-047` | Verification | memory bandwidth stress test |

### 4.5 이슈/리스크 후보

| ID | Type | 목적 |
| --- | --- | --- |
| `CAM-ISS-060` | Issue | AE convergence latency spike 120ms |
| `CAM-ISS-061` | Issue | HDR TME AXI bus contention |
| `CAM-ISS-062` | Risk | MIPI VC verification missing |
| `CAM-ISS-063` | Issue | face embedding upload risk |
| `CAM-ISS-064` | Issue | cold-start regression |
| `CAM-ISS-065` | Risk | thermal policy conflicts with latency |
| `CAM-ISS-066` | Issue | debug log leaked sensor serial |
| `CAM-ISS-067` | Risk | calibration blob version mismatch |

## 5. Ground Truth Edges

Dummy dataset은 expected edge set을 명시해야 한다.

### 5.1 Source-derived edges

| source | relation | target | 근거 |
| --- | --- | --- | --- |
| `CAM-ARCH-010` | `satisfies` | `CAM-REQ-001` | ISP tile pipeline meets latency |
| `CAM-ARCH-012` | `satisfies` | `CAM-REQ-002` | HDR TME supports HDR10 |
| `CAM-DES-022` | `implements` | `CAM-REQ-003` | DVFS for power |
| `CAM-VER-040` | `verifies` | `CAM-REQ-001` | latency bench |
| `CAM-VER-041` | `verifies` | `CAM-REQ-002` | HDR compliance |
| `CAM-VER-042` | `verifies` | `CAM-REQ-003` | power measurement |
| `CAM-ISS-060` | `affects` | `CAM-REQ-001` | latency spike |
| `CAM-ISS-061` | `affects` | `CAM-ARCH-011` | memory bandwidth |

### 5.2 AI-candidate edges

| source | relation | target | 검증 목적 |
| --- | --- | --- | --- |
| `CAM-DES-022` | `affects` | `CAM-REQ-001` | DVFS latency impact inferred |
| `CAM-ISS-061` | `affects` | `CAM-REQ-001` | memory contention indirect latency |
| `CAM-DES-023` | `satisfies` | `CAM-REQ-004` | MIPI VC support |
| `CAM-VER-047` | `verifies` | `CAM-ARCH-011` | memory stress validates architecture |
| `CAM-DES-024` | `implements` | `CAM-REQ-005` | local face processing |
| `CAM-DES-026` | `affects` | `CAM-REQ-001` | thermal frame-drop latency tradeoff |

AI-candidate edge는 approval 전에는 approved graph에 나타나면 안 된다.

## 6. Expected Findings

| ID | Type | Severity | 조건 |
| --- | --- | --- | --- |
| `F-CAM-001` | conflict | high | `CAM-DES-020` and `CAM-DES-021` both implement scheduler architecture |
| `F-CAM-002` | conflict | high | DVFS transition affects latency requirement |
| `F-CAM-003` | missing_verification | medium | MIPI virtual channel lacks direct verification |
| `F-CAM-004` | orphan_node | medium | 3A unified loop has no parent requirement |
| `F-CAM-005` | missing_implementation | critical | GDPR requirement has no approved implementation before AI proposal |
| `F-CAM-006` | cross_domain_hidden | high | memory bandwidth issue indirectly affects latency |
| `F-CAM-007` | stale_trace | medium | source update changes latency target from 100ms to 80ms |
| `F-CAM-008` | policy_violation | critical | debug log contains sensor serial before masking |
| `F-CAM-009` | weak_evidence | low | inferred edge has only title similarity, no body evidence |
| `F-CAM-010` | missing_verification | medium | secure log redaction design lacks verification before `CAM-VER-046` |

## 7. Scenario B: `RUNE_CAM_BETA`

목적: source update, stale trace, replay diff를 검증한다.

구성:

- Alpha와 같은 구조이나 일부 requirement가 변경됨
- `CAM-REQ-001` latency target: `<100ms` -> `<80ms`
- `CAM-DES-022` DVFS transition: `12-18ms` -> `20-30ms`
- `CAM-VER-040` test target은 아직 `<100ms`로 남아 stale
- `CAM-DES-021` alternative design이 cancelled 상태로 바뀜

검증:

- stale trace finding 생성
- previous run replay diff 생성
- cancelled design은 conflict에서 제외 또는 severity 감소
- old verification target mismatch 감지

## 8. Scenario C: `RUNE_SECURITY`

목적: masking과 model policy를 검증한다.

포함할 민감 정보:

- 개인 이메일
- 전화번호
- access token 형태 문자열
- customer code name
- device serial number
- private endpoint URL
- biometric data mention
- source artifact marked `no_external_llm`

Expected:

- masking 후 LLM payload에 원문 secret 없음
- `no_external_llm` artifact는 external model profile로 호출 차단
- policy violation finding 또는 security review item 생성

## 9. Scenario D: `RUNE_NOISE`

목적: false positive 방지와 low confidence routing 검증.

포함:

- 회의 일정 공지
- 휴가 알림
- sprint cleanup task
- duplicate title but unrelated body
- ambiguous "performance improvement" ticket
- empty description ticket

Expected:

- processable false artifact는 분석 제외 또는 low value warning
- unrelated noise는 node/edge 생성하지 않음
- ambiguous item은 `needs_review`

## 10. Dummy Model Response Fixture

모델 fixture는 실제 모델 연결 전 gateway와 schema validation을 검증한다.

```text
tests/fixtures/dummy/model_responses/
  node_extraction/
    valid_batch_001.json
    invalid_missing_evidence.json
    invalid_unknown_type.json
    low_confidence_batch.json
  edge_linking/
    valid_edges_001.json
    hallucinated_without_evidence.json
    wrong_direction.json
  finding_reasoning/
    valid_reasoning.json
    timeout.marker
    malformed_json.txt
```

각 fixture는 다음 expected behavior를 가진다.

| fixture | expected |
| --- | --- |
| `valid_batch_001.json` | validation passed |
| `invalid_missing_evidence.json` | validation failed, repair retry |
| `invalid_unknown_type.json` | validation failed |
| `low_confidence_batch.json` | approval required |
| `hallucinated_without_evidence.json` | proposal rejected by validation |
| `wrong_direction.json` | feedback/eval case로 사용 |
| `timeout.marker` | `LLM_TIMEOUT` trace |
| `malformed_json.txt` | `STRUCTURED_OUTPUT_INVALID` trace |

## 11. Feedback Fixture

`tests/fixtures/dummy/feedback/reviewer_events.jsonl`에 다음 사례를 포함한다.

| target | action | reason_code | 목적 |
| --- | --- | --- | --- |
| edge `CAM-DES-022 affects CAM-REQ-001` | approved | null | useful inference |
| edge `CAM-DES-024 implements CAM-REQ-005` | modified | weak_evidence | evidence improvement |
| edge wrong direction | rejected | wrong_relation | linker eval |
| node `CAM-DES-028` | modified | wrong_node_type | extraction eval |
| finding severity | modified | wrong_severity | scoring eval |
| LLM call | marked_low_quality | missing_context | retrieval eval |
| security finding | approved | security_concern | release blocker |

## 12. Stage별 Validation Matrix

| Stage | Dummy assertion |
| --- | --- |
| source_fetch | artifact count, cursor, partial failure |
| normalize | content hash stable, source fields mapped |
| mask | secret redacted, no-external policy enforced |
| chunk | chunk count, evidence offsets valid |
| embed/retrieve | top-k contains expected context, project filter works |
| extract_nodes | expected node count/type, low confidence routed |
| resolve_entities | duplicate merge detected |
| link_edges | source edges + AI candidate edges generated |
| detect_findings | expected findings generated, noise ignored |
| enrich_reasoning | model trace exists, schema validation status recorded |
| stage_approval | approval count and owner routing |
| commit | approved only, idempotent |
| feedback | eval dataset candidates created |
| replay | diff generated for model/prompt/source changes |
| source_skill | MCP/REST/export/dummy transport 선택이 같은 SourceArtifact shape를 만든다 |

## 13. Minimum Test Set

초기 구현에서 반드시 통과해야 하는 test:

```text
tests/contract/test_models.py
tests/unit/adapters/test_dummy_adapter.py
tests/unit/ingestion/test_masking.py
tests/unit/evidence/test_spans.py
tests/unit/model_gateway/test_dummy_provider.py
tests/unit/reasoning/test_extraction.py
tests/unit/findings/test_rules.py
tests/unit/approvals/test_state_transitions.py
tests/integration/test_dummy_ingestion_pipeline.py
tests/integration/test_dummy_analysis_pipeline.py
tests/integration/test_approval_commit.py
tests/replay/test_replay_diff.py
tests/evals/test_feedback_to_eval_dataset.py
tests/security/test_no_external_llm_policy.py
```

## 14. Success Criteria

Dummy validation이 충분하다고 판단하는 기준:

- 실제 external service 없이 ingestion -> analysis -> approval -> commit -> feedback -> replay 흐름이 돈다.
- expected findings 중 critical/high는 모두 탐지된다.
- noise fixture에서 과도한 false positive가 발생하지 않는다.
- masking/security fixture가 release blocker를 검증한다.
- model response fixture로 validation failure, timeout, low confidence를 재현한다.
- replay diff가 source change, prompt change, model change를 구분한다.

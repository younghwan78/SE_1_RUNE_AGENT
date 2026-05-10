# Implementation Design Index

이 폴더는 `PRODUCTION_EXECUTION_PLAN.md`를 실제 구현 작업으로 내리기 위한 상세 설계 문서 세트이다. 구현자는 이 문서를 기준으로 milestone, module ownership, dummy data, 검증 기준을 나눠서 작업한다.

## 우선순위

1. `PRODUCTION_EXECUTION_PLAN.md`
2. `AGENTS.md`
3. 이 폴더의 구현 설계 문서
4. 참고용 POC: `E:\18_ClaudeCode_SystemEngineering\01_RE_Agent_POC1`

POC는 다음 아이디어만 참고한다.

- source-agnostic input model
- content-based classification
- 2-pass 흐름: node/type 확정 후 relation 추론
- dummy data로 graph rule과 metric을 검증하는 방식
- user review 지점이 relation 추론 전에 필요하다는 점

POC에서 그대로 가져오지 않을 것:

- Streamlit 중심 UI
- NetworkX 중심 운영 구조
- hardcoded graph를 운영 완료 기준으로 삼는 방식
- 특정 외부 LLM SDK에 직접 결합된 classification engine

## 문서 구성

| 문서 | 목적 |
| --- | --- |
| `01_MODULE_DESIGN.md` | 구현 모듈, 책임, 의존성, 주요 interface 설계 |
| `02_STORAGE_AND_CONTRACT_DESIGN.md` | Pydantic 계약, PostgreSQL/Neo4j/Qdrant 저장 설계 |
| `03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md` | 단계별 구현 순서, 산출물, 검증 기준 |
| `04_DUMMY_DATA_AND_VALIDATION_DESIGN.md` | 실제 데이터 없이 검증하기 위한 dummy dataset과 test strategy |
| `05_DEBUG_REPLAY_FEEDBACK_DESIGN.md` | debug trace, replay, feedback 기반 개선 설계 |

## 첫 구현 원칙

- 실제 JIRA가 없어도 전체 pipeline shape가 검증되어야 한다.
- dummy source도 production contract와 같은 `SourceArtifact`, `EvidenceSpan`, `AgentRun`, `AgentStepTrace`를 사용해야 한다.
- dummy LLM도 model gateway 뒤에 있어야 한다. 코드가 특정 모델 SDK를 직접 호출하지 않도록 초기에 차단한다.
- graph commit은 승인된 proposal만 반영한다. dummy mode에서도 이 규칙은 예외 없이 지킨다.
- 모든 stage는 `input_hash`, `output_hash`, `output_ref`를 남긴다.


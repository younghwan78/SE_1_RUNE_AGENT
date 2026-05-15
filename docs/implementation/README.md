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
| `06_CLAUDE_CODE_SKILLS_AND_MCP_DESIGN.md` | Claude Code skill과 MCP/REST/export/dummy source 접근 설계 |
| `07_GRAPH_VIEW_SCALABILITY_PLAN.md` | 100+ node graph view 확장 계획과 단계별 구현 전략 |
| `08_CURRENT_STATE_AND_COMPLETION_AUDIT.md` | 구현 증거, 남은 backlog, completion gate 점검 |
| `09_LOCAL_HANDOFF_COMPLETION.md` | 사내 환경 전 로컬 최종 handoff 기준과 gate 명령 |
| `10_DASHBOARD_PRODUCTION_PLAN.md` | 상용 dashboard/workbench 정보 구조, read model, 단계별 구현 계획 |

## 운영 문서 기준점

계획서의 기대 repo shape와 현재 구현 위치를 연결하는 기준 문서는 다음 위치에 둔다.

| 경로 | 역할 |
| --- | --- |
| `docs/api/README.md` | FastAPI route/OpenAPI 문서화 기준 |
| `docs/ontology/ONTOLOGY_V1.md` | ontology v1의 사람이 읽는 기준 문서 |
| `docs/security/DATA_POLICY.md` | 데이터 등급과 모델 전송 허용 정책 |
| `docs/security/RBAC_MATRIX.md` | 역할/권한 matrix |
| `docs/runbooks/BACKUP_RESTORE.md` | backup/restore runbook |
| `docs/runbooks/MODEL_POLICY.md` | model profile, prompt promotion, replay/eval 정책 |
| `ops/migrations/README.md` | packaged PostgreSQL migration 운영 기준 |
| `ops/helm/README.md`, `ops/helm/rune-agent` | Kubernetes 배포 chart 기준과 target-cluster 검증 진입 조건 |
| `tests/evals/README.md` | eval regression test 확장 위치 |
| `tests/security/README.md` | security release-blocking test 확장 위치 |
| `tests/replay/README.md` | replay reproducibility test 확장 위치 |

## 첫 구현 원칙

- 실제 JIRA가 없어도 전체 pipeline shape가 검증되어야 한다.
- dummy source도 production contract와 같은 `SourceArtifact`, `EvidenceSpan`, `AgentRun`, `AgentStepTrace`를 사용해야 한다.
- dummy LLM도 model gateway 뒤에 있어야 한다. 코드가 특정 모델 SDK를 직접 호출하지 않도록 초기에 차단한다.
- JIRA/Confluence/Email 접근 절차는 `.claude/skills/`의 source skill로 관리한다. MCP는 skill 내부 transport로만 취급한다.
- graph commit은 승인된 proposal만 반영한다. dummy mode에서도 이 규칙은 예외 없이 지킨다.
- 모든 stage는 `input_hash`, `output_hash`, `output_ref`를 남긴다.

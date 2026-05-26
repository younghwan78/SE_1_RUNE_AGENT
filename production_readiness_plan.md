# SE_1_RUNE_AGENT: 상용 수준(Production-Grade) 전환 분석 및 실행 계획

본 문서는 현재 로컬 환경에서 높은 완성도로 개발이 완료된 `SE_1_RUNE_AGENT` 프로젝트를 실제 사내 상용(Production) 환경으로 배포하고 운영하기 위한 상세 분석 및 구체적인 마일스톤을 정리한 문서입니다. `PRODUCTION_EXECUTION_PLAN.md`와 `08_CURRENT_STATE_AND_COMPLETION_AUDIT.md` 기반으로 작성되었습니다.

---

## 1. 현재 구현 사항 및 디자인 파악 (Current State & Design)

현재 시스템은 "처음부터 완벽한 AI가 아닌, 피드백 기반의 자율 개선(Controlled Self-Improvement)과 철저한 추적성(Traceability) 및 디버깅 가능성"에 초점을 맞춰 성공적으로 구현되었습니다. 로컬 단위의 테스트(Mock, Dummy 기반)는 100%에 가깝게 완료되었습니다.

### 1.1 핵심 아키텍처 및 디자인 (Architecture & Design)
*   **Model-Agnostic Gateway**: OpenAI, Anthropic 등 특정 모델에 종속되지 않는 게이트웨이를 구현하여 로깅, Fallback 처리, 스키마 검증(Pydantic 기반) 및 재시도를 캡슐화했습니다.
*   **Deterministic Core (안전장치 최우선)**: 권한, 그래프 커밋, 승인 상태 전이 및 정책 위반(마스킹 등) 검사는 LLM이 아닌 결정론적(Deterministic) 코드로 처리되며, AI 제안은 승인 전까지 철저히 대기(Pending) 상태로 유지됩니다.
*   **Source Adapters & 경계 분리**: JIRA, Confluence, Email 등 사내망 접근은 `Claude Code Source Skill` 레이어로 분리하고, 코어 애플리케이션 코드는 MCP 툴에 직접 의존하지 않고 REST 어댑터 인터페이스에만 의존합니다.
*   **Traceability & Debuggability**: 실행(Run), 단계(Step), LLM 호출(Call)의 모든 입력 스냅샷, 출력 해시, 검색된 컨텍스트(Retrieval Context), 프롬프트 버전을 저장하여 완벽한 상태 비교 리플레이(Replay)와 디버깅을 지원합니다.

### 1.2 개발 완료 현황 (Implementation Status)
*   **CI/CD 파이프라인**: 300여 개 이상의 테스트가 통과된 강력한 CI/CD 로컬 게이트 파이프라인.
*   **핵심 기능**: FastAPI 백엔드, PostgreSQL/Neo4j/Qdrant의 로컬 Docker 연동, Operator Dashboard UI, 스케줄러, 지표(Metrics) 추출 등이 완벽히 동작.
*   **보안 파운데이션**: API Key 및 Trusted Proxy 기반의 OIDC SSO 권한 제어 코어 구현 완료.

---

## 2. 상용 수준(Production-Grade)을 위해 개선해야 하는 사항

현재는 Docker/Local 환경과 Dummy Provider에 맞춰진 "검증된 로컬 릴리스" 상태입니다. 사내망(Staging/Production) 관점에서 다음 5가지 핵심 영역의 개선 및 통합이 필수적입니다.

### 2.1 실제 인프라(Persistence/Backend) 검증 부족 (P0/P1)
*   로컬 PostgreSQL, Neo4j, Qdrant 연동은 완료되었으나, 실제 운영 환경(고가용성 클러스터)에서의 마이그레이션 테스트 및 통합 테스트(`run_backend_integration.py`)가 수행되지 않았습니다.

### 2.2 사내 소스 시스템(JIRA, Confluence 등)과의 실 결합 (P2)
*   현재 JIRA/Confluence 연동은 Dummy 기반이거나 환경 변수가 없는 상태입니다.
*   실제 사내 Sandbox 환경에서의 API 페이지네이션, Rate Limit, 접근 권한 매핑(RBAC) 등 네트워크/API 한계 상황 검증이 필요합니다.

### 2.3 LLM Gateway의 실 운영 품질 조정 (P3)
*   로컬 Dummy Provider 기반으로 테스트 되었습니다. 사내 LLM 또는 외부 API 샌드박스를 연동하여 실제 Fallback 상황, 페이로드 제약, 다국어(한국어 등) 인코딩, 토큰 비용 추적 메트릭의 정상 작동을 확인해야 합니다.
*   승인(Approval) 및 거절(Reject) 피드백에 따른 Eval/Canary 임계치 조정 로직에 대해 실 데이터를 이용한 캘리브레이션이 필요합니다.

### 2.4 SSO 및 보안(Security) 실 연동 (P4)
*   Trusted SSO/OIDC Proxy 기반의 RBAC 코드는 준비되었으나, 사내 IdP(Identity Provider) 및 API Gateway 역방향 프록시 환경에서 `x-rune-user` 등의 헤더가 변조 없이 전달되는지, 그룹 매핑이 정상인지 통합 테스트가 필요합니다.
*   제한된 이메일 및 의사결정 아카이브 데이터에 대한 실제 마스킹(Masking) 정책 위반 시나리오 테스트가 요구됩니다.

### 2.5 운영 관측성(Observability) 및 배포 인프라 (P4)
*   Prometheus/Grafana 대시보드와 OpenTelemetry 파이프라인이 코드 레벨로 구현되어 있지만 사내 중앙 Collector와의 연동 작업이 남았습니다.
*   Kubernetes(Helm) 기반의 배포, 백업 및 복원(Restore) 리허설, 부하(Load) 연막 테스트가 실제 운영 타겟 인프라에서 수행되어야 합니다.

---

## 3. 상용화 도달을 위한 구체적인 5단계 실행 계획 (Execution Plan)

위 개선 사항을 바탕으로 첫 상용 릴리스(L1 단계: Assisted Suggestion 적용)로 가기 위한 **5단계 마일스톤 계획**을 제안합니다.

### Phase 1: 인프라 및 배포 환경 통합 (Staging Setup)
*   **목표**: Helm Chart를 이용해 Kubernetes Staging 클러스터에 애플리케이션을 배포하고 DB 환경과 연동합니다.
*   **액션 아이템**:
    1.  Staging용 데이터베이스(PostgreSQL, Neo4j, Qdrant) 프로비저닝.
    2.  `ops/helm/rune-agent` 차트에 환경 변수를 주입하여 배포 테스트 (`helm lint` 및 `helm upgrade`).
    3.  타겟 클러스터 환경 변수(`staging.env` 기반)를 적용하여 `ops/integration/run_backend_integration.py`를 실행, 통합 DB 상태 점검.

### Phase 2: 코어 외부 시스템 Sandbox 연동 (External Systems Integration)
*   **목표**: JIRA/Confluence 원본 소스 수집 및 LLM 게이트웨이의 실제 통신 및 권한 검증.
*   **액션 아이템**:
    1.  사내 JIRA / Confluence Sandbox의 API 인증 토큰을 Staging 환경에 주입하고 `ops/source/rehearse_company_sources.py` 실행.
    2.  사내 LLM Gateway API Key 연동 후 `ops/model_gateway/rehearse_model_gateway.py` 실행 (Fallback 및 Rate Limit 로직 점검).
    3.  실 데이터 50~100건을 대상으로 Ingestion Workflow를 수행하여 Chunking과 Vector 저장이 에러 없이 수행되는지 모니터링.

### Phase 3: 보안, RBAC 및 Observability 연동 (Security & Ops)
*   **목표**: 사내 SSO 권한 인증(Auth), 트레이스 추적 체계 구축 및 메트릭 대시보드 활성화.
*   **액션 아이템**:
    1.  사내 OIDC Proxy(API Gateway) 헤더를 활용한 Trusted Proxy Auth 테스트 진행 (`ops/security/rehearse_trusted_proxy_auth.py`).
    2.  OpenTelemetry Collector 엔드포인트(`OTEL_EXPORTER_OTLP_ENDPOINT`) 설정 후, 실제 분산 트레이스가 수집되는지 관측.
    3.  리포지토리에 포함된 `ops/observability/grafana-dashboard.json`을 사내 Grafana에 연동하여 지표 수집 모니터링 확인.
    4.  데이터 백업 스크립트(`ops/backup/verify_backup_set.py`) 점검 및 복구(Restore) 리허설 수행.

### Phase 4: 품질 조정 및 피드백 루프 파일럿 (Calibration Pilot)
*   **목표**: 실제 사용자(Reviewer) 개입을 통한 AI 신뢰도 튜닝 및 Canary 승인 워크플로우 테스트.
*   **액션 아이템**:
    1.  테스트 그룹(엔지니어/운영자)을 통해 JIRA/Confluence 샘플 데이터 기반으로 Architecture Block, Requirement 노드 및 엣지 자동 추출 파일럿 수행.
    2.  대시보드의 Approval Workbench에 쌓인 AI 제안을 사용자가 수락(Approve)/수정(Modify)/거절(Reject) 하도록 유도.
    3.  수집된 피드백 이력을 바탕으로 `ImprovementCandidate`(프롬프트 수정안, Rule 추가 등)를 평가(Eval) 루프에 태워 시스템 모델이 Regression 없이 향상되는지 검토.

### Phase 5: 프로덕션 릴리스 및 Readiness Audit 완료
*   **목표**: 최종 Production 릴리스를 위한 승인 및 운영 이관.
*   **액션 아이템**:
    1.  Phase 1~4에서 획득된 증거 데이터를 `production_readiness_evidence.json`에 기록.
    2.  `ops/rehearsal/check_production_readiness.py --env-file staging.env --run-local-gates` 및 `check_goal_completion.py`를 수행하여 모든 Blocker가 `0`이 됨을 확인.
    3.  최종 Handoff Bundle을 생성(`build_handoff_bundle.py`)하고 Validation 완료 후 Production 릴리스 승인 획득.

> **Note**: 현재 리포지토리에 이 계획을 바로 수행할 수 있는 수준의 모든 자동화/검증 스크립트(`ops/rehearsal/*`, `ops/source/*`, `ops/security/*`)가 완비되어 있습니다. 각 Phase에 필요한 사내 인프라 및 인증 정보(Env 변수)만 제공되면 바로 시스템 통합 검증 단계로 진입할 수 있습니다.

# 피드백 기반 자율 개선을 위한 장기 기억(Long-term Memory) 체계 분석 및 개선 방안

본 문서는 `SE_1_RUNE_AGENT` 프로젝트가 목표로 하는 **'피드백 기반 자율 개선(Controlled Self-Improvement)'**을 달성하기 위해 현재 구현된 장기 기억(Memory) 체계의 효과성을 분석하고, 상용 수준의 완벽한 자율 개선 루프를 완성하기 위한 개선점 및 로드맵을 제안합니다.

---

## 1. 현재 구현된 기억 체계(Memory System) 분석

현재 시스템은 단순한 대화 기록이 아닌, **에이전트의 의사결정 추적과 평가(Eval)**에 최적화된 구조화된 기억 체계를 갖추고 있습니다.

### 1.1 주요 구성 요소 (현재 구현 상태)
1.  **Traceability Memory (실행 컨텍스트 기억)**
    *   `AgentRun`, `AgentStepTrace`, `LLMCallTrace`를 통해 모든 실행의 입력 해시, 출력 해시, 프롬프트 버전, 사용된 검색 컨텍스트(`edge_retrieval_context.json`)를 PostgreSQL에 저장합니다.
    *   **효과성**: 에이전트가 "과거에 왜 그런 판단을 했는지"를 100% 재현(Replay)할 수 있는 완벽한 디버깅 기억을 제공합니다.
2.  **Feedback Memory (사용자 피드백 기억)**
    *   `FeedbackEvent` 테이블을 통해 사용자의 행동(`approved`, `rejected`, `modified`)과 정형화된 사유 코드(`wrong_relation`, `weak_evidence` 등), 그리고 수정 텍스트(`correction_text`)를 저장합니다.
    *   **효과성**: 자유 텍스트가 아닌 정형화된 분류(Taxonomy)를 사용하여 패턴 분석과 군집화가 용이합니다.
3.  **Knowledge & Vector Memory (지식 및 검색 기억)**
    *   문서와 청크(Chunk)를 Qdrant 기반 벡터 DB에 임베딩하여 저장합니다.
4.  **Improvement & Eval Memory (개선 및 평가 기억)**
    *   `ImprovementCandidate`를 통해 프롬프트, 룰, 임계치 등의 변경 후보를 상태(`draft`, `canary`, `active`)와 함께 관리하며, 회귀 테스트를 위한 `eval_datasets/*.jsonl` 기반의 기억을 설계했습니다.

### 1.2 현재 체계의 강점
*   **Human-in-the-loop 기반의 안전성**: 즉각적인 시스템 변형(Mutation)을 방지하고, 피드백을 평가(Eval)와 카나리(Canary) 배포를 거쳐 점진적으로 기억에 반영하는 구조는 매우 안전하고 상용 친화적입니다.
*   **결정론적 상태와 AI 제안의 분리**: 승인된 그래프 상태(Approved Graph)와 AI의 제안(Pending)을 엄격히 분리하여, 지식 그래프(Knowledge Graph) 자체가 오염되는 것을 막아줍니다.

---

## 2. 개선해야 할 사항 (Gaps & Areas for Improvement)

현재 아키텍처는 훌륭한 뼈대를 갖추고 있으나, **'진정한 자율 개선'**이 사람의 개입 없이(혹은 최소한의 개입으로) 원활히 돌아가기 위해서는 다음과 같은 장기 기억의 동적(Dynamic) 활용 및 관리 측면에서 개선이 필요합니다.

### 2.1 Feedback의 실시간 프롬프트 주입 (Dynamic Retrieval of Mistakes)
*   **현황**: 피드백(`FeedbackEvent`)은 주로 나중에 프롬프트를 개선(`ImprovementCandidate`)하거나 평가 셋(`Eval Dataset`)을 만드는 데 사용됩니다. 즉, 오프라인(Offline) 배치 성격이 강합니다.
*   **개선점**: 에이전트가 새로운 Edge를 추론할 때, Qdrant 벡터 DB에서 단순히 소스 문서의 청크만 검색하는 것이 아니라, **"과거에 유사한 노드 연결에서 사용자가 Reject하거나 Modify했던 피드백 이력"**을 함께 검색하여 프롬프트에 주입(Dynamic Few-shot 또는 Lessons Learned)해야 합니다.
*   **해결책**: `FeedbackEvent`의 내용(오류 패턴 및 수정 결과)을 벡터 DB에 임베딩하여 실시간 추론 시 `Negative Example` 또는 `Correction Guide`로 활용하는 파이프라인 추가.

### 2.2 Eval Dataset의 자동화 및 동적 갱신 (Automated Memory Curation)
*   **현황**: 기획서상 `eval_datasets/*.jsonl` 파일 형태로 관리되도록 설계되어 있습니다.
*   **개선점**: 사용자가 UI에서 승인/수정/거절을 누를 때마다 이 데이터가 JSONL 파일로 자동 동기화되고 품질 지표(Metric)에 반영되는 파이프라인이 수동적일 수 있습니다.
*   **해결책**: PostgreSQL의 `FeedbackEvent`를 주기적으로 스니핑하여, 신뢰도가 높은 수정안이나 치명적 오류 케이스를 `eval_datasets` (또는 DB 기반 Eval 테이블)로 **자동 승격(Auto-promotion)**시키는 백그라운드 Worker 로직이 필요합니다.

### 2.3 지식 망각 및 가중치 감쇠 (Memory Decay & Pruning)
*   **현황**: 데이터베이스와 평가 셋에 피드백이 영구적으로 누적됩니다.
*   **개선점**: 프로젝트의 도메인 룰이 바뀌거나, 아키텍처가 대대적으로 리팩토링된 경우, 과거의 "정답(Approved)" 피드백은 현재 시점에서는 "오답"일 수 있습니다. 장기 기억이 현재의 추론을 방해하는 현상(Stale Memory)이 발생할 수 있습니다.
*   **해결책**:
    *   **Time-decay Weighting**: 오래된 피드백이나 에지(Edge) 생성 이력은 검색 시 가중치를 낮추는 메커니즘 도입.
    *   **Context Invalidation**: 문서 버전이 크게 바뀌면(예: Confluence Stale Trace 발생 시), 해당 문서에서 파생되었던 과거 피드백 기록도 `Deprecated` 상태로 마킹하는 연쇄 무효화 로직 추가.

### 2.4 암묵적 지식의 명시적 룰 변환 (Implicit to Explicit Rule Extraction)
*   **현황**: `ImprovementCandidate`는 시스템이 제안하지만, 구체적으로 어떤 패턴으로 제안을 생성하는지(LLM Batch Clustering 등) 고도화가 필요합니다.
*   **개선점**: 사용자가 "A는 B가 아니라 C와 연결되어야 함"이라고 계속 수정할 때, 이 암묵적 행동 패턴을 추출하여 명시적인 `Ontology Normalization Rule`이나 `Deterministic Finding Rule`로 자동 변환해주는 LLM 기반의 '기억 통합(Memory Consolidation)' 프로세스가 요구됩니다.

---

## 3. 요약 및 향후 로드맵

현재의 장기 기억 체계(PostgreSQL + Trace + Qdrant)는 **"디버깅과 데이터 보존"** 측면에서 이미 상용 수준에 근접해 있습니다. 이를 **"자율 개선(Autonomous Improvement)"** 엔진으로 한 단계 끌어올리기 위한 기술 로드맵은 다음과 같습니다.

1.  **Phase 1: 피드백의 실시간 벡터화 (Immediate)**
    *   사용자의 Reject / Modify 피드백이 발생하면, 해당 케이스를 즉시 임베딩하여 추후 LLM Reasoning 시 `Lessons_Learned` 컨텍스트로 제공.
2.  **Phase 2: Eval Dataset 파이프라인 자동화 (Short-term)**
    *   정형화된 피드백 DB 테이블에서 고품질/엣지 케이스를 추출해 정기적으로 `eval_datasets/*.jsonl`을 갱신하는 배치(Batch) 스크립트 작성.
3.  **Phase 3: LLM 기반 기억 통합 및 규칙 자동 생성 (Mid-term)**
    *   주기적(예: 주 1회)으로 피드백 이력을 군집화(Clustering)하여 새로운 프롬프트 Few-shot 예제나, 결정론적 Rule(`findings/rules.py`) 추가 코드를 AI가 스스로 PR(Pull Request) 또는 Candidate 형태로 제안하는 시스템 구축.
4.  **Phase 4: 지식 감쇠(Decay) 및 무효화 관리 (Long-term)**
    *   버전 제어 체계와 연동하여 낡은 피드백이나 지식이 현재 추론을 오염시키지 않도록 TTL(Time To Live) 및 무효화(Invalidation) 정책 적용.

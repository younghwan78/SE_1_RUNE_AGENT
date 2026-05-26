# SoC Knowledge System — PoC 설계 문서

> Phase 1 구현 single source of truth.
> Agent 자율 실행 전제. 외부 LLM 서비스 의존 없이 Claude Code + 로컬 라이브러리만으로 완결.

---

## 목차

### Part I. Context & Goal
1. [배경](#1-배경)
2. [문제 정의](#2-문제-정의)
3. [목표와 성공 기준](#3-목표와-성공-기준)
4. [비목표](#4-비목표)
5. [기존 자산](#5-기존-자산)

### Part II. 설계 결정
6. [확정된 설계 결정](#6-확정된-설계-결정)
7. [Phase 1 핵심 원칙](#7-phase-1-핵심-원칙)
8. [LLM 의존성 정책](#8-llm-의존성-정책)

### Part III. 시스템 설계
9. [Ontology 설계](#9-ontology-설계)
10. [Architecture](#10-architecture)
11. [Ingestion 설계](#11-ingestion-설계)
12. [Storage 설계](#12-storage-설계)
13. [Query 처리 설계](#13-query-처리-설계)
14. [UI 설계](#14-ui-설계)
15. [Claude Code 통합](#15-claude-code-통합)
16. [정성 평가 설계](#16-정성-평가-설계)

### Part IV. 실행 계획
17. [Phase 1 Stage 구조](#17-phase-1-stage-구조)
18. [Stage 상세](#18-stage-상세)
19. [Agent 자율 실행 Loop](#19-agent-자율-실행-loop)
20. [Open Issues](#20-open-issues)

### Part V. 부록
21. [Initial Vocabulary](#21-initial-vocabulary)
22. [핵심 설계 원칙](#22-핵심-설계-원칙)

---

# Part I. Context & Goal

## 1. 배경

### 1.1 SoC 개발 워크플로우

SoC 개발은 여러 과제가 phase를 달리하며 동시 진행되는 환경. 각 과제는 다음 라이프사이클을 거친다.

| Phase | 주요 활동 | 주된 데이터 소스 |
|---|---|---|
| 1. Architecture exploration | IP 개선/변경, area/PPA 검토 | JIRA, Confluence |
| 2. Spec definition | 고객과 요구사항 정리 (논의는 email, 결과는 JIRA/Conf) | Email + JIRA + Confluence |
| 3. HW micro-architecture + design | RTL, verification 준비 | JIRA, Confluence |
| 4. SW pre-development | 드라이버, FW 선개발 | JIRA, Confluence |
| 5. Chip-out + SW development | 브링업, 본격 SW 개발 | JIRA (heavy) |
| 6. Milestone testing | 성능/파워 측정, SW 검증 이슈 | JIRA + 메트릭 |
| 7. Customer mass-production | 필드 이슈, 추가 요청 | Email (heavy) |
| 8. Pre-launch reviews | 최종 요청, RCA | Email primary |

### 1.2 Shift-left의 의미와 어려움

차기 SoC 과제(N+1)의 architecture 단계에서 이전 과제(N, N-1...)의 학습을 환류하는 것이 shift-left.

원하는 형태의 질문:
- "이전 과제에서 파워 관련된 활동은 무엇이 있었는지?"
- "이전 과제에서 camera의 shot 성능 이슈가 있었는지?"
- "지난 3과제에서 memory 절감 요청이 어떻게 처리 되었는지?"
- "이 이슈는 언제 생겨서 언제 처리되었는지 + 연관 JIRA/Conf link"

**현재의 문제**:

| 측면 | 현재 |
|---|---|
| 자료 위치 | JIRA + Confluence + Email에 산재 |
| Email 자료 | 정리 누락 多, 외부 도메인(고객) 혼재 |
| Confluence 자료 | 누적량 방대, 신호 대 잡음비 낮음 |
| 연결성 | 도구 간 silo, 사람 머릿속에만 연결 존재 |
| 검색 | 도구별 분리, 키워드 기반 |
| 회상 | architect 암묵지에 의존, 누락 빈번 |

### 1.3 이번 시도의 motivation

이전에 다음과 같은 시도가 있었음:
- JIRA는 MCP로 접근
- Confluence와 Email은 skill로 접근
- 각 항목을 node로 구현, edge는 keyword matching + LLM 추론으로 graph 구성

결과적으로 **DB가 너무 평면적**이었음. Query 다양성이 부족했고 차원(axis)이 없어 의미 있는 slice 질의가 어려웠음.

이번 시도는 **Ontology 기반 다차원 모델**로 평면 그래프를 승격하는 것.

---

## 2. 문제 정의

| 측면 | 현재 상태 | 목표 상태 |
|---|---|---|
| 데이터 위치 | JIRA / Confluence / Email 산재 | 동일 (원본 유지) |
| 연결성 | 단절 (silo) | 의미 기반 연결 (Ontology) |
| Graph 구조 | 평면, edge가 keyword/LLM 추론 | V-Model + Concern + Component 다차원 axis |
| 검색 | 도구별 분리, 키워드 기반 | 의도 기반 자연어 질의 + slice 라우팅 |
| 시간축 | 과제별 단절 | 과제 간 연속성 (longitudinal) |
| Shift-left 활용 | 수동 회상, 누락 빈번 | 자연어 질의로 자동 소환 |

**핵심**: 데이터를 옮기는 것이 아니라 **연결 + 차원(axis)**을 만드는 문제. 평면 그래프 → 다차원 ontology.

---

## 3. 목표와 성공 기준

### 3.1 최상위 목표

JIRA / Confluence / Email에 산재된 SoC 개발 지식을 V-Model 기반 ontology로 통합하여, architect가 차기 과제의 shift-left 검토를 자연어 질의로 수행할 수 있게 한다.

### 3.2 성공 기준 (정성)

사용자가 다음 4가지 query 유형에 대해 만족스러운 답변을 받고, **계속 사용하고 싶다고 응답**.

| Query 유형 | 대표 예시 | Slice |
|---|---|---|
| Concern-slice | "이전 과제 power 관련 활동" | Project × Concern |
| Topic intersection | "Camera shot 성능 이슈" | Component × Concern |
| Timeline-slice | "지난 3과제 memory 절감 요청 처리" | Projects × Concern × Lifecycle |
| Lifecycle trace | "JIRA-XXXX 언제 생겨서 처리?" | Single artifact × Event log |

### 3.3 부가 요구

- 모든 응답에 **원본 link 첨부** (JIRA/Conf/Email URL)
- **Lifecycle timeline** 제공
- 신뢰도 표시 (낮음/중간/높음)
- 모를 때 "찾지 못함" graceful 응답

### 3.4 Phase 1 단계 목표

Phase 1은 **두 단계**로 구분:

#### 3.4.1 Phase 1 Core (Stage A~G, Agent 자율 완료)

Agent가 사람 개입 없이 완료할 수 있는 범위. 모든 acceptance criteria 엄격 적용.

| Layer | 목표 |
|---|---|
| 시스템 | Fixture 기반 ground truth Q set에서 **recall 85%+, source 정확도 95%+** |
| 운영 | Connector 교체로 fixture → 실데이터 전환 가능 |
| 진화 | Schema/vocab/prompt가 YAML+Git으로 진화 가능 |

→ **Stage G 완료가 Agent 자율 실행의 종착점**. 이 시점에 실데이터 ingestion까지 완료.

#### 3.4.2 Phase 1 Post (Stage H, 사람 평가)

사람의 일정과 참여가 필요한 단계. Stage G 완료 후 별도로 진행되며 Agent 자율 loop의 일부가 아님.

| Layer | 목표 |
|---|---|
| 사용자 | 10명 사용자가 4가지 query에 만족, "계속 쓰겠다" 응답 |

**품질 우선 원칙**: 비용 제약 없음. 모든 LLM 작업은 최고 품질의 추론으로 수행.

---

## 4. 비목표

| 비목표 | 이유 |
|---|---|
| 사용자 사전 학습 필요한 UI | 자연어 질의로 충분해야 |
| 정량적 정답률 metric 최적화 | 정성 평가 우선 |
| 다중 팀 / 다중 사업부 확장 | 본인 팀 PoC |
| Self-improving agent (L3+ 자율성) | L1 Observer / L2 Suggester까지만 |
| 첨부물(PPT/Excel) 본문 분석 | Email 본문까지만 |
| Email speech act 분류 (L4+) | L1~L3 처리만 |
| 권한별 사용자 필터링 | 망 보안으로 단일 수준 |
| Production SLA | PoC 수준 안정성 |

---

## 5. 기존 자산

| 자산 | 상태 | Phase 1에서 |
|---|---|---|
| JIRA MCP | 구현됨 | Connector layer로 wrapping (Stage G에서 연결) |
| Confluence skill | 구현됨 | Connector layer로 wrapping (Stage G에서 연결) |
| Email skill | 구현됨 | Connector layer로 wrapping (Stage G에서 연결) |
| 키워드 + LLM edge 추론 경험 | 보유 | 분류기 layer로 흡수, axis 명시 분리 |

### 5.1 이전 시도와의 차이

| 측면 | 이전 | 이번 |
|---|---|---|
| Graph 구조 | 평면 | 다차원 (Project × V-Level × Concern × Component) |
| Edge 종류 | 키워드/LLM 추론 단일 종류 | Typed relations |
| Query 패턴 | ad-hoc 검색 | 4가지 slice pattern으로 라우팅 |
| Ontology 정의 | 없음 | YAML 명시적 정의 |
| 데이터 검증 | 실데이터 직접 | **Fixture-first**, 검증 후 실데이터 |
| 평가 | 없음 | Ground truth Q set + loop |
| 사용자 인터페이스 | 없거나 ad-hoc | Streamlit multi-user |

---

# Part II. 설계 결정

## 6. 확정된 설계 결정

| 영역 | 결정 |
|---|---|
| 범위 | 본인 팀 PoC |
| Target 과제 | 2개 (과제1: SW 선개발+Rev HW / 과제2: Spec 정의) |
| 사용자 | 10명 이내 |
| 데이터 소스 | JIRA + Confluence + Email |
| Confluence 범위 | Architecture, Design 관련 페이지 (~50/과제) |
| JIRA 범위 | 전체 그룹 (algorithm, arch, HW, SW 등) |
| Email 범위 | 비실명 수신 계정 |
| Ontology base | V-Model (L0~L5) |
| 다차원 axis | V-Level × Concern × Component × Project (4축) |
| Topic 모델 | Concern과 Component 분리, 경계 모호는 multi-tag |
| Group axis | 미도입 (JIRA ID로 식별) |
| DB | Postgres + Apache AGE + pgvector (단일) |
| Email 처리 깊이 | L1~L3 (헤더 + 인용 제거 + Entity 추출) |
| LLM 의존성 | **Claude Code only** (사내 LLM 가용 시 보조로만) |
| 임베딩 | **로컬 open source 모델** (sentence-transformers 등) |
| UI | Streamlit |
| Claude Code 호출 | Subprocess 방식 |
| 보안 | 사내 망 보안 (SSO는 옵션) |
| 평가 | 정성 (10명 사용 의향) + Fixture ground truth |
| 데이터 검증 방식 | **Fixture-first** (과제당 100 항목 × 2 과제) |
| 품질 vs 비용 | **품질 우선** (비용 제약 없음) |

---

## 7. Phase 1 핵심 원칙

| 원칙 | 의미 |
|---|---|
| **P1. Goal-driven autonomy** | 각 단계의 goal과 acceptance가 명확해서 agent가 구현/검증/리뷰 자율 가능 |
| **P2. Fixture-first** | 실데이터 의존 없이 시작. Fixture로 검증 후 실데이터 전환 |
| **P3. End-to-end skeleton** | Phase 1에 ingestion → storage → query → UI 모두 |
| **P4. Query + UI in Phase 1** | 사용자가 즉시 만져볼 수 있는 형태 |
| **P5. Evaluation loop** | 단계별 평가 목표 명확, 완성도 향상 loop |
| **P6. Self-contained execution** | 외부 LLM 서비스 없이 Claude Code + 로컬 라이브러리만으로 완결 |
| **P7. Quality-first** | 비용 제약 없음. 모든 LLM 작업은 최고 품질 추론 |

---

## 8. LLM 의존성 정책

### 8.1 모든 LLM 작업은 Claude Code

외부 LLM 서비스 의존성 0. Agent 본체인 Claude Code가 모든 추론을 수행.

| 작업 | 실행자 | 비고 |
|---|---|---|
| 자연어 → 쿼리 변환 | **Claude Code** | 사용자 대면 |
| 사용자 응답 생성 | **Claude Code** | 사용자 대면 |
| Multi-hop reasoning | **Claude Code** | 사용자 대면 |
| Ingestion 시 분류 (V-Level/Concern/Component) | **Claude Code** | 룰 1차, Claude Code 보강 |
| Entity 추출 (NER) | **Claude Code** | 룰 1차, Claude Code 보강 |
| 본문 요약 | **Claude Code** | 긴 page/thread |
| Email 인용 제거 fallback | **Claude Code** | talon 1차, 실패 시 |
| Cross-reference 검출 | **Claude Code** | JIRA key 외 의미적 link |

**원칙**: 품질 우선. 룰 기반이 동작하는 경우에도 Claude Code가 검증/보강.

### 8.2 임베딩은 로컬 open source 모델

LLM 서비스가 아닌 Python 라이브러리. Agent가 직접 설치/실행 가능.

| 후보 모델 | 차원 | 다국어 | 비고 |
|---|---|---|---|
| **BAAI/bge-m3** | 1024 | ✓ (한/영 강함) | **권장** — multilingual, sparse + dense |
| intfloat/multilingual-e5-large | 1024 | ✓ | 안정적 alternative |
| BAAI/bge-large-en-v1.5 | 1024 | 영문 | 영문 dominant 환경 |

→ Stage A에서 Agent가 후보 모델 다운로드 + 비교 평가 후 결정.

### 8.3 Reranking 전략

| 옵션 | 설명 | 품질 |
|---|---|---|
| Score 합산 | vector + keyword + graph match score 가중 합 | 기본 |
| **Claude Code reranking** | top-N candidates를 Claude Code가 query 맥락에서 재정렬 | **권장** |
| Cross-encoder model (BAAI/bge-reranker-v2-m3) | 로컬 reranker | 추가 보강 |

→ 품질 우선이므로 **Claude Code reranking + cross-encoder hybrid**.

### 8.4 사내 LLM은 옵션

Stage G 이후 환경이 허용되면 보조적으로 활용:
- 사내 LLM이 더 빠른 경우 batch 작업에 활용
- 그러나 default는 Claude Code 단독.

---

# Part III. 시스템 설계

## 9. Ontology 설계

### 9.1 4축 모델

```
Project axis      : SoC 과제 (과제1, 과제2)
V-Level axis      : L0~L5
Concern axis      : Power, Performance, Memory, Area, Thermal, ...
Component axis    : Camera, Display, NPU, GPU, ...
```

질의 = 큐브의 단면(slice). 사용자는 자연어로 묻고, 시스템이 slice로 변환.

**다차원 모델, 1차원 인터페이스** 원칙.

### 9.2 V-Model Level 정의

| Level | 좌측 (정의/설계) | 우측 (검증/확인) | 주요 소스 |
|---|---|---|---|
| L0 | Customer needs | Field validation | Email, Conf |
| L1 | System requirements | System validation | Conf, JIRA |
| L2 | SoC architecture | Integration test | Conf, JIRA |
| L3 | Subsystem / IP architecture | Subsystem integration | JIRA, Conf |
| L4 | IP / Block design (μArch) | IP verification | JIRA |
| L5 | RTL / SW implementation | Unit test | JIRA, code |

### 9.3 Entity 정의

| Entity | 설명 | 주요 속성 |
|---|---|---|
| `Project` | SoC 과제 | id, name, phase, start_date, end_date |
| `Artifact` | 모든 정보 노드의 super-class | id, source_type, source_url, created_at, last_synced_at |
| `Issue` (Artifact) | JIRA ticket | jira_key, status, assignee, reporter, type |
| `Page` (Artifact) | Confluence page | conf_page_id, space, title, version |
| `EmailThread` (Artifact) | 이메일 스레드 | thread_id, subject, participants |
| `EmailMessage` (Artifact) | 개별 메시지 | message_id, from, to, cc, sent_at, in_reply_to |
| `Concern` | 횡단 관심사 | name, definition, unit |
| `Component` | IP/기능 모듈 | name, definition, parent_component |
| `Decision` | 결정 사항 | description, decided_by, decided_at |
| `Requirement` | 요구사항 | description, source_type (customer/internal) |
| `Person` | 사람 | name, email, role |
| `Metric` | PPA 수치 | type, value, unit, measured_at |
| `Event` | 상태 변화 이벤트 | entity_id, change_type, from, to, timestamp |

### 9.4 Relation 정의

| Relation | From → To | 설명 |
|---|---|---|
| `belongsToProject` | Artifact → Project | 어느 과제 소속 |
| `atLevel` | Artifact → V-Level | V-Model 위치 |
| `addresses` | Artifact → Concern | 어떤 Concern (multi) |
| `involves` | Artifact → Component | 어떤 Component (multi) |
| `tracesTo` | Artifact → Artifact | 상위 요구사항 추적 |
| `verifies` | Artifact → Artifact | 좌측 산출물 검증 |
| `derivedFrom` | Artifact → Artifact | 상위에서 도출 |
| `resolvedBy` | Issue → Decision/Artifact | 해결 |
| `discussedIn` | Decision → EmailThread/Page | 논의 장소 |
| `mentions` | Artifact → Entity | NER 언급 |
| `replyTo` | EmailMessage → EmailMessage | 이메일 reply |
| `partOf` | EmailMessage → EmailThread | 메시지 ↔ 스레드 |
| `authoredBy` | Artifact → Person | 작성자 |
| `assignedTo` | Issue → Person | 담당자 |
| `hasLifecycleEvent` | Artifact → Event | 상태 변화 |
| `feedbackTo` | Artifact → Artifact | 과제 간 환류 (cross-project) |

### 9.5 Schema 표현

YAML 파일로 정의하여 Git으로 버전 관리.

```yaml
# ontology/schema/v0.1/entities.yaml
entities:
  - name: Issue
    parent: Artifact
    properties:
      - {name: jira_key, type: string, required: true, unique: true}
      - {name: status, type: enum, values: [Open, InProgress, Resolved, Closed]}
      - {name: assignee, type: ref, target: Person}
    indexes:
      - {field: jira_key, type: btree}
      - {field: status, type: btree}

# ontology/schema/v0.1/relations.yaml
relations:
  - name: addresses
    from: Artifact
    to: Concern
    cardinality: many-to-many
    properties:
      - {name: confidence, type: float, range: [0,1]}
      - {name: source, type: enum, values: [rule, claude, manual]}
```

---

## 10. Architecture

### 10.1 Layered View

```
┌──────────────────────────────────────────────────────────────┐
│                   USER (10명 architect)                       │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│              UI Layer (Streamlit)                            │
│  - 자연어 질의 / 답변+source link / Timeline / Feedback         │
└────────────────────────┬─────────────────────────────────────┘
                         │ subprocess
┌────────────────────────▼─────────────────────────────────────┐
│              Query Processing (Claude Code)                   │
│  - 자연어 → slice 변환                                          │
│  - Hybrid retrieval orchestration                            │
│  - Multi-hop reasoning                                       │
│  - 답변 생성 + provenance                                       │
└──┬────────────────────┬────────────────────┬─────────────────┘
   │                    │                    │
┌──▼──────────────┐ ┌───▼──────────┐ ┌──────▼──────────────┐
│ Vector Search   │ │ Graph Query  │ │ Keyword Search       │
│ (pgvector)      │ │ (AGE Cypher) │ │ (Postgres FTS)       │
└──┬──────────────┘ └───┬──────────┘ └──────┬──────────────┘
   │                    │                    │
┌──▼────────────────────▼────────────────────▼─────────────────┐
│            Postgres + Apache AGE + pgvector                  │
│  - Ontology graph / Embeddings / Event log / Metadata        │
└──────────────────────────────────────────────────────────────┘
                         ▲
                         │
┌────────────────────────┴─────────────────────────────────────┐
│              Ingestion Pipeline                              │
│  - Connector abstraction (fixture | real)                    │
│  - Classifier (룰 + Claude Code)                              │
│  - Entity Extractor (룰 + Claude Code)                        │
│  - Embedder (local open source model)                        │
│  - Graph Builder / Event Logger                              │
└──┬────────────────┬────────────────┬─────────────────────────┘
   │                │                │
┌──▼─────────┐ ┌────▼──────────┐ ┌──▼────────────┐
│ Fixture    │ │ JIRA MCP /    │ │ Conf/Email    │
│ files      │ │ Real Source   │ │ skill / Real  │
└────────────┘ └───────────────┘ └───────────────┘
```

### 10.2 컴포넌트 책임

| 컴포넌트 | 책임 |
|---|---|
| Connector | 각 소스의 raw data 획득. Fixture/Real 동일 인터페이스 |
| Classifier | V-Level / Concern / Component 부여 (룰 + Claude Code) |
| Entity Extractor | NER (룰 + Claude Code) |
| Embedder | 로컬 open source 모델 (sentence-transformers) |
| Graph Builder | Entity와 Relation을 AGE에 적재 |
| Event Logger | 변경 사항을 event table에 기록 |
| Query Planner | 자연어 → slice/retrieval plan (Claude Code) |
| Retriever | Hybrid (vector + graph + keyword) |
| Reranker | Cross-encoder + Claude Code rerank |
| Reasoner | 결과 종합 + 답변 생성 (Claude Code) |
| UI | Streamlit, 사용자 대면 |
| Eval Harness | Ground truth Q set 자동 실행 + 비교 |

### 10.3 LLM/모델 역할

| 작업 | 실행 |
|---|---|
| 임베딩 생성 | 로컬 모델 (BAAI/bge-m3 등) |
| Reranking (1차) | Cross-encoder 로컬 모델 |
| Reranking (2차) | Claude Code |
| 분류 (1차 룰) | 정규식 + vocab match |
| 분류 (2차) | Claude Code |
| Entity 추출 (1차) | 정규식 + vocab match |
| Entity 추출 (2차) | Claude Code |
| Email 인용 제거 (1차) | talon 라이브러리 |
| Email 인용 제거 (fallback) | Claude Code |
| 자연어 → 쿼리 | Claude Code |
| 사용자 응답 | Claude Code |
| Multi-hop reasoning | Claude Code |

원칙: **룰이 처리 가능한 경우에도 Claude Code가 검증/보강하여 품질 우선**.

---

## 11. Ingestion 설계

### 11.1 공통 흐름

```
Source → Fetch → Normalize → Classify (rule + Claude Code) →
Extract Entities → Embed (local model) → Persist (Graph + Vector) → Log Event
```

### 11.2 Connector 추상화

Fixture mode와 Real mode가 동일 interface.

```python
class Connector(ABC):
    @abstractmethod
    def fetch(self, since: datetime) -> Iterator[RawArtifact]: ...

    @abstractmethod
    def normalize(self, raw: RawArtifact) -> NormalizedArtifact: ...

# Fixture implementations
class JiraFixtureConnector(Connector): ...
class ConfluenceFixtureConnector(Connector): ...
class EmailFixtureConnector(Connector): ...

# Real implementations (Stage G)
class JiraMCPConnector(Connector): ...
class ConfluenceSkillConnector(Connector): ...
class EmailSkillConnector(Connector): ...
```

### 11.3 소스별 ingestion

#### JIRA Ingestion

| 단계 | 작업 |
|---|---|
| Fetch | MCP (real) / fixture file (test) |
| Normalize | Issue + Comments + History를 표준 schema로 |
| Classify | (a) Project: JIRA key 매핑 (b) V-Level: project+label, 약한 case는 Claude Code (c) Concern/Component: label+vocab, 약한 case는 Claude Code |
| Extract | assignee, reporter, link, comment에서 JIRA key 언급 |
| Embed | title + description + comment를 chunk로 임베딩 |
| Persist | Issue node + edges (assignedTo, addresses, involves, ...) |
| Event | status transition, assignee 변경을 event log에 |

#### Confluence Ingestion

| 단계 | 작업 |
|---|---|
| Fetch | skill (real) / fixture file (test) |
| Normalize | storage format → cleaned text |
| Classify | (a) V-Level: parent page hierarchy + Claude Code (b) Concern/Component: label + 본문 Claude Code 분류 |
| Extract | 본문 JIRA key 언급, 페이지 link, 사람 mention |
| Embed | 본문 chunking (500~1000 token) + 임베딩 |
| Persist | Page node + chunk node + 관계 |
| Event | page version 변경 시 새 version event |

**Whitelist**: Architecture/Design space + label `decision/rca/spec/architecture` 우선. Meeting note 제외.

#### Email Ingestion (L1~L3)

| 단계 | 작업 |
|---|---|
| Fetch (L1) | skill (real) / fixture file (test) |
| Thread reconstruction (L1) | In-Reply-To, References 헤더 |
| Quote removal (L2) | talon 라이브러리, fallback은 Claude Code |
| Body normalize (L2) | 인사말/서명/disclaimer 제거 |
| Entity extraction (L3) | 사람, JIRA key, Component/Concern, 날짜 (룰 + Claude Code) |
| Classify (L3) | Project/V-Level/Concern/Component (Claude Code) |
| Embed | 정제된 본문 임베딩 |
| Persist | EmailThread + EmailMessage + replyTo + mentions |
| Event | 새 메시지 도착이 event |

### 11.4 분류 (Classification) 세부

각 Artifact마다 4가지 분류 (Project, V-Level, Concern, Component).

| 분류 | 1차 신호 | 2차 보강 | Fallback |
|---|---|---|---|
| Project | JIRA project key, Conf space, Email 참여자+시기 | Claude Code | Unknown |
| V-Level | JIRA project, label, Conf parent | Claude Code | 빈도 최다 level |
| Concern | Label/tag + vocab alias 매칭 | Claude Code | Multi-tag |
| Component | Label/tag + vocab alias 매칭 | Claude Code | Multi-tag |

**모든 분류는 `confidence ∈ [0,1]` 보유**. 낮으면 응답 시 "추정" 표시.

**품질 보장 정책**: 룰이 high confidence인 경우에도 sampling (예: 20%)으로 Claude Code 검증. 불일치 시 룰 보강.

---

## 12. Storage 설계

### 12.1 단일 Postgres 인스턴스

| Extension | 용도 |
|---|---|
| Apache AGE | Graph (entity, relation) |
| pgvector | Embedding |
| pg_trgm | Fuzzy text search |
| 기본 Postgres | Event log, metadata, raw cache |

### 12.2 주요 구조

#### Graph (AGE)

| Node label | 의미 |
|---|---|
| Project, Artifact, Issue, Page, EmailThread, EmailMessage, Concern, Component, Person, Decision, Requirement, Metric | (entity 섹션 참조) |

| Edge label | 의미 |
|---|---|
| BELONGS_TO_PROJECT, AT_LEVEL, ADDRESSES, INVOLVES, TRACES_TO, VERIFIES, MENTIONS, REPLY_TO, AUTHORED_BY, ASSIGNED_TO, RESOLVED_BY, DISCUSSED_IN, FEEDBACK_TO | (relation 섹션 참조) |

#### Relational tables

| Table | 용도 |
|---|---|
| `artifact_meta` | id, source_type, source_url, last_synced_at, raw_hash |
| `event_log` | entity_id, ts, change_type, before, after, source |
| `embedding` | entity_id, chunk_idx, vector |
| `classification` | entity_id, axis, value, confidence, source |
| `sync_state` | source_type, last_cursor, last_run_at |
| `user_feedback` | user, query, response_id, thumbs, comment, ts |
| `eval_run` | run_id, q_id, expected, actual, pass, ts |

### 12.3 데이터 흐름 원칙

- 원본 본문은 캐시 (선택적)
- 모든 노드는 `source_url` 보유 → 응답에 항상 첨부
- `event_log`는 append-only
- Migration script로 schema 진화

---

## 13. Query 처리 설계

### 13.1 처리 흐름

```
[사용자 자연어 질의]
       │
       ▼
[1. 의도 파악 + Slice 결정]  ← Claude Code
       │
       ▼
[2. Hybrid Retrieval]
   ├─ Graph query (AGE Cypher): slice 조건
   ├─ Vector search (pgvector): 의미 유사
   └─ Keyword search (FTS): exact match
       │
       ▼
[3. Reranking]
   ├─ Cross-encoder (1차)
   └─ Claude Code (2차)
       │
       ▼
[4. Context 조립]
       │
       ▼
[5. 답변 생성]  ← Claude Code
       │
       ▼
[6. UI 렌더링]
```

### 13.2 Slice 패턴별 query template

#### Pattern A: Concern-slice

> "이전 과제 power 관련 활동"

```cypher
MATCH (a:Artifact)-[:BELONGS_TO_PROJECT]->(p:Project {name:'SoC-N-1'}),
      (a)-[:ADDRESSES]->(c:Concern {name:'Power'})
RETURN a, c
ORDER BY a.created_at
```

#### Pattern B: Topic intersection

> "Camera shot 성능 이슈"

```cypher
MATCH (a:Issue)-[:INVOLVES]->(:Component {name:'Camera'}),
      (a)-[:ADDRESSES]->(:Concern {name:'Performance'})
WHERE a.text CONTAINS 'shot' OR a.embedding ~ 'shot'
RETURN a
```

#### Pattern C: Timeline-slice

> "지난 3과제 memory 절감 요청 처리"

```cypher
MATCH (req:Requirement)-[:ADDRESSES]->(:Concern {name:'Memory'}),
      (req)-[:BELONGS_TO_PROJECT]->(p:Project)
WHERE p.name IN ['SoC-N-3', 'SoC-N-2', 'SoC-N-1']
OPTIONAL MATCH (req)-[:RESOLVED_BY]->(d:Decision)
RETURN req, d, p
ORDER BY p.start_date
```

#### Pattern D: Lifecycle trace

```sql
SELECT * FROM event_log
WHERE entity_id = 'jira:JIRA-1234'
ORDER BY ts ASC
```

### 13.3 답변 형식 (표준 JSON)

```json
{
  "summary": "...",
  "items": [
    {
      "title": "...",
      "summary": "...",
      "sources": [{"type": "jira", "key": "...", "url": "..."}],
      "level": "L2",
      "concern": ["Power"],
      "component": ["Camera"]
    }
  ],
  "timeline": [...],
  "confidence": "medium",
  "reasoning_log": "..."
}
```

### 13.4 답변 품질 신호

| 신호 | 표시 |
|---|---|
| 후보 노드 수 0 | "해당 자료를 찾지 못함" |
| 후보 노드 수 적음 (≤2) | "제한적 자료 기반" |
| 분류 confidence 낮음 | "추정 분류로 검색" |
| Source 직접 quote 없음 | "요약 기반" |
| Cross-project 비교 | "과제별 데이터 양 다름" 주의 |

---

## 14. UI 설계

### 14.1 화면 구성

| 영역 | 내용 |
|---|---|
| Sidebar | 사용자명, 사용 가이드 link, feedback 버튼 |
| Main: Chat area | 질의 입력 + 답변 표시 |
| 답변 카드 | 요약 + items + source links |
| Timeline panel | event_log 기반 |
| Filter panel (옵션) | Project / Level / Concern / Component 수동 필터 |
| Feedback widget | thumbs up/down + 코멘트 |
| Debug toggle | Reasoning log 표시 (디버깅용) |

### 14.2 사용자 흐름

1. 질의 입력
2. "검색 중..." 표시 (Claude Code subprocess 실행)
3. 답변 카드 렌더링
4. Timeline 펼치기 가능
5. 각 link 클릭 → 새 탭에서 원본
6. Feedback 버튼 → 정성 평가 데이터 수집
7. Follow-up 질의 가능

### 14.3 Multi-user 처리

- Streamlit session_state로 사용자별 대화 격리
- DB의 `user_feedback`에 user 식별자 기록
- 동시 subprocess 호출은 process pool로 직렬화

### 14.4 보안

- 사내 망 한정 deploy
- 사용자 식별은 환경 변수 또는 사내 SSO 토큰 (옵션)
- Source link는 JIRA/Conf 자체 권한으로 보호

---

## 15. Claude Code 통합

### 15.1 호출 방식: Subprocess

```
Streamlit (Python)
  └─ subprocess.run(['claude-code', '--prompt', ..., '--input-json', ...])
       │
       └─ Claude Code
            ├─ Tools (graph_query, vector_search, ...)
            └─ stdout: 구조화 JSON
       ▲
       │
  ◀────┘
```

### 15.2 입력/출력 schema

**입력**:
```json
{
  "user_query": "이전 과제에서 power 관련 활동은?",
  "user_id": "architect_01",
  "session_id": "...",
  "context": {
    "current_project": "SoC-N",
    "conversation_history": [...]
  }
}
```

**출력**: 13.3 답변 형식.

### 15.3 Claude Code Tool 정의

| Tool | 용도 |
|---|---|
| `graph_query(cypher)` | AGE Cypher 실행 |
| `vector_search(query, top_k)` | pgvector 의미 검색 |
| `keyword_search(query)` | FTS |
| `event_log(entity_id)` | Lifecycle 조회 |
| `rerank(candidates, query)` | Cross-encoder + Claude Code rerank |
| `get_artifact(id)` | 단일 artifact 전체 정보 |
| `classify_text(text, axis)` | 분류 작업 (ingestion 시) |
| `extract_entities(text)` | NER (ingestion 시) |

### 15.4 Claude Code 수행 단계 (질의 응답 시)

1. 자연어 query → slice 의도 파악
2. AGE Cypher 또는 SQL 쿼리 생성 및 실행
3. Vector search 호출
4. 결과 reranking (cross-encoder + 자기 자신)
5. Multi-hop이 필요하면 추가 query
6. 답변 조립
7. Reasoning log 보존

### 15.5 Claude Code Ingestion 작업

Ingestion 시 Claude Code는 분류/추출 작업도 수행:

```
Batch ingestion script
  └─ for each artifact:
       ├─ 룰 기반 1차 분류
       ├─ if confidence < threshold or random sample:
       │     └─ Claude Code 호출 (분류 보강 + 검증)
       ├─ Entity 추출 (룰 + Claude Code)
       └─ DB 저장
```

품질 우선 정책: confidence 충분해도 sampling으로 Claude Code 검증.

---

## 16. 정성 평가 설계

### 16.1 평가 데이터 수집

| 데이터 | 수집 방식 |
|---|---|
| 모든 질의 로그 | UI 자동 |
| 답변 thumbs | 답변 직후 widget |
| 코멘트 | thumbs와 함께 옵션 |
| 사용 빈도 | 사용자별 일/주 단위 |
| 재사용률 | 같은 사용자의 후속 질의 |
| "찾고자 했던 답이었나" 자기 평가 | 주간 짧은 설문 |

### 16.2 평가 기준

| 차원 | 기준 |
|---|---|
| 유용성 | "이걸 안 썼으면 얼마나 걸렸을지" 자기 추정 |
| 신뢰감 | source link 확인 후 만족도 |
| 속도 인지 | 응답까지 체감 시간 |
| 재방문 의향 | "내일 또 쓰겠는가" |
| 권유 의향 | "동료에게 권하겠는가" |

### 16.3 사용자 사전 자료 수집 양식

각 사용자 5개 질문 (총 50개) 수집.

```
[질문 N]
질문 원문:
배경 (1-2줄):
실제 검색 방식 (JIRA/Conf/Email/사람/못 찾음):
소요 시간 (분):
원하는 답의 형태 (단답/리스트/링크 모음/비교 표/모름):
기대하는 항목:
```

---

# Part IV. 실행 계획

## 17. Phase 1 Stage 구조

### 17.1 8-Stage 개요

Phase 1은 **Core (A~G, Agent 자율)**와 **Post (H, 사람 평가)**로 구분.

#### Phase 1 Core (Agent 자율 완료)

| Stage | 이름 | Goal |
|---|---|---|
| **A** | Foundation | 기반 인프라 (DB, Schema, Vocab, 임베딩 모델, Agent 도구) |
| **B** | Fixture & Data Model | Fixture 생성 + Ground truth 정의 |
| **C** | Ingestion (Fixture) | Fixture → 그래프 적재 |
| **D** | Retrieval & Query | Hybrid retrieval + Claude Code |
| **E** | UI | Streamlit |
| **F** | E2E Validation Loop | Ground truth Q set 검증 + 개선 loop |
| **G** | Real Data Switch | Connector 교체로 실데이터 + **Agent 자율 완료점** |

#### Phase 1 Post (사람 평가)

| Stage | 이름 | Goal |
|---|---|---|
| **H** | User Eval & Iteration | 10명 정성 평가 (Stage G 완료 후 별도 활성화) |

### 17.2 의존성 그래프

```
═══════════════════════════════════════════════════
        Phase 1 Core (Agent 자율 완료 범위)
═══════════════════════════════════════════════════

A. Foundation
    │
    ▼
B. Fixture & Data Model ◀──┐
    │                      │  (Stage F에서 fixture 보강 시 회귀)
    ▼                      │
C. Ingestion (fixture) ────┤
    │                      │
    ▼                      │
D. Retrieval & Query ──────┤
    │                      │
    ▼                      │
E. UI ─────────────────────┤
    │                      │
    ▼                      │
F. E2E Validation Loop ────┘ (loop 종료 조건까지)
    │
    ▼
G. Real Data Switch  ★ Agent 자율 완료점
═══════════════════════════════════════════════════
        Phase 1 Post (사람 평가, 별도 활성화)
═══════════════════════════════════════════════════
    │
    ▼
H. User Eval & Iteration
```

**핵심**:
- **B~F**는 fixture만으로 완결. **G**에서 실데이터 붙임.
- **A~G가 Agent 자율 loop 종착점**. 모든 acceptance 통과 시 Agent는 작업 종료.
- **H는 사람 일정에 따라 별도 시작**. Agent loop 평가 대상 아님.

---

## 18. Stage 상세

각 Stage는 다음 구조:
- **Goal**
- **Subgoals**
- **Acceptance Criteria** (measurable)
- **Self-review checklist**

---

### Stage A. Foundation

**Goal**: PoC 모든 단계의 기반인 schema, vocab, DB, 임베딩 모델, agent 도구가 준비된다.

**Subgoals**:
- A1. DB 환경 (Postgres + AGE + pgvector) 동작
- A2. Ontology schema YAML v0.1 정의 (entities, relations)
- A3. Initial vocabulary YAML (Concern + Component)
- A4. Schema → DB 적용 스크립트 (idempotent)
- A5. Schema validator (YAML 무결성 + 참조 정합성)
- A6. 임베딩 모델 선택 + 로컬 설치 (BAAI/bge-m3 우선)
- A7. Cross-encoder reranker 모델 설치
- A8. Claude Code 도구 호출 검증
- A9. Goal/Acceptance YAML 형식 정의
- A10. Automated test harness 기반 (Q runner skeleton)
- A11. 프로젝트 폴더 구조 (`ingestion/`, `ontology/`, `query/`, `ui/`, `tools/`, `fixtures/`, `eval/`, `models/`)

**Acceptance Criteria**:
| 항목 | 검증 방법 |
|---|---|
| `make db-init` → 빈 그래프 생성 | psql에서 AGE label 조회 |
| `make schema-apply v=0.1` 동작 | 노드/edge label이 schema와 일치 |
| `validate.py` schema 통과 | 참조 무결성 위반 0 |
| 임베딩 모델 로드 + sample 임베딩 | shape 확인 |
| Cross-encoder 로드 + sample pair score | float 반환 |
| Claude Code 도구 호출 (graph_query 등) | sample 응답 |
| Goal/Acceptance YAML 파일 존재 | `eval/stages/A.yaml` |

**Self-review checklist**:
- Schema 변경 시 migration script 있는가?
- DB reset 후 한 명령으로 복원 가능?
- vocab YAML이 사람이 읽고 수정 가능?
- 임베딩 모델이 한국어/영어 혼재 텍스트에 잘 작동?
- 다음 Stage의 입력이 명확히 준비됐는가?

---

### Stage B. Fixture & Data Model

**Goal**: 실데이터 없이 ontology의 적절성을 검증할 수 있는 fixture가 완성된다.

**이 Stage가 Phase 1에서 가장 중요**. Ontology와 query template의 적절성이 여기서 결정됨.

**Subgoals**:
- B1. Fixture 생성 spec 작성
- B2. JIRA fixture (과제당 100 ticket = 총 200)
- B3. Confluence fixture (과제당 50 page = 총 100)
- B4. Email fixture (과제당 50 thread = 총 100)
- B5. Fixture 간 cross-reference (JIRA key 언급, link)
- B6. Ground truth annotation (각 fixture의 정답 분류 + query 결과)
- B7. Fixture loader (DB에 적재)
- B8. Fixture validation (예상 query가 정답 결과 내는지)
- B9. Ground truth Q set 작성 (20~30 Q, 4가지 slice 모두 cover)

**Fixture 분포 spec**:

| 차원 | 분포 |
|---|---|
| Project | 과제1 50%, 과제2 50% |
| V-Level | L0:10%, L1:15%, L2:25%, L3:20%, L4:20%, L5:10% |
| Concern | Power, Performance, Memory에 가중치 (40%), 나머지 5종에 분산 |
| Component | Camera, Display, NPU, Memory subsystem이 다수 |
| Lifecycle | Open 30%, In-Progress 30%, Resolved 30%, Closed 10% |

**Fixture 다양성 의도적 포함**:

| 종류 | 목적 |
|---|---|
| 명확한 분류 case | 룰 분류기 통과 |
| 모호한 분류 case | Claude Code 분류 필요 |
| Multi-tag case | "Memory"가 Concern+Component |
| Cross-project 연결 | 과제2가 과제1 참조 |
| Cross-source 연결 | Email→JIRA→Conf 흐름 |
| Long lifecycle | event 10개 이상 ticket |
| Customer email | 외부 도메인 + 요청 발화 |
| 인용 누적 thread | 5단계 reply 이상 |
| Failure 의도 case | 모호해서 분류 실패 예상 |

**Ground truth Q set 예시**:

| Q ID | 질문 | Slice | 정답 |
|---|---|---|---|
| Q1 | "과제1에서 power 관련 활동" | Concern-slice | 7개 항목 |
| Q2 | "Camera shot 성능 이슈" | Intersection | 4개 issue |
| Q3 | "지난 과제에서 memory 절감 요청 처리" | Timeline | 3개 요청 |
| Q4 | "JIRA-FIX-001 lifecycle" | Lifecycle | 7개 event |
| Q5 | (실패 의도) "Bluetooth 관련" | Unknown | "찾지 못함" |
| ... | (총 20~30 Q) | | |

**Acceptance Criteria**:
| 항목 | 검증 |
|---|---|
| 200 JIRA + 100 Conf + 100 Email fixture 존재 | 파일 count |
| 모든 fixture에 ground truth 라벨 | YAML/JSON 분리 |
| Fixture loader 실행 → DB 적재 완료 | 노드 수 일치 |
| 20+ Q set 정답 사전 정의 | `fixtures/queries.yaml` |
| Cross-reference 무결성 (orphan 없음) | validator |
| 4가지 slice pattern 모두 cover | Q ID별 slice tag |
| Architect가 읽어도 자연스러움 | manual review |

**Self-review checklist**:
- 모든 V-Level이 fixture에 존재?
- 모든 Concern/Component가 최소 5개 fixture에서 사용?
- Q set이 4가지 slice 모두 cover?
- 실패 case (graceful 응답)가 포함?
- Fixture가 실제 SoC 도메인의 자연스러운 표현?

---

### Stage C. Ingestion (Fixture Mode)

**Goal**: Fixture를 ingest해서 ontology 그래프가 완성된다.

**Subgoals**:
- C1. Connector 추상화 정의
- C2. JIRA fixture connector
- C3. Confluence fixture connector
- C4. Email fixture connector
- C5. 분류기 (룰 + Claude Code hybrid)
- C6. Entity extractor (룰 + Claude Code)
- C7. Embedder (로컬 모델)
- C8. Graph builder
- C9. Event logger
- C10. End-to-end ingestion pipeline orchestrator
- C11. Idempotent re-ingestion 검증

**기존 자산 흡수 전략**:

| 기존 자산 | Phase 1에서 |
|---|---|
| JIRA MCP | Connector layer 인터페이스 정의, Stage G에서 연결 |
| Confluence skill | 동일 |
| Email skill | 동일 |
| 키워드 + LLM edge 추론 | Classifier로 흡수, axis 명시 분리 |

**Acceptance Criteria**:
| 항목 | 검증 |
|---|---|
| Fixture 200+100+100 모두 ingest 완료 | 노드 수 = fixture 수 |
| 분류 정확도 ≥ 85% (ground truth 대비) | classification table vs label YAML |
| 모든 노드에 source_url, created_at | NOT NULL 검사 |
| Cross-reference edge 자동 생성 | JIRA key mention → MENTIONS edge |
| Event log 누락 없음 | 모든 status transition |
| 재실행 시 idempotent | 두 번 ingest해도 노드 중복 없음 |
| Embedding이 모든 chunk에 존재 | NOT NULL |

**Self-review checklist**:
- 분류 실패 case가 unknown으로 graceful?
- Claude Code 호출이 batch 효율적인가?
- 임베딩이 한 번만 생성되고 재사용?
- Connector interface가 fixture/real 양쪽 동작 가능한 추상화?
- Confidence 낮은 분류가 응답에 표시되는가?

---

### Stage D. Retrieval & Query

**Goal**: 자연어 질의가 4가지 slice pattern으로 라우팅되어 답변이 생성된다.

**Subgoals**:
- D1. Graph query tool (AGE Cypher wrapper)
- D2. Vector search tool (pgvector cosine)
- D3. Keyword search tool (FTS + pg_trgm)
- D4. Lifecycle/event tool
- D5. Cross-encoder rerank tool
- D6. Hybrid retrieval pipeline
- D7. Claude Code prompt: slice classification
- D8. Claude Code prompt: query plan → tool 호출
- D9. Claude Code prompt: 답변 조립 (JSON schema 준수)
- D10. Reasoning log 저장
- D11. Provenance 자동 첨부 검증

**Acceptance Criteria**:
| 항목 | 검증 |
|---|---|
| Q1~Q4 (각 pattern) 정답 반환 | 정답 set 대비 75%+ recall |
| 모든 응답에 source URL | JSON 검증 |
| 응답 5초 이내 (fixture 규모) | timing test |
| 실패 case Q5 graceful "찾지 못함" | 응답 text 검사 |
| Reasoning log에 tool 호출 trace | log 파일 검증 |
| 답변 JSON schema 준수 | schema validator |

**Self-review checklist**:
- 4가지 slice pattern 모두 prompt에 명시?
- Multi-hop이 필요한 Q3가 추가 tool 호출로 풀림?
- 답변 JSON이 schema에 맞음?
- Reasoning log가 사람이 읽고 디버깅 가능?
- Source 정확도 95%+?

---

### Stage E. UI (Streamlit)

**Goal**: 사용자가 자연어로 묻고 구조화된 답변 + source link + timeline을 볼 수 있다.

**Subgoals**:
- E1. Chat UI (질의 입력 + 답변 영역)
- E2. Subprocess wrapper for Claude Code
- E3. 답변 카드 컴포넌트
- E4. Source deep link 렌더링
- E5. Timeline panel (펼침/접힘)
- E6. Feedback widget (thumbs + 코멘트)
- E7. Session 격리 (multi-user)
- E8. 사용자 식별 (env / 사내 ID)
- E9. 에러 처리 (Claude Code timeout, DB 장애)
- E10. 사용 가이드 페이지
- E11. Reasoning log toggle (디버깅용)

**Acceptance Criteria**:
| 항목 | 검증 |
|---|---|
| 질의 → 답변 round trip 동작 | manual test |
| 두 사용자 동시 세션 가능 | 두 브라우저 |
| Source link 클릭 시 새 탭 | manual |
| Feedback 저장 확인 | DB user_feedback row |
| Subprocess timeout 시 graceful 메시지 | 30초 응답 없을 시 |
| Reasoning log 토글 동작 | manual |

**Self-review checklist**:
- 첫 답변이 30초 이내 표시되는가?
- 답변 형식이 가독성 있는가?
- 에러 시 사용자가 다음 행동을 알 수 있는가?
- Architect가 학습 없이 바로 사용 가능?

---

### Stage F. E2E Validation Loop (핵심 평가 단계)

**Goal**: Fixture 기반 ground truth Q set에 대해 시스템이 일관되게 답변하는지 검증하고, 실패 case를 fix하는 loop를 돈다.

**Loop 구조**:

```
[1. Q set 실행 (자동)]
       │
       ▼
[2. 결과 vs ground truth 비교]
       │
       ▼
[3. 실패 case 분류]
   - 분류 오류 → 분류기 / vocab 수정
   - Retrieval 누락 → 임베딩 / Cypher 수정
   - 답변 형식 → prompt 수정
   - Source link 누락 → ingestion 수정
       │
       ▼
[4. 수정 + 재실행]
       │
       ▼
[5. Acceptance 통과까지 반복]
```

**Subgoals**:
- F1. Automated Q runner (20+ Q 한 번에)
- F2. 결과 비교기 (응답 vs ground truth, recall/precision)
- F3. 실패 분류기 (어느 layer에서 실패인지 자동 진단)
- F4. Diff report 생성 (변경 전후 metric 비교)
- F5. Regression detection (이전 통과 Q가 다시 실패하면 알림)
- F6. Loop iteration N → fix → 재평가 (반복)
- F7. Acceptance criteria 도달

**Acceptance Criteria**:
| 항목 | 임계값 |
|---|---|
| Ground truth 20+ Q recall | ≥ 85% |
| Source link 정확도 | ≥ 95% |
| 실패 case graceful 응답 | 100% |
| 응답 형식 schema 준수 | 100% |
| Reasoning log 가독성 | 사람이 읽고 이해 가능 |
| Regression 0 | 이전 통과 Q 모두 통과 |
| 분류 정확도 (모든 axis 평균) | ≥ 90% |

**Self-review checklist** (loop마다):
- 어느 layer에서 실패가 가장 많은가?
- 같은 fix가 다른 case도 개선?
- 새로 발견된 edge case가 fixture에 추가?
- 임계값 도달이 진정한 개선인지 overfit인지?
- 변경이 reasoning log에 명확히 기록되어 있는가?

---

### Stage G. Real Data Switch

**Goal**: Fixture → 실데이터 전환이 connector 교체만으로 가능하다.

**이 Stage가 Phase 1 Core의 종착점**. 모든 acceptance 통과 시 Agent 자율 실행 완료.
이후 Stage H는 사람의 일정에 따라 별도 활성화.

**Subgoals**:
- G1. Connector 추상화 검증 (Stage C에서 미리 설계)
- G2. JIRA MCP 실 연결
- G3. Confluence skill 실 연결
- G4. Email skill 실 연결 (비실명 계정)
- G5. 권한/인증 설정
- G6. 실데이터 sample 50개로 dry run
- G7. 분류 정확도 측정 (실데이터 sample 사람 검토)
- G8. 전체 실데이터 ingest
- G9. 증분 동기화 활성화 (webhook 또는 polling)
- G10. 사내 LLM 가용 시 보조 통합 (옵션)

**Acceptance Criteria**:
| 항목 | 검증 |
|---|---|
| Connector 교체로 fixture → real 전환 | 코드 변경 최소 |
| 실데이터 sample 50개 dry run 성공 | 노드/edge 생성 확인 |
| 분류 정확도 ≥ 75% (실데이터 sample) | 수동 sample check |
| 전체 ingest 완료 | 노드 수 확인 |
| 증분 동기화 동작 | 새 ticket 자동 반영 |
| Source URL 클릭 시 실제 자료 도달 | manual |

**Self-review checklist**:
- Fixture와 실데이터 차이에서 분류기 약점은?
- 추가 vocab 필요한 것은?
- 실데이터 edge case가 fixture에 반영?
- 권한/인증 안전?
- **Agent 자율 완료점에 도달한 상태인가?** (Stage H 사람 평가 시작 가능 상태)
- **사람에게 인계할 산출물 정리됐는가?** (사용 가이드, 평가 절차, 알려진 한계)

---

### Stage H. User Eval & Iteration

> **이 Stage는 Phase 1 Core의 일부가 아님**. Stage G 완료 후 사람의 일정에 따라 별도로 활성화.
> Agent 자율 loop의 acceptance 평가 대상이 아니며, 사람이 사용자 모집/평가/인터뷰를 주도.

**Goal**: 10명 사용자가 실데이터에서 시스템을 사용하고 정성 평가가 수집된다.

**Subgoals**:
- H1. 사용자 가이드 (1-page)
- H2. 사용자 사전 자료 50 Q 분석 → vocab/template 보강
- H3. Baseline 사용 1주
- H4. 사용 로그 분석 (질의 패턴, 실패 case)
- H5. 사용자 인터뷰 (3~5명)
- H6. 개선 cycle (Stage F의 loop를 실 query로 재실행)
- H7. 재평가 (사용 의향 측정)
- H8. 발견된 한계 정리 (다음 phase input)

**Acceptance Criteria** (정성):
| 항목 | 목표 |
|---|---|
| 10명 중 7명 이상 "계속 쓰겠다" | survey |
| 일주일 사용 빈도 | 사용자당 평균 5회 이상 |
| 답변 thumbs-up 비율 | 70%+ |
| 사용자 인터뷰 주요 issue 정리 | 다음 phase input |

**Self-review checklist**:
- 사용자 피드백이 시스템 개선으로 이어졌는가?
- 정성 평가가 정량 metric과 일치?
- 발견된 한계가 다음 phase의 input으로 정리?

---

## 19. Agent 자율 실행 Loop

Phase 1 원칙 P1 (Goal-driven autonomy)과 P5 (Evaluation loop)를 충실히 수행하기 위한 메커니즘.

### 19.1 Agent의 자율성 정의

**Agent 자율 loop 범위: Stage A ~ G**. Stage H는 사람 평가 단계로 자율 범위 밖.

| Layer | 자율성 |
|---|---|
| Goal 정의 | 사람이 (이 문서로) |
| Stage 진행 (A~G) | Agent 자율 |
| Acceptance 판정 (A~G) | Agent 자동 검증 |
| 실패 시 fix | Agent 자율 |
| Schema/vocab 변경 | Agent 제안, 사람 승인 (L2) |
| 다음 Stage 진행 결정 (A→G) | 모든 acceptance 통과 시 자동 |
| Stage G → H 전환 | **사람이 결정** (G 완료 후 H 활성화 시점은 사람 일정) |
| Stage H 진행 | 사람 주도 (Agent는 데이터 분석 보조) |

### 19.2 Agent 작업 단위 (Iteration)

```
[1. 현재 Stage의 goal/acceptance 읽기]
       │
       ▼
[2. 부족한 항목 식별]
       │
       ▼
[3. 구현 (code, config, fixture 등)]
       │
       ▼
[4. 자동 검증 실행]
   - Unit test
   - Acceptance criteria check
   - Self-review checklist
       │
       ▼
[5. 결과 보고서 작성]
       │
       ▼
[6. 통과 → 다음 항목 / 실패 → 분석 + 재시도]
```

### 19.3 Goal/Acceptance YAML 형식

Agent가 stage 완료 여부를 자동 판정할 수 있는 machine-readable 형식.

```yaml
# eval/stages/B.yaml
stage: B
name: "Fixture & Data Model"
goal: "실데이터 없이 ontology의 적절성을 검증할 수 있는 fixture가 완성된다"

subgoals:
  - id: B1
    name: "Fixture 생성 spec 작성"
    artifacts: ["fixtures/spec.md"]
  - id: B2
    name: "JIRA fixture"
    artifacts: ["fixtures/jira/*.yaml"]
    count: 200
  # ...

acceptance:
  - id: ACC-B-01
    description: "200 JIRA fixture 존재"
    check: "ls fixtures/jira/*.yaml | wc -l"
    expected: 200
  - id: ACC-B-02
    description: "Ground truth Q set 20개 이상"
    check: "yq '.queries | length' fixtures/queries.yaml"
    expected: ">= 20"
  - id: ACC-B-03
    description: "4가지 slice pattern 모두 cover"
    check: "python eval/check_slice_coverage.py"
    expected: "all 4 patterns present"
  # ...

self_review:
  - "모든 V-Level이 fixture에 존재?"
  - "모든 Concern/Component가 최소 5개 fixture에서 사용?"
  - "실패 case 포함?"
```

### 19.4 Stage 간 전이 조건

Stage N → N+1:
1. 모든 acceptance criteria PASS
2. Self-review checklist 모두 통과
3. 이전 Stage의 회귀 없음 (regression test)
4. (선택) 사람의 final review approval

### 19.5 회귀(Regression) 방지

- Stage F에서 통과한 Q는 이후 Stage에서도 통과해야 함
- 매 iteration마다 regression test 자동 실행
- 회귀 발견 시 해당 iteration의 변경 사항 rollback 후 분석

### 19.6 Loop 종료 조건

| 조건 | 의미 | 결과 |
|---|---|---|
| Stage G의 모든 acceptance 통과 | **Phase 1 Core 정상 종료** | Agent 자율 작업 완료, Stage H 사람 인계 |
| 특정 Stage에서 N회 (예: 5회) iteration 후에도 개선 없음 | 자율 개선 한계 | 사람 개입 trigger |
| 동일 실패 case 반복 | Fix가 효과 없음 | 다른 접근 필요, 사람 개입 |
| 회귀 발견 후 회복 실패 | rollback도 안 됨 | 사람 개입 |

### 19.7 Reasoning Log 표준

Agent의 모든 결정이 추적 가능:

```yaml
# logs/iteration_<n>.yaml
iteration: 42
stage: F
timestamp: 2024-XX-XX
goal: "Q3 (Timeline-slice) recall 향상"
hypothesis: "Cypher의 ORDER BY 누락으로 결과 단편적"
change:
  file: query/templates/timeline.cypher
  diff: "..."
test_before:
  q3_recall: 0.6
test_after:
  q3_recall: 0.85
regression: none
self_review: "통과. 다음 iteration으로."
```

### 19.8 Agent 개입 한계 (Safety)

| 영역 | Agent 자율 | 사람 승인 필요 |
|---|---|---|
| Code 작성/수정 | ✓ | |
| Fixture 추가 | ✓ | |
| Vocab 추가 | ✓ | |
| Schema 변경 | 제안 | 승인 |
| Prompt 변경 | ✓ | (큰 변경은 승인) |
| Acceptance criteria 변경 | 제안 | 승인 |
| Real data 접근 | | 승인 (Stage G) |
| Production deploy | | 승인 |

---

## 20. Open Issues

구현 중 결정할 항목:

| # | 항목 | 결정 시점 |
|---|---|---|
| O1 | Schema versioning 도구 (Alembic vs sqlx vs custom) | Stage A |
| O2 | 임베딩 모델 최종 선택 (bge-m3 vs e5-large) | Stage A |
| O3 | Fixture format (YAML / JSON / SQL dump) | Stage B |
| O4 | Chunking 전략 (token 크기, overlap) | Stage C |
| O5 | Email 첨부 메타 처리 깊이 | Stage C |
| O6 | Multi-language (한/영 혼재) 처리 | Stage C |
| O7 | Cross-project `feedbackTo` 자동 추출 여부 | Stage F 이후 |
| O8 | Confidence threshold | Stage D |
| O9 | Streamlit session 동시성 (process pool 크기) | Stage E |
| O10 | Reasoning log 보존 기간 | Stage E |
| O11 | Acceptance 임계값 조정 (실데이터 후) | Stage G |
| O12 | 사용자 vocab 반영 시점 | Stage H |
| O13 | 사내 LLM 통합 시점 (옵션) | Stage G |

---

# Part V. 부록

## 21. Initial Vocabulary

### 21.1 Concerns (PoC 시작 set, 8개)

| Name | Aliases (한/영) | Units |
|---|---|---|
| Power | 전력, 파워, 소비전력, consumption | mW, mA, W |
| Performance | 성능, perf, throughput | fps, MHz, MOPS |
| Memory | 메모리, 메모리 사용량, footprint | MB, GB, KB |
| Area | 면적, die size | mm², gate count |
| Thermal | 발열, 온도 | °C, junction temp |
| Latency | 지연, 응답시간 | ms, μs, ns |
| Bandwidth | BW, 대역폭 | GB/s |
| Reliability | 신뢰성 | FIT |

### 21.2 Components (PoC 시작 set, Stage B에서 보강)

- **Multimedia**: Camera, ISP, Display, Codec (Video/Image), GPU
- **AI/Compute**: NPU, DSP, CPU cluster
- **Memory**: MemorySubsystem, DRAM controller, Cache
- **Interconnect**: NoC, AXI bus
- **Power**: PMIC, PMU, Power domain
- **Sensor**: Touch, Sensor hub

### 21.3 V-Level 분류 룰 (초기)

| Source | 신호 → Level |
|---|---|
| JIRA `Architecture` project | L2 |
| JIRA `IP design` project | L4 |
| JIRA `SW` project | L4-L5 |
| JIRA label `level/L1` 등 명시 | 직접 |
| Confluence parent page `System Requirements` 하위 | L1 |
| Confluence parent page `Architecture` 하위 | L2 |
| Email subject에 customer 도메인 | L0 |
| Default | Claude Code 분류 결과 |

---

## 22. 핵심 설계 원칙

1. **다차원 모델, 1차원 인터페이스** — 사용자는 자연어, 시스템은 큐브
2. **단면(slice) 사고법** — 한 질의는 한 단면
3. **Fixture-first** — 실데이터 의존 없이 검증
4. **Self-contained execution** — 외부 LLM 서비스 없이 Claude Code + 로컬 라이브러리만으로
5. **Quality-first** — 비용 제약 없음, 모든 LLM 작업은 최고 품질 추론
6. **Source 보존 우선** — 모든 응답에 원본 link
7. **Schema as YAML + Git** — 진화 가능
8. **Goal-driven autonomy** — Agent 자율, acceptance로 판정
9. **Evaluation loop** — 완성도는 loop로 올림
10. **Connector 추상화** — Fixture ↔ Real 전환 가능
11. **확장은 점진적** — PoC → Beta → Production 진화 경로 보존
12. **정성 평가 친화** — 사용 의향이 정답률보다 중요
13. **실패에 graceful** — 모를 때 모른다고 답
14. **Agent 자율 범위는 A~G** — 사람 평가(H)는 자율 loop 밖, 별도 활성화

---

*PoC 설계 문서. Agent 자율 실행 기반 Phase 1 구현 시작 준비.*

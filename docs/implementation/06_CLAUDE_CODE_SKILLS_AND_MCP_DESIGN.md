# Claude Code Skills and MCP Design

## 1. 목표

사내 환경은 Claude Code를 기준으로 한다. JIRA, Confluence, Email source 접근은 제품 코드에 직접 고정하지 않고 Claude Code skill로 관리한다. MCP는 사용할 수 있지만, MCP는 skill 내부에서 선택 가능한 접근 방식 중 하나로 둔다.

핵심 목표:

- 사내 환경별 JIRA/Confluence/Email 접근 방식을 쉽게 교체한다.
- MCP, REST API, file export, mock/dummy source를 같은 source contract로 정규화한다.
- secret, endpoint, project key, query scope를 코드에 하드코딩하지 않는다.
- source skill이 반환해야 할 output shape를 명확히 해서 agent pipeline과 연결한다.
- Claude Code 작업자가 source별 규칙을 매번 다시 묻지 않게 한다.

## 2. 설계 원칙

- Source skill은 "데이터 접근 절차와 변환 규칙"을 관리한다.
- Application code는 source skill 존재 여부를 몰라야 한다.
- Application code는 `SourceAdapter` interface와 `SourceArtifact` contract만 본다.
- MCP는 source skill의 optional transport다.
- 같은 skill은 MCP, REST, export file, dummy fixture 중 하나를 선택할 수 있어야 한다.
- 사내 환경 변경은 skill reference/config만 수정하고 core pipeline은 수정하지 않는다.

## 3. Project-local Skill 위치

이 repo는 Claude Code 기준으로 다음 project-local skill을 제공한다.

```text
.claude/skills/
  rune-source-jira/
    SKILL.md
  rune-source-confluence/
    SKILL.md
  rune-source-email/
    SKILL.md
  rune-source-skill-pattern/
    SKILL.md
```

각 skill은 짧은 실행 규칙만 가진다. 구체적인 endpoint, token, query, mailbox, project key는 commit하지 않는다.

## 4. Skill과 MCP의 관계

```text
Claude Code user request
  -> source skill selected
  -> skill chooses transport
       ├─ MCP tool
       ├─ REST API
       ├─ exported file
       └─ dummy fixture
  -> normalize to SourceArtifact
  -> run ingestion/analysis workflow
```

MCP를 쓰는 경우에도 skill이 다음을 책임진다.

- 어떤 MCP server/tool을 사용할지 선택
- tool output을 source contract로 매핑
- permission/scope를 확인
- 민감 정보가 payload에 섞이지 않게 사전 점검
- 실패 시 REST/export/dummy fallback 가능 여부 안내

## 5. 권장 Transport 선택 순서

| 우선순위 | 방식 | 사용 조건 |
| --- | --- | --- |
| 1 | MCP | 사내 Claude Code에 해당 MCP server가 설치되어 있고 권한/감사 정책이 맞는 경우 |
| 2 | REST API | MCP가 없지만 사내 API token/proxy 접근이 가능한 경우 |
| 3 | Export File | 폐쇄망 또는 권한 제한으로 live access가 어려운 경우 |
| 4 | Dummy Fixture | 개발/테스트/CI 또는 실제 데이터 사용 불가한 경우 |

초기 구현은 dummy fixture를 기본값으로 둔다. 사내 적용 시 skill config만 바꿔 MCP나 REST를 선택한다.

## 6. Source Skill 공통 Output Contract

Source skill은 최종적으로 다음 field를 채울 수 있어야 한다.

```text
source_type
external_id
source_url
project_key
title
body_text
author_id
created_at
updated_at
labels
links
parent_id
child_ids
metadata
access_scope
data_classification
content_hash
```

Application code에서는 이를 `SourceArtifact`와 `ArtifactChunk`로 변환한다.

## 7. JIRA Skill 책임

JIRA skill은 다음을 관리한다.

- project key, JQL, component/release scope
- issue, comment, link, history 수집 정책
- comment/changelog이 허용되는 경우 `metadata.comment_refs`,
  `metadata.comment_count`, `metadata.history_refs`,
  `metadata.history_count`로 보존해서 replay/debug에서 어떤 입력이
  사용되었는지 추적 가능하게 한다.
- JIRA issue type과 MBSE node type을 직접 동일시하지 않는 규칙
- incremental cursor 기준
- deleted/moved/renamed issue 처리
- source link와 evidence span 후보 생성

MCP tool이 있다면 issue search, issue detail, comments, links, changelog 조회에 사용한다.

## 8. Confluence Skill 책임

Confluence skill은 다음을 관리한다.

- space key, page tree, label, ancestor scope
- page body, section heading, table extraction
- page version과 diff 처리. 이전 version 정보가 있으면 source artifact
  `metadata.previous_version_number`에 저장하고 현재 version은
  `metadata.version_number`에 저장해서 stale trace rule이 동일한 contract로
  동작하게 한다.
- JIRA mention/link 매핑
- source evidence의 section path/table cell ref 생성
- attachment metadata는 초기에 metadata만 수집

MCP tool이 있다면 page search, page read, children, version history 조회에 사용한다.

## 9. Email Skill 책임

Email skill은 전체 mailbox 수집용이 아니다. 승인된 decision source 또는 제한된 mailbox/label/archive만 다룬다.

Email skill은 다음을 관리한다.

- 허용 mailbox, folder, label, date range
- thread metadata와 participant masking
- decision candidate extraction
- JIRA/Confluence reference link 추출
- 개인정보/비업무 본문 제외
- 민감 thread manual review routing

MCP tool이 있다면 email search/read 대신 decision archive 접근을 우선한다. 일반 mailbox MCP는 보안 검토 후 제한적으로만 사용한다.

## 10. 사내 환경별 변경 포인트

사내 적용 시 보통 바뀌는 것은 다음이다.

| 변경 대상 | 위치 | 제품 코드 수정 필요 여부 |
| --- | --- | --- |
| MCP server name/tool name | `.claude/skills/*/SKILL.md` 또는 local config | 없음 |
| JIRA project/JQL | local env or source config | 없음 |
| Confluence space/page scope | local env or source config | 없음 |
| Email label/archive scope | local env or source config | 없음 |
| auth token | local env/Claude Code secret | 없음 |
| source field mapping | skill reference 또는 adapter config | 보통 없음 |
| new source type | new skill + new adapter | 일부 있음 |

## 11. MCP 설정 파일 정책

실제 `.mcp.json`에는 사내 endpoint나 server name이 들어갈 수 있으므로 commit하지 않는다.

권장:

- `.mcp.example.json`은 commit한다.
- `.mcp.json`은 local 전용으로 둔다.
- token은 `.mcp.json`에도 직접 쓰지 말고 environment variable을 참조한다.

예:

```json
{
  "jira-internal": {
    "type": "http",
    "url": "${RUNE_JIRA_MCP_URL}",
    "headers": {
      "Authorization": "Bearer ${RUNE_JIRA_MCP_TOKEN}"
    }
  }
}
```

## 12. 구현 반영 사항

`03_STEP_BY_STEP_IMPLEMENTATION_PLAN.md`의 Step 5는 다음처럼 해석한다.

- 먼저 `DummySourceAdapter`를 구현한다.
- 동시에 Claude Code source skill을 사용해 dummy fixture를 production contract로 변환하는 절차를 검증한다.
- 이후 JIRA/Confluence/Email live access는 skill에서 transport를 바꿔 검증한다.
- app code는 MCP tool name을 알지 않는다.

## 13. 검증 기준

Source skill 설계가 충분한지 확인하는 기준:

- MCP 없이 dummy fixture로 전체 pipeline이 돈다.
- MCP가 있어도 output은 같은 `SourceArtifact` shape다.
- 사내 endpoint 변경이 core Python module 변경 없이 가능하다.
- source access 실패가 `SOURCE_AUTH_ERROR`, `SOURCE_RATE_LIMIT`, `SOURCE_MALFORMED_ARTIFACT`로 trace된다.
- Email skill은 mailbox 전체 수집을 기본값으로 하지 않는다.
- skill 문서에 secret이나 실제 endpoint가 없다.

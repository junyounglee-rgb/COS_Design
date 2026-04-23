# event_infos × 이벤트 기획서 (Notion) 교차 분석

## Context

1차 read-only 분석으로 `event_infos.xlsx`의 구조·FK·데이터 입력 패턴은 파악됨 (하단 "섹션 A" 참조).
이제 Notion의 **미션/이벤트 기획서 페이지**와 **실제 Excel 데이터**를 교차 분석해 **설계-구현 갭·불일치·결손 항목**을 도출해야 한다.
절차: (1) 1차 분석 계획 확정 → (2) 에이전트 구성 확정 → (3) 하네스 실행.

---

## 섹션 A. event_infos.xlsx 1차 분석 요약 (기록 보존)

### 구조
- 단일 시트, ~78행, PK=`^id` (INT)
- 컬럼: `^id`, `name`, `tab_order`, `tab_order_type`(SHOW / SHOW_CLEAR_BOTTOM / HIDE_CLEAR), `event_path`(Block_*), `event/%key`(variant FK), `event/%param1`(ref id), `$filter`(빌드 분기)
- **variant FK 패턴**: `event/%key` = `<자식테이블>:ref_event_id`, `event/%param1` = 실제 키 값

### 연결 테이블 8종
`step_mission_events` / `nday_mission_events` / `vault_mission_events` / `attendance_events` / `quest_gacha_events` / `invitation_events` / `pve_events` / `daily_fortune_events`
(각 테이블은 다시 `quests`, `items` 등 2차 FK 참조)

### 데이터 입력 컨벤션
- `^id`는 숫자 범위로 카테고리 암묵 분류 (1·3·5·10 기본 / 301~314 데일리 / 4001~ 금고 / 60010~ 게임모드 등)
- `event/%param1` ≈ `^id` (일부 예외)
- 같은 `name`이 여러 행 — 빌드·시점별 행 복제 운영 패턴
- `event_path = Block_<EventName>` Unity 프리팹 키 컨벤션

### 확인 필요 이슈
1. `vault_mission_events.xlsx` 단독 파일 미확인 (step_mission에 흡수된 가능성)
2. `protobuf/`에 `.proto` 파일 직접 노출 없음 → oneof 정확 구조 재확인 필요

---

## 섹션 B. Notion 측에서 파악된 구조

### 루트 페이지: 미션 / 이벤트
URL: `https://www.notion.so/22bde3da895680e7b0a5e743433b24e5`
- 하위 DB: **미션 / 이벤트 기획서** (collection `22bde3da-8956-81be-aabc-000ba9c38331`)
- 하위 가이드: `[가이드] 이벤트 작성법 - event_infos`

### 가이드 페이지의 매핑 테이블 (Notion 기준)
| 기획서 (Notion 페이지) | 설명 | 데이터 테이블 |
|---|---|---|
| 공통 이벤트 탭 프리팹 | 이벤트 탭 개요 | `event_infos` |
| 스텝 미션 이벤트 | 순차 달성 + 보너스 | `step_mission_events` |
| 주말 특별 보너스 | 스텝 미션 하위 | `step_mission_events` |
| (스텝 미션 서브2) | 스텝 미션 하위 | `step_mission_events` |
| 어드벤트 캘린더 | 일자별 미션보드 | `nday_mission_events` |
| 꽝뽑 이벤트 | 미션→재화→가챠→마일스톤 | `quest_gacha_events` |
| 초대 이벤트 | 미션+친구초대→코스튬 | `invitation_events` |
| 금고 미션 | 달성 후 지연 보상 | `vault_mission_events` |
| PvE | **스펙아웃** | `pve_events` |
| (미정) | **스펙아웃** | `-` |
| quests 가이드 | quests 사용 규칙 | `quests` |

### DB 스키마 (미션/이벤트 기획서)
컬럼: `문서명`, `메인 담당자`, `서브 담당자`, `진행상태`, `최초 작성 일자`, `최종 업데이트 목표`, `일감 주소`
`진행상태` enum: 기획서 작성중 / 작성 완료 / 기획 리드 리뷰 / PD 리뷰 / 개발 리뷰 / 기발 진행 중 / 개발 완료 / 갱신 필요

### 가이드가 명시하는 설정 규칙
1. **event_infos**: 탭 오더, 탭 이름, 프리팹 → (탭 디스플레이 메타)
2. **개별 이벤트 테이블**: **이벤트 시작/종료 시간**, 퀘스트(보상) 설정
3. **quests**: 보상 정의, town과 ID 범위 분리 필수

---

## 섹션 C. 교차 분석 계획 (1차)

### 분석 축 (Axes)

| 축 | 질문 | 비교 대상 |
|---|---|---|
| A1. 존재성 | Notion 가이드에 명시된 8개 테이블이 excel에 실제로 다 있는가? | 가이드 매핑 vs `excel/*.xlsx` 파일 목록 |
| A2. 스키마 정합 | 가이드 규칙("개별 테이블에 시작/종료 시간") vs 실제 스키마 컬럼 | 가이드 텍스트 vs textconv 시트 스키마 |
| A3. FK 무결성 | `event_infos.event/%param1` 값이 자식 테이블 `ref_event_id`에 실제 존재? | event_infos 행 vs 자식 테이블 행 |
| A4. 기획-구현 커버리지 | Notion 기획서 각 페이지의 상세 설계 내용 vs excel 데이터 반영 여부 | 개별 기획서 페이지 vs 해당 자식 테이블 |
| A5. 진행상태 vs 데이터 존재 | DB의 `진행상태=개발 완료` 항목이 실제 excel에 데이터가 있는가? (반대로 `작성중`인데 excel에 이미 있는 경우) | DB 상태값 vs excel 행 존재 |
| A6. 스펙아웃 처리 | PvE 등 "스펙아웃"으로 적힌 이벤트가 excel에서 어떻게 관리되고 있는가? (잔존 데이터, 유령 FK 등) | 가이드 "스펙아웃" vs `pve_events.xlsx` 행·참조 |
| A7. 명명 컨벤션 | `event_path = Block_*`이 가이드의 프리팹 컨벤션과 일치? | excel 값 vs 가이드 기대 |
| A8. 시간 설정 실존 | 각 `*_events.xlsx`에 start/end date 컬럼이 있는가? 빈 값/미래 값 비율? | 자식 테이블 스키마·데이터 |
| **A10. 실제 연결 구조 (심층)** | `D:\COS_Project\cos-data\excel\` 내에서 `event_infos`를 기점으로 모든 연결 테이블을 전수 탐색. 자식 테이블의 **모든 FK 컬럼** 식별 → 2차/3차 FK 체인까지 추적. 각 FK가 어느 파일·어느 컬럼을 가리키는지 명시하고 **샘플 레코드로 end-to-end 참조 흐름** 실증. | event_infos → 자식 8개 → quests/items/modes/cookies/costumes 등 2차 FK → 3차까지 |

**A10 산출물 (필수)**:
- **연결 그래프 (ASCII/Markdown 표)**: 루트 `event_infos` → 각 브랜치별 테이블·컬럼 트리
- **샘플 체인 5건 이상**: 특정 `^id` 하나를 골라 excel 간 참조를 단말 노드(보상 아이템 이름 등)까지 전부 추적한 사례
- **깨진 링크 리스트**: FK 값이 참조 대상 테이블에 없는 고아 레코드
- **고아 자식 레코드**: 자식 테이블에 있지만 `event_infos`에서 참조 안 되는 `ref_event_id` (운영 사전준비 / 레거시)

### 산출물 (Deliverables)
1. **교차 매트릭스 (표)**: 축별 PASS/WARN/FAIL 표시 + 건수
2. **이슈 로그**: FAIL·WARN 항목마다 증거 (excel 행 / Notion 인용 / 불일치 정도)
3. **권고사항**: 운영/기획 팀에 전달할 조치 리스트 (우선순위 포함)

### 스코프 & 비스코프
- **In**: Notion 가이드 + DB + 각 개별 기획서 페이지 ↔ `event_infos.xlsx` + 8개 `*_events.xlsx` + `quests.xlsx` (참조만)
- **Out**: `items.xlsx`·`modes.xlsx` 등 2차/3차 FK 상세는 샘플만, 전수검사 아님
- **Out**: protobuf 바이너리 구조 검증 (별도 작업)
- **Out**: 밸런스(보상값) 평가

---

## 섹션 D. 에이전트 구성 (확정)

사용자 결정:
- 기존 재활용 3개 + **전용 신규 1개 추가**
- Notion 전체 순회 (8~10 페이지)
- 리포트 별도 파일 저장
- **protobuf 전체 검증 포함** → Generator-C 1개 추가 필요

### 하네스 구조: Planner → Generator ×3 → Critic → Consolidator(신규)

| 역할 | 에이전트 | 재활용/신규 | 담당 축 | 주 도구 |
|---|---|---|---|---|
| **Planner** | 본인 (오케스트레이터) | - | iteration 계약 확정, 루브릭 | - |
| **Generator-A (Excel)** | `qa` | 재활용 | A1, A2, A3, A7, A8, **A10** | `manager.exe textconv`, Read, Grep, Glob |
| **Generator-B (Notion)** | `content-designer` | 재활용 | A4, A5, A6 | `notion-fetch`, `notion-query-data-sources` |
| **Generator-C (protobuf)** | `explorer` | 재활용 | A9 (신규축: protobuf oneof 정합) | Glob, Grep, Read on `protobuf/`·`manager/` |
| **Critic** | `content-evaluator` | 재활용 | 전 축 회의적 재검토 | Read |
| **Consolidator** | **`cross-reference-auditor`** | **신규** | 3자 보고서 + Critic 피드백 통합 → 매트릭스·이슈로그·권고사항 | Read, Write |

### 신규 에이전트 스펙: `cross-reference-auditor`

```yaml
name: cross-reference-auditor
description: |
  3자 교차 검증 컨솔리데이터. 서로 다른 소스(Excel 데이터·Notion 기획서·protobuf 정의)의
  추출 보고서를 입력받아, 축별 PASS/WARN/FAIL 매트릭스로 통합하고 증거·반례·권고사항을
  생성한다. Critic 피드백 반영 후 최종 리포트 작성.
tools: Read, Grep, Glob, Write
model: sonnet
role: |
  - Generator-A/B/C의 중간 보고서와 Critic 피드백을 입력으로 받는다
  - 사전 정의된 8~9개 분석 축별로 3자 소스를 대조, PASS/WARN/FAIL 판정
  - 불일치 항목마다 (축, 심각도, 증거3종, 근거 인용, 권고) 형식으로 이슈 로그 생성
  - 최종 마크다운 리포트 작성 (표 중심, 서술 최소)
constraints:
  - 새로운 기획을 제안하지 않는다 (검증만)
  - 증거 없는 주관 판단 금지 — 모든 FAIL은 원문 인용 필수
  - 양립 가능한 해석이 있으면 WARN으로 격상, FAIL 남발 금지
  - 최종 리포트는 표·리스트 중심, 700토큰 이하 요약 선두 배치
```

**파일 경로**: `C:\Users\Devsisters\.claude\agents\cross-reference-auditor.md` (공통 에이전트로 등록)

### 추가된 분석 축 (A9, A10)

| 축 | 질문 | 소스 | 담당 |
|---|---|---|---|
| **A9. protobuf 정합** | `.proto` 또는 datasheet 내부 정의의 `EventInfo.oneof` 필드가 `event_infos.event/%key` 8종과 1:1 매칭되는가? 자식 메시지의 `ref_event_id` 필드명이 실제 FK 컬럼과 일치? | `protobuf/` 디렉토리 + `manager/src/` 소스 | Generator-C |
| **A10. 실제 연결 구조 (심층)** | excel 파일 간 실 FK 흐름 전수 추적 + 샘플 체인 + 고아/깨진 링크 | `excel/*.xlsx` 전체 | Generator-A |

### Generator-A 프롬프트 보강 (A10 수행 지시)

```
# A10 필수 출력
1. 연결 그래프 (테이블 단위 트리): event_infos를 루트로, 8개 자식 테이블 → 각 2차 FK (quests/items/modes/cookies/costumes/...) → 필요시 3차까지
   - 각 엣지에 (출발 컬럼, 도착 테이블, 도착 컬럼) 명시
2. end-to-end 샘플 체인 5건 (각 이벤트 타입 1건씩 우선)
   - 예: event_infos.^id=1 → attendance_events.ref_event_id=1000 → 보상 item_id=X → items.^id=X 의 name
3. 깨진 링크 리스트: event_infos.%param1 값이 자식 테이블에 없는 경우 + 자식의 FK가 2차 테이블에 없는 경우
4. 고아 자식 레코드: 자식 테이블에 있지만 어느 event_infos 행에서도 %param1로 참조 안 하는 ref_event_id

# 탐색 방법
- `./manager/manager.exe textconv --excel ./excel/<파일>.xlsx`로 각 테이블 전문 추출
- 헤더에 `%key`, `%param1`, `^id`, `foreign_key`, `ref_*_id` 등 FK 표식 grep
- 2차 FK 후보: quests, items, modes, cookies, costumes, skill_*, buff_cards (각 자식 테이블의 컬럼 패턴으로 판단)
```

### 실행 순서 (하네스 계약)

```
[T0] Planner (본인)
     ├ 각 Generator에게 출력 스키마 고정: { axis, source_evidence, raw_excerpt, interpretation }
     └ 병렬 호출 시 공통 타임스탬프·식별자 부여

[T1] 병렬 실행
     ├ Generator-A (qa): excel 8+1개 테이블 × 축 A1·A2·A3·A7·A8
     ├ Generator-B (content-designer): Notion 8~10 페이지 × 축 A4·A5·A6
     └ Generator-C (explorer): protobuf/ + manager/ × 축 A9

[T2] Critic (content-evaluator)
     ├ 3개 보고서 입력
     ├ 회의적 재검토: "이 PASS가 진짜 PASS인가? 반례는?"
     └ 이슈 정제 + 누락 축 지적

[T3] Consolidator (cross-reference-auditor)
     ├ 3 보고서 + Critic 피드백 통합
     ├ 최종 매트릭스 (10축: A1~A10 × PASS/WARN/FAIL + 건수)
     ├ 이슈 로그 (각 이슈: 축·심각도·증거3종·권고)
     ├ **연결 그래프 (A10 산출물) 포함**
     └ 파일 저장:
         - D:\claude_make\docs\event\event_infos_crosscheck_2026-04-21.md (메인)
         - 이 plan 파일 섹션 F에 요약 append
```

### 산출물 저장 (사용자 확정)
- **메인 리포트**: `D:\claude_make\docs\event\event_infos_crosscheck_2026-04-21.md`
- **plan 파일**: `D:\claude_make\docs\event\event-info-quiet-willow.md` (섹션 F에 요약·링크 append)
- 중간 보고서 3종·Critic 피드백: 세션 메모리 (파일 저장 안 함)

---

## 섹션 E. Exit Plan Mode 후 실행 단계

이 plan 승인 후 수행할 변경·도구 실행:

1. **파일 생성** (1건)
   - `C:\Users\Devsisters\.claude\agents\cross-reference-auditor.md` — 신규 에이전트 정의

2. **병렬 에이전트 호출** (3건 동시)
   - `qa` / `content-designer` / `explorer` → 각각 iteration 계약 프롬프트 주입

3. **순차 에이전트 호출** (2건)
   - `content-evaluator` (Critic)
   - `cross-reference-auditor` (신규, Consolidator)

4. **파일 저장** (1건)
   - `D:\claude_make\docs\event\event_infos_crosscheck_2026-04-21.md`

5. **plan 파일 섹션 F append** (1건)

필요 권한:
- Bash (`manager.exe textconv ...`)
- Read / Glob / Grep / Write (에이전트 정의 + 최종 리포트)
- notion-fetch / notion-query-data-sources (이미 로드됨)

---

## 섹션 F. 최종 교차 매트릭스 (하네스 실행 결과 · 2026-04-21)

### 한 줄 결론
Excel 측 FK 무결성은 거의 건전(78/78 PASS)이나, **Notion 가이드-Excel 간 컬럼명 드리프트 · PVE 잔존 · 운세 미연결 · proto 원문 부재**가 겹쳐 "구현은 됐지만 문서·스키마 일관성이 뒤처진" 상태.

### 판정 집계
| 판정 | 건수 | 해당 축 |
|---|---|---|
| PASS | 6 | A1a(파일 존재), A2(start/end 이관), A3-1(1차 FK), A5-a(개발 완료 실존), A7(Block_ 컨벤션), A10-core(연결 그래프) |
| WARN | 8 | A1b(daily_fortune·pve 미연결), A3-2(2차 FK 보류), A3-3(^key=2010 H4 pending), A4(컬럼명 드리프트), A5-b(운세 "미정"), A8b(만료 epoch), A10-drift, daily_fortune 독립 |
| FAIL | 1 | A6 PVE 4중 모순 |
| NOT_EVALUABLE | 1 | A9 `.proto` 원문 외부 저장소 |
| INFO | 2 | daily_fortune 이중 id, n_day vs nday 표기 |

### 즉시 조치 Top 3
1. **A6 FAIL — PVE 잔존 데이터 정리**: `pve_events.xlsx` 25행 + `pve_events.pb` 64B가 event_infos 미참조 상태로 만료 epoch(2025-08~11) 유지. 삭제 OR "스펙아웃 → 보류/재개" 상태 재선언.
2. **A1b/A10 WARN — daily_fortune·pve 진입 경로 문서화**: event_infos 경유 없이 독립 UI 진입인지 or 연결 누락인지 Notion 가이드에 명시. 클라이언트 코드의 로드 지점 추적으로 증거 확정.
3. **A4 WARN — Notion event_infos 기획서 컬럼명 동기화**: Notion 표기 `Id/MainTabOrder/EventJson/EventJsonGroupId/...` vs Excel `^id/tab_order/event/%key/event/%param1/event_path`. 25.08.11 스키마 변경 이후 Notion 기획서 업데이트 필요.

### 주요 산출물
- **메인 리포트**: [event_infos_crosscheck_2026-04-21.md](./event_infos_crosscheck_2026-04-21.md)
  - 8개 섹션: 요약 · 17개 세부축 매트릭스 · 이슈 로그 11건 · A10 연결 그래프 · e2e 샘플 체인 5건 · 권고사항(즉시/단기/장기) · 향후 작업 · 부록(Notion↔Excel 매핑, Critic 결정 로그, 하네스 메타데이터)
- **신규 에이전트**: `C:\Users\Devsisters\.claude\agents\cross-reference-auditor.md` (다음 세션부터 호출 가능)

### 하네스 실행 메모
- Generator 3종(qa, content-designer, explorer) 병렬 실행 → Critic(content-evaluator) 회의적 재검토 → Consolidator 수동 수행 (`cross-reference-auditor`는 현 세션 로드 불가로 오케스트레이터가 직접 통합)
- Critic 피드백으로 축 세분화(A1→A1a/A1b, A3→A3-1/A3-2/A3-3, A5→A5-a/A5-b, A8→A8a/A8b, A10→core/drift/독립), A9 NOT_EVALUABLE 신설, A6 FAIL 격상, ^key=2 PASS 격하
- 미실행 축 없음, 10축 전부 커버

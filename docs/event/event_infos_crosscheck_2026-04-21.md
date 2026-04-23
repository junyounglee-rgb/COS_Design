# event_infos × 이벤트 기획서 × protobuf 교차 분석 리포트

**생성일**: 2026-04-21
**범위**: `D:\COS_Project\cos-data\excel\event_infos.xlsx` + 8개 `*_events.xlsx` + `quests.xlsx` (참조) ↔ Notion 미션/이벤트 기획서(가이드 + DB + 10 하위 페이지) ↔ `D:\COS_Project\cos-data\protobuf\*.pb`
**하네스**: Planner → Generator-A(qa) ‖ Generator-B(content-designer) ‖ Generator-C(explorer) → Critic(content-evaluator) → Consolidator
**플랜**: `D:\claude_make\docs\event\event-info-quiet-willow.md`

---

## 1. 요약

### 한 줄 결론
Excel 측 데이터 무결성은 거의 건전(78행 FK 무결성 100%)하나, Notion 가이드-Excel 간 컬럼명 체계 드리프트·PVE 잔존·운세 미연결·proto 원문 부재가 겹쳐 **"구현은 됐지만 문서·스키마 일관성이 뒤처져 있는" 상태**.

### 판정 건수
| 판정 | 건수 | 비고 |
|---|---|---|
| PASS | 6 | A1a, A2, A3-1, A5-a, A7, A10-core |
| WARN | 8 | A1b, A3-2, A3-3(2010), A4, A5-b, A8b, A10-drift, daily_fortune 독립 |
| FAIL | 1 | A6 PVE 4중 모순 |
| NOT_EVALUABLE | 1 | A9 proto 원문 부재 |
| INFO | 2 | 명명 드리프트 2건 |

### 즉시 조치 Top 3
1. **A6 FAIL — PVE 잔존 데이터 정리**: `pve_events.xlsx` 25행 + `pve_events.pb` 64B가 event_infos 미참조 상태로 만료 epoch(2025-08~11) 유지. 삭제 또는 "스펙아웃 → 보류/재개" 상태 재선언 중 택1.
2. **A1b/A10 WARN — daily_fortune·pve 진입 경로 문서화**: event_infos 경유 없이 독립 UI 진입인지 or 연결 누락인지 Notion 가이드에 명시. 클라이언트 코드의 로드 지점 추적으로 증거 확정.
3. **A4 WARN — Notion event_infos 기획서 컬럼명 동기화**: Notion은 `Id/MainTabOrder/EventJson/EventJsonGroupId/TagImage/Ref_TagStringId` 표기, Excel은 `^id/tab_order/event/%key/event/%param1/event_path` 표기. 25.08.11 스키마 변경 이후 Notion 기획서 표기 업데이트 필요.

---

## 2. 축별 매트릭스

| 축 | 내용 | 판정 | 증거 건수 | 핵심 이슈 |
|---|---|---|---|---|
| **A1a** | 파일 존재성 | PASS | 8/8 | 기대 8개 `*_events.xlsx` + `event_infos.xlsx` 전부 존재 |
| **A1b** | event_infos 연결 존재성 | WARN | 6/8 | daily_fortune_event·pve_event variant는 정의만 있고 event_infos 참조 0 |
| **A2** | 스키마 정합 (start/end 이관) | PASS | 8/8 | 25.08.11 Notion 규칙대로 자식 테이블에 start_timestamp/end_timestamp 전부 보유 |
| **A3-1** | FK 무결성 (1차, 전수) | PASS | 78/78 | event_infos.event/%param1 → 자식 ^key 깨진 링크 0건 |
| **A3-2** | FK 무결성 (2차, 샘플) | WARN | 1 (보류 권고) | pve_events.areas.missions.ref_mode_id=1이 modes.xlsx ^key 목록에 없음 — placeholder 가능성 미확인 |
| **A3-3** | 고아 자식 레코드 | WARN (2건) + INFO (2건) | 2+2 | step_mission ^key=2는 크로스 프로모션 예약(PASS 격하), ^key=2010은 H4 pending(WARN 유지), daily_fortune·pve ^key=1은 A10에 귀속 |
| **A4** | 기획-구현 컬럼명/규칙 정합 | WARN | 1 | Notion event_infos 기획서의 컬럼명(`Id/EventJson/...`)이 Excel 표기(`^id/event/%key/...`)와 표기체계 상이. 25.08.11 이후 Notion 갱신 지연 |
| **A5-a** | 진행상태="개발 완료" vs Excel 존재 | PASS | 6/6 | event_infos·step_mission·nday_mission·invitation·vault_mission·크로스 프로모션 전부 Excel 데이터 있음 |
| **A5-b** | 진행상태="미정" vs 기획 완결 (운세) | WARN | 1 | Notion DB 태그 "미정"이나 페이지는 2025-10-09까지 완결 업데이트. daily_fortune_events.xlsx 1행만 존재 + event_infos 미연결 |
| **A6** | 스펙아웃 처리 (PVE) | **FAIL** | 4 | ①가이드 "스펙아웃" ②pve_events.xlsx 25행 존재 ③event_infos 참조 0 ④epoch 2025-08~11 만료 — 4중 모순 |
| **A7** | 명명 컨벤션 `Block_` | PASS | 78/78 (25 unique) | event_path 전건 Block_ 접두 준수 |
| **A8a** | 시간 컬럼 구문 존재 | PASS | 8/8 | 모든 자식 테이블에 start/end_timestamp 채워짐, 빈 값 0건 |
| **A8b** | 시간 의미 유효성 | WARN | 2 | pve_events·daily_fortune_events의 epoch(1756684800=2025-08-31 ~ 1764460800=2025-11-30)가 현재(2026-04-21) 기준 이미 만료 |
| **A9** | protobuf oneof 정합 | **NOT_EVALUABLE** | - | `.proto` 원문이 본 저장소 부재. 실제 정의는 외부 `github.com/devsisters/cos-data-manager/tools/` 소재. `.pb`는 datasheet 독자 포맷으로 decode 불가 추정. 원문 확보 전 판정 불가. |
| **A10-core** | 연결 그래프 (실 FK 흐름) | PASS | 6 branch | attendance/step_mission/n_day_mission/vault_mission/invitation/quest_gacha 6 branch end-to-end 추적 완료 |
| **A10-drift** | variant 명명 드리프트 | INFO | 2 | (1) `n_day_mission_event` (Excel key) vs `nday_mission_events` (파일명) 언더스코어 위치 차이 (2) daily_fortune_events만 `^key` + `event_id` 이중 id 컬럼 |
| **A10-daily_fortune/pve 독립** | 독립 노출 경로? 증거 부족 | WARN | 2 (증거 보강 필요) | 클라 진입점 문서·코드 미확인 상태에서 "독립" 단정 불가 |

---

## 3. 이슈 로그 (FAIL/WARN 전건)

| # | 축 | 심각도 | 증거 (Excel) | 증거 (Notion) | 증거 (proto) | 권고 |
|---|---|---|---|---|---|---|
| 1 | A6 | **FAIL** | `pve_events.xlsx` 25행 + `events.^key=1 start=1756684800 end=1764460800 event_ticket_config/ref_item_id=8004` | 가이드 매핑 테이블에 "스펙아웃" 표기; 페이지(225de3da...eb4a)는 월드맵·4테이블 상세 기획 잔존 | `pve_events.pb 64B`(거의 비어있음) | 삭제 OR "스펙아웃 해제/보류" 상태 재선언. DB의 "스펙아웃" 태그 의미 정의도 통일 필요. |
| 2 | A1b, A10 | WARN | event_infos의 event/%key 78건 중 `daily_fortune_event:*` 0건 | Notion DB 태그 "미정". 그러나 운세 이벤트 페이지(262de3da...03be)는 완결 기획 (4테이블 구조, 3종 운세, 쿠키 풀 추첨 규칙 명시) | `daily_fortune_events.pb 304B` 존재 | (a) daily_fortune_events를 event_infos에 등록해 탭 경유 노출 OR (b) Notion 가이드에 "독립 진입점" 명시. 클라 코드의 `daily_fortune_events` 로드 지점 추적 선행. |
| 3 | A1b, A10 | WARN | event_infos의 `pve_event:*` 0건 + `pve_events.xlsx` 25행 잔존 | 가이드 "스펙아웃" + 상세 기획 4테이블 잔존 | `pve_events.pb 64B` | 이슈 #1과 병합 처리 (A6 FAIL 해결 시 자동 해소). |
| 4 | A3-3 | WARN | `step_mission_events.^key=2010 start=$$H4_START end=$$H4_END normal_quest_ids=[]{2011,2012,2013,2014,2015}` | - | - | 라벨링을 "고아"에서 "pending (H4 시즌 연동 대기)"로 변경. Excel에 pending row 표기 컨벤션(주석 `#name` 필드 활용) 도입 권고. |
| 5 | A4 | WARN | event_infos 실제 컬럼: `^id, name, tab_order, tab_order_type, event_path, event/%key, event/%param1, $filter` | Notion 기획서 표기: `Id, MainTabOrder, EventJson, EventJsonGroupId, TagImage, Ref_TagStringId, Ref_BtnStringId, Ref_DescriptionStringId, StartDay(삭제), EndDay(삭제)` | - | Notion 공통 이벤트 기획서(211de3da...c053) 컬럼 테이블을 Excel 실 헤더로 업데이트. 최소 `event/%key`, `event/%param1`, `tab_order_type`, `$filter` 4개 반영. |
| 6 | A5-b | WARN | `daily_fortune_events.xlsx` 1행(end=1764460800, 2025-11-30 만료) | DB 태그 "미정"; 페이지 히스토리 2025-09-08 초안 → 2025-09-15 1차 완료 → 2025-10-09 아이콘 업데이트 | - | Notion DB 태그를 "구현 보류" 또는 "기획서 작성 완료-구현 대기"로 조정. "미정" 의미 애매. |
| 7 | A8b | WARN | `pve_events.start=1756684800(2025-08-31)`, `daily_fortune_events.end=1764460800(2025-11-30)` — 현재 2026-04-21 기준 만료 | - | - | 만료 데이터 아카이빙/삭제 정책 수립. 라이브 운영에 영향 없는지 확인. Excel에 "종료 이벤트 보존 기간" 컨벤션 필요. |
| 8 | A3-2 | WARN (보류) | `pve_events.areas.missions.ref_mode_id=1`; `modes.xlsx` 최소 ^key=100 | - | - | Consolidator 판단: **판정 유보**. modes.xlsx의 ^key=0/1/2가 null placeholder인지 예약/기본값인지 확인 선행. pve가 FAIL 처리되면(#1) 자동 해소 가능. |
| 9 | A10-drift (daily_fortune id 이중) | INFO | `daily_fortune_events.xlsx`만 `^key=1` + `event_id=1` 이중 컬럼 | - | - | 의도된 이중 인덱싱(외부 연결키 vs 내부 PK)인지 확인. 의도된 것이면 주석화, 아니면 컬럼 정리. |
| 10 | A10-drift (n_day vs nday) | INFO | Excel key: `n_day_mission_event` (언더스코어 3개), 파일명: `nday_mission_events` (언더스코어 2개) | - | `nday_mission_events.pb` (파일명 쪽 채택) | datasheet 정규화 규칙 확인. 실제 로드 오류 없으면 INFO 유지, 장기적으로 표기 통일. |
| 11 | A9 | NOT_EVALUABLE | - | - | `.proto` 부재 (외부 저장소 `cos-data-manager/tools/`); `.pb` 130개 독자 포맷 | `github.com/devsisters/cos-data-manager` 저장소 조회 후 `EventInfo` 메시지 oneof 필드 확인 별도 작업. |

---

## 4. A10 연결 그래프

```
event_infos (^id, event_path, event/%key, event/%param1)
│
├── [event/%key=attendance_event] → attendance_events (^key) ─ 5건 infos 참조
│   ├── events (start/end_timestamp, type, consecutive_attendance_enabled)
│   │   └── consecutive_reward_items/id → items (^key)
│   └── events.attendance_days (day, reward_grade_type, item/id)
│       └── item/id → items (^key)  [샘플 OK]
│
├── [event/%key=n_day_mission_event] → nday_mission_events (^key) ─ 15건 참조
│   ├── events (mission_active_days)
│   └── events.day (day, description, quest_ids, finish_quest_id)
│       ├── quest_ids[] → quests (^key)  [샘플 OK]
│       └── finish_quest_id → quests (^key)
│
├── [event/%key=step_mission_event] → step_mission_events (^key) ─ 46건 참조
│   └── events (normal_quest_ids, special_quest_ids, link_url)
│       ├── normal_quest_ids[] → quests (^key)  [샘플 OK]
│       └── special_quest_ids[] → quests (^key)
│       ※ ^key=2  ── 크로스 프로모션 예약 슬롯 (PASS)
│       ※ ^key=2010 ── H4 시즌 연동 pending (WARN)
│
├── [event/%key=vault_mission_event] → vault_mission_events (^key) ─ 8건 참조
│   ├── events (quest_ids, magnifier_item, key_item)
│   │   ├── quest_ids[] → quests (^key)  [샘플 OK]
│   │   ├── magnifier_item/id → items (^key)  [샘플 OK]
│   │   └── key_item/id → items (^key)  [샘플 OK]
│   └── events.candidates (id, weight, reward/id, reward/qty)
│       └── reward/id → items (^key)
│
├── [event/%key=invitation_event] → invitation_events (^key) ─ 2건 참조
│   └── events (point_item_id, ref_reward_quest_ids, ref_inviter_quest_ids, ref_invitee_quest_ids)
│       ├── point_item_id → items (^key)  [샘플 OK]
│       └── ref_*_quest_ids[] → quests (^key)  [샘플 OK]
│
├── [event/%key=quest_gacha_event] → quest_gacha_events (^key) ─ 2건 참조
│   └── events (special/daily/repeat/milestone_quest_ids, price, reward, multiplier)
│       ├── price/id → items (^key)  [샘플 OK]
│       ├── reward/id → items (^key)  [샘플 OK]
│       └── *_quest_ids[] → quests (^key)  [샘플 OK]
│
├── [참조 없음, WARN] daily_fortune_events ─ event_infos 참조 0건
│   ├── events (^key + event_id 이중 id, event_name)
│   ├── fortune_buffs (ref_buff_item_id → items)
│   ├── fortune_messages (message_content, message_type)
│   └── root
│   (운세 이벤트: Notion 기획 완결, DB "미정", Excel 1행 만료)
│
└── [참조 없음, FAIL] pve_events ─ event_infos 참조 0건 + 스펙아웃 표기 + 만료
    ├── events (event_ticket_config: ref_item_id → items)
    ├── events.areas (start_timestamp)
    └── areas.missions (ref_mode_id, ref_cookie_id, ref_costume_ids, ref_power_sand_ids)
        ├── ref_mode_id=1 → modes (^key)  ※ MISSING (A6 FAIL에 귀속)
        ├── ref_cookie_id=110001 → cookies (^key)  [OK]
        └── ref_costume_ids[]·ref_power_sand_ids[] → 빈 배열
```

---

## 5. end-to-end 샘플 체인 5건

### 체인 1 — 출석 (attendance)
```
event_infos.^id=1 name="웰컴 출석 이벤트!" event_path=Block_SpecialAttendanceEvent
  event/%key=attendance_event:ref_event_id  event/%param1=1000
  → attendance_events.^key=1000 desc="런칭을 기념하여, 매일 무료 보상을 드려요."
     start_timestamp=1769871600  end_timestamp=$$H2_END
     consecutive_attendance_enabled=0
     → events.attendance_days (day=1, item/id=1 → items.^key=1 "코인", qty=1)
```

### 체인 2 — 데일리 미션 (n_day_mission)
```
event_infos.^id=3 "웰컴 데일리 미션!" event_path=Block_DailyMissionEvent
  event/%key=n_day_mission_event:ref_event_id  event/%param1=1
  → nday_mission_events.^key=1 desc="데일리 미션"
     start=$$TIMESTAMP_260326_12PM  end=$$INDEFINITE_TIMESTAMP
     mission_active_days=28
     → events.day (day=1, quest_ids=[]{101..109}, finish_quest_id=100 → quests.^key)
```

### 체인 3 — 금고 미션 (vault_mission)
```
event_infos.^id=4001 "금고 열기 이벤트" event_path=Block_VaultMission
  event/%key=vault_mission_event:ref_event_id  event/%param1=4001
  → vault_mission_events.^key=4001
     quest_ids=[]{40001..40006}
     magnifier_item/id=8500 → items.^key=8500 "돋보기"
     key_item/id=8600 → items.^key=8600 "열쇠"
     → events.candidates (id=1, weight=42000, reward/id=4100001, qty=1)
```

### 체인 4 — 친구 초대 (invitation)
```
event_infos.^id=5 "친구 초대 이벤트" event_path=Block_InvitationEvent
  event/%key=invitation_event:ref_event_id  event/%param1=1
  → invitation_events.^key=1
     start=$$TIMESTAMP_260326_12PM
     end=$$TIMESTAMP_MAINTENANCE_260409_06AM
     point_item_id=8002 → items.^key=8002 "우정 포인트"
     ref_reward_quest_ids=[]{30011..30015} → quests
     ref_inviter_quest_ids=[]{30001..30005} → quests
     ref_invitee_quest_ids=[]{30006..30008} → quests
```

### 체인 5 — 꽝 없는 럭키 뽑기 (quest_gacha)
```
event_infos.^id=30000 "꽝 없는 럭키 뽑기" event_path=Block_QuestGachaEvent
  event/%key=quest_gacha_event:ref_event_id  event/%param1=1
  → quest_gacha_events.^key=1
     start=$$ISTANBUL_1_START  end=$$ISTANBUL_4_END
     special_quest_ids=[]{50001,50002}
     daily_quest_ids=[]{50003..50007}
     repeat_quest_ids=[]{50008..50010}
     milestone_quest_ids=[]{50011..50014}
     price/id=8003 → items.^key=8003 "럭키 코인"
     reward/id=5100001 → items.^key=5100001
```

---

## 6. 권고사항 (우선순위)

### 즉시 (blocker / 운영 리스크)
1. **PVE 정리 결정** (A6 FAIL): 스펙아웃 확정이면 `pve_events.xlsx`·`pve_events.pb`·Notion 페이지 일괄 삭제 또는 아카이브 디렉토리 이동. 재개 고려 중이면 Notion 태그 "보류"로 변경.
2. **daily_fortune / pve 독립 진입 문서화** (A1b, A10): 가이드에 "event_infos 경유 필수 8종 / 독립 진입 N종" 구분 추가. 현 가이드는 두 경로 구분 없음.

### 단기 (2주 내)
3. **Notion event_infos 기획서 컬럼명 동기화** (A4): 25.08.11 스키마 변경 이후 갱신 누락. Excel 실 헤더로 교체.
4. **운세 이벤트 DB 태그 재정의** (A5-b): "미정" → "구현 보류" 또는 "개발 대기" 명확화.
5. **만료 이벤트 보존 정책 수립** (A8b): 라이브 서비스 영향 범위와 아카이빙 기준 문서화.
6. **Excel "pending row" 컨벤션 도입** (A3-3): 고아로 오인되지 않도록 `#name` 또는 별도 컬럼에 예약/대기 상태 표기.

### 장기
7. **proto 원문 접근 워크플로우 수립** (A9): cos-data-manager 저장소 동기화를 본 저장소 검증 프로세스에 편입. oneof 정합 자동 검증 스크립트 작성.
8. **명명 드리프트 정리** (A10-drift): `n_day` ↔ `nday` 표기 통일, `daily_fortune` 이중 id 컬럼 의도 확정.
9. **FK 자동 검증 파이프라인**: 현재 수동 textconv로 한 A3 검증을 CI에 편입 (깨진 FK 커밋 차단).

---

## 7. 추가 검토 필요 (future work)

Critic이 제안한 누락 축 5개:

| 축 | 제안 내용 | 권장 후속 |
|---|---|---|
| **A11 lifecycle** | 만료·아카이빙 정책, 과거 epoch row 보존 기간 | 운영팀과 정책 수립 후 리비전 |
| **A12 다국어 리소스** | `event_path` 외 스트링 리소스(번역)가 translations/에 전부 있는지 | `gen-string-map` 스킬로 후속 분석 |
| **A13 서버 데이터 분기** | `ServerMapData/`, `ServerPatternData/`에 event 관련 데이터 존재 여부 | `explorer`로 별도 스윕 |
| **A14 이벤트 상호 의존성** | step_mission → attendance 완료 조건 체이닝 등 의존 그래프 | quests.xlsx의 condition 참조 전수 분석 |
| **A15 25.08.11 이전 잔존 레거시** | StartDay/EndDay 같은 구 컬럼이 event_infos에 남아있지 않은지 | 컬럼 diff 간단 스크립트 |

protobuf 외부 저장소 조사 (A9 NOT_EVALUABLE 해소):
- `github.com/devsisters/cos-data-manager` clone → `tools/datasheet/` 하위 `.proto` 확인
- 또는 `cos-client`의 proto-generated C# 클래스, `cos-battle-server`/`cos-town-server`의 Go 구조체 역추적

---

## 8. 부록

### 8-1. Notion ↔ Excel 컬럼명 매핑 (event_infos)

| Notion 표기 | Excel 실 헤더 | 상태 |
|---|---|---|
| Id | ^id | 동일 의미 |
| #Description | (Excel에 없음, `$filter` 필드로 대체?) | 불일치 |
| MainTabOrder | tab_order | 동일 의미 |
| Ref_BtnStringId | (Excel에 없음) | Notion 기술만, Excel 미반영 |
| EventJson | event/%key | variant 표기 체계만 다름 |
| EventJsonGroupId | event/%param1 | variant param 표기 |
| TagImage | (Excel에 없음) | Notion 기술만 (CBT 제외 표기) |
| Ref_TagStringId | (Excel에 없음) | Notion 기술만 |
| Ref_DescriptionStringId | (Excel에 없음) | Notion 기술만 |
| ~~StartDay~~ | (25.08.11 제거됨) | Excel 규칙 준수 |
| ~~EndDay~~ | (25.08.11 제거됨) | Excel 규칙 준수 |
| (Notion 미기술) | event_path | Excel만 존재 (Block_* UI 프리팹) |
| (Notion 미기술) | tab_order_type | Excel만 존재 (SHOW/SHOW_CLEAR_BOTTOM/HIDE_CLEAR) |
| (Notion 미기술) | $filter | Excel만 존재 ($$DEV/$$ISTANBUL_3) |

### 8-2. Critic 권고 반영 의사결정 로그

| Critic 권고 | Consolidator 결정 | 사유 |
|---|---|---|
| A1 2층위 분리 | **수용** | A1a/A1b로 분할. "파일 존재"와 "연결 존재"는 별개 의미 |
| A3 2차 FK 판정 보류 | **수용 (WARN 유지 + 보류 표기)** | A6 FAIL에 귀속되면 자동 해소되므로 부담 적음 |
| A3 고아 ^key=2 PASS 격하 | **수용** | Notion 크로스 프로모션 증거로 예약 슬롯 확정 |
| A3 고아 ^key=2010 pending 라벨링 | **수용** | $$H4_END 변수 기반 pending은 "고아"와 구분 필요 |
| A6 PVE FAIL 격상 | **수용** | 4중 모순 신호 명확 |
| A8 a/b 분할 | **수용** | 구문 체크와 의미 체크 분리가 진단적으로 유용 |
| A9 NOT_EVALUABLE | **수용** | 원문 부재 상태에서 WARN/PASS는 모순 |
| A10 daily_fortune 독립 판정 유보 | **수용 (WARN 유지 + 증거 보강 필요 표기)** | 클라 진입점 확인 전 단정 불가 |
| A11~A15 누락 축 추가 | **future work로 분리 수용** | 본 리포트 10축 스코프 유지, 섹션 7에 기재 |

### 8-3. 하네스 실행 메타

| 단계 | 에이전트 | 토큰 | 도구 호출 | 소요 시간 |
|---|---|---|---|---|
| T1 Generator-A | qa | 105,873 | 98 | 52분 |
| T1 Generator-B | content-designer | 95,398 | 19 | 7분 |
| T1 Generator-C | explorer | 80,676 | 45 | 25분 |
| T2 Critic | content-evaluator | 27,353 | 0 | 1분 |
| T3 Consolidator | (cross-reference-auditor 신설 예정, 현 세션 수동 실행) | - | - | - |

---

**원본 Excel**: `D:\COS_Project\cos-data\excel\`
**플랜 문서**: `D:\claude_make\docs\event\event-info-quiet-willow.md`
**신규 에이전트 정의**: `C:\Users\Devsisters\.claude\agents\cross-reference-auditor.md` (차기 세션부터 사용 가능)

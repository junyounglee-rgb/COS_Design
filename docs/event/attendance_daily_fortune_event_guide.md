# 출석·데일리 운세 이벤트 데이터 가이드

**대상**: 데이터 기획자 + QA
**생성일**: 2026-04-21
**근거**: 교차 분석 리포트 [`event_infos_crosscheck_2026-04-21.md`](./event_infos_crosscheck_2026-04-21.md) + `attendance_events.xlsx`·`daily_fortune_events.xlsx` textconv 실측

---

## 1. 개요

### 1.1 두 이벤트 비교

| 항목 | 출석 이벤트 | 데일리 운세 이벤트 |
|---|---|---|
| 자식 테이블 | `attendance_events.xlsx` | `daily_fortune_events.xlsx` |
| variant key | `attendance_event:ref_event_id` | `daily_fortune_event:ref_event_id` |
| 라이브 상태 | ✅ 5건 운영 (PASS) | ⚠ event_infos 미연결 (WARN) |
| 시트 수 | 2 | 4 |
| 주요 리소스 | 일별 보상 아이템 | 버프 아이템 + 메시지 + 쿠키 추첨 풀 |
| 유저 경험 | 매일 로그인 → 일자별 보상 | 매일 입장 → 3종 운세 중 1종 + 쿠키 추첨 |

### 1.2 공통 진입 구조 (variant FK)

```
event_infos.xlsx (^id, tab_order, event_path, event/%key, event/%param1)
   │
   │  event/%key = "<자식테이블>:ref_event_id"
   │  event/%param1 = <자식 ^key 값>
   ▼
<자식>_events.xlsx (^key, ...)
```

---

## 2. 출석 이벤트 (attendance_events)

### 2.1 시트 1 — `events` (기본 정보)

| 컬럼 | 타입 | 의미 | 예시 |
|---|---|---|---|
| `^key` | PK INT | 이벤트 고유 키 | 1000 |
| `description` | TEXT | 이벤트 설명(유저 노출) | "런칭을 기념하여, 매일 무료 보상을 드려요." |
| `start_timestamp` | EPOCH \| VAR | 시작 시각 (epoch 또는 `$$H2_START` 변수) | `1769871600`(2026-01-31) / `$$H3_START` |
| `end_timestamp` | EPOCH \| VAR | 종료 시각 | `$$H2_END` / `$$ISTANBUL_4_END` |
| `type` | ENUM | `TYPE_SEQUENTIAL`(순차) / `TYPE_ELAPSED`(경과일) | `TYPE_SEQUENTIAL` |
| `consecutive_attendance_enabled` | BOOL | 연속 출석 보너스 ON/OFF | `1` / `0` |
| `consecutive_reward_items/id` | FK → `items.^key` | 연속 출석 보너스 아이템 | `1` |
| `consecutive_reward_items/qty` | INT | 연속 보너스 수량 | `500`, `1` |

### 2.2 시트 2 — `events.attendance_days` (일별 보상)

| 컬럼 | 타입 | 의미 | 예시 |
|---|---|---|---|
| `^key` | FK → `events.^key` | 상위 이벤트 연결 | `1000` |
| `day` | INT | 일차 (1부터) | `1~7` |
| `reward_grade_type` | ENUM | `REWARD_GRADE_COMMON` / `REWARD_GRADE_RARE` / `REWARD_GRADE_EPIC` | `REWARD_GRADE_RARE` |
| `item/id` | FK → `items.^key` | 보상 아이템 | `200002021` |
| `item/qty` | INT | 보상 수량 | `1`, `20` |

### 2.3 FK 연결 다이어그램

```
event_infos.event/%param1 ──► attendance_events.events.^key
                               │
                               ├─► consecutive_reward_items/id ──► items.^key
                               │
                               └─► events.attendance_days.^key (내부 FK)
                                    └─► item/id ──► items.^key
```

### 2.4 event_infos 등록 실황 (5건)

| `^id` | `event/%param1` | `event_path` | 비고 |
|---|---|---|---|
| `1` | `1000` | `Block_SpecialAttendanceEvent` | 런칭 기념 |
| `1001` | `1` | `Block_AttendanceEvent` | 상시 출석 슬롯 1 |
| `1002` | `2` | `Block_AttendanceEvent` | 상시 출석 슬롯 2 |
| `1003` | `3` | `Block_AttendanceEvent` | 상시 출석 슬롯 3 |
| `1004` | `4` | `Block_AttendanceEvent` | 상시 출석 슬롯 4 |

전건 `event/%key = attendance_event:ref_event_id`.

### 2.5 모범 예시 — `^key=1000` "런칭 기념" 전문

**events 1행**
```
^key=1000
description="런칭을 기념하여, 매일 무료 보상을 드려요."
start_timestamp=1769871600   # 2026-01-31 15:00 UTC
end_timestamp=$$H2_END
type=TYPE_SEQUENTIAL
consecutive_attendance_enabled=0
consecutive_reward_items/id=1
consecutive_reward_items/qty=1
```

**attendance_days 7행**
| day | reward_grade_type | item/id | item/qty |
|---|---|---|---|
| 1 | REWARD_GRADE_COMMON | 1000130 | 1 |
| 2 | REWARD_GRADE_COMMON | 10511 | 20 |
| 3 | REWARD_GRADE_COMMON | 1000150 | 1 |
| 4 | REWARD_GRADE_RARE | 200002021 | 1 |
| 5 | REWARD_GRADE_COMMON | 13006 | 20 |
| 6 | REWARD_GRADE_COMMON | 20002 | 1 |
| 7 | REWARD_GRADE_RARE | 400002021 | 1 |

### 2.6 운영 포인트

- **시간 표기 선택**
  - 특정 런칭·프로모션 이벤트 → epoch 상수 (예: `1769871600`)
  - 시즌 연동 상시 이벤트 → 변수 (`$$H2_END` / `$$H3_START` / `$$ISTANBUL_4_END`)
- **type 선택 기준**
  - `TYPE_SEQUENTIAL`: 1일차→2일차→... 순차 개봉 (누락 시 대기)
  - `TYPE_ELAPSED`: 이벤트 시작 기준 경과일로 보상 매핑
- **consecutive_attendance_enabled = 1 시**
  - `consecutive_reward_items/id`·`qty` 반드시 유효값
  - 연속 출석 달성 조건은 프리팹(`Block_*`) 측 파라미터로 관리

---

## 3. 데일리 운세 이벤트 (daily_fortune_events)

### 3.1 현재 상태 경고

> ⚠ **본 이벤트는 현재 라이브 미운영 상태**. 활성화 전 §3.5 체크리스트 필수 수행.

| 이슈 | 교차 리포트 참조 |
|---|---|
| event_infos 미연결 (variant FK 0건) | 이슈 #2 |
| `end_timestamp=1764460800`(2025-11-30) 만료 | 이슈 #7 |
| `^key` + `event_id` 이중 id 체계 (유일 예외) | 이슈 #9 |

### 3.2 시트 1 — `events`

| 컬럼 | 타입 | 의미 | 현재 값 |
|---|---|---|---|
| `^key` | PK INT | 내부 고유 키 | `1` |
| `event_id` | SECONDARY INT | event_infos 연결용 후보 id (이중) | `1` |
| `start_timestamp` | EPOCH | 시작 시각 | `1756684800` (2025-09-01) |
| `end_timestamp` | EPOCH | 종료 시각 | `1764460800` (2025-11-30, **만료**) |
| `event_name` | TEXT | 이벤트명 | `"오늘의 운세"` |

### 3.3 시트 2 — `fortune_buffs` (3종 운세 × 버프 아이템)

| `^key` | `message_type` | `ref_buff_item_id` → `items.^key` | 운세 의미 |
|---|---|---|---|
| 1 | `FORTUNE_MESSAGE_TYPE_CHALLENGE` | `220001` | 도전 |
| 2 | `FORTUNE_MESSAGE_TYPE_TRAINING` | `230001` | 단련 |
| 3 | `FORTUNE_MESSAGE_TYPE_WEALTH` | `240001` | 재물 |

### 3.4 시트 3 — `fortune_messages` (운세 문구)

| `^key` | `message_type` | `message_content` 예 |
|---|---|---|
| 1 | `..._CHALLENGE` | "오늘은 도전을 하면 좋아~" |
| 2 | `..._TRAINING` | "오늘은 단련을 하면 좋아~" |
| 3 | `..._WEALTH` | "오늘은 재물운이 좋아~" |

### 3.5 시트 4 — `root` (글로벌 추첨 규칙)

| 컬럼 | 값 | 의미 |
|---|---|---|
| `config/owned_cookie_select_count` | `2` | 플레이어 보유 쿠키 풀에서 선택할 수 |
| `config/all_cookie_select_count` | `1` | 전체 쿠키 풀(미보유 포함)에서 추첨할 수 |

**추첨 공식**: 하루 한 번, **보유 쿠키 중 2개** + **전체 풀 중 1개** = 총 3 후보 쿠키를 유저에게 제시, 그중 1마리 선택 → 선택한 운세 타입의 `ref_buff_item_id` 지급.

### 3.6 FK 연결 다이어그램

```
event_infos.event/%param1 ──► daily_fortune_events.events.event_id  ◆ 미연결 ◆
                               │
                               └─► fortune_buffs.ref_buff_item_id ──► items.^key
```
- `events.^key`와 `events.event_id`가 현재 동일값(`1`)이나 의도 미확인 → §3.7 Step 1
- `fortune_buffs`·`fortune_messages`는 `message_type` enum으로 암묵 조인

### 3.7 활성화(라이브 운영) 체크리스트

| Step | 작업 | 완료 기준 |
|---|---|---|
| 1 | **독립 진입점 여부 확정** — 클라(`cos-client`) 측 `daily_fortune_events` 로드 코드 추적, UI 진입 경로가 event_infos 탭인지 독립 홈 버튼인지 결정 | 기획/개발 합의 결과 문서화 (Notion 운세 페이지에 명시) |
| 2 | **event_infos 등록(경유형인 경우)** — `event_infos.xlsx`에 1행 추가<br>`event/%key=daily_fortune_event:ref_event_id`, `event/%param1=<events.^key>`, `event_path=Block_DailyFortune*`, `tab_order` 확정 | `attendance` 예시(§2.4)와 동일 패턴 적용 |
| 3 | **Notion DB 태그 정리** — "미정" → "구현 완료/운영 대기" 또는 "라이브" | Notion 미션/이벤트 DB 업데이트 |
| 4 | **start/end_timestamp 갱신** — 만료값(2025-11-30) → 실제 라이브 윈도우<br>변수 표기(`$$H4_START` 등) 또는 신규 epoch | textconv로 `start < 현재시각 < end` 검증 |
| 5 | **이중 id 의도 확정** — `^key`와 `event_id` 용도 분리 문서화 or 한쪽 삭제 | 기획 문서에 컬럼 주석 추가 |

---

## 4. event_infos 등록 공통 규칙

| 항목 | 값 / 규칙 | 예시 |
|---|---|---|
| `^id` | INT, 카테고리별 숫자 범위 암묵 분류 | 1~10(기본) / 1001~(상시) / 4001~(금고) / 60010~(게임모드) |
| `name` | 내부용 식별명 | `attendance_event` |
| `tab_order` | INT, 탭 정렬 순서 | `1, 2, 3...` |
| `tab_order_type` | ENUM | `SHOW` / `SHOW_CLEAR_BOTTOM` / `HIDE_CLEAR` |
| `event_path` | TEXT, Unity 프리팹 키 | `Block_AttendanceEvent`, `Block_SpecialAttendanceEvent` |
| `event/%key` | variant key | `attendance_event:ref_event_id`, `daily_fortune_event:ref_event_id` |
| `event/%param1` | FK 값 | 자식 테이블 `^key` |
| `$filter` | 빌드 분기 조건 (선택) | 특정 빌드만 노출 시 사용 |

---

## 5. 자주 하는 실수

| # | 실수 | 증상 | 교차 리포트 |
|---|---|---|---|
| 1 | 만료 epoch 방치 | 종료된 이벤트 데이터가 Excel에 잔존, 클라가 빈 탭 노출 | A8b |
| 2 | Notion-Excel 컬럼명 혼용 | Notion `Id/EventJson/EventJsonGroupId` 표기로 작성하려다 실패 — Excel은 `^id/event/%key/event/%param1` | A4 |
| 3 | 이중 id 오해 | daily_fortune만의 예외 — 다른 테이블에 `event_id` 컬럼 추가 금지 | A10-drift |
| 4 | `event/%param1`과 자식 `^key` 불일치 | `event_infos` 등록 시 `%param1`을 자식 `^key`가 아닌 다른 값으로 입력 → FK 깨짐 | A3 |
| 5 | `Block_*` 누락 | `event_path` 접두 미준수 → 클라 프리팹 로드 실패 | A7 |

---

## 6. QA 체크리스트

### 6.1 등록 전
- [ ] 자식 테이블 `^key`가 실존하며 중복 없음
- [ ] `event/%param1` 값이 자식 `^key`와 일치 (텍스트 아님, 숫자)
- [ ] `event_path`가 `Block_` 접두 준수
- [ ] `items.^key` 등 FK 대상이 실존 (보상 아이템)
- [ ] `$filter` 필요 시 빌드 플래그와 정확 일치
- [ ] `tab_order` 중복 없음

### 6.2 등록 후
- [ ] `manager.exe textconv --excel event_infos.xlsx`로 신규 행 확인
- [ ] 자식 테이블도 동일 방법으로 조회, FK 양방향 일치
- [ ] `start_timestamp < end_timestamp` 수식 검증 (변수일 경우 해석 후)
- [ ] 실기기 또는 에디터에서 `Block_*` 프리팹 로드 성공

### 6.3 라이브 모니터링
- [ ] 주 1회 만료 임박(7일 이내) 이벤트 목록 생성
- [ ] 만료 이벤트는 14일 내 아카이빙(삭제 or `$filter` 무효화)
- [ ] `HIDE_CLEAR` 설정 이벤트 종료 후 진행 상태 저장 여부 점검

---

## 7. 참조

| 문서 | 경로 |
|---|---|
| 교차 분석 리포트 | [`event_infos_crosscheck_2026-04-21.md`](./event_infos_crosscheck_2026-04-21.md) |
| 플랜 문서 | [`event-info-quiet-willow.md`](./event-info-quiet-willow.md) |
| Notion 미션/이벤트 루트 | `https://www.notion.so/devsisters/22bde3da895680e7b0a5e743433b24e5` |
| Notion 데일리 운세 기획 | Notion 페이지 `262de3da...03be` (완결 상태) |
| Excel 조회 도구 | `D:\COS_Project\cos-data\manager\manager.exe textconv --excel <파일>` |
| 원본 Excel | `D:\COS_Project\cos-data\excel\attendance_events.xlsx`, `daily_fortune_events.xlsx`, `event_infos.xlsx`, `items.xlsx` |

# quests.xlsx 로컬룰 심층 분석 — 이벤트 템플릿화 근거 보고서

> 작성일: 2026-04-23
> 저자: 이준영(기획) + Claude (quest-data-qa, system-designer 에이전트 협업)
> 목적: `quest_tool` 을 이벤트 타입별 템플릿 입력 UX 로 확장하기 전, 현 데이터의 로컬룰 전수 분석
> 연관 문서: `quest_event_template_designer_draft.md` (system-designer 작성 7종 템플릿 스펙)

---

## 0. 요약 (TL;DR)

1152행의 quests.xlsx 를 전수 분석하여 **14개 로컬룰 클러스터**를 식별했다.
핵심 클러스터 7개(A–G)는 **이벤트 템플릿 7종**으로 UI 화할 가치가 있고,
나머지 7개(H–N)는 **고급 condition/특수 goal 패턴**으로 템플릿의 옵션 필드로 흡수하거나 fallback(G)로 처리.

**긴급 이슈 2건**
1. **reward_battle_road 스펙 위반** — quest-data-qa 스펙은 HIGHEST 요구, 실데이터 20/20 SUM 사용. 기획 확정 필요.
2. **play_mode_category 파라미터 300** — 스펙에 없는 값 5건 (key 60001–60005). 카테고리 정의 추가 또는 데이터 수정 필요.

**설계 초안 수정 필요 1건**
- system-designer 초안의 **TPL_C reset_type = REPEAT 는 DAILY 의 오기**. 실데이터 10건 parent 전부 `QUEST_RESET_TYPE_DAILY`.

---

## 1. 실데이터 통계 (기준: `D:\COS_Project\cos-data\excel\quests.xlsx`)

| 축 | 분포 |
|---|---|
| 총 행 수 | 1152 (헤더 3행 제외) |
| category | GENERAL 556, TOWN 596, VAULT_MISSION **0** |
| reset_type | NONE 99, DAILY 74, REPEAT 6, 나머지 빈칸 |
| count_type | SUM 1056, HIGHEST 96 |
| $filter | `$$LAUNCH_0` 541, `$$NONE` 268, `$$HELSINKI_3` 164, `$$ISTANBUL_1` 153, `$$DEV` 14, `$$ISTANBUL_3` 12 |
| goal_type 상위 | `play:need_win` 424, `play_report:key` 210, `play` 157, `use_item:ref_item_id` 60, `open_battle_box:box_type` 55, `pull_gacha:gacha_type` 53, `get_ovencrown` 43, `reward_quest:ref_quest_ids` 40 |
| on_quest_completed | 5건 (전부 CGP 프로모션) |
| reward_expiry | **0건 (미사용)** |
| conditions/2 | **0건 (3번째 조건은 사용된 적 없음)** |

---

## 2. 14개 로컬룰 클러스터 전수표

### 2.1 핵심 템플릿 대상 (A–G)

| 코드 | 이름 | 대표 filter | 건수 | 핵심 식별 기준 | 템플릿화 |
|---|---|---|---|---|---|
| **A** | 시즌 이벤트 7일차 | `$$LAUNCH_0` | parent 7 + child 63 = 70 | parent key 50 간격, child 9개, rc=`days_between:(day-1),28` | ✅ TPL_A |
| **B** | 시즌 이벤트 단축형 | `$$HELSINKI_3` `$$ISTANBUL_1` | HEL 70 + IST 35 = 105 | parent key 100 간격, child 5개, rc=`days_between:0,1` (타임스탬프로 날짜 분리) | ✅ TPL_B |
| **C** | 데일리 리셋 세트 | DAILY reset + reward_quest parent | parent 10 + child 54 = 64 | **reset_type=DAILY** (❗ designer draft의 REPEAT 오기), parent HIGHEST/child SUM | ✅ TPL_C |
| **D** | 광장 상시 NPC | `$$NONE` + TOWN | 268 | cond0=`finish_town_dialog` 100%, reward_condition=None 100% | ✅ TPL_D |
| **E** | 광장 이벤트 연동 | `$$LAUNCH_0` + TOWN | 328 | TPL_D와 동일 cond0, timestamp 존재, reward_condition=None | ✅ TPL_E |
| **F** | 반복 퀘스트 (REPEAT) | REPEAT reset | 6 | 전부 `pull_gacha:gacha_type`, 단일 행 | ✅ TPL_F |
| **G** | 독립 개별 (fallback) | - | ~50 | 위 A–F 에 속하지 않는 기타. CGP 포함 | ✅ TPL_G |

### 2.2 추가 클러스터 (H–N, quest-data-qa 발견)

| 코드 | 이름 | 대표 키 | 건수 | 특이사항 | 템플릿 편입 |
|---|---|---|---|---|---|
| **H** | 모드 지정 플레이 | 60021–60105 | 45 | `play_mode_id:mode_ids` cond, param1=`[]{1160}/{1200}/{1360}` | A/B/E 의 **goal 선택지**로 흡수 |
| **I** | 모드 카테고리 | 30004/30019/60001–60005 + 기타 | 15 | `play_mode_category`, param1 ∈ {100, 200, **300**} — ⚠ 300은 스펙 외 | 동일 흡수 |
| **J** | Coin Rush 모드 | 60011–60015 | 5 | cond0=`play_mode:mode_type`, param1=`MODE_TYPE_COIN_RUSH` | goal 선택지 |
| **K** | 파티 플레이 | 207/257/357/407 | 4 | cond0=`play_with_party`, param1=1 | cond 선택지 |
| **L** | Battle Road 보상 | 3041–3075 (HELSINKI_3) | 20 | goal=`reward_battle_road`, **⚠ 전부 SUM (스펙은 HIGHEST 요구)** | 특수 템플릿 or 스펙 수정 |
| **M** | ISTANBUL_3 단축 | 10131–10135 + 1010501–1010507 | 12 | 후자 7자리 key 체계 — **새 key range 관례** 도입 흔적 | TPL_B 변형 |
| **N** | `$$DEV` 테스트 세트 | 51001–51014 | 14 | 개발 전용, goal 제각각 | G fallback |

---

## 3. A·B 패턴의 타임스탬프 구조 (quest-data-qa 검증)

의문: ISTANBUL_1/HELSINKI_3 parent 전부 `rc_param1=0, rc_param2=1` 동일한데 왜?

**답**: 각 parent 의 `start_timestamp` / `end_timestamp` 가 **일차별 절대 시각**으로 keywords.timestamp 에 등록되어 있어, `days_between:0,1` 은 "parent 활성 구간의 하루 동안만 수령"을 의미.

| filter | parent 수 | 타임스탬프 매핑 | 누락 |
|---|---|---|---|
| HELSINKI_3 | 14 | `HELSINKI_3_EVENT_SPECIAL_NDAY01_START/END` ~ `NDAY14_START/END` | 0 |
| ISTANBUL_1 | 7 | `ISTANBUL_1_EVENT_SPECIAL_NDAY08_START/END` ~ `NDAY14_START/END` | 0 |
| LAUNCH_0 Day1~7 | 7 | (모두 동일 `EVENT_LAUNCH_0_*`, rc 로 일차 분리) | 0 |

→ **LAUNCH_0 와 HELSINKI_3/ISTANBUL_1 는 서로 다른 날짜 분리 방식을 쓴다**:
- **A(LAUNCH_0)**: 타임스탬프 1세트 + `rc_param1` 을 일차별로 증가(0,1,2,3,4,5,6). 수령은 `(day-1, 28)` 기간 내.
- **B(HELSINKI_3/ISTANBUL_1)**: 타임스탬프를 일차별 세트로 분리 + rc 전부 `(0,1)` 동일. 수령은 각 parent 활성 구간 24시간.

템플릿 설계 시 이 차이를 명확히 유저에게 안내해야 함.

---

## 4. D·E 패턴의 완결성 (quest-data-qa 검증)

- `$$NONE` + TOWN 268/268 **cond0 = finish_town_dialog** 100%
- `$$LAUNCH_0` + TOWN 328/328 **cond0 = finish_town_dialog** 100%, **reward_condition = None** 100%
- 신규 TOWN 퀘스트 추가 시 `finish_town_dialog:ref_dialog_group_id` 자동 주입은 안전

---

## 5. C 패턴의 완결성 (quest-data-qa 검증)

- DAILY+reward_quest parent 10건 (30001/30016/40001/40011/40021/40031/40051/40061/40071/40081)
- **전 parent/child 쌍이 reset_type=DAILY, count_type 규약(parent HIGHEST / child SUM) 준수**
- child 누락 0

⚠ **system-designer 초안 TPL_C 정정 필요**:
- 초안: `reset_type = QUEST_RESET_TYPE_REPEAT`
- 실제: `reset_type = QUEST_RESET_TYPE_DAILY`
- REPEAT 는 **TPL_F(pull_gacha 6건)** 에만 사용됨.

---

## 6. 스펙 위반 이슈 (기획 확인 필요)

### 6.1 reward_battle_road — SUM 사용
- quest-data-qa 에이전트 내부 스펙: `reward_battle_road` → HIGHEST
- 실데이터: 20/20 SUM 사용 (HELSINKI_3 key 3041–3075)
- **선택지**:
  - (a) 스펙을 SUM 으로 정정 (현행 유지)
  - (b) 데이터를 HIGHEST 로 일괄 교정 (런타임 영향 검토 필요)

### 6.2 play_mode_category param1 = 300
- 에이전트 스펙: 100(상시), 200(로테이션)
- 실데이터: key 60001–60005 에서 **300** 사용 (5건)
- **선택지**:
  - (a) 스펙에 `300: 시즌/특수` 정의 추가
  - (b) 데이터 재검토 (300 이 의도된 값인지 확인)

### 6.3 `conditions/2` 전혀 미사용
- 52컬럼 중 Y/Z/AA (conditions/2) 는 1152행 모두 비어있음
- quest_tool UI 설계 시 **condition 최대 2개** 로 간소화 제안

### 6.4 `reward_expiry` 전혀 미사용
- AJ/AK 컬럼 0건 사용
- UI 에서 숨김 처리 권장

---

## 7. 신규 이벤트 추가 가이드 (기획용)

### 7.1 Key range 예약 현황

| 구간 | 용도 | 비고 |
|---|---|---|
| 31~35 | LAUNCH_0 기타 | 예약 |
| 100~409 | LAUNCH_0 Day1~7 (A) | 50 간격, 수정 시 주의 |
| 3041~3075 | HELSINKI_3 Battle Road (L) | SUM 이슈 관찰 |
| 5600~5604 | LAUNCH_0 TOWN 편입 | 예약 |
| 10000~10075 | LAUNCH_0 기타 | - |
| 20000~20004 | LAUNCH_0 CGP (N) | on_quest_completed |
| 30001~30015 | LAUNCH_0 DAILY (C) | - |
| 30016~ | ISTANBUL_1 DAILY (C) | - |
| 40001~40081 | DAILY parent-child (C) | 10 간격 |
| 51001~51014 | DEV (N) | 테스트 |
| 60001~60105 | LAUNCH_0 모드 제한 (H/I/J) | 45+ |
| 71100~72400 | HELSINKI_3 B | 100 간격 |
| 73100~73700 | ISTANBUL_1 B | 100 간격 |
| 500001~500005 | TOWN 더미 | - |
| 1010501~1010507 | ISTANBUL_3 7자리 (M) | 새 체계 |
| 11000190000+ | TOWN 상시 대규모 | 11자리 거대 key |

**신규 이벤트 원칙**: 위 구간 중 어느 것과도 겹치지 않게 선점. 템플릿 A/B 일 때는 parent_step(50 또는 100) 의 배수 경계에 맞춤.

### 7.2 템플릿 선택 의사결정 트리

```
이 퀘스트는...
├─ TOWN 광장에서 NPC 대화로 시작?
│   ├─ 상시(기간 무관) → TPL_D
│   └─ 이벤트 기간 한정 → TPL_E
├─ 매일 리셋되는 데일리?
│   └─ reward_quest parent + N child → TPL_C
├─ 시즌/런칭 이벤트?
│   ├─ 7일 × 9 child (LAUNCH 스타일) → TPL_A
│   └─ N일 × 5 child (HELSINKI/ISTANBUL 스타일) → TPL_B
├─ 무한 반복 가챠?
│   └─ TPL_F
└─ 그 외 (CGP 연동, 특수 condition 조합 등) → TPL_G (fallback)
```

### 7.3 count_type 강제 규칙

| goal_type | 필수 count_type |
|---|---|
| `reward_quest:ref_quest_ids` | HIGHEST |
| `have_*` 계열 | HIGHEST |
| `achieve_smash_level` | HIGHEST |
| `have_highest_normal_ovencrown` | HIGHEST |
| `reward_battle_road` | **확정 필요** (현 실데이터 SUM) |
| 그 외 | SUM |

---

## 8. 템플릿 스펙 요약 (자세한 스펙은 designer draft 참조)

| 템플릿 | filter | category | reset_type | parent step | children/parent | 자동 주입 |
|---|---|---|---|---|---|---|
| TPL_A | 선택 | GENERAL | NONE | 50 | 9 | rc=`days_between:(day-1),28` |
| TPL_B | 선택 | GENERAL | NONE | 100 | 5 | rc=`days_between:0,1`, 일차별 timestamp 필수 |
| TPL_C | 선택 | GENERAL | **DAILY** ⚠ | 10 (가변) | 4~5 | rc=None |
| TPL_D | `$$NONE` | **TOWN** | NONE | - | - | cond0=`finish_town_dialog` |
| TPL_E | 선택 | **TOWN** | NONE | - | - | cond0=`finish_town_dialog`, rc=옵션 |
| TPL_F | REPEAT 계열 | GENERAL | REPEAT | - | - | goal=`pull_gacha:gacha_type` |
| TPL_G | 자유 | 자유 | 자유 | - | - | 없음 (기존 UI) |

---

## 9. 구현 로드맵 제안

1. **Phase 1 (P1 — 즉시 착수 가능)**: TPL_D (광장 상시) + TPL_F (반복) — 단일 행, 리스크 최저
2. **Phase 2 (P2)**: TPL_C (데일리 세트) — parent-child 첫 구현
3. **Phase 3 (P3)**: TPL_B (시즌 단축) — 일차별 timestamp 로직
4. **Phase 4 (P4)**: TPL_A (시즌 7일) — 가장 복잡, 9×7 매트릭스
5. **Phase 5 (P5)**: TPL_E (광장 이벤트) — TPL_D + timestamp
6. **Phase 6 (P6)**: TPL_G (fallback 정리) — 기존 UI 이관
7. **Phase 7 (추후)**: H/I/J/K/L 을 A/B/C/E 의 고급 옵션으로 편입

---

## 10. 오픈 이슈 / 결정 대기

| # | 이슈 | 담당 |
|---|---|---|
| 1 | `reward_battle_road` HIGHEST vs SUM | 기획 |
| 2 | `play_mode_category` 300 정의 | 기획 |
| 3 | `description` 의 `<color=…>{0}회…</color>` 프리셋 제공 여부 | UX |
| 4 | `dialog_group_id` FK 로더 추가 (dialog_groups.xlsx 연동) | 개발 |
| 5 | parent-child 자동 key 발급 알고리즘 (기존 최대+step vs 수동) | UX |
| 6 | DAILY 계열 filter 네이밍 규칙 ($$DAILY_* 같은 prefix 도입 여부) | 기획 |

---

## 11. 참고: 원시 데이터 덤프 위치

- `D:\claude_make\docs\_quest_raw_dump.txt` — 1차 탐색 (ISTANBUL_1 전체, DAILY parent, cond 분포 등)
- `D:\claude_make\docs\_quest_raw_dump2.txt` — 2차 심층 (parent 전수, timestamp 검증, key range)
- `D:\claude_make\docs\quest_event_template_designer_draft.md` — system-designer 가 작성한 7종 템플릿 스펙 초안 (본 문서의 Phase 1~6 근거)

---

**문서 끝.**

# Quest Event Template Designer — Draft Spec

> 퀘스트 데이터 입력 도구(`D:\claude_make\quest_tool\`)를 "이벤트 타입 선택 → 필요한 필드만 표로 입력" 방식으로 확장하기 위한 **템플릿 7종 데이터 모델 스펙**.
> 문서 작성일 2026-04-23. 본 문서는 **스펙만** 정의하며 코드는 수정하지 않는다.

---

## 0. 개요

### 0.1 템플릿 카탈로그

| # | 코드 | 템플릿 이름 (UI 탭) | 실데이터 클러스터 | 비고 |
|---|---|---|---|---|
| 1 | **TPL_A** | 시즌 이벤트 (7일차) | LAUNCH_0 70건 | parent 7 + child 63, 9 sub-quest |
| 2 | **TPL_B** | 시즌 이벤트 (단축) | HELSINKI_3 70 / ISTANBUL_1 35 | parent N + child 5N, 5 sub-quest |
| 3 | **TPL_C** | 데일리 리셋 세트 | DAILY 74건 | HIGHEST+reward_quest / SUM |
| 4 | **TPL_D** | 광장 상시 NPC | TOWN NONE 268건 | finish_town_dialog 필수 |
| 5 | **TPL_E** | 광장 이벤트 연동 | TOWN LAUNCH_0 328건 | TPL_D + 기간 한정 |
| 6 | **TPL_F** | 반복 (REPEAT) | REPEAT 6건 | pull_gacha 전용 |
| 7 | **TPL_G** | 개별 (fallback) | 기타 | 기존 단건 UI 유지 |

### 0.2 공용 용어

- **parent quest**: `count_type=QUEST_COUNT_TYPE_HIGHEST`, `goal_type=reward_quest:ref_quest_ids`. 자식 퀘스트 key 배열을 target 으로 받아 N개 이상 완료 시 전체 보상.
- **child quest**: `count_type=QUEST_COUNT_TYPE_SUM`. 실제 게임 행동을 수집.
- **parent key / child key 규칙**
  - TPL_A: parent 간격 **50** (100, 150, 200 ...), child = parent+1~parent+9
  - TPL_B: parent 간격 **100** (71100, 71200 ...), child = parent+1~parent+5
- **days_between**: `reward_condition=days_between:from,to`. 이벤트 시작 대비 수령 가능 기간 (day offset).

### 0.3 공용 FK/검증 규칙

| 필드 | 소스 | 비고 |
|---|---|---|
| `$filter` | `keywords.xlsx!build` | 드롭다운 필수 |
| `start_timestamp` / `end_timestamp` | `keywords.xlsx!timestamp` | 드롭다운 필수 |
| `reward_id` | `items.xlsx!items[^key]` | autocomplete |
| `cond:play_with_cookie:ref_cookie_id` | `cookies.xlsx!cookies[^key]` | |
| `cond:town_finish_dialog:ref_dialog_group_id` | dialog_group 테이블 | 현 도구엔 로드 없음 → 자유입력 + 범위 경고 |
| `goal:reward_quest:ref_quest_ids` | 같은 시트 내 child key 배열 | 자동 계산 |

### 0.4 공용 출력 컬럼 맵 (quests.xlsx)

| 컬럼 | 필드 | 템플릿 설정 방식 |
|---|---|---|
| A | `$filter` | 사용자 입력 (공통) |
| B | `^key` | 자동 발급 |
| C | `category` | 템플릿 고정 |
| F | `description` | 사용자 입력 (공통) |
| G,I | `start_timestamp`/`end_timestamp` | 사용자 입력 (공통) |
| K~N | `town_*` | TPL_D/E만 사용 |
| O | `count_type` | 템플릿 고정 (parent=HIGHEST, child=SUM) |
| P | `goal_count` | parent=자식 수(또는 -1), child=사용자 입력 |
| Q | `reset_type` | 템플릿 고정 |
| R~AA | `conditions/0~2` | 템플릿별 조합 |
| AB~AD | `goal_type` | 템플릿별 기본 + 사용자 선택 |
| AE~AG | `reward_condition` | 템플릿별 자동 |
| AH,AI | `reward_id`, `reward_qty` | 사용자 입력 |
| AL~AP | `on_quest_completed` | TPL_G에서만 노출 (CGP) |

---

## 1. TPL_A — 시즌 이벤트 (7일차)

### 1.1 정의

| 항목 | 값 |
|---|---|
| 대표 실데이터 | `$$LAUNCH_0` Day1~Day7 (parent 100/150/200/250/300/350/400) |
| 건수 | parent 7 + child 63 = **70행** 생성 |
| 적용 조건 | "신규 시즌 런칭/재런칭 - 7일차 일일 퀘스트" 형태 |

### 1.2 고정 필드 (템플릿이 자동 세팅)

| 필드 | parent | child |
|---|---|---|
| `category` | `QUEST_CATEGORY_GENERAL` | `QUEST_CATEGORY_GENERAL` |
| `reset_type` | `QUEST_RESET_TYPE_NONE` | `QUEST_RESET_TYPE_NONE` |
| `count_type` | `QUEST_COUNT_TYPE_HIGHEST` | `QUEST_COUNT_TYPE_SUM` |
| `goal_count` (parent) | child 개수(=9) | - |
| `goal_type` (parent) | `reward_quest:ref_quest_ids` | - |
| `reward_condition` | `days_between:from,to` | `days_between:from,to` |
| `rc_param1` (from) | `day - 1` | `day - 1` |
| `rc_param2` (to) | `28` (상수) | `28` |
| `description` (parent) | `'{day}일차 전체 퀘스트 완료 보상'` | 사용자 입력 |

### 1.3 사용자 입력 필드

**Level-1 (시즌 공용, 1회 입력)**

| 필드 | 타입 | 예시 |
|---|---|---|
| `filter` | select | `$$LAUNCH_0` |
| `start_timestamp` | select | `EVENT_LAUNCH_0_START` |
| `end_timestamp` | select | `EVENT_LAUNCH_0_END` |
| `start_parent_key` | int | `100` (→ day2=150, day3=200 ...) |
| `days` | int (고정 7) | `7` |
| `reward_period_days` | int | `28` (상수이지만 조정 가능) |

**Level-2 (Day × Sub-quest 표, 7×9 = 63 셀)**

Day별 parent 보상(AH/AI)도 parent 단위 1행씩 입력.

### 1.4 자동 유도 필드

```
for day in 1..7:
    parent_key = start_parent_key + (day-1) * 50
    parent.rc_param1 = day - 1
    parent.rc_param2 = reward_period_days
    parent.goal_count = 9
    parent.goal_type.param1 = "[]{" + ",".join(str(parent_key+1+i) for i in range(9)) + "}"

    for i in 1..9:
        child_key = parent_key + i
        child.rc_param1 = day - 1
        child.rc_param2 = reward_period_days
```

### 1.5 검증 규칙

- `start_parent_key` mod 50 == 0 권장 (경고)
- `start_parent_key + 6*50 + 9` 까지의 모든 key 가 `quests.xlsx` 에 이미 존재하지 않을 것 (중복 금지)
- 각 day 의 9개 child 중 최소 1개는 `goal_type` 필수
- `reward_id` 는 `items` FK, `reward_qty > 0`

### 1.6 UI 와이어프레임

```
[탭: 시즌 이벤트(7일)]
─────────────────────────────────────────────────────────────────
시즌 공용 설정
  filter: [$$LAUNCH_0 ▼]   start: [EVENT_LAUNCH_0_START ▼]   end: [EVENT_LAUNCH_0_END ▼]
  start_parent_key: [100]   days: 7 (고정)   reward_period: [28]

Day별 Parent 보상
┌─────┬────────────┬────────────┬──────────┬──────────┐
│ Day │ parent_key │ parent_desc│ reward_id│ reward_qty│
├─────┼────────────┼────────────┼──────────┼──────────┤
│ 1   │ 100 (자동) │ [1일차 …]  │ [8001]   │ [1]      │
│ 2   │ 150        │ [2일차 …]  │ [8002]   │ [1]      │
│ ...                                                   │
│ 7   │ 400        │ [7일차 …]  │ [8007]   │ [1]      │
└─────┴────────────┴────────────┴──────────┴──────────┘

Day x Sub-quest (9개) 입력 표
탭 [Day1][Day2][Day3][Day4][Day5][Day6][Day7]

── Day1 ──
┌───┬──────────┬─────────────────────────────┬────┬─────────┬──────────┬───────────┐
│ # │ child_key│ goal_type                    │prm1│ target  │ reward_id│ reward_qty│
├───┼──────────┼─────────────────────────────┼────┼─────────┼──────────┼───────────┤
│ 1 │ 101      │ [play                    ▼] │    │ [3]     │ [1111020]│ [1]       │
│ 2 │ 102      │ [play:need_win           ▼] │TRUE│ [2]     │ [1121010]│ [1]       │
│ 3 │ 103      │ [play_report:key         ▼] │KILL│ [30]    │ [1131005]│ [1]       │
│ ...                                                                                 │
│ 9 │ 109      │ [play:need_win           ▼] │TRUE│ [2]     │ [13001]  │ [10]      │
└───┴──────────┴─────────────────────────────┴────┴─────────┴──────────┴───────────┘
+ description: [<color=#ffe535>{0}회 …]

[미리보기] [저장(70행 append)]
```

### 1.7 의사코드

```python
def build_tpl_a(inputs: dict) -> list[dict]:
    rows = []
    days = 7
    for day in range(1, days + 1):
        pkey = inputs["start_parent_key"] + (day - 1) * 50
        child_keys = [pkey + 1 + i for i in range(9)]
        rows.append(make_parent_row(
            key=pkey, day=day,
            child_keys=child_keys,
            rc_from=day - 1, rc_to=inputs["reward_period_days"],
            reward=inputs["parent_rewards"][day],
            filter_=inputs["filter"], ts=inputs["timestamps"],
        ))
        for i, ck in enumerate(child_keys):
            rows.append(make_child_row(
                key=ck, sub=inputs["days_subquests"][day][i],
                rc_from=day - 1, rc_to=inputs["reward_period_days"],
                filter_=inputs["filter"], ts=inputs["timestamps"],
            ))
    return rows  # 7 + 63 = 70 rows
```

---

## 2. TPL_B — 시즌 이벤트 (단축)

### 2.1 정의

| 항목 | 값 |
|---|---|
| 대표 실데이터 | HELSINKI_3 (14 parent × 5 child), ISTANBUL_1 (7 parent × 5 child) |
| 건수 | parent N + child 5N (N=사용자 지정, 보통 7~14) |
| 적용 조건 | "1~2주 이벤트에서 일일 퀘스트 5개씩 단축 구성" |

### 2.2 고정 필드

| 필드 | parent | child |
|---|---|---|
| `category` | `QUEST_CATEGORY_GENERAL` | `QUEST_CATEGORY_GENERAL` |
| `count_type` | `HIGHEST` (goal=5) | `SUM` |
| `goal_type` (parent) | `reward_quest:ref_quest_ids` | - |
| `reward_condition` | `days_between:0,1` (고정) | `days_between:0,1` |
| `reset_type` | `NONE` | `NONE` |

> 실데이터 관찰: HELSINKI_3 / ISTANBUL_1 모두 parent.rc_param1=0, rc_param2=1 로 고정.

### 2.3 사용자 입력 필드

**Level-1 (시즌 공용)**

| 필드 | 타입 |
|---|---|
| `filter` | select |
| `start_timestamp`, `end_timestamp` | select |
| `start_parent_key` | int (예: 73100) |
| `num_days` | int (7~14) |
| `parent_key_step` | int (기본 **100**) |

**Level-2 (Day × 5 sub-quest 표)**

5개 child = `{parent+1, +2, +3, +4, +5}`.

### 2.4 자동 유도

```
for d in 0..num_days-1:
    pkey = start_parent_key + d * parent_key_step
    child_keys = [pkey + 1 + i for i in range(5)]
    parent.goal_count = 5
    parent.rc = (0, 1)
    child.rc = (0, 1)
```

### 2.5 검증

- `start_parent_key + num_days * parent_key_step - 1` 범위 전체 신규 key
- 기존 HELSINKI_3 / ISTANBUL_1 키 영역(71000~73999)과 충돌 금지 경고

### 2.6 UI 와이어프레임

```
[탭: 시즌 이벤트(단축)]
─────────────────────────────────────────────────────────────────
공용 설정
  filter: [$$HELSINKI_3 ▼]   start/end: [... ▼]
  start_parent_key: [71100]   num_days: [14]   step: [100]

Day x 5 sub-quest (최대 num_days 탭)
[Day1][Day2]...[Day14]

── Day1 (parent_key=71100) ──
Parent 보상: reward_id [30] qty [300] desc [전체 퀘스트 완료 보상]

┌───┬──────────┬───────────────────────┬──────┬─────────┬──────────┬──────┐
│ # │ child_key│ goal_type              │ prm1 │ target  │ reward_id│ qty  │
├───┼──────────┼───────────────────────┼──────┼─────────┼──────────┼──────┤
│ 1 │ 71101    │ [play                ▼]│      │ [8]     │ [1111040]│ [1]  │
│ 2 │ 71102    │ [play:need_win       ▼]│ TRUE │ [4]     │ [1121020]│ [1]  │
│ 3 │ 71103    │ [play_report:key     ▼]│ KILL │ [25]    │ [10]     │ [300]│
│ 4 │ 71104    │ [play_report:key     ▼]│ DMG  │ [250000]│ [1000110]│ [1]  │
│ 5 │ 71105    │ [get_ovencrown       ▼]│      │ [100]   │ [1311010]│ [1]  │
└───┴──────────┴───────────────────────┴──────┴─────────┴──────────┴──────┘

[미리보기(84행)] [저장]
```

---

## 3. TPL_C — 데일리 리셋 세트

### 3.1 정의

| 항목 | 값 |
|---|---|
| 대표 실데이터 | `reset_type=QUEST_RESET_TYPE_REPEAT` + DAILY filter |
| 건수 | parent N + child N×M (일반 N=10, M=6~9) |
| 적용 조건 | "매일 리셋되는 데일리 미션 세트" |

### 3.2 고정 필드

| 필드 | parent | child |
|---|---|---|
| `category` | `QUEST_CATEGORY_GENERAL` | `QUEST_CATEGORY_GENERAL` |
| `reset_type` | `QUEST_RESET_TYPE_REPEAT` | `QUEST_RESET_TYPE_REPEAT` |
| `count_type` | `HIGHEST` | `SUM` |
| `goal_type` (parent) | `reward_quest:ref_quest_ids` | - |
| `reward_condition` | `None` (또는 `days_between:0,1` daily) | `None` |
| `filter` | `$$DAILY` 류 (사용자 선택) | 동일 |

### 3.3 사용자 입력

**Level-1**

| 필드 | 타입 |
|---|---|
| `filter` | select (DAILY keyword 풀) |
| `start_parent_key` | int |
| `num_children_per_parent` | int (기본 **6**) |
| `parent_key_step` | int (기본 **10**) |
| `goal_count_for_parent` | int (= num_children 또는 -1) |

**Level-2**: child 행별 `goal_type`, `target`, `reward_id`, `reward_qty`.

### 3.4 자동 유도

```
for idx in range(num_parents):
    pkey = start_parent_key + idx * parent_key_step
    child_keys = [pkey + 1 + i for i in range(num_children_per_parent)]
    parent.goal_count = goal_count_for_parent
    parent.goal_type.param1 = "[]{" + ",".join(ck) + "}"
```

### 3.5 검증

- DAILY 퀘스트는 `reset_type=REPEAT` 필수
- child 의 `reward_id` 가 소비형(재화/코인)인지 확인 (경고)
- `filter` 가 DAILY 계열 keyword 인지 확인

### 3.6 UI 와이어프레임

```
[탭: 데일리 세트]
─────────────────────────────────────────────────────────────────
공용 설정
  filter: [$$DAILY ▼]   start_parent_key: [1000]
  num_parents: [10]   children_per_parent: [6]   parent_step: [10]

[Set 1 (pkey=1000)] [Set 2 (1010)] ... [Set 10 (1090)]

── Set 1 (parent=1000) ──
Parent desc: [데일리 미션 완료 세트]   reward: [30] qty [100]
┌───┬────────┬──────────────────┬──────┬─────────┬──────────┬──────┐
│ # │ ckey   │ goal_type         │ prm1 │ target  │ reward_id│ qty  │
├───┼────────┼──────────────────┼──────┼─────────┼──────────┼──────┤
│ 1 │ 1001   │ [play_report:key▼]│ KILL │ [10]    │ [10]     │ [50] │
│ 2 │ 1002   │ [play           ▼]│      │ [3]     │ [1]      │ [500]│
│ ...                                                                │
│ 6 │ 1006   │ [daily_login    ▼]│      │ [1]     │ [20001]  │ [1]  │
└───┴────────┴──────────────────┴──────┴─────────┴──────────┴──────┘

[미리보기(70행)] [저장]
```

---

## 4. TPL_D — 광장 상시 NPC

### 4.1 정의

| 항목 | 값 |
|---|---|
| 대표 실데이터 | filter=`NONE`, `category=TOWN`, `conditions/0=finish_town_dialog:ref_dialog_group_id` |
| 건수 | 단건 입력 반복 (일반적으로 한 번에 1~10개) |
| 적용 조건 | "특정 NPC 대화 후 열리는 광장 상시 퀘스트" |

### 4.2 고정 필드

| 필드 | 값 |
|---|---|
| `filter` | `$$NONE` (기본) |
| `category` | `QUEST_CATEGORY_TOWN` |
| `reset_type` | `QUEST_RESET_TYPE_NONE` |
| `count_type` | `QUEST_COUNT_TYPE_SUM` |
| `conditions/0/%key` | `finish_town_dialog:ref_dialog_group_id` **(자동 주입)** |
| `reward_condition` | `None` |

### 4.3 사용자 입력

| 필드 | 비고 |
|---|---|
| `^key` | 자동(마지막 TOWN key + 1 제안) |
| `town_category` | `INGAME` / `OUTGAME` |
| `town_icon` | autocomplete (Icon_Mini_CH_*) |
| `town_title` | string (UI 제목) |
| `town_description` | string |
| `dialog_group_id` | int (조건 파라미터) |
| `goal_type` | select |
| `goal_param1`, `goal_param2` | select/int |
| `target` (goal_count) | int |
| `reward_id`, `reward_qty` | FK + int |
| `description` | 내부 메모 (F열) |

### 4.4 자동 주입 예시

```
conditions/0: finish_town_dialog:ref_dialog_group_id = {dialog_group_id}
conditions/1: None
conditions/2: None
```

### 4.5 검증

- `dialog_group_id` 는 정수, 현재 0 ~ 999_999_999 범위 (스키마 로딩 불가 시 경고만)
- `town_title`, `town_description` 필수
- `category=TOWN` 일 때 `town_icon` 필수

### 4.6 UI 와이어프레임

```
[탭: 광장 상시]
─────────────────────────────────────────────────────────────────
공용: filter [$$NONE ▼]   (timestamp 불필요 - 상시)

입력 표 (여러 행 동시 추가 가능)
┌──────┬──────┬──────┬──────┬────────┬────────┬──────┬──────┬─────┬──────┬─────┬────┐
│ key  │t_cat │t_icon│t_titl│ t_desc │dlg_grp │ goal │ prm1 │ tgt │ r_id │ qty │desc│
├──────┼──────┼──────┼──────┼────────┼────────┼──────┼──────┼─────┼──────┼─────┼────┤
│auto  │INGAME│[...] │[...] │ [...]  │ [500004│[play▼│ TRUE │ [1] │ [10] │[33] │... │
│auto  │      │      │      │        │ ]      │      │      │     │      │     │    │
└──────┴──────┴──────┴──────┴────────┴────────┴──────┴──────┴─────┴──────┴─────┴────┘
[행 추가] [미리보기] [저장]
※ conditions/0 = finish_town_dialog:ref_dialog_group_id 는 자동 채움
```

---

## 5. TPL_E — 광장 이벤트 연동

### 5.1 정의

| 항목 | 값 |
|---|---|
| 대표 실데이터 | filter=`$$LAUNCH_0` + `category=TOWN` |
| 적용 조건 | "이벤트 기간 한정 광장 퀘스트" |

### 5.2 고정 필드

TPL_D 의 모든 고정 필드 +

| 필드 | 값 |
|---|---|
| `filter` | 사용자 선택 (비-NONE keyword) |
| `start_timestamp`, `end_timestamp` | 사용자 선택 |
| `reward_condition` | `days_between:0,N` **(자동, 기본 N=기간전체)** |
| `conditions/0` | `finish_town_dialog:ref_dialog_group_id` (자동) |

> 실데이터에서 TPL_E 는 `reward_condition` 이 종종 비어있으나, 이벤트 만료 후에도 보상 수령하려면 `days_between` 추가 필요. 기본값은 `None` + 옵션 체크박스로 보상 기간 지정.

### 5.3 사용자 입력

TPL_D 입력 + 공용 `filter`, `start_timestamp`, `end_timestamp` + 선택 `reward_period_days`.

### 5.4 자동 주입

```
if reward_period_days is set:
    reward_condition = days_between:0,{reward_period_days}
else:
    reward_condition = None
conditions/0: finish_town_dialog:ref_dialog_group_id = {dialog_group_id}
```

### 5.5 UI 와이어프레임

TPL_D 와 동일하되 상단에 `filter / start / end / reward_period` 공용 설정 4필드 추가.

---

## 6. TPL_F — 반복 (REPEAT)

### 6.1 정의

| 항목 | 값 |
|---|---|
| 대표 실데이터 | filter=REPEAT, goal=`pull_gacha:gacha_type` (6건) |
| 적용 조건 | "반복 수행 가능한 가챠 미션" |

### 6.2 고정 필드

| 필드 | 값 |
|---|---|
| `category` | `QUEST_CATEGORY_GENERAL` |
| `reset_type` | `QUEST_RESET_TYPE_REPEAT` |
| `count_type` | `QUEST_COUNT_TYPE_SUM` |
| `reward_condition` | `None` |

### 6.3 사용자 입력

| 필드 | 비고 |
|---|---|
| `^key` | 자동 제안 |
| `filter` | REPEAT 계열 select |
| `gacha_type` | select (`GACHA_TYPE_COOKIE_GACHA` / `GACHA_TYPE_TREND_GACHA` / ...) |
| `target` | int |
| `reward_id`, `reward_qty` | FK + int |
| `description` | string |

### 6.4 자동 설정

```
goal_type: pull_gacha:gacha_type
goal_param1: {gacha_type}
```

### 6.5 UI 와이어프레임

```
[탭: 반복]
─────────────────────────────────────────────────────────────────
filter [$$REPEAT ▼]

┌──────┬─────────────────────────┬──────┬──────┬──────┬─────┐
│ key  │ gacha_type               │ tgt  │ r_id │ qty  │desc │
├──────┼─────────────────────────┼──────┼──────┼──────┼─────┤
│ auto │ [GACHA_TYPE_COOKIE_GACHA▼]│ [10] │ [1]  │ [500]│[..] │
│ auto │ [GACHA_TYPE_TREND_GACHA ▼]│ [1]  │ [30] │ [100]│[..] │
└──────┴─────────────────────────┴──────┴──────┴──────┴─────┘
[행 추가] [미리보기] [저장]
```

---

## 7. TPL_G — 개별 (Fallback)

기존 `app.py` 의 단건 입력 UI 를 그대로 유지. 사용자가 템플릿에 맞지 않는 퀘스트 (예: CGP 연동 `on_quest_completed`, 특수 condition 2개 이상 등) 를 만들 때 사용.

---

## 8. 공통: 탭 기반 UI 전환 구조

### 8.1 라우팅

```python
TEMPLATES = {
    "개별":             render_tpl_g,
    "데일리 세트":       render_tpl_c,
    "시즌 이벤트(7일)":  render_tpl_a,
    "시즌 이벤트(단축)": render_tpl_b,
    "광장 상시":         render_tpl_d,
    "광장 이벤트":       render_tpl_e,
    "반복":             render_tpl_f,
}

tab_names = list(TEMPLATES.keys())
tabs = st.tabs(tab_names)
for tab, name in zip(tabs, tab_names):
    with tab:
        TEMPLATES[name]()
```

### 8.2 공통 하단 액션 바

```
[미리보기 DataFrame]
  │
  ▼
[검증 결과]  ✓ 통과 N건   ⚠ 경고 M건   ✗ 에러 K건
  │ (K>0 이면 저장 비활성)
  ▼
[행 N개 저장]  [취소]
```

### 8.3 저장 로직 (공통)

```python
def save_template_rows(rows: list[dict]) -> None:
    # 1. key 중복 최종 확인 (concurrent edit 방지)
    existing = get_existing_keys(quests_path)
    conflict = set(r["key"] for r in rows) & existing
    if conflict:
        raise KeyConflictError(conflict)
    # 2. 검증
    for r in rows:
        validate_row(r)
    # 3. append (순서 보존: parent → children)
    for r in rows:
        append_quest_row(quests_path, r)
```

---

## 9. 템플릿 × 컬럼 매핑 요약 표

| 컬럼 | TPL_A | TPL_B | TPL_C | TPL_D | TPL_E | TPL_F | TPL_G |
|---|---|---|---|---|---|---|---|
| `$filter` | 입력 | 입력 | 입력(DAILY) | `$$NONE` 고정 | 입력 | 입력(REPEAT) | 입력 |
| `^key` | 자동(parent+step) | 자동 | 자동 | 자동 | 자동 | 자동 | 입력 |
| `category` | GENERAL | GENERAL | GENERAL | **TOWN** | **TOWN** | GENERAL | 입력 |
| `start_ts` | 입력 | 입력 | - | - | 입력 | - | 입력 |
| `end_ts` | 입력 | 입력 | - | - | 입력 | - | 입력 |
| `town_*` | - | - | - | 입력 | 입력 | - | 옵션 |
| `reset_type` | NONE | NONE | **REPEAT** | NONE | NONE | **REPEAT** | 입력 |
| `count_type` | parent HIGHEST / child SUM | 동일 | 동일 | SUM | SUM | SUM | 입력 |
| `cond0` | - | - | - | `finish_town_dialog` 자동 | `finish_town_dialog` 자동 | - | 입력 |
| `goal_type` | parent `reward_quest` 자동 / child 입력 | 동일 | 동일 | 입력 | 입력 | `pull_gacha` 자동 | 입력 |
| `reward_cond` | `days_between:(day-1),28` 자동 | `days_between:0,1` 자동 | None | None | `days_between:0,N` 옵션 | None | 입력 |
| `reward_id/qty` | 입력 | 입력 | 입력 | 입력 | 입력 | 입력 | 입력 |

---

## 10. 미리보기 DataFrame 설계 (공통)

모든 템플릿은 저장 전 아래 컬럼을 가진 preview DF 를 노출.

```
┌────────┬─────┬──────────┬──────────┬──────┬──────┬──────────┬──────────┬──────────┬────────┐
│role    │key  │category  │count_type│goal  │target│ goal_type│ cond0    │ reward_c │ reward │
│        │     │          │          │      │      │          │          │          │(id×qty)│
├────────┼─────┼──────────┼──────────┼──────┼──────┼──────────┼──────────┼──────────┼────────┤
│parent  │100  │GENERAL   │HIGHEST   │9     │-     │reward_q… │-         │db:0,28   │8001×1  │
│child   │101  │GENERAL   │SUM       │-     │3     │play      │-         │db:0,28   │111..×1 │
│child   │102  │GENERAL   │SUM       │-     │2     │play:win  │-         │db:0,28   │112..×1 │
│...                                                                                          │
└────────┴─────┴──────────┴──────────┴──────┴──────┴──────────┴──────────┴──────────┴────────┘
총 70행  (parent 7 + child 63)
```

`role` 컬럼은 UI 전용 (parent / child / single). 저장 시 제거.

---

## 11. 에러 / 경고 카탈로그

| 코드 | 레벨 | 메시지 | 발생 템플릿 |
|---|---|---|---|
| E001 | 에러 | `key` 중복: {k} 는 이미 존재 | 전체 |
| E002 | 에러 | `reward_id` 가 items.xlsx 에 없음 | 전체 |
| E003 | 에러 | `filter` 가 keywords.build 에 없음 | 전체 |
| E004 | 에러 | TOWN 템플릿인데 `town_title` 누락 | D/E |
| E005 | 에러 | `dialog_group_id` 음수/비정수 | D/E |
| E006 | 에러 | child 행 수가 parent.goal_count 와 불일치 | A/B/C |
| W101 | 경고 | `start_parent_key` mod 50 ≠ 0 (A) 또는 mod 100 ≠ 0 (B) | A/B |
| W102 | 경고 | DAILY filter 가 아닌데 reset_type=REPEAT | C |
| W103 | 경고 | TOWN 인데 timestamp 미지정 (상시 의도?) | D |
| W104 | 경고 | 이벤트 연동인데 reward_period 미지정 → 만료 후 보상 불가 | E |

---

## 12. 구현 우선순위 제안

| 단계 | 대상 | 사유 |
|---|---|---|
| P1 | TPL_D, TPL_F | 단일 행 중심, 리스크 최저. 기존 코드 확장 최소 |
| P2 | TPL_C | parent-child 로직 첫 도입, 10 세트로 반복 검증 용이 |
| P3 | TPL_B | 5 child × N day, C 보다 복잡하나 매트릭스 단순 |
| P4 | TPL_A | 7×9 매트릭스, 가장 복잡 |
| P5 | TPL_E | TPL_D 확장형, timestamp 로직만 추가 |
| P6 | TPL_G | 기존 UI 이관 / 정리 |

---

## 13. 오픈 이슈 (추가 결정 필요)

1. **`description` 의 `<color=…>{0}회…</color>` 포맷**: 템플릿이 기본 문구 세트를 프리셋으로 제공할지, 완전 자유 입력으로 둘지.
2. **`on_quest_completed` (5건만 사용)**: TPL_G 에서만 노출 vs. 모든 템플릿 고급 모드로 노출.
3. **`dialog_group_id` FK 로딩**: 현재 quest_tool 에는 dialogs 테이블 미로드. 추후 loader 추가 제안.
4. **DAILY filter 후보 풀**: keywords.build 에서 prefix 기반 (`$$DAILY_*`) 자동 필터링 vs. 수동 선택.
5. **자동 key 발급의 시작값 추천 알고리즘**: 기존 key 최대값 + 간격 vs. 수동 입력 선호.

---

## 14. 변경 영향도 (quest_tool 코드)

| 파일 | 변경 범위 | 비고 |
|---|---|---|
| `app.py` | 탭 구조 도입, `QUEST_TYPES` 딕셔너리 → `TEMPLATES` 맵 | +300~500 라인 |
| `quest_writer.py` | `build_parent_row()`, `build_child_row()`, `append_batch()` 추가 | +150 라인 |
| `config.py` | 변경 없음 | - |
| 신규 `templates/` 모듈 | `tpl_a.py` ~ `tpl_f.py` 로 분리 권장 | 유지보수성 |
| `tests/` | 템플릿별 generator unit test + 샘플 DataFrame 비교 | 필수 |

---

## 부록 A. 실데이터 키 분포 (검증용)

| 시즌 | parent key 범위 | step | child/parent | total |
|---|---|---|---|---|
| LAUNCH_0 Day1~7 | 100, 150, ..., 400 | 50 | 9 | 70 |
| LAUNCH_0 etc | 10000, 20000, 30001, 40001-40031 | 가변 | 4~5 | +23 |
| HELSINKI_3 | 71100 ~ 72400 | 100 | 5 | 70 |
| ISTANBUL_1 | 73100 ~ 73700 | 100 | 5 | 35 |
| ISTANBUL_1 etc | 30016, 40051-40081 | 가변 | 4~5 | +22 |
| DAILY | 1000~1099 범위 가변 | 10 | 6 | 74 |
| TOWN NONE | 500001~, 11xxxxxxxxx | - | - | 268 |
| TOWN LAUNCH_0 | 5600~, 11xxxxxxxxx | - | - | 328 |
| REPEAT | 소수 (pull_gacha) | - | - | 6 |

## 부록 B. goal_type 카탈로그 (발견된 것)

```
play                         (p1=None)
play:need_win                (p1=TRUE/FALSE)
play_report:key              (p1=PLAY_REPORT_KEY_*)
open_battle_box:box_type     (p1=BOX_TYPE_*)
pull_gacha:gacha_type        (p1=GACHA_TYPE_*)
get_ovencrown                (p1=None)
have_highest_normal_ovencrown(p1=None)
daily_login                  (p1=None)
send_friend_request          (p1=None)
reward_quest:ref_quest_ids   (p1=[]{...})   ← parent 전용
town_finish_dialog:ref_dialog_group_id (p1=int)
get_smash_pass_exp           (p1=None)
achieve_smash_level          (p1=None)
```

## 부록 C. condition 카탈로그 (발견된 것)

```
play_with_cookie:ref_cookie_id     (p1=cookie_key)
finish_town_dialog:ref_dialog_group_id (p1=dialog_group_id)  ← TOWN 필수
```

---

**문서 끝.** (약 3,800 단어)

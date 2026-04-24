# Quest Tool TPL_C 데이터 QA 리포트 — 2026-04-24

**평가자 역할**: 독립 Evaluator (하네스 엔지니어링)
**검증 대상**: Generator가 커밋한 TPL_C 구현 및 8건 결정 사항
**실데이터 기준**: quests.xlsx 1152행, items.xlsx 1973개, keywords.xlsx (build 18 / timestamp 194), dialog_groups.xlsx

---

## 0. 전체 요약

- `quest_writer.py` + `app.py` + 테스트 74건 pytest **PASS**.
- Generator가 주장한 8건 결정 중 **3건 PASS**, **2건 WARN**, **3건 FAIL**.
- 가장 큰 문제: **비즈니스 규칙 검증이 UI 레이어에만 존재** — `append_quest_row` / `append_daily_set`는 `^key` 중복만 검증. FK·GoalType↔CountType·Condition 파라미터·reset_type 제한이 **write 경로에서 미검증**.
- `FILTER_KEY_STEP`는 step 값만 맵핑하고 각 filter별 키 영역은 구분하지 않음 → LAUNCH_0 parent 제안이 73755 (HELSINKI 구역)로 튀는 의미 없는 제안이 발생.

---

## 1. 실데이터 관례 vs 구현 대조

| 항목 | 실데이터 관찰 (표본) | Generator 구현 | 판정 |
|---|---|---|---|
| LAUNCH_0 NON-DAILY parent 간격 | keys=[100, 150, 200, 250, 300, 350, 400, 10000, 20000] → step 50 이후 10000/10000 점프 | `FILTER_KEY_STEP["$$LAUNCH_0"]=50` | **PASS (초기 7건만 부합)** — 8번째(10000) 이후는 다른 관례, 구현은 무관함 |
| LAUNCH_0 DAILY parent 간격 | keys=[30001, 40001, 40011, 40021, 40031] → 첫 이후 step 10 | `DEFAULT_PARENT_STEP=10` (DAILY 강제) | **PASS** |
| HELSINKI_3 parent 간격 | keys=[71100, 71200, 71300, ..., 72400] → step 100 일관 | `FILTER_KEY_STEP["$$HELSINKI_3"]=100` | **PASS** |
| ISTANBUL_1 DAILY parent 간격 | keys=[30016, 40051, 40061, 40071, 40081] → step 10 | DAILY step=10 | **PASS** |
| ISTANBUL_1 NON-DAILY parent 간격 | keys=[73100, 73200, ..., 73700] → step 100 | `FILTER_KEY_STEP["$$ISTANBUL_1"]=100` | **PASS** |
| ISTANBUL_3 | **데이터에 전혀 존재하지 않음** (0건) | `FILTER_KEY_STEP["$$ISTANBUL_3"]=100` | **WARN** — 데이터 없어 관례 미검증, 코드 상 step 100으로 가정함 |
| parent count_type (reward_quest:ref_quest_ids) | HIGHEST=40건, SUM=0건 | UI 하드코딩 HIGHEST | **PASS (표면)** — writer는 강제 안 함 |
| parent goal_count = child 개수 | 40건 모두 `goal_count == len(child_ids)` | `append_daily_set`에서 비어있을 때만 채움 (사용자가 다른 값 넣으면 덮지 않음) | **WARN** — test_parent_and_children_written 스스로 증명: `goal_count=1`로 세팅된 parent에 child 3개 넣어도 1이 유지됨 |
| parent-child filter 일관성 | 40 parent × 9 child = 360건 모두 일치 | UI에서 `daily_filter` 공통 변수 사용 | **PASS** |
| WEEKLY reset_type | **데이터에 전혀 존재하지 않음** (0건) | UI drop-down에서 제외 | **PASS** |

### 1-1. LAUNCH_0 parent 제안값 진단

- 현재 `suggest_next_parent_key(existing, "$$LAUNCH_0", "QUEST_RESET_TYPE_NONE", ...)` 결과: **73755**
- 이는 범위 `[30011..99999]` 전역 최대값(73705=HELSINKI_3 child)에 step 50을 더한 값.
- LAUNCH_0은 실제로는 100~400 또는 10000~20000대에 존재. 73755 값은 어떤 LAUNCH_0 관례에도 맞지 않음.
- **함의**: filter 별 고유 영역 구분 없이 step만 보고 추천하므로, 새 LAUNCH_0 parent를 넣을 자리가 실제로는 420~450이거나 10001~10050 근처여야 하는데, 자동 제안은 무의미한 값이 됨.

---

## 2. 비즈니스 규칙 위반 가능 시나리오

| # | 시나리오 | UI 차단? | 저장 차단? | 실 검증 결과 | 위험도 |
|---|---|---|---|---|---|
| S1 | `rewards/0/id`에 items.xlsx에 없는 ID 입력 | YES (selectbox only) | **NO** | bad_reward_FK 테스트: row 1156 기입 성공 | 中 |
| S2 | `$filter`에 keywords.build에 없는 `$$FAKE_FILTER_999` | YES (selectbox only) | **NO** | bad_filter_FK 테스트: row 1156 기입 성공 | 中 |
| S3 | `start_timestamp`에 존재하지 않는 `$$FAKE_TS_999` | YES | **NO** | bad_timestamp_FK 성공 기입 | 中 |
| S4 | `daily_login` + `QUEST_COUNT_TYPE_HIGHEST` (스펙 위반) | **NO** (drop-down 자유 선택) | **NO** | bad_count_type 테스트: 성공 기입 | **高** |
| S5 | `days_between:from=7, to=3` (from > to) | NO (free_text) | **NO** | bad_days_between 성공 기입 | 中 |
| S6 | `conditions/0/condition/%key == finish_town_dialog:dialog_group_id`, `%param1=99999999` (존재 X) | YES (dialog_picker) | **NO** | bad_dialog_group_FK 성공 기입 | 中 |
| S7 | `QUEST_RESET_TYPE_WEEKLY` 입력 | YES (_RESET_TYPES에 없음) | **NO** | weekly_reset 성공 기입 | 中 |
| S8 | TPL_C parent의 count_type을 SUM으로 넘김 | **NO** (UI 하드코딩 방어만) | **NO** | append_daily_set(parent={"count_type":"SUM"}) → 파일에 SUM 저장됨 | **高** (Parent 의미 파괴) |
| S9 | TPL_C parent goal_type을 `daily_login`으로 넘김 | **NO** | **NO** | append_daily_set가 goal_type에 무관하게 `%param1=[]{c1,...}` 덮어씀 → 모순 상태 (`goal_type=daily_login`인데 `%param1=[]{99991}`) | **高** |
| S10 | `suggest_next_parent_key` 값이 이미 누군가의 child key | (가능하지만 현 데이터에서는 미발생) | (get_existing_keys + collision escape) | HELSINKI_3 제안=73805, 현재 미사용 → 이번엔 OK | 低 (조기 경보 필요) |
| S11 | parent `goal_count`를 수동 1로 설정, child 3건 저장 | **NO** | **NO** | `test_parent_and_children_written` 스스로 `goal_count==1` 유지 확인 | 中 (스펙 §parent-child: parent goal_count=N 강제라는 규칙과 불일치) |

### 2-1. 시나리오 S4/S8/S9의 의미

- Writer 계층에서 무조건 UI를 거친다는 가정만으로 무결성을 유지하는 구조.
- 추후 batch import·CLI·테스트 자동화에서 writer를 직접 호출하면 **규칙 불문 통과**.
- 실제로 `D:/claude_make/quest_tool/tests/test_writer.py::TestAppendDailySet::test_parent_and_children_written`은 parent에 `count_type=HIGHEST`를 **사용자가 수동 지정**한 뒤 검증하는 것 → 구현이 HIGHEST를 강제하는지는 테스트되지 않음.

---

## 3. 스펙 표기 오류 / 누락 항목

기준: `C:\Users\Devsisters\.claude\agents\quest-data-qa.md` (업데이트 후 상태) + 평가 브리프.

| 항목 | quest-data-qa.md 표기 | 실데이터 (quests.xlsx 1152행) | 판정 |
|---|---|---|---|
| `reward_battle_road` | SUM (2026-04-24 정정) | SUM=20, HIGHEST=0 | **PASS (정정 정확)** |
| `get_smash_pass_exp` | SUM (필수 매핑 표) | **SUM=5, HIGHEST=3** (혼재) | **FAIL** — 스펙이 틀렸거나, 현존 HIGHEST 3건이 레거시 미정정 데이터 (결정 필요) |
| `play_mvp` | SUM | **데이터 0건** — 검증 불가 | **WARN** — 스펙이 순수 추정 |
| `reward_town_quest` | HIGHEST | **데이터 0건** | **WARN** — 스펙이 순수 추정 |
| `have_cookie:ref_cookie_id` | HIGHEST | **데이터 0건** | **WARN** — 스펙이 순수 추정 |
| `get_item:ref_item_id` | SUM (qa-md 스펙) | **데이터 0건** | **WARN** — 스펙이 순수 추정 |
| `play` (파라미터 없는 변형) | **스펙 표에 누락** | SUM=157 (실데이터 상위 3위!) | **FAIL** — 중요 GoalType 누락 |
| `play_report:key` | 스펙 표에는 `play_report`로만 기재 | 실제 헤더는 `play_report:key` (파라미터 버전) | **WARN** — 표기 차이, GOAL_TYPES 상수는 `play_report:key`로 정확 |
| `open_battle_box` | 표기만 | 실제: `open_battle_box:box_type` | 동일 (WARN, 일관성) |
| `pull_gacha` | 표기만 | 실제: `pull_gacha:gacha_type` | 동일 (WARN) |
| `level_up_cookie` | 표기만 | 실제: `level_up_cookie:ref_cookie_id` | 동일 (WARN) |
| `achieve_cookie_level_count:level` | **스펙 표에 누락** | HIGHEST=10건 | **FAIL** — 실존 GoalType 누락 |
| `town_use_landmark:ref_landmark_id` | 스펙 표에 없음 | SUM=12건 | **FAIL** — 실존 GoalType 누락 |
| `town_finish_dialog:ref_dialog_group_id` | 스펙엔 `finish_town_dialog:dialog_group_id` (Condition 쪽) | GoalType으로도 SUM=6건 존재 | **WARN** — GoalType/Condition 두 쪽에서 쓰이는 키인데 스펙은 condition 쪽만 기록 |
| `invite_code_share:ref_event_id` | 스펙 표에 없음 | SUM=2건 | **WARN** — 드물지만 실재 |
| `have_power_sand:ref_power_sand_id` | 스펙 표에 없음 | HIGHEST=1건 | **WARN** — 드물지만 실재 |
| `entry_rank:rank` | app.py GOAL_TYPES에는 있음 | **데이터 0건** | **WARN** (스펙 표에는 없음, UI에만 있음) |
| `finish_town_dialog:dialog_group_id` | GOAL_TYPES에 있음 | **데이터 0건** (실데이터는 `town_finish_dialog:ref_dialog_group_id`로 다른 키) | **FAIL** — UI가 실제 존재하지 않는 키를 노출 |

### 3-1. app.py GOAL_TYPES의 키 변종 불일치

GOAL_TYPES가 드롭다운에 제공하는 `finish_town_dialog:dialog_group_id`는 quests.xlsx 실데이터 0건이며 실제 사용 키는 `town_finish_dialog:ref_dialog_group_id`임. Generator의 goal_types에 이 변종이 누락됨. Condition 쪽 `finish_town_dialog:dialog_group_id`는 9건 사용되므로 Condition/GoalType 간 키 이름 혼재 가능성이 있음.

### 3-2. reset_type 허용 스펙

- quest-data-qa.md: NONE/DAILY/REPEAT (WEEKLY 제외) — **실데이터 일치**
- 실데이터 분포: None=973, NONE=99, DAILY=74, REPEAT=6, WEEKLY=0
- 대부분 행이 `reset_type`이 비어 있음(973/1152) → `None` 취급 ≡ `QUEST_RESET_TYPE_NONE`과 의미 동일이라는 전제가 구현에 반영됨 (`KEY_RANGES`에서 `(..., None)` 폴백). **PASS**

---

## 4. TC 매트릭스 (계약 기반 검증)

quest-data-qa 에이전트 정의 리포트 양식에 맞춰 주요 TC를 실데이터로 돌린 결과:

| TC | 시나리오 | 실행 결과 | 증거 |
|---|---|---|---|
| TC-07 | GoalType+CountType 조합 전수 검증 (실데이터 1152행) | **FAIL** — `get_smash_pass_exp`에 SUM 5 + HIGHEST 3 혼재. 스펙 표에 `play`(SUM=157), `achieve_cookie_level_count:level`(HIGHEST=10), `town_use_landmark:ref_landmark_id`(SUM=12), `town_finish_dialog:ref_dialog_group_id`(SUM=6), `invite_code_share`, `have_power_sand` 누락 | 실데이터 Counter 추출 결과 (§1) |
| TC-08 | FK (rewards/timestamp/$filter) 전수 검증 (실파일) | **PASS** (실파일은 깨끗) / **FAIL** (신규 행 쓰기 경로 검증 부재) | bad_reward_FK / bad_filter_FK / bad_timestamp_FK 테스트 모두 ACCEPTED |
| TC-09 | Condition 파라미터 형식 검증 | **FAIL** — days_between from>to, dialog_group_id 존재 안 함, play_mode_category=999 등이 write 경로에서 통과됨 | bad_days_between / bad_dialog_group_FK 테스트 통과 기입 |
| TC-17 | TPL_C parent 불변식(count=HIGHEST, goal_type=reward_quest) | **FAIL** (writer 미강제) / **PASS** (UI 하드코딩) | append_daily_set(parent=count_SUM) / (goal_type=daily_login) 모두 ACCEPTED, 모순 상태로 저장됨 |
| TC-18 | parent goal_count ≡ len(children) | **WARN** — parent에 goal_count가 빈 경우만 자동 채움. 값이 있으면 그 값을 신뢰 → 틀린 값이 그대로 저장 가능 | test_parent_and_children_written 자체가 `goal_count==1` 보존 확인 |
| TC-19 | suggest_next_parent_key 안전성 (child key와 충돌, 기존 key와 충돌) | **PASS (실데이터 기준)** — 현재 73805 등 미사용 영역 추천. 충돌 시 generate_unique_key 폴백 로직 존재 | §1-1, HELSINKI_3 제안=73805 `in existing=False` |
| TC-20 | reset_type WEEKLY 차단 | **FAIL** — UI drop-down만 차단, writer는 저장 | weekly_reset 테스트 ACCEPTED |
| TC-21 | description 프리셋 11건 | **PASS** — `DESC_PRESETS` 11개 선언, 모두 `<color=#ffe535>...</color>` 형식. 실데이터 상위 빈도 문구와 부합 | quest_writer.py:434-446 |
| TC-22 | filter 별 key step 관례 부합 | **MIXED** — step 값 자체는 실데이터와 일치. 그러나 "max+step 전역 기반" 추천 방식이 filter 고유 영역을 무시함 (§1-1) | LAUNCH_0 NONE 제안=73755 (실 LAUNCH_0 영역 100~20000과 무관) |
| TC-23 | 74 unit 테스트 일체 통과 | **PASS** | `pytest` 74/74 PASS |

---

## 5. 결정 8건 재평가

| # | 결정 | 판정 | 근거 |
|---|---|---|---|
| 1 | `reward_battle_road` count_type → SUM | **PASS** | 실데이터 20건 모두 SUM |
| 2 | `play_mode_category` param = 100/200/300 | **PASS** | 실데이터 `200=17, 100=11, 300=5` 모두 존재, CONDITIONS 상수에 option_labels 제공 |
| 3 | TPL_C 탭 완성 | **WARN** | UI 작동·테스트 PASS. 그러나 writer가 parent 불변식을 강제하지 않음 (§2 S8/S9) |
| 4 | `reset_type` 허용 = NONE/DAILY/REPEAT (WEEKLY 제외) | **PASS (UI)** / **FAIL (writer)** | _RESET_TYPES 상수 WEEKLY 제외, 그러나 writer는 WEEKLY도 저장 |
| 5 | description 색상 프리셋 11건 | **PASS** | 11개 존재, 모두 `<color=#ffe535>` |
| 6 | `finish_town_dialog:ref_dialog_group_id` dialog_picker + 미리보기 | **WARN** | condition 쪽 키는 `finish_town_dialog:dialog_group_id`로 구현. GoalType 쪽 drop-down의 `finish_town_dialog:dialog_group_id`는 실데이터 0건 (실제 키는 `town_finish_dialog:ref_dialog_group_id`). 브리프 표기와 app.py 구현이 서로 다른 키를 가리킴 |
| 7 | parent-child key 자동 제안 (filter별 max+step) | **WARN** | step 맵핑은 정확. 그러나 "filter별 max" 아닌 "전역 카테고리 max" 사용 → LAUNCH_0 제안이 73755로 타 filter 영역으로 넘어감 |
| 8 | `$filter` = keywords.build id 전용 | **PASS (UI)** / **FAIL (writer)** | select_or_paste가 keywords 목록으로 제한. 그러나 writer는 `$$FAKE_FILTER` 자유 저장 가능 |

---

## 6. 최종 판정

### 전체: **WARN** (조건부 합격)

실데이터 패턴 · 74 unit 테스트 · UI 작동은 타당. 다만 **write 경로에 비즈니스 규칙 방어선이 없다**는 구조적 취약성이 TPL_C 목적(parent-child 세트 무결성 보장)과 직접 충돌함.

### 추가 수정 필요 항목 (우선순위 순)

1. **[FAIL 해결 필요] parent 불변식 writer-side 강제 (TC-17)**
   - `append_daily_set`에 assertion 추가:
     - `parent["count_type"] == "QUEST_COUNT_TYPE_HIGHEST"` 아니면 ValueError
     - `parent["goal_type/type/%key"] == "reward_quest:ref_quest_ids"` 아니면 ValueError
   - `test_parent_and_children_written`도 SUM parent를 넘길 때 ValueError 기대하도록 수정 필요.

2. **[FAIL] parent `goal_count` 자동 덮어쓰기 (TC-18)**
   - 현재 "빈 경우만 채움" → "항상 `len(children)`로 덮어씀"으로 변경 권장 (brief §3 "저장 직전 자동 덮어쓰기?" 질문에 명시적 답변 필요).
   - 변경 안 하려면 parent.goal_count ≠ len(children)이면 ValueError.

3. **[FAIL] quest-data-qa.md 스펙 표 갱신 (TC-07)**
   - 누락 항목 추가: `play`, `achieve_cookie_level_count:level`, `town_use_landmark:ref_landmark_id`, `town_finish_dialog:ref_dialog_group_id`, `invite_code_share:ref_event_id`, `have_power_sand`
   - `get_smash_pass_exp` SUM+HIGHEST 혼재 사실 기록 또는 HIGHEST 3건 정정 결정 기록
   - 순수 추정(play_mvp / reward_town_quest / have_cookie / get_item)은 "데이터 미검증 추정" 명시

4. **[FAIL] GoalType drop-down 오류 (§3-1)**
   - `finish_town_dialog:dialog_group_id` (GoalType, 실데이터 0건) 제거
   - `town_finish_dialog:ref_dialog_group_id` (SUM=6) 추가

5. **[FAIL] write-path FK 검증 계층 추가 (TC-08/09)**
   - 최소한 `append_quest_row` / `append_daily_set`에 선택적 `validate: bool = True` 파라미터 추가 → items/keywords/dialog_groups 로드 후 멤버십 검증
   - 또는 `app.py`에서 save 직전 validator 함수 호출 (별도 모듈 `quest_validator.py`)

6. **[WARN] suggest_next_parent_key를 filter 고유 영역 기반으로 (TC-22)**
   - 현재: 카테고리+reset_type 범위 내 글로벌 max + step
   - 제안: "해당 filter로 쓰인 기존 key만 필터링한 뒤 max + step", 단 해당 filter 최초 추가 시에만 전역 범위 사용
   - LAUNCH_0 신규 parent 추가 시 73755 대신 420 or 30041 등 의미 있는 값 제공

7. **[WARN] reset_type=WEEKLY writer 차단 (TC-20)**
   - `append_quest_row`에서 `reset_type not in {NONE, DAILY, REPEAT, None, ""}` ValueError.

8. **[WARN] Condition 파라미터 형식 검증 (TC-09)**
   - `days_between:from,to` — from ≤ to 체크
   - `play_mode_category` — param1 ∈ {100, 200, 300}
   - `play:need_win` (condition) — TRUE/FALSE

9. **[WARN] ISTANBUL_3 step 100 가정 검증**
   - 데이터가 없어 실관례 미확인 — 릴리즈 전 기획 확인 필요.

### 합격 처리 조건

- 위 1-3번(FAIL) 최소 해결 후 재평가.
- 4-9번(WARN)은 TPL_C 범위를 넘어선 기존 Quest Tool 구조적 개선이므로 별도 티켓 권장.

---

## 7. 참고: 검증에 사용한 실데이터 샘플

### 7-1. parent ^key=100 (LAUNCH_0, NONE) 역추적

```
Parent ^key=100 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_HIGHEST goal_count=9
  param1=[]{101,102,103,104,105,106,107,108,109}
    child ^key=101 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=play
    child ^key=102 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=play:need_win
    child ^key=103 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=play_report:key
    child ^key=104 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_HIGHEST goal_type=have_highest_normal_ovencrown
    child ^key=105 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=play_report:key
    child ^key=106 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=daily_login
    child ^key=107 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=send_friend_request
    child ^key=108 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=play:need_win
    child ^key=109 filter=$$LAUNCH_0 reset=None count=QUEST_COUNT_TYPE_SUM goal_type=play:need_win
```

→ parent-child filter/reset/count_type 구조는 Generator 스펙과 일치.
→ 단, 이 parent는 reset_type이 **비어있음(None)**이지 DAILY가 아니라는 점 주목. TPL_C 탭은 현재 parent.reset_type을 DAILY로 하드코딩 → 이런 NON-DAILY parent 세트(LAUNCH_0 Day1~7, HELSINKI_3 14개 parent 등)는 TPL_C 탭으로 생성 불가. 일반/광장 탭에서 수동으로 만들어야 함.

### 7-2. GoalType × CountType 실 분포 상위 15개

| goal_type | count_type | 빈도 |
|---|---|---|
| play:need_win | SUM | 424 |
| play_report:key | SUM | 210 |
| play | SUM | 157 |
| use_item:ref_item_id | SUM | 60 |
| open_battle_box:box_type | SUM | 55 |
| pull_gacha:gacha_type | SUM | 53 |
| get_ovencrown | SUM | 43 |
| reward_quest:ref_quest_ids | HIGHEST | 40 |
| reward_battle_road | SUM | 20 |
| have_item:ref_item_id | HIGHEST | 15 |
| achieve_smash_level | HIGHEST | 13 |
| have_highest_normal_ovencrown | HIGHEST | 12 |
| town_use_landmark:ref_landmark_id | SUM | 12 |
| achieve_cookie_level_count:level | HIGHEST | 10 |
| town_finish_dialog:ref_dialog_group_id | SUM | 6 |

### 7-3. 누적 FK 무결성 (실파일)

- `rewards/0/id`: 전부 items.xlsx에 존재 (불일치 0건)
- `start_timestamp` / `end_timestamp`: `$$`로 시작하는 모든 값이 keywords.timestamp에 존재
- `$filter`: `$$`로 시작하는 모든 값이 keywords.build에 존재
- `reward_quest:ref_quest_ids` param1의 자식 ID들: 전부 quests.xlsx ^key로 존재

→ 현재 파일은 무결하나, 현재 write 경로는 이 무결성을 **보장하지 않음**.

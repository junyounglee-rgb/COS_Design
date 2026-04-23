# Quest Tool — quests.xlsx 행 추가 도구

## Context

quests.xlsx에 퀘스트 행을 수작업으로 추가하면 컬럼 수(52개)가 많고 FK 참조 관계가 복잡해 오류가 잦다.  
퀘스트 타입(템플릿)을 선택하면 필요한 필드만 표시되고, FK 참조(items, keywords)는 selectbox로 제공해  
손으로 입력하지 않고 클릭으로 퀘스트 행을 추가하는 Streamlit 도구를 만든다.

---

## 생성 파일

| 파일 | 역할 |
|---|---|
| `D:\claude_make\quest_tool\app.py` | Streamlit 메인 앱 |
| `D:\claude_make\quest_tool\quest_writer.py` | Excel 읽기/쓰기 + 참조 로드 |
| `D:\claude_make\quest_tool\config.py` | YAML 설정 로드/저장 |
| `D:\claude_make\quest_tool\quest_tool.yaml` | 파일 경로 설정 |
| `D:\claude_make\quest_tool\run_quest_tool.bat` | 실행 bat |

---

## 실 데이터 분석 결과 (2026-04-22)

### quests.xlsx 실제 컬럼 구조 (헤더 행=3, 데이터 시작=4)

| Col | 헤더명 | 비고 |
|---|---|---|
| A | $filter | $$LAUNCH_0 등 (keywords.build) |
| B | ^key | 유니크 정수 |
| C | category | QUEST_CATEGORY_GENERAL/TOWN/VAULT_MISSION |
| D | #NPC | 기획자 확인용 |
| E | # | 기획자 확인용 |
| F | description | 번역용 퀘스트 설명 |
| G | start_timestamp | $$KEYWORD 또는 Unix 정수 |
| H | (시작) | 기획자 확인용 |
| I | end_timestamp | $$KEYWORD 또는 Unix 정수 |
| J | (종료) | 기획자 확인용 |
| K | town_icon | 광장 퀘스트 전용 |
| L | town_title | 광장 퀘스트 전용 |
| M | town_description | 광장 퀘스트 전용 |
| N | count_type | QUEST_COUNT_TYPE_SUM/HIGHEST/LOWEST/STREAK |
| O | goal_count | 달성 목표 수 (정수) |
| ... | ... | 동적 로드 필요 |
| Q | reset_type | QUEST_RESET_TYPE_NONE/DAILY/WEEKLY/REPEAT |

> ⚠️ 정확한 컬럼 인덱스는 앱 시작 시 `get_header_map()` 으로 동적 로드. 절대 하드코딩 금지.

**통계**: 총 1,103개 데이터 행 (GENERAL: 507행, TOWN: 596행)

### #quest 시트 구조
- 헤더 행=3, 데이터 Row 4~35 (32개 템플릿)
- Column A: desc (town_description)
- Column B: quest (description, `{0}` placeholder 포함)

### items.xlsx 실제 컬럼 구조 (헤더 행=3)
- A: ^key, B: $filter, C: #, F: name, J: category
- 총 1,921개 아이템

### keywords.xlsx 실제 구조 (헤더 행=3)
- **build 시트**: A=id, B=value, C=vng_value — 26개 키워드 (예: LAUNCH_0, HELSINKI_3, ISTANBUL_1)
- **timestamp 시트**: A=id, B=value, C=#시간, D=vng_value — 166개 타임스탬프 (예: INDEFINITE_TIMESTAMP)

---

## 참조 파일

| 파일 | 참조 필드 | 로드 방식 |
|---|---|---|
| `items.xlsx` | reward ids | ^key(A), name(F), category(J) — 헤더행 3 |
| `keywords.xlsx` | start/end_timestamp | timestamp 시트 A=id |
| `keywords.xlsx` | $filter | build 시트 A=id |

---

## quest_writer.py 핵심 함수

```python
@st.cache_data(ttl=300)
def get_header_map(xlsx_path: str, sheet: str = "quests", header_row: int = 3) -> dict[str, int]:
    """헤더 행에서 {컬럼명: 컬럼인덱스} 반환"""

def get_existing_keys(xlsx_path: str) -> set[int]:
    """^key 컬럼의 기존 값 전부 수집"""

def generate_unique_key(existing: set[int], lo=100000, hi=999999) -> int:
    """랜덤 6자리 정수, existing에 없을 때까지 재시도"""

@st.cache_data(ttl=300)
def load_items(items_path: str) -> list[dict]:
    """items.xlsx → [{id, name, category}] (selectbox용)"""

@st.cache_data(ttl=300)
def load_keywords(keywords_path: str) -> dict[str, dict[str, str]]:
    """keywords.xlsx → {시트명: {키: 값}} — timestamp/build 시트
    build 시트: 헤더행 3, id(A)/value(B) 컬럼
    timestamp 시트: 헤더행 3, id(A)/value(B) 컬럼
    반환: {"build": {"LAUNCH_0":"1",...}, "timestamp": {"INDEFINITE_TIMESTAMP":"..."},...}
    $filter selectbox: build 키 → "$$LAUNCH_0" 형식으로 표시
    timestamp selectbox: timestamp 키 → "$$INDEFINITE_TIMESTAMP" 형식으로 표시"""

@st.cache_data(ttl=300)
def load_quest_templates(quests_path: str) -> dict[str, str]:
    """#quest 시트 로드 → {B컬럼(quest텍스트): A컬럼(desc텍스트)}
    헤더행 3, 데이터 행 4~35"""

def append_quest_row(xlsx_path: str, row_data: dict[str, Any]) -> None:
    """header_map 기반으로 quests 시트 마지막 행에 기입 후 저장"""
```

---

## select+paste 위젯 패턴

`$filter`, `start_timestamp`, `end_timestamp` 등 허용 목록이 있는 필드에 사용.  
selectbox(브라우징) + text_input(복붙) 조합으로 구현.

```python
def select_or_paste(label: str, allowed: list[str], key: str) -> str | None:
    """selectbox로 선택하거나 text_input에 직접 붙여넣기 가능한 콤보 위젯.
    허용 목록에 없는 값 입력 시 st.error 표시 + None 반환."""
    MANUAL = "(직접 입력 / 붙여넣기)"
    sel = st.selectbox(label, [MANUAL] + allowed, key=f"{key}_sel")
    if sel == MANUAL:
        val = st.text_input("", placeholder="예) $$LAUNCH_0", key=f"{key}_txt",
                             label_visibility="collapsed")
    else:
        val = sel

    if val and val not in allowed:
        st.error(f"허용 목록에 없는 값: `{val}`")
        return None
    return val or None
```

---

## Quest 타입 템플릿 (5종)

| 템플릿 | category | reset_type | count_type | 특이 사항 |
|---|---|---|---|---|
| 일반 퀘스트 | GENERAL | NONE | SUM | 기본 구성 |
| 데일리 서브 | GENERAL | REPEAT | SUM | condition에 days_between 기본 추가 |
| 데일리 메인 | GENERAL | REPEAT | HIGHEST | goal_count=9, reward_condition=reward_quest |
| 광장 퀘스트 | TOWN | NONE | SUM | town_category/icon/title/description 표시 |
| 금고 퀘스트 | VAULT_MISSION | NONE | SUM | - |

---

## GoalType 목록

```python
GOAL_TYPES = [
    {"key": "daily_login",                     "label": "출석하기",           "params": []},
    {"key": "play:need_win",                   "label": "플레이/승리",         "params": [{"label":"need_win","options":["FALSE","TRUE"]}]},
    {"key": "play_report:key",                 "label": "전투 리포트",         "params": [{"label":"key","options":["PLAY_REPORT_KEY_KILL_COUNT","PLAY_REPORT_KEY_DAMAGE_SUM","PLAY_REPORT_KEY_BUFF_CARD_USED_COUNT","PLAY_REPORT_KEY_DEFAULT_SKILL_USAGE_COUNT","PLAY_REPORT_KEY_SPECIAL_SKILL_USAGE_COUNT","PLAY_REPORT_KEY_ULTIMATE_SKILL_USAGE_COUNT","PLAY_REPORT_KEY_PLAY_DURATION","PLAY_REPORT_KEY_EMOJI_USAGE_COUNT","PLAY_REPORT_KEY_FIRST_KILL_TIME"]}]},
    {"key": "open_battle_box:box_type",        "label": "배틀박스 열기",       "params": [{"label":"box_type","options":["BOX_TYPE_BATTLE","BOX_TYPE_COIN","BOX_TYPE_COSTUME","BOX_TYPE_ALL"]}]},
    {"key": "pull_gacha:gacha_type",           "label": "쿠키 뽑기",          "params": [{"label":"gacha_type","options":["GACHA_TYPE_COOKIE_GACHA","GACHA_TYPE_COOKIE_REMIX_GACHA","GACHA_TYPE_TREND_GACHA"]}]},
    {"key": "level_up_cookie:ref_cookie_id",   "label": "쿠키 레벨업",        "params": [{"label":"cookie_id (빈칸=전체)","free_text":True}]},
    {"key": "have_cookie:ref_cookie_id",       "label": "쿠키 보유",           "params": [{"label":"cookie_id","free_text":True}]},
    {"key": "get_item:ref_item_id",            "label": "아이템 획득",         "params": [{"label":"item_id","item_picker":True}]},
    {"key": "use_item:ref_item_id",            "label": "아이템 사용",         "params": [{"label":"item_id","item_picker":True}]},
    {"key": "have_item:ref_item_id",           "label": "아이템 보유",         "params": [{"label":"item_id","item_picker":True}]},
    {"key": "reward_quest:ref_quest_ids",      "label": "퀘스트 완료",        "params": [{"label":"[]{id1,id2,...}","free_text":True}]},
    {"key": "achieve_smash_level",             "label": "성장레벨 달성",      "params": []},
    {"key": "get_ovencrown",                   "label": "오븐크라운 획득",    "params": []},
    {"key": "have_highest_normal_ovencrown",   "label": "오븐크라운 점수",    "params": []},
    {"key": "send_friend_request",             "label": "친구 신청",          "params": []},
    {"key": "get_smash_pass_exp",              "label": "배틀패스 경험치",    "params": []},
    {"key": "play_mvp",                        "label": "MVP",                "params": []},
    {"key": "reward_battle_road",              "label": "배틀로드 박스",      "params": []},
    {"key": "achieve_cookie_level_all",        "label": "쿠키 레벨 총합",    "params": []},
    {"key": "reward_town_quest",               "label": "광장 퀘스트 완료",  "params": []},
    {"key": "entry_rank:rank",                 "label": "n등 달성",           "params": [{"label":"rank","free_text":True}]},
    {"key": "town_finish_dialog:ref_dialog_group_id","label":"광장 대화 완료","params":[{"label":"dialog_group_id","free_text":True}]},
    {"key": "town_use_landmark:ref_landmark_id","label":"광장 랜드마크",      "params":[{"label":"landmark_id","free_text":True}]},
]
```

---

## Condition 목록

```python
CONDITIONS = [
    {"key": "(없음)",                               "label": "조건 없음",          "params": []},
    {"key": "days_between:from,to",                "label": "기간 조건 (일차)",    "params": [{"label":"from (시작 일차)","free_text":True},{"label":"to (종료 일차)","free_text":True}]},
    {"key": "play:need_win",                        "label": "승리 여부",           "params": [{"label":"need_win","options":["TRUE","FALSE"]}]},
    {"key": "play_with_cookie:ref_cookie_id",      "label": "특정 쿠키로 플레이", "params": [{"label":"cookie_id","free_text":True}]},
    {"key": "play_with_party:player_count",        "label": "파티 플레이",         "params": [{"label":"player_count","free_text":True}]},
    {"key": "play_with_friend",                    "label": "친구와 플레이",       "params": []},
    {"key": "play_mode:mode_type",                 "label": "모드 타입",           "params": [{"label":"mode_type","free_text":True}]},
    {"key": "play_mode_category:ref_display_category_id","label":"모드 카테고리","params":[{"label":"id (상시=100, 로테이션=200)","options":["100","200"]}]},
    {"key": "receive_quest_reward:ref_quest_id",   "label": "이전 퀘스트 완료",   "params": [{"label":"quest_id","free_text":True}]},
    {"key": "play_with_costume:ref_costume_id",    "label": "코스튬 착용",        "params": [{"label":"costume_id","free_text":True}]},
]
```

---

## 테스트 환경 구조

실 데이터(`D:\COS_Project\cos-data\excel\`) 절대 수정 금지.

```
D:\claude_make\quest_tool\
├── app.py
├── quest_writer.py
├── config.py
├── quest_tool.yaml              # 실 운용용 경로
├── run_quest_tool.bat
└── tests/
    ├── fixtures/
    │   ├── quests_test.xlsx     # quests.xlsx — Row 1~3 + 6개 데이터행 발췌
    │   ├── items_test.xlsx      # items.xlsx — Row 1~3 + 20개 발췌
    │   └── keywords_test.xlsx   # keywords.xlsx — build/timestamp 전체 복사
    ├── quest_tool_test.yaml     # fixtures 경로 설정
    ├── run_test.bat             # 테스트 환경으로 앱 실행
    └── test_writer.py           # pytest 단위 테스트
```

### 픽스처 추출 대상 행

| 파일 | 대상 | Row 번호 | ^key |
|---|---|---|---|
| quests_test.xlsx | GENERAL 일반 | Row 4, 5 | 31, 32 |
| quests_test.xlsx | TOWN 광장 | Row 511, 512 | 500001, 500002 |
| items_test.xlsx | 다양한 카테고리 19개 | 지정 행 | 1, 40, 110001, 2000101... |

---

## append_quest_row 안전장치

```python
def append_quest_row(xlsx_path: str, field_values: dict[str, Any]) -> None:
    wb = load_workbook(xlsx_path)
    ws = wb["quests"]
    header_map = _build_header_map(ws, header_row=3)  # 캐시 없는 내부 함수

    # 안전장치 1: 쓰기 직전 ^key 재확인
    key_col = header_map["^key"]
    existing_at_write = {
        ws.cell(row=r, column=key_col).value
        for r in range(4, ws.max_row + 1)
        if ws.cell(row=r, column=key_col).value is not None
    }
    new_key = field_values.get("^key")
    if new_key in existing_at_write:
        wb.close()
        raise ValueError(f"^key 중복: {new_key} 이미 파일에 존재")

    # 안전장치 2: max_row + 1 = 마지막 행 다음에만 추가
    next_row = ws.max_row + 1
    for field, value in field_values.items():
        if field in header_map and value is not None and value != "":
            ws.cell(row=next_row, column=header_map[field], value=value)

    wb.save(xlsx_path)
    wb.close()

    # 안전장치 3: 저장 후 검증
    _verify_written_key(xlsx_path, new_key, next_row, header_map)
```

| 시점 | 검사 내용 |
|---|---|
| UI (세션 시작) | get_existing_keys() → session_state 캐시, ^key 자동 발급 |
| 쓰기 직전 | 파일 재오픈 후 ^key 전체 스캔 → 충돌 시 ValueError |
| 위치 확인 | max_row + 1 — 마지막 행 다음에만 삽입 |
| 쓰기 직후 | 파일 재오픈 → 기록 값 검증 |

---

## 단계별 구현 계획

| STEP | 범위 | 검증 방법 |
|---|---|---|
| 1 | 픽스처 생성 + quest_writer.py 읽기 전용 + test_writer.py | pytest |
| 2 | config.py + 앱 뼈대 + run_test.bat | bat 실행 + UI 확인 |
| 3 | 단건 추가 UI + append_quest_row | 픽스처 행 재현 + pytest |
| 4 | 배치 추가 UI (Tab 2) | #quest 텍스트 붙여넣기 재현 |
| 5 | quest-data-qa 에이전트 + 최종 QA | TC-01~15 전체 통과 |

---

## TC 목록 (TC-01 ~ TC-15)

| TC | 내용 | 담당 |
|---|---|---|
| TC-01 | ^key 100000~999999 범위 자동 발급 | qa-tool |
| TC-02 | GoalType play:need_win → param 드롭다운 표시 | qa-tool |
| TC-03 | 데일리 서브 → reset_type=REPEAT, count_type=SUM 자동 | qa-tool |
| TC-04 | timestamp selectbox → $$INDEFINITE_TIMESTAMP 셀 기록 | qa-tool |
| TC-05 | reward selectbox → ^key 숫자 셀 기록 | qa-tool |
| TC-06 | 중복 ^key 없음, reward id FK 유효 | qa |
| TC-07 | GoalType + CountType 조합 규칙 | quest-data-qa |
| TC-08 | timestamp/build 키워드 존재 여부 | quest-data-qa |
| TC-09 | Condition 파라미터 유효성 | quest-data-qa |
| TC-10 | $filter 허용 목록 외 입력 → st.error | qa-tool |
| TC-11 | 배치 붙여넣기 → town_description 자동 채움 | qa-tool |
| TC-12 | 배치 저장 → {0} 그대로 유지 | qa-tool |
| TC-13 | 추가 행이 max_row+1 위치에 삽입 (덮어쓰기 없음) | qa-tool |
| TC-14 | 쓰기 직전 ^key 재검사 → 충돌 시 ValueError | qa-tool |
| TC-15 | 쓰기 직후 파일 재오픈 → 기록 값 검증 | qa |

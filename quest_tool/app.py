"""Quest Tool - Streamlit app (STEP 3: 단건 추가 UI)."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from config import load_config
from quest_writer import (
    DESC_PRESETS,
    allocate_child_keys,
    append_daily_set,
    append_quest_row,
    generate_unique_key,
    get_existing_keys,
    get_existing_keys_by_filter,
    get_header_map,
    load_dialog_groups,
    load_items,
    load_keywords,
    load_quest_templates,
    parse_quest_texts,
    suggest_next_parent_key,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Quest Tool",
    page_icon="scroll",
    layout="wide",
)

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

QUEST_TYPES = {
    "일반 퀘스트": {
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_NONE",
        "count_type": "QUEST_COUNT_TYPE_SUM",
    },
    "데일리 서브": {
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_DAILY",
        "count_type": "QUEST_COUNT_TYPE_SUM",
    },
    "데일리 메인": {
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_DAILY",
        "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        "goal_count": 9,
    },
    "광장 퀘스트": {
        "category": "QUEST_CATEGORY_TOWN",
        "reset_type": "QUEST_RESET_TYPE_NONE",
        "count_type": "QUEST_COUNT_TYPE_SUM",
    },
    "금고 퀘스트": {
        "category": "QUEST_CATEGORY_VAULT_MISSION",
        "reset_type": "QUEST_RESET_TYPE_NONE",
        "count_type": "QUEST_COUNT_TYPE_SUM",
    },
}

GOAL_TYPES = [
    {"key": "daily_login", "label": "출석하기", "params": []},
    {"key": "play:need_win", "label": "플레이/승리", "params": [{"label": "need_win", "options": ["FALSE", "TRUE"]}]},
    {
        "key": "play_report:key",
        "label": "전투 리포트",
        "params": [
            {
                "label": "key",
                "options": [
                    "PLAY_REPORT_KEY_KILL_COUNT",
                    "PLAY_REPORT_KEY_DAMAGE_SUM",
                    "PLAY_REPORT_KEY_BUFF_CARD_USED_COUNT",
                    "PLAY_REPORT_KEY_DEFAULT_SKILL_USAGE_COUNT",
                    "PLAY_REPORT_KEY_SPECIAL_SKILL_USAGE_COUNT",
                    "PLAY_REPORT_KEY_ULTIMATE_SKILL_USAGE_COUNT",
                    "PLAY_REPORT_KEY_PLAY_DURATION",
                    "PLAY_REPORT_KEY_EMOJI_USAGE_COUNT",
                    "PLAY_REPORT_KEY_FIRST_KILL_TIME",
                ],
            }
        ],
    },
    {
        "key": "open_battle_box:box_type",
        "label": "배틀박스 열기",
        "params": [
            {
                "label": "box_type",
                "options": ["BOX_TYPE_BATTLE", "BOX_TYPE_COIN", "BOX_TYPE_COSTUME", "BOX_TYPE_ALL"],
            }
        ],
    },
    {
        "key": "pull_gacha:gacha_type",
        "label": "쿠키 뽑기",
        "params": [
            {
                "label": "gacha_type",
                "options": ["GACHA_TYPE_COOKIE_GACHA", "GACHA_TYPE_COOKIE_REMIX_GACHA", "GACHA_TYPE_TREND_GACHA"],
            }
        ],
    },
    {
        "key": "level_up_cookie:ref_cookie_id",
        "label": "쿠키 레벨업",
        "params": [{"label": "cookie_id (빈칸=전체)", "free_text": True}],
    },
    {"key": "have_cookie:ref_cookie_id", "label": "쿠키 보유", "params": [{"label": "cookie_id", "free_text": True}]},
    {"key": "get_item:ref_item_id", "label": "아이템 획득", "params": [{"label": "item_id", "item_picker": True}]},
    {"key": "use_item:ref_item_id", "label": "아이템 사용", "params": [{"label": "item_id", "item_picker": True}]},
    {"key": "have_item:ref_item_id", "label": "아이템 보유", "params": [{"label": "item_id", "item_picker": True}]},
    {
        "key": "reward_quest:ref_quest_ids",
        "label": "퀘스트 완료",
        "params": [{"label": "[]{id1,id2,...}", "free_text": True}],
    },
    {"key": "achieve_smash_level", "label": "성장레벨 달성", "params": []},
    {"key": "get_ovencrown", "label": "오븐크라운 획득", "params": []},
    {"key": "have_highest_normal_ovencrown", "label": "오븐크라운 점수", "params": []},
    {"key": "send_friend_request", "label": "친구 신청", "params": []},
    {"key": "get_smash_pass_exp", "label": "배틀패스 경험치", "params": []},
    {"key": "play_mvp", "label": "MVP", "params": []},
    {"key": "reward_battle_road", "label": "배틀로드 박스", "params": []},
    {"key": "achieve_cookie_level_all", "label": "쿠키 레벨 총합", "params": []},
    {"key": "reward_town_quest", "label": "광장 퀘스트 완료", "params": []},
    {"key": "entry_rank:rank", "label": "n등 달성", "params": [{"label": "rank", "free_text": True}]},
    {
        "key": "town_finish_dialog:ref_dialog_group_id",
        "label": "광장 대화 완료(goal)",
        "params": [{"label": "dialog_group_id", "dialog_picker": True}],
    },
    {
        "key": "town_use_landmark:ref_landmark_id",
        "label": "광장 랜드마크",
        "params": [{"label": "landmark_id", "free_text": True}],
    },
]

CONDITIONS = [
    {"key": "", "label": "(조건 없음)", "params": []},
    {
        "key": "days_between:from,to",
        "label": "기간 조건(일차)",
        "params": [{"label": "from(시작)", "free_text": True}, {"label": "to(종료)", "free_text": True}],
    },
    {
        "key": "play:need_win",
        "label": "승리 여부",
        "params": [{"label": "need_win", "options": ["TRUE", "FALSE"]}],
    },
    {
        "key": "play_with_cookie:ref_cookie_id",
        "label": "특정 쿠키 플레이",
        "params": [{"label": "cookie_id", "free_text": True}],
    },
    {
        "key": "play_with_party:player_count",
        "label": "파티 플레이",
        "params": [{"label": "player_count", "free_text": True}],
    },
    {"key": "play_with_friend", "label": "친구와 플레이", "params": []},
    {
        "key": "play_mode:mode_type",
        "label": "모드 타입",
        "params": [{"label": "mode_type", "free_text": True}],
    },
    {
        "key": "play_mode_category:ref_display_category_id",
        "label": "모드 카테고리",
        "params": [
            {
                "label": "id(상시=100,로테이션=200,특별이벤트=300)",
                "options": ["100", "200", "300"],
                "option_labels": {"100": "상시", "200": "로테이션", "300": "특별 이벤트"},
            }
        ],
    },
    {
        "key": "receive_quest_reward:ref_quest_id",
        "label": "이전 퀘스트 완료",
        "params": [{"label": "quest_id", "free_text": True}],
    },
    {
        "key": "play_with_costume:ref_costume_id",
        "label": "코스튬 착용",
        "params": [{"label": "costume_id", "free_text": True}],
    },
    {
        "key": "finish_town_dialog:dialog_group_id",
        "label": "광장 대화 완료",
        "params": [{"label": "dialog_group_id", "dialog_picker": True}],
    },
]

_COUNT_TYPES = [
    "QUEST_COUNT_TYPE_SUM",
    "QUEST_COUNT_TYPE_HIGHEST",
    "QUEST_COUNT_TYPE_LOWEST",
    "QUEST_COUNT_TYPE_STREAK",
]
_COUNT_TYPE_KEYS = ["SUM", "HIGHEST", "LOWEST", "STREAK"]

_RESET_TYPES = [
    "QUEST_RESET_TYPE_NONE",
    "QUEST_RESET_TYPE_DAILY",
    "QUEST_RESET_TYPE_REPEAT",
]
_RESET_TYPE_KEYS = ["NONE", "DAILY", "REPEAT"]


# ---------------------------------------------------------------------------
# Config path helper
# ---------------------------------------------------------------------------


def _get_config_path() -> str:
    """streamlit run app.py -- --config path.yaml 형식에서 경로 추출."""
    args = sys.argv
    for i, arg in enumerate(args):
        if arg == "--config" and i + 1 < len(args):
            return args[i + 1]
    return str(Path(__file__).parent / "quest_tool.yaml")


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------


@st.cache_data
def _load_items(items_path: str) -> list[dict]:
    return load_items(items_path)


@st.cache_data
def _load_keywords(keywords_path: str) -> dict[str, dict[str, str]]:
    return load_keywords(keywords_path)


@st.cache_data
def _load_quest_templates(quests_path: str) -> dict[str, str]:
    return load_quest_templates(quests_path)


@st.cache_data
def _get_header_map(quests_path: str) -> dict[str, int]:
    return get_header_map(quests_path, sheet="quests", header_row=3)


@st.cache_data
def _load_dialog_groups(dialog_groups_path: str) -> list[dict]:
    return load_dialog_groups(dialog_groups_path)


# ---------------------------------------------------------------------------
# UI 위젯 함수
# ---------------------------------------------------------------------------


def select_or_paste(label: str, allowed: list[str], key: str, help: str = "") -> str | None:
    """허용 목록에서만 고르는 selectbox. (직접 입력 옵션은 제공하지 않음.)

    decision 8 적용: $filter 등은 keywords.xlsx 에 정의된 id 만 허용.
    필요한 id 가 없으면 keywords 에 먼저 추가한 뒤 툴을 재시작해야 한다.
    """
    if not allowed:
        st.warning(
            f"{label}: keywords 에 정의된 id 가 없습니다. "
            "keywords.xlsx 에 먼저 id 를 추가한 뒤 툴을 재시작하세요."
        )
        return None
    PLACEHOLDER = "(선택)"
    sel = st.selectbox(label, [PLACEHOLDER] + allowed, key=f"{key}_sel", help=help)
    return sel if sel != PLACEHOLDER else None


def render_param_fields(
    params: list[dict],
    prefix: str,
    items_list: list[dict],
    dialog_groups: list[dict] | None = None,
) -> list[str | None]:
    """GoalType/Condition의 동적 param 필드 렌더링. 값 목록 반환."""
    values = []
    dialog_groups = dialog_groups or []
    for i, p in enumerate(params):
        if p.get("options"):
            opts = p["options"]
            option_labels = p.get("option_labels") or {}
            fmt = (lambda x: f"{x} ({option_labels[x]})") if option_labels else (lambda x: x)
            v = st.selectbox(p["label"], opts, key=f"{prefix}_p{i}", format_func=fmt)
        elif p.get("item_picker"):
            opts = [f"{it['id']}: {it['name']} ({it['category']})" for it in items_list]
            sel = st.selectbox(p["label"], ["(선택 안함)"] + opts, key=f"{prefix}_p{i}")
            if sel != "(선택 안함)":
                v = str(items_list[opts.index(sel)]["id"])
            else:
                v = ""
        elif p.get("dialog_picker"):
            if not dialog_groups:
                v = st.text_input(
                    p["label"] + " (dialog_groups 로드 실패 — 직접 입력)",
                    key=f"{prefix}_p{i}",
                )
            else:
                opts = [
                    f"{g['id']} — {g.get('actor_name','')}: {str(g.get('dialog_text',''))[:40]}"
                    for g in dialog_groups
                ]
                sel = st.selectbox(p["label"], ["(선택 안함)"] + opts, key=f"{prefix}_p{i}")
                if sel != "(선택 안함)":
                    v = str(dialog_groups[opts.index(sel)]["id"])
                else:
                    v = ""
        else:
            v = st.text_input(p["label"], key=f"{prefix}_p{i}")
        values.append(v if v else None)
    return values


# ---------------------------------------------------------------------------
# Tab 1: 단건 추가
# ---------------------------------------------------------------------------


def render_tab_add(
    quests_path: str,
    items_list: list[dict],
    kw: dict[str, dict[str, str]],
    dialog_groups: list[dict] | None = None,
) -> None:
    st.title("퀘스트 단건 추가")

    build_kw = kw.get("build", {})
    ts_kw = kw.get("timestamp", {})
    dialog_groups = dialog_groups or []

    # --- 퀘스트 타입 ---
    quest_type = st.selectbox("퀘스트 타입", list(QUEST_TYPES.keys()), key="quest_type_sel")
    tpl = QUEST_TYPES[quest_type]

    st.divider()

    # --- ^key: 현재 퀘스트 타입의 카테고리/리셋타입 범위 기준으로 발급 ---
    # quest_type이 바뀌었거나 auto_key가 None이면 재발급
    cur_cat = tpl["category"]
    cur_rt = tpl["reset_type"]
    if (
        st.session_state.auto_key is None
        or st.session_state.get("auto_key_type") != quest_type
    ):
        st.session_state.auto_key = generate_unique_key(
            st.session_state.existing_keys, category=cur_cat, reset_type=cur_rt
        )
        st.session_state.auto_key_type = quest_type

    # --- 기본 정보 ---
    col_key, col_cat = st.columns([1, 2])
    with col_key:
        auto_key = st.session_state.auto_key
        st.metric("^key (자동 발급)", auto_key)
    with col_cat:
        st.text_input("category", value=tpl["category"], disabled=True, key="category_display")

    filter_val = select_or_paste(
        "$filter",
        ["$$" + k for k in build_kw.keys()],
        "filter",
    )

    # description: 프리셋 selectbox -> text_area 에 삽입
    desc_preset = st.selectbox(
        "description 프리셋",
        ["(사용 안함)"] + DESC_PRESETS,
        key="desc_preset_sel",
        help="선택 시 아래 text_area 에 삽입. {0} 은 게임 서버가 런타임에 goal_count 로 치환.",
    )
    if desc_preset != "(사용 안함)" and st.button("프리셋 적용", key="apply_desc_preset"):
        st.session_state["desc_input"] = desc_preset
    description = st.text_area("description", height=68, key="desc_input")
    start_ts = select_or_paste(
        "start_timestamp",
        ["$$" + k for k in ts_kw.keys()],
        "start_ts",
    )
    end_ts = select_or_paste(
        "end_timestamp",
        ["$$" + k for k in ts_kw.keys()],
        "end_ts",
    )

    # count_type: 템플릿 기본값 선택
    tpl_count = tpl["count_type"]
    tpl_count_key = tpl_count.replace("QUEST_COUNT_TYPE_", "")
    count_type_idx = _COUNT_TYPE_KEYS.index(tpl_count_key) if tpl_count_key in _COUNT_TYPE_KEYS else 0
    count_type = st.selectbox("count_type", _COUNT_TYPES, index=count_type_idx, key="count_type_sel")

    goal_count = st.number_input("goal_count", min_value=1, value=tpl.get("goal_count", 1), key="goal_count_input")

    # reset_type: 템플릿 기본값 선택
    tpl_reset = tpl["reset_type"]
    tpl_reset_key = tpl_reset.replace("QUEST_RESET_TYPE_", "")
    reset_type_idx = _RESET_TYPE_KEYS.index(tpl_reset_key) if tpl_reset_key in _RESET_TYPE_KEYS else 0
    reset_type = st.selectbox("reset_type", _RESET_TYPES, index=reset_type_idx, key="reset_type_sel")

    st.divider()

    # --- GoalType ---
    st.subheader("GoalType")
    goal_opts = [f"{g['key']} — {g['label']}" for g in GOAL_TYPES]
    goal_sel = st.selectbox("GoalType", goal_opts, key="goal_type_sel")
    goal_def = GOAL_TYPES[goal_opts.index(goal_sel)]
    goal_params = render_param_fields(goal_def["params"], "goal", items_list, dialog_groups)

    st.divider()

    # --- 조건 (최대 3개) ---
    st.subheader("조건")
    if "condition_count" not in st.session_state:
        st.session_state.condition_count = 1

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("+ 조건 추가", key="add_cond_btn") and st.session_state.condition_count < 3:
            st.session_state.condition_count += 1

    cond_results = []
    cond_opts = [f"{c['key']} — {c['label']}" if c["key"] else c["label"] for c in CONDITIONS]
    for ci in range(st.session_state.condition_count):
        with st.expander(f"조건 {ci + 1}", expanded=True):
            cond_sel = st.selectbox(
                "",
                cond_opts,
                key=f"cond_{ci}_key",
                label_visibility="collapsed",
            )
            cond_def = CONDITIONS[cond_opts.index(cond_sel)]
            cond_ps = render_param_fields(cond_def["params"], f"cond_{ci}", items_list, dialog_groups)
            # 최대 2 param slot 패딩
            while len(cond_ps) < 2:
                cond_ps.append(None)
            cond_results.append((cond_def["key"], cond_ps[0], cond_ps[1]))

    st.divider()

    # --- 보상 ---
    st.subheader("보상")
    item_opts = [f"{it['id']}: {it['name']} ({it['category']})" for it in items_list]
    item_sel = st.selectbox("보상 아이템", ["(선택 안함)"] + item_opts, key="reward_item_sel")
    if item_sel != "(선택 안함)":
        reward_id = items_list[item_opts.index(item_sel)]["id"]
    else:
        reward_id = None
    reward_qty = st.number_input("수량", min_value=1, value=1, key="reward_qty_input")

    st.divider()

    # --- 광장 전용 필드 ---
    town_category = None
    town_icon = None
    town_title = None
    town_desc = None

    if tpl["category"] == "QUEST_CATEGORY_TOWN":
        st.subheader("광장 전용 필드")
        town_category = st.selectbox(
            "town_category",
            ["TOWN_CATEGORY_GENERAL", "TOWN_CATEGORY_INGAME"],
            key="town_category_sel",
        )
        town_icon = st.text_input("town_icon", key="town_icon_input")
        town_title = st.text_input("town_title", key="town_title_input")
        town_desc = st.text_area("town_description", height=68, key="town_desc_input")
        st.divider()

    # --- 미리보기 ---
    st.subheader("미리보기")
    preview_data: dict = {
        "^key": auto_key,
        "$filter": filter_val,
        "category": tpl["category"],
        "description": description,
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "count_type": count_type,
        "goal_count": goal_count,
        "reset_type": reset_type,
        "goal_type/type/%key": goal_def["key"],
    }
    if goal_params:
        for idx, gp in enumerate(goal_params, 1):
            if gp is not None:
                preview_data[f"goal_type/type/%param{idx}"] = gp
    if cond_results:
        for ci, (ck, cp1, cp2) in enumerate(cond_results):
            if ck:
                preview_data[f"conditions/{ci}/condition/%key"] = ck
            if cp1 is not None:
                preview_data[f"conditions/{ci}/condition/%param1"] = cp1
            if cp2 is not None:
                preview_data[f"conditions/{ci}/condition/%param2"] = cp2
    if reward_id is not None:
        preview_data["rewards/0/id"] = reward_id
        preview_data["rewards/0/qty"] = reward_qty
    if tpl["category"] == "QUEST_CATEGORY_TOWN":
        if town_category:
            preview_data["town_category"] = town_category
        if town_icon:
            preview_data["town_icon"] = town_icon
        if town_title:
            preview_data["town_title"] = town_title
        if town_desc:
            preview_data["town_description"] = town_desc

    df_preview = pd.DataFrame([{k: str(v) if v is not None else "" for k, v in preview_data.items()}])
    st.dataframe(df_preview, use_container_width=True)

    # --- 추가 버튼 ---
    st.divider()
    if st.button("quests.xlsx에 추가", type="primary", key="append_btn"):
        # 필수 값 검증
        errors = []
        if not auto_key:
            errors.append("^key가 없습니다.")
        if not description:
            errors.append("description을 입력하세요.")
        if errors:
            for e in errors:
                st.error(e)
            return

        # field_values 구성 (None/빈 값 제외)
        field_values: dict = {}

        def _set(k, v):
            if v is not None and v != "":
                field_values[k] = v

        _set("^key", auto_key)
        _set("$filter", filter_val)
        _set("category", tpl["category"])
        _set("description", description)
        _set("start_timestamp", start_ts)
        _set("end_timestamp", end_ts)
        _set("count_type", count_type)
        _set("goal_count", int(goal_count))
        _set("reset_type", reset_type)
        _set("goal_type/type/%key", goal_def["key"])

        if goal_params:
            for idx, gp in enumerate(goal_params, 1):
                _set(f"goal_type/type/%param{idx}", gp)

        for ci, (ck, cp1, cp2) in enumerate(cond_results):
            _set(f"conditions/{ci}/condition/%key", ck)
            _set(f"conditions/{ci}/condition/%param1", cp1)
            _set(f"conditions/{ci}/condition/%param2", cp2)

        if reward_id is not None:
            _set("rewards/0/id", reward_id)
            _set("rewards/0/qty", int(reward_qty))

        if tpl["category"] == "QUEST_CATEGORY_TOWN":
            _set("town_category", town_category)
            _set("town_icon", town_icon)
            _set("town_title", town_title)
            _set("town_description", town_desc)

        try:
            target_row = append_quest_row(quests_path, field_values)
            st.success(f"^key {auto_key} 추가 완료 (Row {target_row})")

            # 상태 갱신: 같은 quest_type 기준으로 다음 키 발급
            st.session_state.existing_keys.add(auto_key)
            st.session_state.auto_key = generate_unique_key(
                st.session_state.existing_keys,
                category=tpl["category"],
                reset_type=tpl["reset_type"],
            )
            st.session_state.auto_key_type = quest_type
            st.session_state.condition_count = 1
            st.cache_data.clear()
            st.rerun()
        except ValueError as e:
            st.error(f"중복 키 오류: {e}")
        except Exception as e:
            st.error(f"추가 실패: {e}")


# ---------------------------------------------------------------------------
# Tab 2: TPL_C 데일리 세트 (parent + child N)
# ---------------------------------------------------------------------------


def _default_daily_children(n: int = 4) -> list[dict]:
    """data_editor 기본 child 행 템플릿."""
    return [
        {
            "^key (auto)": 0,
            "description": "",
            "goal_type_key": "play:need_win",
            "goal_type_param1": "FALSE",
            "goal_count": 1,
            "reward_id": "",
            "qty": 1,
            "delete": False,
        }
        for _ in range(n)
    ]


def render_tab_daily_set(
    quests_path: str,
    items_list: list[dict],
    kw: dict[str, dict[str, str]],
    dialog_groups: list[dict] | None = None,
) -> None:
    """TPL_C: 데일리 parent + child N 을 한 번에 저장.

    parent:
        category=GENERAL, reset_type=DAILY, count_type=HIGHEST,
        goal_type %key=reward_quest:ref_quest_ids,
        goal_type %param1=[]{c1,c2,...} (child ^key 자동 생성, append_daily_set 에서 처리),
        goal_count=N (child 개수, append_daily_set 에서 자동 채움)

    child:
        category=GENERAL, reset_type=DAILY, count_type=SUM,
        goal_type / rewards / conditions 는 각 행에서 편집
    """
    st.title("데일리 세트 (parent + child)")
    st.caption(
        "parent 1건 + child N건 을 한 번에 기입합니다. "
        "parent goal_type/type/%param1 은 child ^key 들로 자동 생성됩니다."
    )

    build_kw = kw.get("build", {})
    ts_kw = kw.get("timestamp", {})

    # --- 공통 필드 ---
    st.subheader("공통 설정 (parent + child 모두 적용)")
    col1, col2 = st.columns(2)
    with col1:
        daily_filter = select_or_paste(
            "$filter", ["$$" + k for k in build_kw.keys()], "daily_filter"
        )
        daily_start = select_or_paste(
            "start_timestamp", ["$$" + k for k in ts_kw.keys()], "daily_start"
        )
        daily_end = select_or_paste(
            "end_timestamp", ["$$" + k for k in ts_kw.keys()], "daily_end"
        )
    with col2:
        st.text_input("category", value="QUEST_CATEGORY_GENERAL", disabled=True, key="daily_cat_disp")
        st.text_input("reset_type", value="QUEST_RESET_TYPE_DAILY", disabled=True, key="daily_rt_disp")

    # R-09: filter 변경 감지 → daily_parent_key session_state 초기화 (key 재제안 반영)
    last_filter = st.session_state.get("_last_daily_filter")
    if last_filter != daily_filter:
        st.session_state["_last_daily_filter"] = daily_filter
        # session_state 에 남아있는 이전 filter 기반 값 제거 → text_input 이 value= 재반영
        if "daily_parent_key" in st.session_state:
            del st.session_state["daily_parent_key"]

    st.divider()

    # --- parent ---
    st.subheader("parent 설정")

    # parent key 제안 (filter+reset_type 기반, filter-scoped)
    existing_by_filter: dict[int, str] | None = None
    try:
        if quests_path and Path(quests_path).exists():
            existing_by_filter = get_existing_keys_by_filter(quests_path)
    except Exception:
        existing_by_filter = None

    suggested_parent = suggest_next_parent_key(
        st.session_state.existing_keys,
        filter_id=daily_filter,
        reset_type="QUEST_RESET_TYPE_DAILY",
        category="QUEST_CATEGORY_GENERAL",
        existing_by_filter=existing_by_filter,
    )

    col_pkey, col_pdesc = st.columns([1, 3])
    with col_pkey:
        parent_key_str = st.text_input(
            "^key (parent, 수정 가능)",
            value=str(suggested_parent),
            key="daily_parent_key",
        )
    with col_pdesc:
        # description 프리셋 selectbox
        desc_preset_p = st.selectbox(
            "parent description 프리셋",
            ["(사용 안함)"] + DESC_PRESETS,
            key="daily_parent_desc_preset",
        )
        if desc_preset_p != "(사용 안함)" and st.button("프리셋 적용", key="daily_parent_apply_preset"):
            st.session_state["daily_parent_desc"] = desc_preset_p
        parent_description = st.text_input(
            "parent description",
            key="daily_parent_desc",
            placeholder="예) 데일리 퀘스트 완료",
        )

    st.divider()

    # --- child 리스트 ---
    st.subheader("child 리스트")

    if "daily_children" not in st.session_state:
        st.session_state.daily_children = _default_daily_children(4)

    col_add, col_reset = st.columns([1, 1])
    with col_add:
        if st.button("+ child 추가", key="daily_add_child"):
            st.session_state.daily_children.append(_default_daily_children(1)[0])
    with col_reset:
        if st.button("리스트 초기화 (4행)", key="daily_reset_children"):
            st.session_state.daily_children = _default_daily_children(4)

    goal_keys = [g["key"] for g in GOAL_TYPES]

    df_children = pd.DataFrame(st.session_state.daily_children)
    edited = st.data_editor(
        df_children,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "^key (auto)": st.column_config.NumberColumn("^key (auto)", disabled=True),
            "description": st.column_config.TextColumn("description", width="large"),
            "goal_type_key": st.column_config.SelectboxColumn("GoalType", options=goal_keys),
            "goal_type_param1": st.column_config.TextColumn("param1"),
            "goal_count": st.column_config.NumberColumn("goal_count", min_value=1, default=1),
            "reward_id": st.column_config.TextColumn("reward_id (items ^key)"),
            "qty": st.column_config.NumberColumn("qty", min_value=1, default=1),
            "delete": st.column_config.CheckboxColumn("삭제", default=False),
        },
        key="daily_children_editor",
    )

    # 삭제 제외한 실제 행
    active_rows = edited[~edited["delete"]].to_dict("records")
    n = len(active_rows)

    # child ^key 자동 발급
    try:
        parent_key_int = int(parent_key_str)
    except ValueError:
        parent_key_int = None

    child_keys: list[int] = []
    if parent_key_int is not None and n > 0:
        child_keys = allocate_child_keys(st.session_state.existing_keys, parent_key_int, n)
    for i, ck in enumerate(child_keys):
        active_rows[i]["^key (auto)"] = ck

    # --- 미리보기 ---
    st.divider()
    st.subheader("미리보기")
    st.caption(
        f"parent ^key={parent_key_int}, child 수={n}, "
        f"parent goal %param1 = []{{ {','.join(str(k) for k in child_keys)} }}"
    )

    preview_rows = []
    if parent_key_int is not None:
        preview_rows.append(
            {
                "^key": parent_key_int,
                "role": "parent",
                "description": parent_description,
                "goal_type/type/%key": "reward_quest:ref_quest_ids",
                "goal_type/type/%param1": "[]{" + ",".join(str(k) for k in child_keys) + "}",
                "count_type": "QUEST_COUNT_TYPE_HIGHEST",
                "goal_count": n,
            }
        )
    for i, row in enumerate(active_rows):
        preview_rows.append(
            {
                "^key": row["^key (auto)"],
                "role": f"child {i + 1}",
                "description": row["description"],
                "goal_type/type/%key": row["goal_type_key"],
                "goal_type/type/%param1": row["goal_type_param1"],
                "count_type": "QUEST_COUNT_TYPE_SUM",
                "goal_count": row["goal_count"],
            }
        )
    if preview_rows:
        st.dataframe(
            pd.DataFrame(preview_rows),
            use_container_width=True,
            hide_index=True,
        )

    # --- 저장 버튼 ---
    st.divider()
    save_disabled = parent_key_int is None or n == 0 or not daily_filter or not parent_description
    help_msgs = []
    if parent_key_int is None:
        help_msgs.append("parent ^key 가 정수여야 합니다.")
    if n == 0:
        help_msgs.append("child 행이 1개 이상 필요합니다.")
    if not daily_filter:
        help_msgs.append("$filter 를 선택해주세요.")
    if not parent_description:
        help_msgs.append("parent description 을 입력해주세요.")

    if help_msgs:
        for m in help_msgs:
            st.warning(m)

    if st.button(
        f"{1 + n}행 일괄 저장 (parent + child {n})",
        type="primary",
        disabled=save_disabled,
        key="daily_save_btn",
    ):
        # parent dict
        parent_row: dict = {
            "^key": parent_key_int,
            "$filter": daily_filter,
            "category": "QUEST_CATEGORY_GENERAL",
            "description": parent_description,
            "start_timestamp": daily_start,
            "end_timestamp": daily_end,
            "reset_type": "QUEST_RESET_TYPE_DAILY",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
            "goal_count": n,
            "goal_type/type/%key": "reward_quest:ref_quest_ids",
            # goal_type/type/%param1 은 append_daily_set 이 child ^key 로 자동 생성
        }

        # child dicts
        child_rows: list[dict] = []
        for i, row in enumerate(active_rows):
            ck = child_keys[i]
            reward_id_raw = row.get("reward_id")
            try:
                reward_id = int(reward_id_raw) if str(reward_id_raw).strip().isdigit() else None
            except (ValueError, TypeError):
                reward_id = None
            child_dict = {
                "^key": ck,
                "$filter": daily_filter,
                "category": "QUEST_CATEGORY_GENERAL",
                "description": row["description"],
                "start_timestamp": daily_start,
                "end_timestamp": daily_end,
                "reset_type": "QUEST_RESET_TYPE_DAILY",
                "count_type": "QUEST_COUNT_TYPE_SUM",
                "goal_count": int(row["goal_count"]) if row["goal_count"] else 1,
                "goal_type/type/%key": row["goal_type_key"] or None,
                "goal_type/type/%param1": row["goal_type_param1"] or None,
            }
            if reward_id is not None:
                child_dict["rewards/0/id"] = reward_id
                child_dict["rewards/0/qty"] = int(row["qty"]) if row["qty"] else 1
            child_rows.append(child_dict)

        try:
            rows_written = append_daily_set(quests_path, parent_row, child_rows)
            st.success(
                f"데일리 세트 저장 완료: parent ^key={parent_key_int}, "
                f"child ^keys={child_keys}, 기입 row={rows_written}"
            )
            # 세션 갱신
            st.session_state.existing_keys.add(parent_key_int)
            st.session_state.existing_keys.update(child_keys)
            st.session_state.daily_children = _default_daily_children(4)
            # R-09: 저장 성공 후 parent 입력 session_state 제거 → 새 값 재제안
            for k in ("daily_parent_desc", "daily_parent_key", "_last_daily_filter"):
                if k in st.session_state:
                    del st.session_state[k]
            st.cache_data.clear()
            st.rerun()
        except ValueError as e:
            st.error(f"저장 실패 (파일 저장 전 검증 실패 — 롤백됨): {e}")
        except Exception as e:
            st.error(f"저장 실패: {e}")


# ---------------------------------------------------------------------------
# Tab 3: 광장 배치 추가
# ---------------------------------------------------------------------------


def render_tab_plaza(quests_path: str, kw: dict[str, dict[str, str]]) -> None:
    st.title("광장 퀘스트 배치 추가")
    st.caption("category=QUEST_CATEGORY_TOWN 퀘스트를 여러 개 한 번에 추가합니다.")

    build_kw = kw.get("build", {})
    ts_kw = kw.get("timestamp", {})

    # --- 공통 설정 ---
    st.subheader("공통 설정 (모든 행에 적용)")

    col1, col2 = st.columns(2)
    with col1:
        batch_filter = select_or_paste("$filter", ["$$" + k for k in build_kw], "batch_filter")
        batch_start = select_or_paste("start_timestamp", ["$$" + k for k in ts_kw], "batch_start")
        batch_end = select_or_paste("end_timestamp", ["$$" + k for k in ts_kw], "batch_end")
    with col2:
        batch_reset = st.selectbox(
            "reset_type",
            _RESET_TYPES,
            key="batch_reset",
        )
        batch_town_cat = st.selectbox(
            "town_category",
            ["TOWN_CATEGORY_GENERAL", "TOWN_CATEGORY_INGAME"],
            key="batch_town_cat",
        )

    st.divider()

    # --- 텍스트 붙여넣기 ---
    st.subheader("퀘스트 텍스트 붙여넣기")
    st.caption("#quest 시트의 quest(B컬럼) 텍스트를 한 줄씩 붙여넣으세요.")
    pasted = st.text_area(
        "",
        height=200,
        key="batch_paste",
        label_visibility="collapsed",
        placeholder="<color=#ffe535>{0}회 전투 승리</color>하기\n...",
    )

    if st.button("텍스트 파싱", type="secondary"):
        if pasted.strip():
            templates = _load_quest_templates(quests_path)
            parsed = parse_quest_texts(pasted, templates)
            st.session_state.batch_rows = parsed
            matched = sum(1 for r in parsed if r["matched"])
            st.info(f"총 {len(parsed)}행 파싱 완료. 템플릿 매칭: {matched}/{len(parsed)}")
        else:
            st.warning("텍스트를 먼저 입력해주세요.")

    # --- 편집 테이블 ---
    if st.session_state.get("batch_rows"):
        st.subheader("파싱 결과 편집")

        batch_rows = st.session_state.batch_rows

        goal_keys = [g["key"] for g in GOAL_TYPES]

        df = pd.DataFrame(batch_rows)[
            ["description", "town_description", "goal_count", "goal_type_key", "goal_type_param1", "reward_id", "qty", "delete"]
        ]

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "description": st.column_config.TextColumn("description", width="large"),
                "town_description": st.column_config.TextColumn("town_description", width="large"),
                "goal_count": st.column_config.NumberColumn("goal_count", min_value=1, default=1),
                "goal_type_key": st.column_config.SelectboxColumn("GoalType", options=goal_keys),
                "goal_type_param1": st.column_config.TextColumn("param1"),
                "reward_id": st.column_config.TextColumn("reward_id", help="items ^key 입력"),
                "qty": st.column_config.NumberColumn("qty", min_value=1, default=1),
                "delete": st.column_config.CheckboxColumn("삭제", default=False),
            },
        )

        # 삭제 체크된 행 제외
        valid_rows = edited_df[~edited_df["delete"]].to_dict("records")

        # 미리보기
        st.caption(f"총 {len(valid_rows)}개 행 추가 예정")

        # 전체 추가 버튼
        if st.button(f"{len(valid_rows)}개 전체 추가", type="primary", disabled=(not valid_rows)):
            success_count = 0
            fail_msgs = []

            for row in valid_rows:
                # 광장 배치는 항상 TOWN 카테고리
                new_key = generate_unique_key(
                    st.session_state.existing_keys,
                    category="QUEST_CATEGORY_TOWN",
                    reset_type=batch_reset,
                )

                fv = {
                    "^key": new_key,
                    "$filter": batch_filter,
                    "category": "QUEST_CATEGORY_TOWN",
                    "description": row["description"],
                    "start_timestamp": batch_start,
                    "end_timestamp": batch_end,
                    "reset_type": batch_reset,
                    "town_category": batch_town_cat,
                    "town_description": row["town_description"] or None,
                    "count_type": "QUEST_COUNT_TYPE_SUM",
                    "goal_count": int(row["goal_count"]) if row["goal_count"] else 1,
                    "goal_type/type/%key": row["goal_type_key"] or None,
                    "goal_type/type/%param1": row["goal_type_param1"] or None,
                    "rewards/0/id": int(row["reward_id"]) if str(row["reward_id"]).isdigit() else None,
                    "rewards/0/qty": int(row["qty"]) if row["qty"] else 1,
                }

                try:
                    append_quest_row(quests_path, fv)
                    st.session_state.existing_keys.add(new_key)
                    success_count += 1
                except Exception as e:
                    fail_msgs.append(f"^key {new_key}: {e}")

            if success_count:
                st.success(f"{success_count}개 퀘스트 추가 완료")
            if fail_msgs:
                st.error("\n".join(fail_msgs))

            # 배치 초기화: auto_key는 단건 탭 기준이라 다음 로드 시 재발급되도록 None
            st.session_state.batch_rows = []
            st.session_state.auto_key = None
            st.session_state.auto_key_type = None
            st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    config_path = _get_config_path()
    cfg = load_config(config_path)

    quests_path = cfg.get("quests_path", "")
    items_path = cfg.get("items_path", "")
    keywords_path = cfg.get("keywords_path", "")
    dialog_groups_path = cfg.get("dialog_groups_path", "")

    # -- session_state 초기화 --
    # auto_key는 quest_type에 따라 range가 달라지므로, render_tab_add에서 lazy하게 발급.
    if "existing_keys" not in st.session_state:
        if quests_path and Path(quests_path).exists():
            st.session_state.existing_keys = get_existing_keys(quests_path)
        else:
            st.session_state.existing_keys = set()
    if "auto_key" not in st.session_state:
        st.session_state.auto_key = None
    if "auto_key_type" not in st.session_state:
        st.session_state.auto_key_type = None
    if "condition_count" not in st.session_state:
        st.session_state.condition_count = 1
    if "batch_rows" not in st.session_state:
        st.session_state.batch_rows = []
    # NOTE: daily_children 은 render_tab_daily_set 에서만 초기화 (이중 초기화 제거, R-04)

    # -- Sidebar: file paths --
    with st.sidebar:
        st.title("Quest Tool")
        st.caption(f"Config: `{Path(config_path).name}`")

        st.subheader("File Paths")
        st.code(
            f"quests:        {quests_path}\n"
            f"items:         {items_path}\n"
            f"keywords:      {keywords_path}\n"
            f"dialog_groups: {dialog_groups_path}",
            language=None,
        )

        if st.button("Cache Refresh", use_container_width=True):
            st.cache_data.clear()
            if quests_path and Path(quests_path).exists():
                st.session_state.existing_keys = get_existing_keys(quests_path)
            # auto_key는 render_tab_add 진입 시 현재 quest_type 기준으로 재발급
            st.session_state.auto_key = None
            st.session_state.auto_key_type = None
            st.rerun()

        st.divider()

        # -- File load status --
        st.subheader("Load Status")

        if quests_path and Path(quests_path).exists():
            try:
                header_map = _get_header_map(quests_path)
                st.write(f"quests.xlsx: (header {len(header_map)})")
            except Exception as e:
                st.write(f"quests.xlsx: {e}")
        else:
            st.write("quests.xlsx: (file not found)")

        if items_path and Path(items_path).exists():
            try:
                items = _load_items(items_path)
                st.write(f"items.xlsx: ({len(items)} items)")
            except Exception as e:
                st.write(f"items.xlsx: {e}")
        else:
            st.write("items.xlsx: (file not found)")

        if keywords_path and Path(keywords_path).exists():
            try:
                kw = _load_keywords(keywords_path)
                build_cnt = len(kw.get("build", {}))
                ts_cnt = len(kw.get("timestamp", {}))
                st.write(f"keywords.xlsx: (build {build_cnt}, timestamp {ts_cnt})")
            except Exception as e:
                st.write(f"keywords.xlsx: {e}")
        else:
            st.write("keywords.xlsx: (file not found)")

        if quests_path and Path(quests_path).exists():
            try:
                templates = _load_quest_templates(quests_path)
                st.write(f"#quest templates: {len(templates)}")
            except Exception as e:
                st.write(f"#quest templates: {e}")
        else:
            st.write("#quest templates: (file not found)")

        if dialog_groups_path and Path(dialog_groups_path).exists():
            try:
                dgs = _load_dialog_groups(dialog_groups_path)
                st.write(f"dialog_groups.xlsx: ({len(dgs)} groups)")
            except Exception as e:
                st.write(f"dialog_groups.xlsx: {e}")
        else:
            st.write("dialog_groups.xlsx: (file not found or not set)")

    # -- Guard: required files must exist --
    missing = []
    if not quests_path:
        missing.append("quests_path is empty in config")
    elif not Path(quests_path).exists():
        missing.append(f"quests file not found: {quests_path}")

    if not items_path:
        missing.append("items_path is empty in config")
    elif not Path(items_path).exists():
        missing.append(f"items file not found: {items_path}")

    if not keywords_path:
        missing.append("keywords_path is empty in config")
    elif not Path(keywords_path).exists():
        missing.append(f"keywords file not found: {keywords_path}")

    if missing:
        for msg in missing:
            st.error(msg)
        st.stop()

    # 데이터 로드
    items_list = _load_items(items_path)
    kw = _load_keywords(keywords_path)

    # dialog_groups 는 선택 — 없으면 dialog_picker 가 free_text 로 폴백
    dialog_groups: list[dict] = []
    if dialog_groups_path and Path(dialog_groups_path).exists():
        try:
            dialog_groups = _load_dialog_groups(dialog_groups_path)
        except Exception as e:
            st.warning(f"dialog_groups 로드 실패: {e}. finish_town_dialog 는 직접 입력으로 폴백.")

    # -- Tabs --
    tab_add, tab_daily, tab_plaza = st.tabs(["단건 추가", "데일리 세트", "광장 배치"])

    with tab_add:
        render_tab_add(quests_path, items_list, kw, dialog_groups)

    with tab_daily:
        render_tab_daily_set(quests_path, items_list, kw, dialog_groups)

    with tab_plaza:
        render_tab_plaza(quests_path, kw)


if __name__ == "__main__" or True:
    main()

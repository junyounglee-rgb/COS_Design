"""Quest Tool - Streamlit app (STEP 3: 단건 추가 UI)."""
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from config import load_config
from quest_writer import (
    DESC_PRESETS,
    allocate_child_keys,
    append_daily_set,
    append_nday_mission_event,
    append_quest_row,
    default_parent_desc,
    generate_unique_key,
    get_existing_event_keys,
    get_existing_keys,
    get_existing_keys_by_filter,
    get_header_map,
    load_dialog_groups,
    load_goal_types_yaml,
    load_item_categories,
    load_items,
    load_keywords,
    load_nday_mission_events,
    load_quest_templates,
    parse_quest_texts,
    save_goal_types_yaml,
    suggest_next_event_key,
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
    "데일리 미션": {
        # parent+child 통합 타입. render_daily_mission_form 으로 분기.
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_DAILY",
        "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        "goal_count": 5,
        "is_daily_mission": True,
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

# GOAL_TYPES: quest_tool/goal_types.yaml 에서 로드. 파일 부재/오류 시 quest_writer._HARDCODED_GOAL_TYPES 폴백.
GOAL_TYPES = load_goal_types_yaml()

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
def _load_item_categories(items_path: str) -> list[dict]:
    return load_item_categories(items_path)


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


@st.cache_data
def _load_nday_events(path: str) -> list[dict]:
    return load_nday_mission_events(path)


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
    nday_mission_events_path: str = "",
) -> None:
    st.title("퀘스트 추가")

    build_kw = kw.get("build", {})
    ts_kw = kw.get("timestamp", {})
    dialog_groups = dialog_groups or []

    # --- 퀘스트 타입 ---
    quest_type = st.selectbox("퀘스트 타입", list(QUEST_TYPES.keys()), key="quest_type_sel")
    tpl = QUEST_TYPES[quest_type]

    # --- 데일리 미션 분기 (parent + child N 통합 폼) ---
    if tpl.get("is_daily_mission"):
        render_daily_mission_form(quests_path, items_list, kw, dialog_groups, nday_mission_events_path=nday_mission_events_path)
        return

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
# 데일리 미션 폼 (Tab 1 내에서 호출, parent + child N 통합)
# ---------------------------------------------------------------------------


def _default_child() -> dict:
    """개별 child 초기값."""
    return {
        "description": "",
        "goal_type_key": "play:need_win",
        "goal_type_param1": "FALSE",
        "goal_count": 1,
        "reward_category": "",
        "reward_id": 0,
        "reward_qty": 1,
    }


def _default_day() -> dict:
    """day(일자) 초기값."""
    return {
        "parent_description": "",
        "event_description": "",
        "event_day_description": "",
        "children": [],
    }


def _resize_children(current: list[dict], target_n: int) -> list[dict]:
    """child 리스트 길이를 target_n 으로 맞춤. 기존 값 보존, 부족 시 append, 초과 시 truncate."""
    cur_n = len(current)
    if cur_n == target_n:
        return current
    if cur_n < target_n:
        return current + [_default_child() for _ in range(target_n - cur_n)]
    return current[:target_n]


def _resize_days(current: list[dict], target_n: int, n_children: int) -> list[dict]:
    """dm_days 리스트 길이를 target_n, 각 day 의 children 길이를 n_children 으로 맞춤."""
    cur_n = len(current)
    if cur_n < target_n:
        current = current + [_default_day() for _ in range(target_n - cur_n)]
    elif cur_n > target_n:
        current = current[:target_n]
    for d in current:
        d["children"] = _resize_children(d.get("children", []), n_children)
    return current


def _find_items_path_from_config() -> str:
    """items_path 를 config 에서 로드 (cache 통해)."""
    try:
        cfg = load_config(_get_config_path())
        return cfg.get("items_path", "")
    except Exception:
        return ""


def render_daily_mission_form(
    quests_path: str,
    items_list: list[dict],
    kw: dict[str, dict[str, str]],
    dialog_groups: list[dict] | None = None,
    nday_mission_events_path: str = "",
) -> None:
    """데일리 미션 N일치 통합 폼.

    1회 저장 = N_DAYS × (parent 1건 + child N_CHILDREN건) + N_DAYS × (events + events.day)
    이벤트 그룹은 자동 할당 (기존 max_group + 100).
    parent 복사 기능으로 "N일차" 문자열을 해당 일차로 자동 치환.
    """
    dialog_groups = dialog_groups or []
    st.divider()
    st.subheader("데일리 미션 (N일치 parent+child 통합)")
    st.caption(
        "N_DAYS × (parent 1 + child N_CHILDREN) + N_DAYS × (events + events.day) 을 한 번에 저장. "
        "count_type / reset_type / goal_type %key 는 강제. 이벤트 그룹은 100단위 자동 할당."
    )

    build_kw = kw.get("build", {})
    ts_kw = kw.get("timestamp", {})

    # --- ItemCategory 로드 ---
    items_path = _find_items_path_from_config()
    try:
        item_categories = _load_item_categories(items_path) if items_path else []
    except Exception:
        item_categories = []
    category_keys = [c["key"] for c in item_categories]

    # --- 공통 필드 ---
    col1, col2 = st.columns(2)
    with col1:
        daily_filter = select_or_paste(
            "$filter", ["$$" + k for k in build_kw.keys()], "dm_filter"
        )
        daily_start = select_or_paste(
            "start_timestamp", ["$$" + k for k in ts_kw.keys()], "dm_start"
        )
        daily_end = select_or_paste(
            "end_timestamp", ["$$" + k for k in ts_kw.keys()], "dm_end"
        )
    with col2:
        st.text_input("category (자동)", value="QUEST_CATEGORY_GENERAL", disabled=True, key="dm_cat_disp")
        st.text_input("reset_type (자동)", value="QUEST_RESET_TYPE_DAILY", disabled=True, key="dm_rt_disp")
        st.text_input(
            "count_type (자동, parent=HIGHEST / child=SUM)",
            value="QUEST_COUNT_TYPE_HIGHEST",
            disabled=True,
            key="dm_ct_disp",
        )

    st.divider()

    # --- N_DAYS / N_CHILDREN ---
    col_nd, col_nc = st.columns(2)
    with col_nd:
        n_days = int(st.number_input(
            "미션 일수 (N_DAYS)",
            min_value=1,
            max_value=30,
            value=int(st.session_state.get("dm_n_days", 1)),
            step=1,
            key="dm_n_days",
            help="1=단일일, 5=5일치 parent 5개, 14=HELSINKI_3 같은 장기",
        ))
    with col_nc:
        n_children = int(st.number_input(
            "하루 child 수 (N_CHILDREN)",
            min_value=1,
            max_value=20,
            value=int(st.session_state.get("dm_n_children", 5)),
            step=1,
            key="dm_n_children",
            help="모든 day 동일 적용. day별 가변은 미지원.",
        ))

    # --- 이벤트 그룹 자동 계산 ---
    existing_event_keys: set[int] = set()
    if nday_mission_events_path and Path(nday_mission_events_path).exists():
        try:
            existing_event_keys = get_existing_event_keys(nday_mission_events_path)
        except Exception:
            existing_event_keys = set()

    used_groups = {(ek // 100) * 100 for ek in existing_event_keys if ek >= 100}
    group_base = (max(used_groups) + 100) if used_groups else 100
    st.text_input(
        "이벤트 그룹 (자동, 100단위)",
        value=str(group_base),
        disabled=True,
        key="dm_group_disp",
        help=f"기존 사용 그룹: {sorted(used_groups) if used_groups else '(없음)'} → 신규: {group_base}",
    )

    # --- 첫 parent ^key 자동 제안 ---
    existing_by_filter: dict[int, str] | None = None
    try:
        if quests_path and Path(quests_path).exists():
            existing_by_filter = get_existing_keys_by_filter(quests_path)
    except Exception:
        existing_by_filter = None

    suggested_first_parent = suggest_next_parent_key(
        st.session_state.existing_keys,
        filter_id=daily_filter,
        reset_type="QUEST_RESET_TYPE_DAILY",
        category="QUEST_CATEGORY_GENERAL",
        existing_by_filter=existing_by_filter,
    )

    first_parent_str = st.text_input(
        "^key (첫 parent, 수정 가능; 이후 +10 씩 자동)",
        value=str(suggested_first_parent),
        key="dm_first_parent_key",
    )
    try:
        first_parent_int = int(first_parent_str)
    except ValueError:
        first_parent_int = None

    # --- parent keys / event keys 행렬 ---
    parent_keys: list[int] = (
        [first_parent_int + 10 * i for i in range(n_days)]
        if first_parent_int is not None else []
    )
    event_keys: list[int] = [group_base + 1 + i for i in range(n_days)]

    # --- child keys 행렬 (중첩 방지) ---
    child_keys_matrix: list[list[int]] = []
    if parent_keys:
        existing_accum = set(st.session_state.existing_keys)
        for d in range(n_days):
            existing_accum.add(parent_keys[d])
            cks = allocate_child_keys(existing_accum, parent_keys[d], n_children)
            existing_accum.update(cks)
            child_keys_matrix.append(cks)

    # --- dm_days 세션 상태 ---
    if "dm_days" not in st.session_state:
        st.session_state.dm_days = []
    st.session_state.dm_days = _resize_days(
        st.session_state.dm_days, n_days, n_children
    )

    # mission_active_days = 0 고정 (실 데이터 패턴: 데일리 미션 이벤트는 항상 단일일)
    mission_active_days = 0

    st.divider()

    goal_opts = [f"{g['key']} — {g['label']}" for g in GOAL_TYPES]
    goal_key_index = {g["key"]: i for i, g in enumerate(GOAL_TYPES)}

    # --- day 별 expander ---
    for d in range(n_days):
        day = st.session_state.dm_days[d]
        pk = parent_keys[d] if d < len(parent_keys) else "?"
        ek = event_keys[d]
        cks = child_keys_matrix[d] if d < len(child_keys_matrix) else []

        with st.expander(
            f"{d + 1}일차   parent ^key={pk}  /  event ^key={ek}",
            expanded=(d == 0),
        ):
            # --- 복사 기능 (N_DAYS > 1 일 때만) ---
            if n_days > 1:
                other_days = [i for i in range(n_days) if i != d]
                src_opts = ["(선택 안함)"] + [f"{i + 1}일차" for i in other_days]
                col_src, col_btn = st.columns([2, 1])
                with col_src:
                    src_sel = st.selectbox(
                        "복사할 날짜 (source)",
                        src_opts,
                        index=0,
                        key=f"dm_d{d}_copysrc",
                    )
                with col_btn:
                    st.write("")  # 정렬용 공백
                    if st.button(
                        "복사 적용",
                        key=f"dm_d{d}_copybtn",
                        disabled=(src_sel == "(선택 안함)"),
                    ):
                        real_src = other_days[src_opts.index(src_sel) - 1]
                        src_day = st.session_state.dm_days[real_src]

                        def _sub(s: str) -> str:
                            return re.sub(r"\d+일차", f"{d + 1}일차", s or "")

                        day["parent_description"] = _sub(src_day["parent_description"])
                        day["event_description"] = _sub(src_day["event_description"])
                        day["event_day_description"] = _sub(src_day["event_day_description"])
                        day["children"] = [
                            {**c, "description": _sub(c.get("description", ""))}
                            for c in src_day["children"]
                        ]
                        # text_input 키 값도 초기화 필요 (session_state 직접 삭제)
                        for i in range(n_children):
                            for suffix in ("desc", "gcnt", "gkey_sel", "rcat", "rid", "rqty"):
                                k = f"dm_d{d}_c{i}_{suffix}"
                                if k in st.session_state:
                                    del st.session_state[k]
                        for suffix in ("pdesc", "edesc", "ddesc"):
                            k = f"dm_d{d}_{suffix}"
                            if k in st.session_state:
                                del st.session_state[k]
                        st.success(f"{real_src + 1}일차 → {d + 1}일차 복사 완료")
                        st.rerun()
                st.divider()

            # --- parent description ---
            day["parent_description"] = st.text_input(
                f"parent description ({d + 1}일차)",
                value=day.get("parent_description", ""),
                key=f"dm_d{d}_pdesc",
                placeholder=f"예) [데일리미션]{d + 1}일차 전체 퀘스트 완료 보상",
            )

            # --- event descriptions ---
            col_ed, col_dd = st.columns(2)
            with col_ed:
                day["event_description"] = st.text_input(
                    "events.description (UI용)",
                    value=day.get("event_description", ""),
                    key=f"dm_d{d}_edesc",
                    placeholder="예) 가정의 달! 스페셜 미션",
                )
            with col_dd:
                day["event_day_description"] = st.text_input(
                    "events.day.description (UI용 일차명)",
                    value=day.get("event_day_description", ""),
                    key=f"dm_d{d}_ddesc",
                    placeholder=f"예) 데일리 미션 {d + 1}일차",
                )

            st.divider()

            # --- children 입력 ---
            for i in range(n_children):
                ck = cks[i] if i < len(cks) else "?"
                child = day["children"][i]
                with st.expander(
                    f"  child {i + 1}   ^key={ck}",
                    expanded=False,
                ):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        child["description"] = st.text_input(
                            "description",
                            value=child.get("description", ""),
                            key=f"dm_d{d}_c{i}_desc",
                            placeholder=f"예) {d + 1}일차(승리 4회)",
                        )
                    with c2:
                        child["goal_count"] = int(st.number_input(
                            "goal_count",
                            min_value=1,
                            value=int(child.get("goal_count", 1)),
                            step=1,
                            key=f"dm_d{d}_c{i}_gcnt",
                        ))

                    cur_gkey = child.get("goal_type_key", "play:need_win")
                    default_idx = goal_key_index.get(cur_gkey, 0)
                    gsel = st.selectbox(
                        "goal_type/%key",
                        goal_opts,
                        index=default_idx,
                        key=f"dm_d{d}_c{i}_gkey_sel",
                    )
                    gdef = GOAL_TYPES[goal_opts.index(gsel)]
                    child["goal_type_key"] = gdef["key"]
                    param_vals = render_param_fields(
                        gdef.get("params", []) or [],
                        f"dm_d{d}_c{i}_gparam",
                        items_list,
                        dialog_groups,
                    )
                    child["goal_type_param1"] = param_vals[0] if param_vals else None

                    rcat_col, rid_col, rqty_col = st.columns([1, 2, 1])
                    with rcat_col:
                        cat_options = ["(선택)"] + category_keys
                        cur_cat = child.get("reward_category", "")
                        cat_idx = cat_options.index(cur_cat) if cur_cat in cat_options else 0
                        sel_cat = st.selectbox(
                            "reward_category",
                            cat_options,
                            index=cat_idx,
                            key=f"dm_d{d}_c{i}_rcat",
                        )
                        child["reward_category"] = "" if sel_cat == "(선택)" else sel_cat

                    with rid_col:
                        if child["reward_category"]:
                            filtered = [it for it in items_list if it.get("category") == child["reward_category"]]
                        else:
                            filtered = list(items_list)
                        if filtered:
                            fmt = lambda it: f"{it['id']} | {it['name']} | {it.get('filter','')}"
                            id_opts = ["(선택 안함)"] + [fmt(it) for it in filtered]
                            cur_rid = int(child.get("reward_id") or 0)
                            cur_label = "(선택 안함)"
                            for it in filtered:
                                if it["id"] == cur_rid:
                                    cur_label = fmt(it)
                                    break
                            try:
                                cur_idx = id_opts.index(cur_label)
                            except ValueError:
                                cur_idx = 0
                            sel_id = st.selectbox(
                                "reward_id",
                                id_opts,
                                index=cur_idx,
                                key=f"dm_d{d}_c{i}_rid",
                            )
                            if sel_id == "(선택 안함)":
                                child["reward_id"] = 0
                            else:
                                idx_in_filtered = id_opts.index(sel_id) - 1
                                child["reward_id"] = int(filtered[idx_in_filtered]["id"])
                        else:
                            st.write("(해당 category 에 items 없음)")
                            child["reward_id"] = 0

                    with rqty_col:
                        child["reward_qty"] = int(st.number_input(
                            "reward_qty",
                            min_value=1,
                            value=int(child.get("reward_qty", 1) or 1),
                            step=1,
                            key=f"dm_d{d}_c{i}_rqty",
                        ))

    # --- 미리보기 ---
    st.divider()
    st.subheader("미리보기")
    total_quest_rows = n_days * (1 + n_children)
    st.caption(
        f"parent_keys={parent_keys}, event_keys={event_keys}, "
        f"quests 총 {total_quest_rows} 행, nday events {n_days} 행 + events.day {n_days} 행"
    )

    preview_rows: list[dict] = []
    for d in range(n_days):
        if d >= len(parent_keys):
            continue
        pk = parent_keys[d]
        ek = event_keys[d]
        cks = child_keys_matrix[d] if d < len(child_keys_matrix) else []
        day = st.session_state.dm_days[d]
        preview_rows.append({
            "^key": pk,
            "role": f"day{d + 1} parent",
            "description": day.get("parent_description", ""),
            "goal_type/type/%key": "reward_quest:ref_quest_ids",
            "goal_type/type/%param1": "[]{" + ",".join(str(k) for k in cks) + "}",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
            "goal_count": n_children,
            "event_^key": ek,
        })
        for i in range(n_children):
            ck = cks[i] if i < len(cks) else None
            c = day["children"][i]
            preview_rows.append({
                "^key": ck,
                "role": f"day{d + 1} child{i + 1}",
                "description": c.get("description", ""),
                "goal_type/type/%key": c.get("goal_type_key", ""),
                "goal_type/type/%param1": c.get("goal_type_param1", ""),
                "count_type": "QUEST_COUNT_TYPE_SUM",
                "goal_count": c.get("goal_count", 1),
                "event_^key": ek,
            })
    if preview_rows:
        st.dataframe(
            pd.DataFrame(preview_rows),
            use_container_width=True,
            hide_index=True,
        )

    # --- 저장 ---
    st.divider()
    save_disabled = (
        first_parent_int is None
        or n_days == 0
        or n_children == 0
        or not daily_filter
        or any(not d.get("parent_description") for d in st.session_state.dm_days)
        or any(not d.get("event_description") for d in st.session_state.dm_days)
    )
    warnings = []
    if first_parent_int is None:
        warnings.append("첫 parent ^key 가 정수여야 합니다.")
    if not daily_filter:
        warnings.append("$filter 를 선택해주세요.")
    for d, day in enumerate(st.session_state.dm_days):
        if not day.get("parent_description"):
            warnings.append(f"{d + 1}일차 parent description 이 비어 있습니다.")
        if not day.get("event_description"):
            warnings.append(f"{d + 1}일차 events.description 이 비어 있습니다.")
    for m in warnings:
        st.warning(m)

    btn_label = (
        f"{total_quest_rows}행 일괄 저장 "
        f"(N_DAYS={n_days} × (parent + child {n_children}))"
        f" + nday events {n_days}건"
    )

    if st.button(btn_label, type="primary", disabled=save_disabled, key="dm_save_btn"):
        saved_days: list[dict] = []
        failed_nday_days: list[int] = []
        aborted_at: int | None = None

        for d in range(n_days):
            day = st.session_state.dm_days[d]
            pk = parent_keys[d]
            ek = event_keys[d]
            cks = child_keys_matrix[d]

            parent_row: dict = {
                "^key": pk,
                "$filter": daily_filter,
                "category": "QUEST_CATEGORY_GENERAL",
                "description": day["parent_description"],
                "start_timestamp": daily_start,
                "end_timestamp": daily_end,
                "reset_type": "QUEST_RESET_TYPE_DAILY",
                "count_type": "QUEST_COUNT_TYPE_HIGHEST",
                "goal_count": n_children,
                "goal_type/type/%key": "reward_quest:ref_quest_ids",
            }

            child_rows: list[dict] = []
            for i in range(n_children):
                c = day["children"][i]
                ck = cks[i]
                cd: dict = {
                    "^key": ck,
                    "$filter": daily_filter,
                    "category": "QUEST_CATEGORY_GENERAL",
                    "description": c.get("description", ""),
                    "start_timestamp": daily_start,
                    "end_timestamp": daily_end,
                    "reset_type": "QUEST_RESET_TYPE_DAILY",
                    "count_type": "QUEST_COUNT_TYPE_SUM",
                    "goal_count": int(c.get("goal_count", 1) or 1),
                    "goal_type/type/%key": c.get("goal_type_key") or None,
                }
                p1 = c.get("goal_type_param1")
                if p1:
                    cd["goal_type/type/%param1"] = p1
                rid = int(c.get("reward_id") or 0)
                if rid > 0:
                    cd["rewards/0/id"] = rid
                    cd["rewards/0/qty"] = int(c.get("reward_qty", 1) or 1)
                child_rows.append(cd)

            # --- quests 저장 ---
            try:
                append_daily_set(quests_path, parent_row, child_rows)
            except ValueError as e:
                st.error(f"day {d + 1} quests 저장 실패 (검증 실패 — 이후 중단): {e}")
                aborted_at = d + 1
                break
            except Exception as e:
                st.error(f"day {d + 1} quests 저장 실패 (이후 중단): {e}")
                aborted_at = d + 1
                break

            # --- nday 저장 ---
            event_dict_save = {
                "^key": ek,
                "description": day["event_description"],
                "start_timestamp": daily_start,
                "end_timestamp": daily_end,
                "mission_active_days": mission_active_days,
            }
            event_day_dict_save = {
                "^key": ek,
                "day": 1,
                "description": day["event_day_description"],
                "quest_ids": "[]{" + ",".join(str(k) for k in cks) + "}",
                "finish_quest_id": pk,
            }
            nday_ok = True
            try:
                append_nday_mission_event(
                    nday_mission_events_path,
                    event_dict_save,
                    event_day_dict_save,
                )
            except Exception as e:
                st.warning(
                    f"day {d + 1} nday_mission_events 저장 실패 (quests 는 이미 저장됨): {e}"
                )
                nday_ok = False
                failed_nday_days.append(d + 1)

            saved_days.append({"day": d + 1, "pk": pk, "ek": ek, "cks": cks, "nday_ok": nday_ok})
            st.session_state.existing_keys.add(pk)
            st.session_state.existing_keys.update(cks)

        # --- 결과 요약 ---
        if saved_days:
            st.success(
                f"저장 완료: {len(saved_days)}/{n_days} day. "
                f"parent ^keys={[s['pk'] for s in saved_days]}, "
                f"event ^keys={[s['ek'] for s in saved_days]}"
                + (f" | nday 실패 day: {failed_nday_days}" if failed_nday_days else "")
                + (f" | day {aborted_at} 에서 중단" if aborted_at else "")
            )

        # 전량 성공 시에만 입력 초기화
        if len(saved_days) == n_days and not failed_nday_days and aborted_at is None:
            st.session_state.dm_days = []
            for k in ("dm_first_parent_key", "dm_n_days", "dm_n_children"):
                if k in st.session_state:
                    del st.session_state[k]
            # day-scoped 키도 정리
            for k in list(st.session_state.keys()):
                if k.startswith("dm_d") or k.startswith("_last_dm_"):
                    del st.session_state[k]
            st.cache_data.clear()
            st.rerun()


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
    nday_mission_events_path = cfg.get("nday_mission_events_path", "")

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
    # NOTE: dm_children 은 render_daily_mission_form 에서만 초기화 (이중 초기화 제거, R-04)

    # -- Sidebar: file paths --
    with st.sidebar:
        st.title("Quest Tool")
        st.caption(f"Config: `{Path(config_path).name}`")

        st.subheader("File Paths")
        st.code(
            f"quests:        {quests_path}\n"
            f"items:         {items_path}\n"
            f"keywords:      {keywords_path}\n"
            f"dialog_groups: {dialog_groups_path}\n"
            f"nday_events:   {nday_mission_events_path}",
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

        if nday_mission_events_path and Path(nday_mission_events_path).exists():
            try:
                nday_events = _load_nday_events(nday_mission_events_path)
                st.write(f"nday_mission_events.xlsx: ({len(nday_events)} events)")
            except Exception as e:
                st.write(f"nday_mission_events.xlsx: {e}")
        else:
            st.write("nday_mission_events.xlsx: (file not found or not set)")

        st.divider()

        # -- GoalType 편집기 --
        with st.expander("⚙️ GoalType / Param 편집", expanded=False):
            st.caption(
                "goal_types.yaml 에 저장. 저장 후 앱 재시작 시 반영됩니다.\n"
                "param_options 는 세미콜론(;) 으로 구분. free_text=TRUE 면 options 무시하고 자유입력."
            )

            current_gt = load_goal_types_yaml()
            gt_rows = []
            for entry in current_gt:
                params = entry.get("params", []) or []
                if params:
                    p = params[0]
                    gt_rows.append(
                        {
                            "key": entry.get("key", ""),
                            "label": entry.get("label", ""),
                            "param_label": p.get("label", ""),
                            "param_options": ";".join(str(o) for o in (p.get("options", []) or [])),
                            "free_text": bool(p.get("free_text", False)),
                            "item_picker": bool(p.get("item_picker", False)),
                            "dialog_picker": bool(p.get("dialog_picker", False)),
                        }
                    )
                else:
                    gt_rows.append(
                        {
                            "key": entry.get("key", ""),
                            "label": entry.get("label", ""),
                            "param_label": "",
                            "param_options": "",
                            "free_text": False,
                            "item_picker": False,
                            "dialog_picker": False,
                        }
                    )

            gt_df = pd.DataFrame(gt_rows)
            edited_gt = st.data_editor(
                gt_df,
                num_rows="dynamic",
                use_container_width=True,
                key="goal_types_editor",
                column_config={
                    "key": st.column_config.TextColumn("key", help="goal_type 식별자 (예: daily_login, play:need_win)"),
                    "label": st.column_config.TextColumn("label", help="UI 표시 이름"),
                    "param_label": st.column_config.TextColumn("param_label", help="파라미터 라벨 (있을 때만)"),
                    "param_options": st.column_config.TextColumn(
                        "param_options (;구분)", help="고정 옵션 리스트. 세미콜론으로 구분"
                    ),
                    "free_text": st.column_config.CheckboxColumn("free_text", help="자유 입력 여부"),
                    "item_picker": st.column_config.CheckboxColumn("item_picker", help="items.xlsx 피커"),
                    "dialog_picker": st.column_config.CheckboxColumn(
                        "dialog_picker", help="dialog_groups.xlsx 피커"
                    ),
                },
            )

            if st.button("💾 goal_types.yaml 저장", use_container_width=True, key="save_goal_types_btn"):
                new_gt: list[dict] = []
                for _, row in edited_gt.iterrows():
                    key = str(row.get("key", "") or "").strip()
                    label = str(row.get("label", "") or "").strip()
                    if not key or not label:
                        continue
                    entry: dict = {"key": key, "label": label, "params": []}
                    p_label = str(row.get("param_label", "") or "").strip()
                    p_opts_raw = str(row.get("param_options", "") or "").strip()
                    p_free = bool(row.get("free_text", False))
                    p_item = bool(row.get("item_picker", False))
                    p_dialog = bool(row.get("dialog_picker", False))
                    has_param = bool(p_label or p_opts_raw or p_free or p_item or p_dialog)
                    if has_param:
                        param: dict = {"label": p_label or "param"}
                        if p_opts_raw:
                            param["options"] = [o.strip() for o in p_opts_raw.split(";") if o.strip()]
                        if p_free:
                            param["free_text"] = True
                        if p_item:
                            param["item_picker"] = True
                        if p_dialog:
                            param["dialog_picker"] = True
                        entry["params"] = [param]
                    new_gt.append(entry)

                try:
                    save_goal_types_yaml(new_gt)
                    st.success(f"저장 완료: {len(new_gt)} 항목")
                    st.info("재시작 후 반영됩니다 (Cache Refresh 또는 브라우저 새로고침).")
                except Exception as e:
                    st.error(f"저장 실패: {e}")

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

    if not nday_mission_events_path:
        missing.append("nday_mission_events_path is empty in config")
    elif not Path(nday_mission_events_path).exists():
        missing.append(f"nday_mission_events file not found: {nday_mission_events_path}")

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
    # 2026-04-24: "🔁 데일리 세트" 탭 제거 — "데일리 미션" 단일 타입으로 통합되어 Tab 1 에서 처리
    tab_add, tab_plaza = st.tabs(["퀘스트 추가", "광장 배치"])

    with tab_add:
        render_tab_add(quests_path, items_list, kw, dialog_groups, nday_mission_events_path=nday_mission_events_path)

    with tab_plaza:
        render_tab_plaza(quests_path, kw)


if __name__ == "__main__" or True:
    main()

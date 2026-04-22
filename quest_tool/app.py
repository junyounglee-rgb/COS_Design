"""Quest Tool - Streamlit app (STEP 3: 단건 추가 UI)."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from config import load_config
from quest_writer import (
    append_quest_row,
    generate_unique_key,
    get_existing_keys,
    get_header_map,
    load_items,
    load_keywords,
    load_quest_templates,
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
        "reset_type": "QUEST_RESET_TYPE_REPEAT",
        "count_type": "QUEST_COUNT_TYPE_SUM",
    },
    "데일리 메인": {
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_REPEAT",
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
        "label": "광장 대화 완료",
        "params": [{"label": "dialog_group_id", "free_text": True}],
    },
    {
        "key": "town_use_landmark:ref_landmark_id",
        "label": "광장 랜드마크",
        "params": [{"label": "landmark_id", "free_text": True}],
    },
    {
        "key": "finish_town_dialog:dialog_group_id",
        "label": "광장 대화(finish)",
        "params": [{"label": "dialog_group_id", "free_text": True}],
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
        "params": [{"label": "id(상시=100,로테이션=200)", "options": ["100", "200"]}],
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
    "QUEST_RESET_TYPE_WEEKLY",
    "QUEST_RESET_TYPE_REPEAT",
]
_RESET_TYPE_KEYS = ["NONE", "DAILY", "WEEKLY", "REPEAT"]


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


# ---------------------------------------------------------------------------
# UI 위젯 함수
# ---------------------------------------------------------------------------


def select_or_paste(label: str, allowed: list[str], key: str, help: str = "") -> str | None:
    """selectbox + text_input 조합. 허용 목록 외 입력 시 st.error 표시 + None 반환."""
    MANUAL = "(직접 입력 / 붙여넣기)"
    sel = st.selectbox(label, [MANUAL] + allowed, key=f"{key}_sel", help=help)
    if sel == MANUAL:
        val = st.text_input(
            "",
            placeholder="예) $$LAUNCH_0",
            key=f"{key}_txt",
            label_visibility="collapsed",
        )
    else:
        val = sel
    if val and val not in allowed:
        st.error(f"허용 목록에 없는 값: `{val}`")
        return None
    return val or None


def render_param_fields(params: list[dict], prefix: str, items_list: list[dict]) -> list[str | None]:
    """GoalType/Condition의 동적 param 필드 렌더링. 값 목록 반환."""
    values = []
    for i, p in enumerate(params):
        if p.get("options"):
            v = st.selectbox(p["label"], p["options"], key=f"{prefix}_p{i}")
        elif p.get("item_picker"):
            opts = [f"{it['id']}: {it['name']} ({it['category']})" for it in items_list]
            sel = st.selectbox(p["label"], ["(선택 안함)"] + opts, key=f"{prefix}_p{i}")
            if sel != "(선택 안함)":
                v = str(items_list[opts.index(sel)]["id"])
            else:
                v = ""
        else:
            v = st.text_input(p["label"], key=f"{prefix}_p{i}")
        values.append(v if v else None)
    return values


# ---------------------------------------------------------------------------
# Tab 1: 단건 추가
# ---------------------------------------------------------------------------


def render_tab_add(quests_path: str, items_list: list[dict], kw: dict[str, dict[str, str]]) -> None:
    st.title("퀘스트 단건 추가")

    build_kw = kw.get("build", {})
    ts_kw = kw.get("timestamp", {})

    # --- 퀘스트 타입 ---
    quest_type = st.selectbox("퀘스트 타입", list(QUEST_TYPES.keys()), key="quest_type_sel")
    tpl = QUEST_TYPES[quest_type]

    st.divider()

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
    goal_params = render_param_fields(goal_def["params"], "goal", items_list)

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
            cond_ps = render_param_fields(cond_def["params"], f"cond_{ci}", items_list)
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

            # 상태 갱신
            st.session_state.existing_keys.add(auto_key)
            st.session_state.auto_key = generate_unique_key(st.session_state.existing_keys)
            st.session_state.condition_count = 1
            st.cache_data.clear()
            st.rerun()
        except ValueError as e:
            st.error(f"중복 키 오류: {e}")
        except Exception as e:
            st.error(f"추가 실패: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    config_path = _get_config_path()
    cfg = load_config(config_path)

    quests_path = cfg.get("quests_path", "")
    items_path = cfg.get("items_path", "")
    keywords_path = cfg.get("keywords_path", "")

    # -- session_state 초기화 --
    if "existing_keys" not in st.session_state:
        if quests_path and Path(quests_path).exists():
            st.session_state.existing_keys = get_existing_keys(quests_path)
        else:
            st.session_state.existing_keys = set()
    if "auto_key" not in st.session_state or st.session_state.auto_key is None:
        st.session_state.auto_key = generate_unique_key(st.session_state.existing_keys)
    if "condition_count" not in st.session_state:
        st.session_state.condition_count = 1

    # -- Sidebar: file paths --
    with st.sidebar:
        st.title("Quest Tool")
        st.caption(f"Config: `{Path(config_path).name}`")

        st.subheader("File Paths")
        st.code(
            f"quests:   {quests_path}\n"
            f"items:    {items_path}\n"
            f"keywords: {keywords_path}",
            language=None,
        )

        if st.button("Cache Refresh", use_container_width=True):
            st.cache_data.clear()
            if quests_path and Path(quests_path).exists():
                st.session_state.existing_keys = get_existing_keys(quests_path)
            st.session_state.auto_key = generate_unique_key(st.session_state.existing_keys)
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

    # -- Tabs --
    tab_add, tab_plaza = st.tabs(["단건 추가", "광장 레이아웃"])

    with tab_add:
        render_tab_add(quests_path, items_list, kw)

    with tab_plaza:
        st.info("광장 레이아웃 UI (future)")


if __name__ == "__main__" or True:
    main()

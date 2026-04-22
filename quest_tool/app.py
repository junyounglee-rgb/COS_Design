"""Quest Tool - Streamlit app (STEP 2: skeleton)."""
import sys
from pathlib import Path

import streamlit as st

from config import load_config
from quest_writer import (
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
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config_path = _get_config_path()
    cfg = load_config(config_path)

    quests_path = cfg.get("quests_path", "")
    items_path = cfg.get("items_path", "")
    keywords_path = cfg.get("keywords_path", "")

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
            st.rerun()

        st.divider()

        # -- File load status --
        st.subheader("Load Status")

        # quests header
        quests_ok = False
        items_ok = False
        keywords_ok = False
        templates_ok = False

        if quests_path and Path(quests_path).exists():
            try:
                header_map = _get_header_map(quests_path)
                st.write(f"quests.xlsx: (header {len(header_map)})")
                quests_ok = True
            except Exception as e:
                st.write(f"quests.xlsx: {e}")
        else:
            st.write(f"quests.xlsx: (file not found)")

        # items
        if items_path and Path(items_path).exists():
            try:
                items = _load_items(items_path)
                st.write(f"items.xlsx: ({len(items)} items)")
                items_ok = True
            except Exception as e:
                st.write(f"items.xlsx: {e}")
        else:
            st.write(f"items.xlsx: (file not found)")

        # keywords
        if keywords_path and Path(keywords_path).exists():
            try:
                kw = _load_keywords(keywords_path)
                build_cnt = len(kw.get("build", {}))
                ts_cnt = len(kw.get("timestamp", {}))
                st.write(f"keywords.xlsx: (build {build_cnt}, timestamp {ts_cnt})")
                keywords_ok = True
            except Exception as e:
                st.write(f"keywords.xlsx: {e}")
        else:
            st.write(f"keywords.xlsx: (file not found)")

        # templates
        if quests_path and Path(quests_path).exists():
            try:
                templates = _load_quest_templates(quests_path)
                st.write(f"#quest templates: {len(templates)}")
                templates_ok = True
            except Exception as e:
                st.write(f"#quest templates: {e}")
        else:
            st.write(f"#quest templates: (file not found)")

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

    # -- Tabs --
    tab_add, tab_plaza = st.tabs(["Add Quest", "Plaza Layout"])

    with tab_add:
        st.info("Single quest add UI (STEP 3)")

    with tab_plaza:
        st.info("Plaza layout UI (future)")


if __name__ == "__main__" or True:
    main()

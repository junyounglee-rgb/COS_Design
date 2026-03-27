"""
excel_analyze — 1단계: 텍스트 출력으로 파싱 결과 검증
실행: streamlit run app_text.py
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

from parser import (
    GraphData, TableNode,
    parse_excel_folder, build_file_category_map,
    save_exclude_files, get_all_file_names,
)

YAML_PATH = str(Path(__file__).parent / "categories.yaml")

# 디폴트 제외 파일 목록
DEFAULT_EXCLUDE_FILES: list[str] = sorted([
    "ai_infos",
    "camera_shakes",
    "cameras",
    "community_urls",
    "damage_fonts",
    "errors",
    "game_config",
    "hit_fx_sockets",
    "keywords",
    "minimap_configs",
    "miya_dialogs",
    "mode_tool_tips",
    "nicknames",
    "observes",
    "parabola_guides",
    "portraits",
    "string_keywords",
    "town_config",
    "translations_en",
    "translations_id",
    "translations_ja",
    "translations_ko",
    "translations_th",
    "translations_vi",
    "translations_zh_hant",
    "ui_sounds",
    "ui_strings",
    "virtual_pads",
    "voices",
    "win_lose_poss",
    "word_filters",
])


# ─────────────────────────── 필터링 ─────────────────────────────────

OUTGAME_PREFIX = "아웃게임"

def filter_graph(graph: GraphData, selected_categories: set[str]) -> GraphData:
    filtered_nodes = [n for n in graph.nodes if n.category in selected_categories]
    visible_names = {n.table_name for n in filtered_nodes}
    filtered_edges = [
        e for e in graph.edges
        if e.source in visible_names and e.target in visible_names
    ]
    return GraphData(nodes=filtered_nodes, edges=filtered_edges, warnings=graph.warnings)


# ─────────────────────────── 렌더링 함수 ─────────────────────────────

def render_summary(graph: GraphData, filtered: GraphData) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("전체 테이블", len(graph.nodes))
    col2.metric("표시 테이블", len(filtered.nodes))
    col3.metric("FK 관계 (표시)", len(filtered.edges))
    col4.metric("경고", len(graph.warnings))


def render_category_tables(filtered: GraphData) -> None:
    st.subheader("카테고리별 테이블 목록")

    by_cat: dict[str, list[TableNode]] = defaultdict(list)
    for node in filtered.nodes:
        by_cat[node.category].append(node)

    if not by_cat:
        st.info("표시할 테이블이 없습니다.")
        return

    for cat_name in sorted(by_cat.keys()):
        nodes = by_cat[cat_name]
        with st.expander(f"**{cat_name}** ({len(nodes)}개 테이블)", expanded=False):
            for node in sorted(nodes, key=lambda n: n.table_name):
                fk_list = [
                    f"{c.name} → {c.fk_target}"
                    for c in node.columns if c.fk_target
                ]
                label = (
                    f"📄 **{node.table_name}** "
                    f"| PK: `{node.pk_column or '-'}` "
                    f"| FK {node.fk_count}개"
                    + (f" | {', '.join(fk_list)}" if fk_list else "")
                )
                with st.expander(label, expanded=False):
                    col_rows = []
                    for c in node.columns:
                        if c.is_comment:
                            continue
                        col_rows.append({
                            "컬럼명": c.name,
                            "설명 (Row1)": c.description,
                            "익스포트 경로 (Row2)": c.export_path,
                            "PK": "✓" if c.is_pk else "",
                            "FK → ": c.fk_target or "",
                        })
                    if col_rows:
                        st.dataframe(
                            pd.DataFrame(col_rows),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.caption("컬럼 정보 없음")


def render_edge_list(filtered: GraphData) -> None:
    st.subheader(f"FK 관계 목록 ({len(filtered.edges)}개)")

    if not filtered.edges:
        st.info("표시할 FK 관계가 없습니다.")
        return

    # source 카테고리 맵
    cat_map = {n.table_name: n.category for n in filtered.nodes}

    rows = []
    for e in sorted(filtered.edges, key=lambda x: (x.source, x.target)):
        rows.append({
            "source 테이블": e.source,
            "source 카테고리": cat_map.get(e.source, "-"),
            "FK 컬럼": e.label,
            "target 테이블": e.target,
            "target 카테고리": cat_map.get(e.target, "-"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_warnings(graph: GraphData) -> None:
    if not graph.warnings:
        return

    dangling = [w for w in graph.warnings if "dangling" in w]
    others = [w for w in graph.warnings if "dangling" not in w]

    if others:
        with st.expander(f"파싱 경고 ({len(others)}개)", expanded=True):
            for w in others:
                st.warning(w)

    if dangling:
        with st.expander(f"Dangling FK (target 없음) ({len(dangling)}개)", expanded=False):
            for w in dangling:
                st.caption(w)


# ─────────────────────────── 메인 앱 ────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Excel 데이터 구조 분석 (텍스트)",
        page_icon="📋",
        layout="wide",
    )
    st.title("📋 Excel 기획 데이터 구조 분석")
    st.caption("1단계: 텍스트 출력으로 파싱 결과 검증")

    # ── 사이드바 ──────────────────────────────────────────────────────
    with st.sidebar:
        st.header("설정")

        if st.button("🔄 파싱 실행", use_container_width=True):
            with st.spinner("Excel 파일 파싱 중..."):
                st.session_state["graph_data"] = parse_excel_folder(YAML_PATH)
            st.success("파싱 완료!")

        st.divider()

        # ── 제외 파일 관리 ─────────────────────────────────────────────
        _, _, _, current_excludes = build_file_category_map(YAML_PATH)
        all_file_names = get_all_file_names(YAML_PATH)

        hdr_col, reset_col = st.columns([3, 1])
        hdr_col.subheader("제외 파일 관리")
        if reset_col.button("↺ 초기화", help="디폴트 값으로 되돌리기"):
            st.session_state["confirm_reset"] = True

        # 리셋 확인 다이얼로그
        if st.session_state.get("confirm_reset"):
            st.warning("디폴트 값으로 변경할까요?")
            yes_col, no_col = st.columns(2)
            if yes_col.button("✅ 네", use_container_width=True):
                try:
                    save_exclude_files(YAML_PATH, DEFAULT_EXCLUDE_FILES)
                    st.session_state.pop("confirm_reset", None)
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))
            if no_col.button("❌ 아니오", use_container_width=True):
                st.session_state.pop("confirm_reset", None)
                st.rerun()

        # 파일 추가
        add_col, btn_col = st.columns([3, 1])
        with add_col:
            new_file = st.selectbox(
                "파일 추가",
                options=[""] + [f for f in all_file_names if f not in current_excludes],
                label_visibility="collapsed",
                placeholder="파일명 선택 또는 입력",
            )
        with btn_col:
            if st.button("추가", disabled=not new_file):
                updated = sorted(current_excludes | {new_file})
                try:
                    save_exclude_files(YAML_PATH, updated)
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

        # 현재 제외 목록 — 각 항목에 삭제 버튼
        if current_excludes:
            for fname in sorted(current_excludes):
                row = st.columns([4, 1])
                row[0].caption(fname)
                if row[1].button("✕", key=f"del_{fname}"):
                    updated = sorted(current_excludes - {fname})
                    try:
                        save_exclude_files(YAML_PATH, updated)
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
        else:
            st.caption("제외된 파일 없음")

        st.divider()

        graph: GraphData | None = st.session_state.get("graph_data")
        if graph is None:
            st.info("위 버튼을 눌러 파싱을 시작하세요.")
            return

        # 카테고리 목록 수집
        _, _, visible_map, _ = build_file_category_map(YAML_PATH)
        all_categories = sorted({n.category for n in graph.nodes})

        st.subheader("표시 범위")
        show_outgame_only = st.toggle("아웃게임만 표시", value=True)

        st.subheader("카테고리 필터")
        selected: set[str] = set()
        for cat in all_categories:
            is_outgame = cat.startswith(OUTGAME_PREFIX)
            if show_outgame_only and not is_outgame:
                continue
            default = visible_map.get(cat, True)
            if st.checkbox(cat, value=default, key=f"cat_{cat}"):
                selected.add(cat)

        st.divider()
        st.caption(f"전체 테이블: {len(graph.nodes)}개")
        st.caption(f"전체 FK: {len(graph.edges)}개")

    # ── 메인 영역 ─────────────────────────────────────────────────────
    graph = st.session_state.get("graph_data")
    if graph is None:
        st.info("👈 사이드바에서 '파싱 실행'을 눌러주세요.")
        return

    filtered = filter_graph(graph, selected)

    render_summary(graph, filtered)
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📁 카테고리별 테이블", "🔗 FK 관계 목록", "⚠️ 경고"])

    with tab1:
        render_category_tables(filtered)

    with tab2:
        render_edge_list(filtered)

    with tab3:
        render_warnings(graph)


if __name__ == "__main__":
    main()

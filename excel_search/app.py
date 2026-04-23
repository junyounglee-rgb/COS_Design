"""
app.py - Excel 데이터 검색 Streamlit 앱
"""

import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

from config import load_config, save_config
from indexer import get_connection, init_db, run_indexing
from searcher import SearchResult, get_index_stats, search

# ---------------------------------------------------------------------------
# 페이지 설정 (반드시 최상단에 위치해야 함)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Excel 검색 도구", layout="wide")

# 페이지 하단 클리핑 방지
st.markdown("""
<style>
.block-container { padding-bottom: 120px !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------------------------

def open_file(file_path: str) -> None:
    """운영체제별로 파일을 기본 앱으로 연다."""
    if not os.path.exists(file_path):
        st.error(f"파일을 찾을 수 없습니다: {Path(file_path).name}")
        return
    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
    except Exception as e:
        st.error(f"파일 열기 실패: {e}")


def results_to_csv(results: list[SearchResult]) -> str:
    """검색 결과를 CSV 문자열로 변환한다."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["파일명", "시트명", "컬럼명", "매칭수", "매칭값"])
    for r in results:
        writer.writerow([
            r.file_name, r.sheet_name, r.col_name,
            r.match_count, ", ".join(r.matched_values)
        ])
    return output.getvalue()


def update_stats() -> None:
    """세션에 저장된 conn으로 인덱스 통계를 갱신한다."""
    st.session_state.stats = get_index_stats(st.session_state.conn)


def render_results(results: list[SearchResult], query: str) -> None:
    """
    같은 파일의 결과를 묶어서 렌더링한다.
    파일당 1개 헤더 행 + 시트별 expander.
    50개 파일까지 바로 표시하고, 나머지는 expander로 묶는다.
    """
    import pandas as pd

    # 파일 경로 기준으로 그룹화 (순서 유지)
    grouped: dict[str, list[SearchResult]] = {}
    for r in results:
        grouped.setdefault(r.file_path, []).append(r)
    file_list = list(grouped.items())

    # 헤더
    header_cols = st.columns([5, 1, 1])
    header_cols[0].markdown("**파일명**")
    header_cols[1].markdown("**매칭수**")
    header_cols[2].markdown("**열기**")
    st.divider()

    def render_file_group(idx: int, file_path: str, file_results: list[SearchResult]) -> None:
        """파일 단위로 헤더 + 시트별 expander를 렌더링한다."""
        total = sum(r.match_count for r in file_results)
        cols = st.columns([5, 1, 1])
        cols[0].markdown(
            f'<span style="font-weight:bold; font-size:1.2em">{file_results[0].file_name}</span>',
            unsafe_allow_html=True,
        )
        cols[1].markdown(str(total))
        if cols[2].button("📂", key=f"open_{idx}"):
            open_file(file_path)

        for result in file_results:
            with st.expander(f"📋 {result.sheet_name} — {result.match_count}행 매칭"):
                if result.matched_rows and result.col_headers:
                    df = pd.DataFrame(result.matched_rows, columns=result.col_headers)
                    matched_col = result.col_name

                    def highlight_matched(col):
                        return [
                            "background-color: rgba(0, 180, 80, 0.25);" if col.name == matched_col else ""
                            for _ in col
                        ]

                    styled = df.style.apply(highlight_matched, axis=0)
                    # 행 수에 맞게 높이 동적 계산 (내부 스크롤 최소화)
                    _row_h, _header_h, _max_h = 35, 38, 800
                    _height = min(_header_h + len(df) * _row_h, _max_h)
                    st.dataframe(styled, use_container_width=True, hide_index=True, height=_height)
                else:
                    st.info("행 데이터를 불러올 수 없습니다.")

    # 처음 50개 파일은 바로 표시
    for i, (file_path, file_results) in enumerate(file_list[:50]):
        render_file_group(i, file_path, file_results)
        st.divider()

    # 51번째 파일부터는 expander로 묶음
    if len(file_list) > 50:
        remaining = file_list[50:]
        with st.expander(f"결과 더 보기 ({len(remaining)}개 파일)"):
            for j, (file_path, file_results) in enumerate(remaining):
                render_file_group(50 + j, file_path, file_results)
                st.divider()


# ---------------------------------------------------------------------------
# 세션 상태 초기화
# ---------------------------------------------------------------------------

# DB 연결 초기화 (앱 생명주기 동안 1회만 실행)
if "conn" not in st.session_state:
    db_path = str(Path(__file__).parent / "index.db")
    conn = get_connection(db_path)
    init_db(conn)
    st.session_state.conn = conn

# 검색 결과 초기화
if "search_results" not in st.session_state:
    st.session_state.search_results = []

# 설정 초기화
if "config" not in st.session_state:
    config_path = str(Path(__file__).parent / "config.txt")
    st.session_state.config = load_config(config_path)
    st.session_state.config_path = config_path

# 인덱스 통계 초기화
if "stats" not in st.session_state:
    update_stats()


# ---------------------------------------------------------------------------
# 사이드바
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ 설정")

    st.subheader("엑셀 폴더 경로")
    folder_input = st.text_input(
        "폴더 경로",
        value=st.session_state.config.get("excel_folder", ""),
        label_visibility="collapsed",
        placeholder="예: C:/Users/user/Documents/excel",
    )
    if st.button("저장", key="save_folder"):
        st.session_state.config["excel_folder"] = folder_input.strip()
        save_config(st.session_state.config, st.session_state.config_path)
        st.success("폴더 경로가 저장되었습니다.")

    st.subheader("제외 파일")
    exclude_input = st.text_area(
        "제외 파일 (쉼표 구분)",
        value=", ".join(st.session_state.config.get("exclude_files", [])),
        label_visibility="collapsed",
        placeholder="예: 임시.xlsx, 백업.xlsx",
        height=80,
    )
    if st.button("저장", key="save_exclude"):
        # 쉼표로 split 후 빈 항목 제거
        exclude_list = [f.strip() for f in exclude_input.split(",") if f.strip()]
        st.session_state.config["exclude_files"] = exclude_list
        save_config(st.session_state.config, st.session_state.config_path)
        st.success("제외 파일 목록이 저장되었습니다.")

    st.divider()

    # 인덱스 업데이트 버튼
    if st.button("🔄 인덱스 업데이트", use_container_width=True):
        folder = st.session_state.config.get("excel_folder", "").strip()
        if not folder:
            st.error("엑셀 폴더 경로를 먼저 설정해주세요.")
        elif not Path(folder).is_dir():
            st.error(f"폴더를 찾을 수 없습니다: {folder}")
        else:
            exclude = st.session_state.config.get("exclude_files", [])
            db_path = str(Path(__file__).parent / "index.db")

            # progress_callback을 통해 진행 상황을 실시간으로 표시
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)

            def progress_callback(current: int, total: int, filename: str) -> None:
                ratio = current / total if total > 0 else 0
                progress_bar.progress(ratio)
                progress_placeholder.text(f"처리 중 ({current}/{total}): {filename}")

            with st.spinner("인덱싱 중..."):
                result = run_indexing(
                    folder_path=folder,
                    db_path=db_path,
                    exclude_files=exclude,
                    progress_callback=progress_callback,
                    conn=st.session_state.conn,
                )

            progress_bar.empty()
            progress_placeholder.empty()

            # 결과 메시지 표시
            indexed = result["indexed"]
            skipped = result["skipped"]
            failed = result["failed"]
            st.success(f"완료: {indexed}개 인덱싱, {skipped}개 건너뜀")
            if failed:
                st.warning(f"실패 {len(failed)}개:\n" + "\n".join(failed))

            # 통계 갱신
            update_stats()

    # 인덱스 상태 표시
    stats = st.session_state.stats
    last = stats["last_indexed"]
    # ISO 포맷 날짜시간에서 초 단위까지만 표시 (문자열이면 슬라이싱)
    if last and last != "없음" and len(last) >= 19:
        last = last[:19].replace("T", " ")
    st.caption(
        f"📁 파일 {stats['file_count']}개 | "
        f"🔢 셀 {stats['cell_count']}개 | "
        f"🕐 최종: {last}"
    )


# ---------------------------------------------------------------------------
# 메인 영역
# ---------------------------------------------------------------------------

st.title("🔍 Excel 데이터 검색")

# 검색 입력 폼
query = st.text_input("검색어", placeholder="검색할 단어를 입력하세요")

col_mode, col_limit = st.columns([2, 1])
with col_mode:
    mode = st.radio(
        "검색 모드",
        options=["정확 일치", "부분 일치"],
        horizontal=True,
    )
with col_limit:
    limit = st.number_input("결과 제한", min_value=1, max_value=100000, value=1000, step=100)

# 검색 실행
if st.button("🔍 검색", type="primary"):
    if not query.strip():
        st.warning("검색어를 입력해주세요.")
    else:
        # 인덱싱된 파일이 없으면 자동으로 인덱스 업데이트 실행
        if st.session_state.stats["file_count"] == 0:
            folder = st.session_state.config.get("excel_folder", "").strip()
            if not folder:
                st.warning("엑셀 폴더 경로를 먼저 설정해주세요.")
                st.stop()
            elif not Path(folder).is_dir():
                st.error(f"폴더를 찾을 수 없습니다: {folder}")
                st.stop()
            else:
                exclude = st.session_state.config.get("exclude_files", [])
                db_path = str(Path(__file__).parent / "index.db")
                with st.spinner("인덱스가 없어 자동으로 인덱싱 중..."):
                    result = run_indexing(
                        folder_path=folder,
                        db_path=db_path,
                        exclude_files=exclude,
                        conn=st.session_state.conn,
                    )
                update_stats()
                if result["indexed"] == 0 and not result["failed"]:
                    st.info("인덱싱할 파일이 없습니다.")
                    st.stop()
                elif result["failed"]:
                    st.warning(f"일부 파일 인덱싱 실패: {', '.join(result['failed'])}")

        search_mode = "exact" if mode == "정확 일치" else "partial"
        with st.spinner("검색 중..."):
            results = search(
                conn=st.session_state.conn,
                query=query.strip(),
                mode=search_mode,
                limit=int(limit),
            )
        st.session_state.search_results = results
        st.session_state.last_query = query.strip()

# 결과 표시
results = st.session_state.search_results
last_query = st.session_state.get("last_query", "")

if results:
    # 결과 요약
    unique_files = len(set(r.file_path for r in results))
    st.info(f"총 {len(results)}건 ({unique_files}개 파일에서 발견)")

    # CSV 내보내기 버튼
    csv_data = results_to_csv(results)
    st.download_button(
        "📥 CSV 내보내기",
        data=csv_data.encode("utf-8-sig"),
        file_name="search_results.csv",
        mime="text/csv",
    )

    # 결과 렌더링
    render_results(results, last_query)

elif last_query:
    # 검색 실행 후 결과가 없는 경우
    st.info("검색 결과가 없습니다.")

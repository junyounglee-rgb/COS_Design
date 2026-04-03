"""
UI String 브랜치 전파 도구 - Streamlit GUI
"""

from __future__ import annotations

import queue
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from string_propagate import (
    BranchResult,
    Propagator,
    PropagatorThread,
    Rollbacker,
    RollbackerThread,
    StringDiff,
    compute_diff,
    current_branch,
    load_rollback_log,
    load_config,
    save_config,
    LOCK_FILE,
    CONFIG_PATH,
)

# ──────────────────────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="UI String 브랜치 전파 도구",
    page_icon="🔤",
    layout="wide",
)

# ──────────────────────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────────────────────

if "log_queue" not in st.session_state:
    st.session_state["log_queue"] = queue.Queue()
if "propagator_thread" not in st.session_state:
    st.session_state["propagator_thread"] = None
if "run_logs" not in st.session_state:
    st.session_state["run_logs"] = []
if "results" not in st.session_state:
    st.session_state["results"] = []
if "diff" not in st.session_state:
    st.session_state["diff"] = None
if "diff_error" not in st.session_state:
    st.session_state["diff_error"] = ""
if "editing_config" not in st.session_state:
    st.session_state["editing_config"] = False
if "confirm_rollback" not in st.session_state:
    st.session_state["confirm_rollback"] = False
if "rollback_thread" not in st.session_state:
    st.session_state["rollback_thread"] = None
if "rollback_logs" not in st.session_state:
    st.session_state["rollback_logs"] = []
if "rollback_results" not in st.session_state:
    st.session_state["rollback_results"] = []
if "rollback_log_queue" not in st.session_state:
    st.session_state["rollback_log_queue"] = queue.Queue()


# ──────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────

def refresh_diff(repo_root: str) -> None:
    xlsx_path = Path(repo_root) / "excel" / "ui_strings.xlsx"
    if not xlsx_path.exists():
        st.session_state["diff"] = None
        st.session_state["diff_error"] = f"파일 없음: {xlsx_path}"
        return
    try:
        diff = compute_diff(repo_root, xlsx_path)
        st.session_state["diff"] = diff
        st.session_state["diff_error"] = ""
    except Exception as e:
        st.session_state["diff"] = None
        st.session_state["diff_error"] = str(e)


def extract_panic_summary(detail: str) -> str:
    """panic: ... 첫 줄만 추출. 없으면 첫 줄 반환."""
    for line in detail.splitlines():
        line = line.strip()
        if line.startswith("panic:"):
            return line
    first = detail.strip().splitlines()[0] if detail.strip() else ""
    return first[:200] if first else "(상세 정보 없음)"


def is_running() -> bool:
    t: PropagatorThread | None = st.session_state.get("propagator_thread")
    return t is not None and not t.is_done()


def make_commit_msg(author: str, branches: list[str]) -> str:
    branch_tag = ",".join(branches) if branches else "?"
    return f"[{author}][{branch_tag}] ui_strings 업데이트[#CL]"


# ──────────────────────────────────────────────────────────────
# 메인 UI
# ──────────────────────────────────────────────────────────────

st.title("🔤 UI String 브랜치 전파 도구")

cfg = load_config()

# ── 설정 섹션 ─────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("설정")
    col1, col2 = st.columns(2)
    with col1:
        repo_root = st.text_input(
            "저장소 경로 (cos-data 루트)",
            value=cfg.get("repo_root", ""),
            help="excel/, protobuf/ 디렉토리가 포함된 cos-data 루트 경로",
        )
        datasheet_exe = st.text_input(
            "datasheet.exe 경로",
            value=cfg.get("datasheet", ""),
        )
        sibling_repos_raw = st.text_area(
            "연동 저장소 경로 (한 줄에 하나씩)",
            value="\n".join(cfg.get("sibling_repos", [])),
            height=90,
            help="datasheet 실행 전 함께 최신화할 저장소 경로 (cos-common, cos-client 등). 같은 브랜치명으로 checkout+pull됩니다.",
        )
        sibling_repos = [p.strip() for p in sibling_repos_raw.splitlines() if p.strip()]
    with col2:
        author = st.text_input("작업자 이름", value=cfg.get("author", ""))
        dry_run = st.checkbox(
            "Dry-run (커밋/푸시 없이 결과만 확인)",
            value=cfg.get("dry_run", False),
        )

    if st.button("💾 설정 저장", use_container_width=False):
        new_cfg = {
            **cfg,
            "repo_root": repo_root,
            "datasheet": datasheet_exe,
            "sibling_repos": sibling_repos,
            "author": author,
            "dry_run": dry_run,
        }
        save_config(new_cfg)
        st.success("설정이 저장됐습니다.")

    # 잠금 파일 잔류 감지
    if LOCK_FILE.exists():
        st.warning("⚠️ 잠금 파일이 남아있습니다. 이전 실행이 비정상 종료됐을 수 있습니다.")
        if st.button("🗑️ 잠금 파일 삭제"):
            LOCK_FILE.unlink(missing_ok=True)
            st.success("잠금 파일을 삭제했습니다.")
            st.rerun()

# ── 브랜치 선택 ──────────────────────────────────────────────
with st.container(border=True):
    col_title, col_edit = st.columns([4, 1])
    with col_title:
        st.subheader("대상 브랜치 선택")
    with col_edit:
        if st.button("⚙️ 브랜치 목록 편집"):
            st.session_state["editing_config"] = not st.session_state["editing_config"]

    # 브랜치 설정 편집 패널
    if st.session_state["editing_config"]:
        with st.expander("브랜치 목록 편집 (YAML)", expanded=True):
            yaml_text = st.text_area(
                "propagate_branches.yaml",
                value=CONFIG_PATH.read_text(encoding="utf-8") if CONFIG_PATH.exists() else "",
                height=200,
            )
            if st.button("저장"):
                try:
                    parsed = yaml.safe_load(yaml_text)
                    CONFIG_PATH.write_text(yaml_text, encoding="utf-8")
                    st.success("저장 완료. 페이지를 새로고침하세요.")
                    st.session_state["editing_config"] = False
                    st.rerun()
                except yaml.YAMLError as e:
                    st.error(f"YAML 파싱 오류: {e}")

    all_branches: list[str] = cfg.get("branches", [])
    src_branch = ""
    if repo_root and Path(repo_root).exists():
        try:
            src_branch = current_branch(repo_root)
        except Exception:
            pass

    if all_branches:
        # main이 목록에 없으면 맨 앞에 자동 추가
        if "main" not in all_branches:
            all_branches = ["main"] + all_branches

        selected_branches = []
        cols = st.columns(min(4, len(all_branches)))
        for i, br in enumerate(all_branches):
            is_main = br == "main"
            suffix = ""
            if is_main:
                suffix = " 🔒 (필수)"
            if br == src_branch:
                suffix += "  ← 현재 브랜치"
            label = f"{br}{suffix}"
            with cols[i % len(cols)]:
                if is_main:
                    # main은 강제 선택 (비활성화된 체크박스로 표시)
                    st.checkbox(label, value=True, disabled=True, key=f"branch_{br}")
                    selected_branches.append(br)
                else:
                    if st.checkbox(label, value=True, key=f"branch_{br}"):
                        selected_branches.append(br)

        st.caption("🔒 main 브랜치는 필수 포함이며 가장 먼저 처리됩니다.")
    else:
        st.warning("propagate_branches.yaml에 브랜치가 없습니다.")
        selected_branches = []

# ── 변경 사항 ─────────────────────────────────────────────────
with st.container(border=True):
    col_title, col_refresh = st.columns([4, 1])
    with col_title:
        st.subheader("ui_strings.xlsx 변경 사항")
    with col_refresh:
        if st.button("🔄 새로고침"):
            refresh_diff(repo_root)

    # 최초 로딩 시 자동 감지
    if st.session_state["diff"] is None and not st.session_state["diff_error"]:
        if repo_root and Path(repo_root).exists():
            refresh_diff(repo_root)

    diff_err = st.session_state.get("diff_error", "")
    diff: StringDiff | None = st.session_state.get("diff")

    if diff_err:
        st.error(diff_err)
    elif diff is None:
        st.info("저장소 경로를 입력하고 새로고침 버튼을 눌러주세요.")
    elif diff.is_empty():
        st.warning("HEAD 대비 변경된 내용이 없습니다. xlsx를 수정한 뒤 새로고침해주세요.")
    else:
        import pandas as pd

        rows = []
        for k, v in diff.added.items():
            rows.append({"구분": "➕ 추가", "Key": k, "이전값": "-", "현재값": v})
        for k, (old_v, new_v) in diff.changed.items():
            rows.append({"구분": "✏️ 변경", "Key": k, "이전값": old_v, "현재값": new_v})
        for k, v in diff.removed.items():
            rows.append({"구분": "➖ 삭제", "Key": k, "이전값": v, "현재값": "-"})

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(
            f"추가 {len(diff.added)}개 / 변경 {len(diff.changed)}개 / 삭제 {len(diff.removed)}개"
        )

# ── 커밋 메시지 ───────────────────────────────────────────────
with st.container(border=True):
    st.subheader("커밋 메시지")
    default_msg = make_commit_msg(author or "작업자", selected_branches)
    commit_msg = st.text_input("커밋 메시지 (직접 편집 가능)", value=default_msg)

# ── 실행 버튼 ─────────────────────────────────────────────────
st.divider()

run_disabled = is_running()

def _start_propagator(pull_only: bool) -> None:
    """공통 Propagator 생성 및 실행 헬퍼."""
    errors = []
    if not repo_root:
        errors.append("저장소 경로를 입력해주세요.")
    if not pull_only and not author.strip():
        errors.append("작업자 이름을 입력해주세요.")
    if not selected_branches:
        errors.append("대상 브랜치를 하나 이상 선택해주세요.")
    if not pull_only and not commit_msg.strip():
        errors.append("커밋 메시지를 입력해주세요.")

    if errors:
        for e in errors:
            st.error(e)
        return

    log_q: queue.Queue = st.session_state["log_queue"]
    st.session_state["run_logs"] = []
    st.session_state["results"] = []

    def log_callback(msg: str) -> None:
        log_q.put(msg)

    xlsx_path = Path(repo_root) / "excel" / "ui_strings.xlsx"

    propagator = Propagator(
        repo_root=repo_root,
        datasheet_exe=datasheet_exe,
        xlsx_path=str(xlsx_path),
        branches=selected_branches,
        commit_msg=commit_msg if not pull_only else "",
        sibling_repos=sibling_repos,
        pull_only=pull_only,
        dry_run=dry_run,
        log_callback=log_callback,
    )

    validation_errors = propagator.validate()
    if validation_errors:
        for e in validation_errors:
            st.error(e)
        return

    pt = PropagatorThread(propagator)
    st.session_state["propagator_thread"] = pt
    pt.start()
    st.rerun()


col_pull, col_push = st.columns(2)

with col_pull:
    pull_label = "⏳ 실행 중..." if run_disabled else "🔽 선택 브랜치 풀 받기"
    if st.button(pull_label, disabled=run_disabled, use_container_width=True):
        _start_propagator(pull_only=True)

with col_push:
    if run_disabled:
        push_label = "⏳ 실행 중..."
    elif dry_run:
        push_label = "🧪 string 파일 전파 [DRY-RUN]"
    else:
        push_label = "🚀 string 파일 전파"
    if st.button(push_label, disabled=run_disabled, type="primary", use_container_width=True):
        _start_propagator(pull_only=False)

# ── 진행 상황 표시 ────────────────────────────────────────────
pt: PropagatorThread | None = st.session_state.get("propagator_thread")

if pt is not None:
    log_q: queue.Queue = st.session_state["log_queue"]

    # 큐에 쌓인 로그 수집
    while not log_q.empty():
        try:
            msg = log_q.get_nowait()
            st.session_state["run_logs"].append(msg)
        except queue.Empty:
            break

    with st.container(border=True):
        st.subheader("진행 상황")

        if st.session_state["run_logs"]:
            log_text = "\n".join(st.session_state["run_logs"])
            st.code(log_text, language=None)

        if not pt.is_done():
            st.spinner("실행 중...")
            time.sleep(0.5)
            st.rerun()
        else:
            # 완료 - 결과 표시
            results: list[BranchResult] = pt.results
            st.session_state["results"] = results

            is_pull_only = pt._propagator.pull_only
            st.subheader("결과")
            for res in results:
                if res.success and not res.skipped:
                    if is_pull_only:
                        st.success(f"✅ {res.branch} — pull 완료")
                    elif dry_run:
                        st.success(f"✅ {res.branch} — dry-run 완료")
                    else:
                        st.success(f"✅ {res.branch} — 커밋+푸시 완료")
                elif res.skipped:
                    st.info(f"⏭️ {res.branch} — 스킵: {res.skip_reason}")
                else:
                    detail = res.error_detail or ""
                    summary = extract_panic_summary(detail)
                    is_panic = "panic:" in detail
                    with st.expander(f"❌ {res.branch} — {res.error_stage} 실패", expanded=True):
                        st.error(summary)
                        if detail.strip() and detail.strip() != summary:
                            label = "스택 트레이스 보기" if is_panic else "상세 메시지 보기"
                            with st.expander(label, expanded=not is_panic):
                                st.code(detail, language=None)

            # 실행 완료 후 잠금 파일 잔여 및 thread 정리
            if LOCK_FILE.exists():
                LOCK_FILE.unlink(missing_ok=True)
            st.session_state["propagator_thread"] = None

# ── 롤백 섹션 ─────────────────────────────────────────────────
st.divider()
with st.container(border=True):
    st.subheader("🔄 마지막 작업 롤백")

    rollback_log = load_rollback_log()

    if rollback_log is None:
        st.info("아직 전파 기록이 없습니다.")
    else:
        st.markdown(f"**마지막 전파**: {rollback_log['timestamp']}")
        st.markdown(f"**커밋 메시지**: `{rollback_log['commit_msg']}`")
        st.markdown("**대상 브랜치**:")
        for entry in rollback_log["entries"]:
            st.markdown(f"- `{entry['branch']}` ({entry['commit_hash'][:8]})")

        rb_thread: RollbackerThread | None = st.session_state.get("rollback_thread")
        rb_running = rb_thread is not None and not rb_thread.is_done()

        if not st.session_state["confirm_rollback"]:
            if st.button("🔄 롤백 실행", disabled=rb_running, type="secondary"):
                st.session_state["confirm_rollback"] = True
                st.rerun()
        else:
            st.warning("⚠️ 정말 롤백하시겠습니까? 위 브랜치들에 revert 커밋이 push됩니다.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 확인, 롤백합니다", type="primary"):
                    st.session_state["confirm_rollback"] = False
                    st.session_state["rollback_logs"] = []
                    st.session_state["rollback_results"] = []
                    # 기존 queue 재사용 (초기화 후 재활용)
                    rb_log_q: queue.Queue = st.session_state["rollback_log_queue"]
                    while not rb_log_q.empty():
                        rb_log_q.get_nowait()

                    rollbacker = Rollbacker(
                        repo_root=repo_root,
                        log=rollback_log,
                        log_callback=rb_log_q.put,
                    )
                    rbt = RollbackerThread(rollbacker)
                    st.session_state["rollback_thread"] = rbt
                    rbt.start()
                    st.rerun()
            with col2:
                if st.button("❌ 취소"):
                    st.session_state["confirm_rollback"] = False
                    st.rerun()

        # 롤백 진행 상황
        if rb_thread is not None:
            rb_log_q = st.session_state["rollback_log_queue"]
            while not rb_log_q.empty():
                try:
                    st.session_state["rollback_logs"].append(rb_log_q.get_nowait())
                except queue.Empty:
                    break

            if st.session_state["rollback_logs"]:
                st.code("\n".join(st.session_state["rollback_logs"]), language=None)

            if not rb_thread.is_done():
                time.sleep(0.5)
                st.rerun()
            else:
                st.subheader("롤백 결과")
                for res in rb_thread.results:
                    if res.success:
                        st.success(f"✅ {res.branch} — 롤백 완료")
                    else:
                        detail = res.error_detail or ""
                        summary = extract_panic_summary(detail)
                        is_panic = "panic:" in detail
                        with st.expander(f"❌ {res.branch} — {res.error_stage} 실패", expanded=True):
                            st.error(summary)
                            if detail.strip() and detail.strip() != summary:
                                label = "스택 트레이스 보기" if is_panic else "상세 메시지 보기"
                                with st.expander(label, expanded=not is_panic):
                                    st.code(detail, language=None)
                st.session_state["rollback_thread"] = None

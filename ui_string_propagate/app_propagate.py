"""
UI String 브랜치 전파 도구 - Streamlit GUI
"""

from __future__ import annotations

import queue
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yaml

from string_propagate import (
    BranchPullStatus,
    BranchResult,
    Propagator,
    PropagatorThread,
    Rollbacker,
    RollbackerThread,
    StatusCheckerThread,
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
if "_propagator_pending" not in st.session_state:
    st.session_state["_propagator_pending"] = None  # None | True(pull) | False(push)
if "_start_errors" not in st.session_state:
    st.session_state["_start_errors"] = []
if "last_is_pull_only" not in st.session_state:
    st.session_state["last_is_pull_only"] = False
if "status_checker_thread" not in st.session_state:
    st.session_state["status_checker_thread"] = None
if "pull_status" not in st.session_state:
    st.session_state["pull_status"] = []       # list[BranchPullStatus]
if "status_log_queue" not in st.session_state:
    st.session_state["status_log_queue"] = queue.Queue()


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
    # pending 플래그가 있으면 아직 시작 전이어도 "실행 중"으로 간주 (버튼 비활성화)
    if st.session_state.get("_propagator_pending") is not None:
        return True
    t: PropagatorThread | None = st.session_state.get("propagator_thread")
    return t is not None and not t.is_done()


def make_commit_msg(author: str, branches: list[str]) -> str:
    branch_tag = ",".join(branches) if branches else "?"
    return f"[{author}][{branch_tag}] ui_strings 업데이트[#CL]"


# ──────────────────────────────────────────────────────────────
# 메인 UI
# ──────────────────────────────────────────────────────────────

st.title("🔤 UI String 브랜치 전파 도구")

st.warning(
    "⚠️ **작업 순서 필수 준수**\n\n"
    "1️⃣ **풀 받기 먼저** — 엑셀 작업 전에 반드시 **🔽 선택 브랜치 풀 받기** 를 실행해 최신 상태로 맞추세요.\n\n"
    "2️⃣ **그 다음 엑셀 작업** — 풀 완료 후 `ui_strings.xlsx` 를 수정하세요.\n\n"
    "3️⃣ **전파 실행** — 수정이 끝나면 **🚀 string 파일 전파** 를 실행하세요.",
    icon="📋",
)

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

        # ── 풀 상태 확인 ──────────────────────────────────────────
        st.divider()
        sc_col, btn_col = st.columns([5, 1])
        with sc_col:
            st.markdown("**📡 풀 상태 확인** (선택 브랜치 기준)")
        with btn_col:
            sc_thread: StatusCheckerThread | None = st.session_state.get("status_checker_thread")
            sc_running = sc_thread is not None and not sc_thread.is_done()
            if st.button("📡 상태 확인", disabled=sc_running or is_running(), key="status_refresh"):
                sq = st.session_state["status_log_queue"]
                while not sq.empty():
                    sq.get_nowait()
                st.session_state["pull_status"] = []
                checker = StatusCheckerThread(
                    repo_root=repo_root,
                    branches=selected_branches,
                    log_callback=sq.put,
                )
                st.session_state["status_checker_thread"] = checker
                checker.start()
                st.rerun()

        # 상태 체커 폴링
        sc_thread = st.session_state.get("status_checker_thread")
        if sc_thread is not None:
            sq = st.session_state["status_log_queue"]
            if sc_thread.is_done():
                st.session_state["pull_status"] = sc_thread.results
                st.session_state["status_checker_thread"] = None
            else:
                with st.spinner("원격 상태 확인 중..."):
                    time.sleep(0.5)
                st.rerun()

        # 상태 표시
        pull_status: list[BranchPullStatus] = st.session_state.get("pull_status", [])
        if pull_status:
            status_map = {s.branch: s for s in pull_status}
            status_cols = st.columns(min(4, len(pull_status)))
            for i, br in enumerate(selected_branches):
                s = status_map.get(br)
                with status_cols[i % len(status_cols)]:
                    if s is None:
                        st.caption(f"`{br}` —")
                    elif s.remote_missing:
                        st.caption(f"`{br}` ⚠️ 원격 브랜치 없음")
                    elif s.local_missing:
                        st.caption(f"`{br}` 🔄 로컬 없음 (첫 풀 필요)")
                    elif s.error:
                        st.caption(f"`{br}` ❌ {s.error}")
                    elif s.is_uptodate:
                        st.caption(f"`{br}` ✅ 최신")
                    else:
                        st.caption(f"`{br}` 🔄 **{s.behind}커밋** 대기")
        elif not sc_running:
            st.caption("새로고침을 눌러 풀 받을 내용이 있는지 확인하세요.")

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
    """Propagator 생성 및 thread 시작. 오류는 session_state에 저장."""
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
        st.session_state["_start_errors"] = errors
        return  # thread 시작 안 함

    st.session_state["_start_errors"] = []
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

    pt = PropagatorThread(propagator)
    st.session_state["propagator_thread"] = pt
    pt.start()


# 저장된 오류 표시 (이전 시도 실패 시)
for _err in st.session_state.get("_start_errors", []):
    st.error(_err)

col_pull, col_push = st.columns(2)

with col_pull:
    pull_label = "⏳ 실행 중..." if run_disabled else "🔽 선택 브랜치 풀 받기"
    if st.button(pull_label, disabled=run_disabled, use_container_width=True):
        # 1단계: 즉시 비활성화 (pending 플래그 set → rerun)
        st.session_state["_propagator_pending"] = True
        st.session_state["_start_errors"] = []
        st.rerun()

_cur_diff: StringDiff | None = st.session_state.get("diff")
_has_changes = _cur_diff is not None and not _cur_diff.is_empty()
push_disabled = run_disabled or not _has_changes

with col_push:
    if run_disabled:
        push_label = "⏳ 실행 중..."
    elif dry_run:
        push_label = "🧪 string 파일 전파 [DRY-RUN]"
    else:
        push_label = "🚀 string 파일 전파"
    if st.button(push_label, disabled=push_disabled, type="primary", use_container_width=True):
        # 1단계: 즉시 비활성화
        st.session_state["_propagator_pending"] = False
        st.session_state["_start_errors"] = []
        st.rerun()

# 2단계: 버튼이 비활성화된 렌더 이후 → 실제 thread 시작
_pending = st.session_state.get("_propagator_pending")
if _pending is not None and st.session_state.get("propagator_thread") is None:
    st.session_state["_propagator_pending"] = None  # 플래그 해제
    _start_propagator(bool(_pending))
    st.rerun()  # thread 시작 후 진행 상황 표시 / 오류 시 버튼 재활성화

# ── 진행 상황 표시 ────────────────────────────────────────────
pt: PropagatorThread | None = st.session_state.get("propagator_thread")

# ① 스레드 관리: 로그 수집 / 브라우저 경고 / 완료 처리
if pt is not None:
    log_q: queue.Queue = st.session_state["log_queue"]
    while not log_q.empty():
        try:
            st.session_state["run_logs"].append(log_q.get_nowait())
        except queue.Empty:
            break

    if not pt.is_done():
        components.html("""
        <script>
        parent.window.onbeforeunload = function(e) {
            var msg = '⚠️ 작업이 진행 중입니다. 창을 닫으면 일부 브랜치만 처리될 수 있습니다.';
            e.returnValue = msg;
            return msg;
        };
        </script>
        """, height=0)
    else:
        # 완료: 결과 session_state에 보존 후 thread 정리 → rerun
        components.html("""
        <script>parent.window.onbeforeunload = null;</script>
        """, height=0)
        st.session_state["results"] = pt.results
        st.session_state["last_is_pull_only"] = pt._propagator.pull_only
        if LOCK_FILE.exists():
            LOCK_FILE.unlink(missing_ok=True)
        st.session_state["propagator_thread"] = None
        st.rerun()  # 버튼 재활성화

# ② 표시: thread 유무와 무관하게 session_state 기준으로 항상 렌더
if pt is not None or st.session_state["run_logs"] or st.session_state["results"]:
    with st.container(border=True):
        st.subheader("진행 상황")

        # 진행 중 안내 (thread 실행 중일 때만)
        if pt is not None and not pt.is_done():
            is_pull = pt._propagator.pull_only
            action = "풀 받기" if is_pull else "전파"
            branches_str = " → ".join(pt._propagator.branches)
            st.info(f"⏳ {action} 진행 중... `{branches_str}`")

        # 로그 (항상 표시 — 완료 후에도 유지)
        if st.session_state["run_logs"]:
            st.code("\n".join(st.session_state["run_logs"]), language=None)

        # 폴링 (thread 실행 중일 때만)
        if pt is not None and not pt.is_done():
            with st.spinner("git 작업 실행 중..."):
                time.sleep(0.5)
            st.rerun()

        # 결과 (thread 완료 후 session_state에서 표시)
        results: list[BranchResult] = st.session_state.get("results", [])
        if results and pt is None:
            is_pull_only: bool = st.session_state.get("last_is_pull_only", False)
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

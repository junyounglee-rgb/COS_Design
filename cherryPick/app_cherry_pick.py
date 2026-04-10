import queue
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from cherry_pick import (
    BranchResult, CellChange, CherryPickPropagator, CherryPickThread,
    _cached_compare, check_needs_pull, compare_xlsx_side_by_side, diff_workbooks,
    fetch_origin, get_commit_files, get_commit_info, get_remote_branches,
    get_source_branches, load_config, load_xlsx_from_ref, run_autopull,
    save_config, validate_commit_hash,
)

st.set_page_config(page_title="Cherry Pick Propagator", layout="wide")

def _init():
    defaults = {
        "config": load_config(), "log_queue": queue.Queue(), "cp_thread": None,
        "run_logs": [], "pending_cp": False, "log_expanded": False,
        "commit_hash": "", "commit_info": None, "commit_files": [],
        "source_branch": "", "source_candidates": [], "ui_strings_warning": False,
        "remote_branches": [], "branches_loaded": False,
        "pull_checked": False, "needs_pull_branches": [], "pull_done": False,
        "autopull_running": False, "autopull_thread": None, "autopull_tick": 0,
        "branch_active": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
cfg = st.session_state.config

@st.dialog("Cherry-pick 전파 확인")
def confirm_cherrypick_dialog(targets):
    st.write(f"다음 **{len(targets)}개** 브랜치에 cherry-pick을 전파합니다:")
    for b in targets: st.markdown(f"- `{b}`")
    st.write("정말 전파하시겠습니까?")
    col_y, col_n = st.columns(2)
    with col_y:
        if st.button("✅ Yes", type="primary", use_container_width=True):
            st.session_state.pending_cp = True; st.session_state.run_logs = []; st.rerun()
    with col_n:
        if st.button("❌ No", use_container_width=True): st.rerun()

st.title("🍒 Cherry Pick Propagator")
st.caption("커밋 해시를 입력하면 선택한 브랜치에 cherry-pick + push 전파")

repo_path = cfg.get("repo_path", "")
if repo_path:
    cherry_pick_head = Path(repo_path) / ".git" / "CHERRY_PICK_HEAD"
    if cherry_pick_head.exists():
        st.error("⚠️ 이전 cherry-pick이 완료되지 않았습니다.\n\n터미널에서 아래 명령을 실행한 후 새로고침 하세요:\n\n```\ngit cherry-pick --abort\n```")
        st.stop()

with st.expander("⚙️ 설정", expanded=not cfg.get("repo_path")):
    new_repo_path = st.text_input("저장소 경로", value=cfg.get("repo_path", ""), placeholder=r"예) D:\COS_Project\cos-data")
    branches_raw = st.text_area("기본 선택 브랜치 (한 줄에 하나)", value="\n".join(cfg.get("branches", [])), height=120)
    if st.button("💾 저장"):
        _hash_backup = st.session_state.get("hash_input", "")
        cfg["repo_path"] = new_repo_path.strip()
        cfg["branches"] = [b.strip() for b in branches_raw.splitlines() if b.strip()]
        save_config(cfg); st.session_state.config = cfg
        st.session_state.branch_active = {}; st.session_state.pull_checked = False
        if cfg["repo_path"]:
            with st.spinner("브랜치 목록 로드 중..."):
                try:
                    st.session_state.remote_branches = get_remote_branches(cfg["repo_path"])
                    st.session_state.branches_loaded = True
                except Exception:
                    st.session_state.remote_branches = []; st.session_state.branches_loaded = False
        else:
            st.session_state.remote_branches = []; st.session_state.branches_loaded = False
        st.session_state["hash_input"] = _hash_backup; st.rerun()
    if st.session_state.branches_loaded and st.session_state.remote_branches:
        remote_set = set(st.session_state.remote_branches)
        lines = [f"✅ `{b}`" if b in remote_set else f"❌ `{b}` — 없는 브랜치" for b in cfg.get("branches", [])]
        if lines: st.markdown("  \n".join(lines))

if not cfg.get("repo_path"):
    st.warning("위 설정에서 저장소 경로를 입력하고 저장해주세요."); st.stop()

cp_thread = st.session_state.cp_thread
is_running = cp_thread is not None and not cp_thread.is_done()
is_busy = is_running or st.session_state.autopull_running

if st.session_state.pending_cp and not is_running:
    st.session_state.pending_cp = False; st.session_state.log_expanded = False
    log_q = queue.Queue(); st.session_state.log_queue = log_q; st.session_state.run_logs = []
    propagator = CherryPickPropagator(cfg["repo_path"], st.session_state.commit_hash, st.session_state.get("selected_targets", []), log_q)
    thread = CherryPickThread(propagator); st.session_state.cp_thread = thread; thread.start()
    is_running = True; cp_thread = thread

st.subheader("커밋 해시 입력")
st.text_input("커밋 해시 (full 또는 short hash)", placeholder="예) a1b2c3d", disabled=is_busy, key="hash_input")
hash_val = st.session_state.get("hash_input", "").strip()

if hash_val != st.session_state.commit_hash:
    st.session_state.commit_hash = hash_val
    st.session_state.commit_info = None; st.session_state.commit_files = []
    st.session_state.source_branch = ""; st.session_state.source_candidates = []
    st.session_state.ui_strings_warning = False; st.session_state.pull_checked = False
    st.session_state.needs_pull_branches = []; st.session_state.pull_done = False
    for k in ["commit_diff_results", "target_diff_results", "commit_compare_results", "target_compare_results"]:
        st.session_state.pop(k, None)

if ".." in hash_val:
    st.error("단일 커밋 해시만 지원합니다."); st.stop()

if hash_val:
    if not validate_commit_hash(cfg["repo_path"], hash_val):
        st.error(f"❌ 유효하지 않은 커밋 해시: `{hash_val}`"); st.stop()

    if st.session_state.commit_info is None:
        info = get_commit_info(cfg["repo_path"], hash_val)
        if info is None: st.error("커밋 정보를 불러올 수 없습니다."); st.stop()
        st.session_state.commit_info = info
        st.session_state.commit_files = get_commit_files(cfg["repo_path"], hash_val)
        candidates = get_source_branches(cfg["repo_path"], hash_val)
        st.session_state.source_candidates = candidates
        st.session_state.source_branch = candidates[0] if len(candidates) == 1 else ""
        ui_files = [f for f in st.session_state.commit_files if "ui_strings" in f.lower()]
        st.session_state.ui_strings_warning = bool(ui_files)

    info = st.session_state.commit_info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ `{info['short']}` — {info['message']}")
        st.caption(f"작성자: {info['author']} | {info['date']}")
    with col2:
        with st.expander(f"변경 파일 ({len(st.session_state.commit_files)}개)"):
            for f in st.session_state.commit_files: st.code(f, language=None)

    xlsx_files = [f for f in st.session_state.commit_files if f.lower().endswith(".xlsx")]
    if xlsx_files:
        if st.button(f"📊 커밋 변경 내용 보기 ({len(xlsx_files)}개 xlsx)", disabled=is_busy):
            commit_compare = {xlsx_f: _cached_compare(cfg["repo_path"], f"{hash_val}^", hash_val, xlsx_f) for xlsx_f in xlsx_files}
            st.session_state["commit_compare_results"] = commit_compare
        if st.session_state.get("commit_compare_results"):
            for xlsx_f, sheet_htmls in st.session_state["commit_compare_results"].items():
                if not sheet_htmls: st.caption(f"**{xlsx_f}** — 변경 없음"); continue
                for sheet_name, html in sheet_htmls.items():
                    with st.expander(f"**{xlsx_f}** [{sheet_name}]"):
                        components.html(html, height=550, scrolling=True)

    candidates = st.session_state.source_candidates
    if not candidates:
        st.warning("⚠️ source 브랜치를 감지할 수 없습니다."); source_branch = ""
    elif len(candidates) == 1:
        source_branch = candidates[0]; st.info(f"📌 Source 브랜치: **{source_branch}**")
    else:
        source_branch = st.selectbox("Source 브랜치 선택", candidates, index=0, disabled=is_busy)
        if source_branch != st.session_state.source_branch: st.session_state.source_branch = source_branch
    st.session_state.source_branch = source_branch

    block_execution = False
    if st.session_state.ui_strings_warning:
        if source_branch != "main":
            st.error(f"❌ `ui_strings.xlsx`는 반드시 **main** 브랜치에서 작업 후 전파해야 합니다.\n\n현재 source: **{source_branch or '(감지 불가)'}**")
            block_execution = True
        else:
            st.info("ℹ️ ui_strings.xlsx 포함 커밋 — source가 main이므로 정상 진행 가능합니다.")
    if block_execution: st.stop()

    st.divider()
    st.subheader("Pull 상태 확인")

    if not st.session_state.branches_loaded:
        with st.spinner("원격 정보 조회 중..."):
            fetch_origin(cfg["repo_path"])
            st.session_state.remote_branches = get_remote_branches(cfg["repo_path"])
            st.session_state.branches_loaded = True

    remote_branches = st.session_state.remote_branches
    preset_branches = [b for b in cfg.get("branches", []) if b != source_branch and b in set(remote_branches)]

    if not st.session_state.pull_checked:
        check_targets = preset_branches if preset_branches else [b for b in remote_branches if b != source_branch][:10]
        with st.spinner("pull 필요 여부 확인 중..."):
            st.session_state.needs_pull_branches = check_needs_pull(cfg["repo_path"], check_targets)
            st.session_state.pull_checked = True

    needs_pull = st.session_state.needs_pull_branches

    if st.session_state.autopull_running:
        ap_thread = st.session_state.autopull_thread
        if ap_thread is not None and not ap_thread.is_alive():
            while not st.session_state.log_queue.empty(): st.session_state.run_logs.append(st.session_state.log_queue.get())
            st.session_state.autopull_running = False; st.session_state.autopull_thread = None
            st.session_state.autopull_tick = 0; st.session_state.pull_done = True
            st.session_state.needs_pull_branches = []; st.rerun()
        else:
            st.session_state.autopull_tick += 1
            st.info(f"🔽 autopull 실행중{'.' * ((st.session_state.autopull_tick % 3) + 1)}")
            while not st.session_state.log_queue.empty(): st.session_state.run_logs.append(st.session_state.log_queue.get())
            time.sleep(1.0); st.rerun()
    elif st.session_state.pull_done:
        st.success("✅ autopull 완료 — 모든 브랜치 최신화됨")
    elif needs_pull:
        st.warning(f"⚠️ {len(needs_pull)}개 브랜치에 미반영 커밋이 있습니다: `{', '.join(needs_pull)}`")
        if st.button("🔽 autopull 실행", disabled=is_busy):
            log_q = queue.Queue(); st.session_state.log_queue = log_q; st.session_state.run_logs = []
            import threading
            t = threading.Thread(target=lambda: run_autopull(needs_pull, log_q), daemon=True)
            st.session_state.autopull_thread = t; st.session_state.autopull_running = True; t.start(); st.rerun()
    else:
        st.success("✅ 모든 브랜치 최신 상태")

    if st.session_state.run_logs and not is_running:
        with st.expander("autopull 로그"): st.code("\n".join(st.session_state.run_logs), language=None)

    st.divider()
    st.subheader("타겟 브랜치")
    st.caption(f"설정의 기본 브랜치 목록을 사용합니다. Source **{source_branch or '(미감지)'}** 는 자동 제외됩니다.")

    cfg_branches = [b for b in cfg.get("branches", []) if b != source_branch]
    remote_set = set(remote_branches)
    if not cfg_branches: st.warning("설정에서 기본 브랜치를 먼저 등록해주세요."); st.stop()

    branch_active = st.session_state.branch_active
    for b in cfg_branches:
        if b not in branch_active: branch_active[b] = True

    for branch in cfg_branches:
        exists = branch in remote_set
        c_toggle, c_name = st.columns([1, 7])
        with c_toggle:
            if exists:
                label = "ON" if branch_active.get(branch, True) else "OFF"
                btn_type = "primary" if branch_active.get(branch, True) else "secondary"
                if st.button(label, key=f"tog_{branch}", type=btn_type, disabled=is_busy):
                    branch_active[branch] = not branch_active.get(branch, True)
                    st.session_state.branch_active = branch_active; st.rerun()
            else:
                st.button("N/A", key=f"tog_{branch}", disabled=True)
        with c_name:
            if not exists: st.markdown(f"❌ ~~{branch}~~ — 브랜치 없음")
            elif branch_active.get(branch, True): st.markdown(f"**{branch}**")
            else: st.markdown(f"~~{branch}~~")

    selected_targets = [b for b in cfg_branches if b in remote_set and branch_active.get(b, True)]
    st.session_state.selected_targets = selected_targets

    if xlsx_files and selected_targets:
        if st.button("📊 타겟 브랜치와 Excel 비교", disabled=is_busy):
            target_compare = {}
            for branch in selected_targets:
                branch_htmls = {}
                for xlsx_f in xlsx_files:
                    sheet_htmls = _cached_compare(cfg["repo_path"], f"origin/{branch}", hash_val, xlsx_f)
                    if sheet_htmls: branch_htmls[xlsx_f] = sheet_htmls
                target_compare[branch] = branch_htmls
            st.session_state["target_compare_results"] = target_compare
        if st.session_state.get("target_compare_results"):
            for branch, file_htmls in st.session_state["target_compare_results"].items():
                if not file_htmls: st.caption(f"**{branch}** — 차이 없음"); continue
                with st.expander(f"**{branch}** ({len(file_htmls)}개 파일 차이)"):
                    for xlsx_f, sheet_htmls in file_htmls.items():
                        for sheet_name, html in sheet_htmls.items():
                            st.markdown(f"**{xlsx_f}** [{sheet_name}]")
                            components.html(html, height=550, scrolling=True)

    st.divider()
    can_run = bool(selected_targets) and not is_running and not st.session_state.autopull_running
    if st.button("🍒 cherry-pick 전파 시작", type="primary", disabled=not can_run):
        confirm_cherrypick_dialog(selected_targets)
    if is_running: st.warning("⚠️ 실행 중입니다. 브랜치가 임시 전환됩니다 — IDE 혼동 주의!")
else:
    st.info("커밋 해시를 위에 입력하세요.")

if is_running or (st.session_state.run_logs and cp_thread is not None):
    st.subheader("진행 상황")
    while not st.session_state.log_queue.empty(): st.session_state.run_logs.append(st.session_state.log_queue.get())
    logs = st.session_state.run_logs
    PREVIEW_LINES = 5
    if st.session_state.log_expanded or len(logs) <= PREVIEW_LINES: st.code("\n".join(logs), language=None)
    else: st.code("\n".join(logs[-PREVIEW_LINES:]), language=None)
    if len(logs) > PREVIEW_LINES:
        if st.session_state.log_expanded:
            if st.button("▲ 닫기"): st.session_state.log_expanded = False; st.rerun()
        else:
            if st.button(f"▼ 더보기 (전체 {len(logs)}줄)"): st.session_state.log_expanded = True; st.rerun()
    if is_running: time.sleep(0.5); st.rerun()

if cp_thread is not None and cp_thread.is_done() and cp_thread.propagator.results:
    results = cp_thread.propagator.results
    n_s = sum(1 for r in results if r.status == "success")
    n_sk = sum(1 for r in results if r.status == "skipped")
    n_f = sum(1 for r in results if r.status == "failed")
    st.subheader("결과")
    st.write(f"✅ 성공 {n_s}  |  ⏭️ 스킵 {n_sk}  |  ❌ 실패 {n_f}")
    for r in results:
        if r.status == "success": st.success(f"✅ {r.branch}" + (f"  [{r.new_commit}]" if r.new_commit else ""))
        elif r.status == "skipped": st.info(f"⏭️ {r.branch}  — {r.message}")
        else: st.error(f"❌ {r.branch}  — {r.message[:300]}")

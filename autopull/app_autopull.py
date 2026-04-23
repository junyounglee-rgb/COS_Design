import queue
import time

import streamlit as st

from autopull import (
    BranchPullStatus,
    Puller,
    PullerThread,
    StatusCheckerThread,
    load_config,
    save_config,
)

st.set_page_config(page_title="Auto Pull", layout="wide")

# ─── Session state init ───────────────────────────────────────────────

def _init() -> None:
    defaults: dict = {
        "log_queue": queue.Queue(),
        "puller_thread": None,
        "run_logs": [],
        "status_checker_thread": None,
        "pull_statuses": [],
        "config": load_config(),
        "pending_pull": False,
        "pending_status_check": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init()
cfg: dict = st.session_state.config

# ─── Title ───────────────────────────────────────────────────────────────

st.title("🔽 Auto Pull")
st.caption("선택한 브랜치를 저장소별로 한 번에 풀 받는 도구")

# ─── Settings ────────────────────────────────────────────────────────────

with st.expander("⚙️ 설정", expanded=not cfg.get("repo_root")):
    repo_root = st.text_input(
        "메인 저장소 경로",
        value=cfg.get("repo_root", ""),
        placeholder="예) D:\\COS_Project\\cos-data",
    )

    sibling_raw = st.text_area(
        "함께 풀 받을 저장소 (한 줄에 하나, 선택사항)",
        value="\n".join(cfg.get("sibling_repos", [])),
        height=90,
        placeholder="예)\nD:\\COS_Project\\cos-common\nD:\\COS_Project\\cos-client",
    )

    branches_raw = st.text_area(
        "브랜치 목록 (한 줄에 하나)",
        value="\n".join(cfg.get("branches", [])),
        height=120,
        placeholder="예)\nmain\nrelease_helsinki2\nrelease_helsinki3",
    )

    if st.button("💾 저장"):
        cfg["repo_root"] = repo_root.strip()
        cfg["sibling_repos"] = [s.strip() for s in sibling_raw.splitlines() if s.strip()]
        cfg["branches"] = [b.strip() for b in branches_raw.splitlines() if b.strip()]
        save_config(cfg)
        st.session_state.config = cfg
        st.success("저장됨")
        st.rerun()

# ─── 저장소 경로 미설정 guard ──────────────────────────────────────────────

if not cfg.get("repo_root"):
    st.warning("위 설정에서 메인 저장소 경로를 입력하고 저장해주세요.")
    st.stop()

all_branches: list[str] = cfg.get("branches", [])
if not all_branches:
    st.warning("설정에서 브랜치 목록을 입력하고 저장해주세요.")
    st.stop()

# ─── Status checker 처리 ──────────────────────────────────────────────────────

checker: StatusCheckerThread | None = st.session_state.status_checker_thread

# pending → thread 시작 (rerun 없이 계속 렌더)
if st.session_state.pending_status_check and checker is None:
    st.session_state.pending_status_check = False
    log_q: queue.Queue = queue.Queue()
    st.session_state.log_queue = log_q
    st.session_state.run_logs = []
    checker_new = StatusCheckerThread(
        repo=cfg["repo_root"],
        branches=all_branches,
        log_queue=log_q,
    )
    st.session_state.status_checker_thread = checker_new
    checker_new.start()
    checker = checker_new

# 완료 → 결과 반영 (rerun은 맨 아래에서)
checker_done = checker is not None and checker.is_done()
if checker_done:
    while not st.session_state.log_queue.empty():
        st.session_state.run_logs.append(st.session_state.log_queue.get())
    st.session_state.pull_statuses = checker.statuses
    st.session_state.status_checker_thread = None
    checker = None

checker_running = checker is not None or st.session_state.pending_status_check

# ─── Branch selection ───────────────────────────────────────────────────────────

st.subheader("브랜치 선택")
if checker_running:
    st.info("📡 원격 상태 확인 중입니다...")

status_map: dict[str, BranchPullStatus] = {
    s.branch: s for s in st.session_state.pull_statuses
}

col_branches, col_actions = st.columns([4, 2])

selected_branches: list[str] = []

with col_branches:
    for branch in all_branches:
        status = status_map.get(branch)
        if status:
            if status.remote_missing:
                badge = "⚠️ 원격 없음"
            elif status.local_missing:
                badge = "🔄 로컈 없음"
            elif status.is_uptodate:
                badge = "✅ 최신"
            else:
                badge = f"🔄 {status.behind}코밋 대기"
            label = f"{branch}  —  {badge}"
        else:
            label = branch

        if st.checkbox(label, value=True, key=f"chk_{branch}"):
            selected_branches.append(branch)

with col_actions:
    st.write("")  # 수직 정렬 맞춰
    STATUS_COOLDOWN = 5
    now = time.time()
    last_check = st.session_state.get("last_status_check", 0)
    cooldown_left = max(0, STATUS_COOLDOWN - (now - last_check))
    on_cooldown = cooldown_left > 0

    if checker_running:
        st.button("📡 확인 중...", use_container_width=True, disabled=True)
    elif on_cooldown:
        st.button(f"📡 대기 중 ({int(cooldown_left) + 1}s)", use_container_width=True, disabled=True)
        time.sleep(1)
        st.rerun()
    elif st.button("📡 상태 확인", use_container_width=True):
        st.session_state.last_status_check = time.time()
        st.session_state.pending_status_check = True
        st.rerun()

# ─── Pending pull 처리 ────────────────────────────────────────────────────────────

puller_thread: PullerThread | None = st.session_state.puller_thread
is_running: bool = puller_thread is not None and not puller_thread.is_done()

if st.session_state.pending_pull and not is_running:
    st.session_state.pending_pull = False
    log_q = queue.Queue()
    st.session_state.log_queue = log_q
    st.session_state.run_logs = []

    puller = Puller(
        repo_root=cfg["repo_root"],
        sibling_repos=cfg.get("sibling_repos", []),
        branches=selected_branches,
        log_queue=log_q,
    )
    thread = PullerThread(puller)
    st.session_state.puller_thread = thread
    thread.start()
    is_running = True

# ─── Pull 버튼 ──────────────────────────────────────────────────────────────────

st.divider()

if st.button(
    "🔽 풀 받기",
    type="primary",
    disabled=is_running or not selected_branches,
    use_container_width=False,
):
    st.session_state.pending_pull = True
    st.rerun()

if is_running:
    st.info("풀 받는 중... 창을 닫지 마세요.")

# ─── Logs ─────────────────────────────────────────────────────────────────────

if is_running or st.session_state.run_logs:
    st.subheader("진행 상황")

    # 큐 드레인
    while not st.session_state.log_queue.empty():
        st.session_state.run_logs.append(st.session_state.log_queue.get())

    st.code("\n".join(st.session_state.run_logs), language=None)

    if is_running:
        time.sleep(0.5)
        st.rerun()

# ─── 결과 요약 ───────────────────────────────────────────────────────────────

if (
    not is_running
    and puller_thread is not None
    and puller_thread.puller.results
):
    st.subheader("결과")
    for r in puller_thread.puller.results:
        if r.success:
            st.success(f"✅  {r.branch}")
        else:
            st.error(f"❌  {r.branch}  [{r.error_stage}]  {r.error_detail[:200]}")

# ─── Status checker 폴링 rerun (UI 렌더 후 실행) ──────────────────────────────────

if checker is not None and not checker.is_done():
    while not st.session_state.log_queue.empty():
        st.session_state.run_logs.append(st.session_state.log_queue.get())
    time.sleep(0.4)
    st.rerun()
elif checker_done:
    st.rerun()

import queue
import time

import streamlit as st

from autopull import (
    ERR_MSG_SLICE_LONG,
    BranchPullStatus,
    Puller,
    PullerThread,
    StatusCheckerThread,
    load_config,
    save_config,
)

st.set_page_config(page_title="Auto Pull", layout="wide")

# ─── 상수 ───────────────────────────────────────────────────────────────────
STATUS_COOLDOWN_SEC = 5           # 수동 "상태 확인" 버튼 쿨다운
POLL_INTERVAL_SEC = 0.5           # Pull/Status 진행 중 폴링 주기


def _drain_log_queue() -> None:
    """log_queue에 쌓인 메시지를 run_logs로 모두 이동."""
    q: queue.Queue = st.session_state.log_queue
    logs: list = st.session_state.run_logs
    while not q.empty():
        logs.append(q.get())

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
        "pull_completion_acked": True,       # 완료 이벤트 1회 처리 플래그 (초기값 True → 과거 기록 ignore)
        "show_save_toast": False,             # 저장 완료 토스트 플래그
        "settings_expanded": None,            # 설정 expander controlled state (None = 초기값 사용)
        "manual_status_check_pending": False,  # 수동 상태 확인 진행 플래그 (완료 감지용)
        "manual_status_check_done": False,     # 수동 상태 확인 완료 표시 플래그 (Result 섹션용)
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

# 설정 expander의 열림/닫힘 상태 결정:
# - settings_expanded가 None이면 repo_root 비어있을 때만 자동으로 열림
# - 저장 버튼 클릭 후에는 False로 강제 설정 (자동 닫힘)
_default_expanded = not cfg.get("repo_root")
_expanded_state = st.session_state.settings_expanded
if _expanded_state is None:
    _expanded_state = _default_expanded

with st.expander("⚙️ 설정", expanded=_expanded_state):
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
        save_ok = save_config(cfg)
        st.session_state.config = cfg
        st.session_state.save_ok = save_ok           # 토스트 분기용
        st.session_state.show_save_toast = True      # 토스트 플래그
        st.session_state.settings_expanded = False   # expander 자동 닫기
        st.rerun()

# 저장 결과 토스트 (expander 바깥, rerun 후에도 수 초간 유지됨)
if st.session_state.show_save_toast:
    if st.session_state.get("save_ok", True):
        st.toast("✅ 저장 완료", icon="💾")
    else:
        st.toast("⚠️ 저장 실패 (권한/디스크 확인)", icon="⚠️")
    st.session_state.show_save_toast = False

# ─── 저장소 경로 미설정 guard ──────────────────────────────────────────────

if not cfg.get("repo_root"):
    st.warning("위 설정에서 메인 저장소 경로를 입력하고 저장해주세요.")
    st.stop()

all_branches: list[str] = cfg.get("branches", [])
if not all_branches:
    st.warning("설정에서 브랜치 목록을 입력하고 저장해주세요.")
    st.stop()

# ─── Status checker 처리 ──────────────────────────────────────────────────────
# 주의: run_logs 클리어는 버튼 핸들러(수동 상태 확인 버튼)로 이동함.
# 자동 트리거 경로(Pull 완료 후)는 pull 로그를 보존해야 하므로 여기서 클리어하지 않음.

checker: StatusCheckerThread | None = st.session_state.status_checker_thread

# pending → thread 시작 (rerun 없이 계속 렌더)
if st.session_state.pending_status_check and checker is None:
    st.session_state.pending_status_check = False
    log_q: queue.Queue = queue.Queue()
    st.session_state.log_queue = log_q
    checker_new = StatusCheckerThread(
        repo=cfg["repo_root"],
        branches=all_branches,
        sibling_repos=cfg.get("sibling_repos", []),  # sibling도 status 체크 (버그 fix)
        log_queue=log_q,
    )
    st.session_state.status_checker_thread = checker_new
    checker_new.start()
    checker = checker_new

# 완료 → 결과 반영 (rerun은 맨 아래에서)
checker_done = checker is not None and checker.is_done()
if checker_done:
    _drain_log_queue()
    st.session_state.pull_statuses = checker.statuses
    st.session_state.status_checker_thread = None
    checker = None
    # 수동 상태 확인 경로였다면 완료 표시 플래그를 세움 (Result 섹션에서 "✅ 상태 확인 완료" 표시)
    if st.session_state.manual_status_check_pending:
        st.session_state.manual_status_check_pending = False
        st.session_state.manual_status_check_done = True

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
        detail_caption = ""
        if status:
            if status.remote_missing:
                badge = "⚠️ 원격 없음"
            elif status.local_missing:
                badge = "🔄 로컬 없음"
            elif status.is_uptodate:
                badge = "✅ 최신"
            else:
                badge = f"🔄 {status.behind}커밋 대기"
                # 저장소별 상세 (behind>0만 표시, 많이 뒤처진 순으로 정렬) — 어느 저장소가 뒤처져 있는지 명시
                behind_repos = sorted(
                    (
                        (name, n)
                        for name, n in status.repo_behinds.items()
                        if n > 0
                    ),
                    key=lambda kv: -kv[1],
                )
                if behind_repos:
                    detail_caption = " · ".join(f"{name}: {n}" for name, n in behind_repos)
            label = f"{branch}  —  {badge}"
        else:
            label = branch

        if st.checkbox(label, value=True, key=f"chk_{branch}"):
            selected_branches.append(branch)
        if detail_caption:
            st.caption(f"　　↳ {detail_caption}")

with col_actions:
    st.write("")  # 수직 정렬 맞추기용
    now = time.time()
    last_check = st.session_state.get("last_status_check", 0)
    cooldown_left = max(0, STATUS_COOLDOWN_SEC - (now - last_check))
    on_cooldown = cooldown_left > 0
    # Pull 진행 중 체크 (아래 Pending pull 블록보다 위에 위치 → session_state 직접 조회)
    _current_puller = st.session_state.puller_thread
    pull_in_progress = _current_puller is not None and not _current_puller.is_done()

    if checker_running:
        st.button("📡 확인 중...", use_container_width=True, disabled=True)
    elif pull_in_progress:
        # Pull 진행 중에는 상태 확인 버튼 비활성화 (puller_thread=None 리셋 방지 + git 리소스 경합 차단)
        st.button("📡 Pull 진행 중...", use_container_width=True, disabled=True)
    elif on_cooldown:
        st.button(f"📡 대기 중 ({int(cooldown_left) + 1}s)", use_container_width=True, disabled=True)
        time.sleep(1)
        st.rerun()
    elif st.button("📡 상태 확인", use_container_width=True):
        st.session_state.last_status_check = time.time()
        st.session_state.pending_status_check = True
        st.session_state.run_logs = []  # 수동 상태 확인 시 로그 클리어 (STEP 1 이동분)
        st.session_state.puller_thread = None  # 이전 pull 결과 초기화 (Result 섹션 클리어)
        st.session_state.manual_status_check_pending = True   # 수동 경로임을 마킹
        st.session_state.manual_status_check_done = False     # 이전 완료 표시 리셋
        st.rerun()

# ─── Pending pull 처리 ────────────────────────────────────────────────────────────

puller_thread: PullerThread | None = st.session_state.puller_thread
is_running: bool = puller_thread is not None and not puller_thread.is_done()

if st.session_state.pending_pull and not is_running:
    st.session_state.pending_pull = False
    log_q = queue.Queue()
    st.session_state.log_queue = log_q
    # run_logs 클리어는 버튼 핸들러로 이동함 (STEP 1)

    puller = Puller(
        repo_root=cfg["repo_root"],
        sibling_repos=cfg.get("sibling_repos", []),
        branches=selected_branches,
        log_queue=log_q,
    )
    thread = PullerThread(puller)
    st.session_state.puller_thread = thread
    thread.start()
    # 로컬 변수 동기화 (완료 감지 블록이 OLD thread를 오감지하지 않도록)
    puller_thread = thread
    is_running = True

# ─── Pull 완료 감지 (1회만) + 자동 status 재확인 ──────────────────────────────
if (
    puller_thread is not None
    and puller_thread.is_done()
    and not st.session_state.pull_completion_acked
):
    # 큐 드레인 (진행 로그 보존)
    _drain_log_queue()
    st.session_state.pull_completion_acked = True
    # 자동 status 재확인 (last_status_check 업데이트 안 함 → 수동 쿨다운 영향 없음)
    st.session_state.pending_status_check = True
    st.rerun()

# ─── Pull 버튼 ──────────────────────────────────────────────────────────────────

st.divider()

# 선택된 브랜치가 모두 최신인지 확인 (status 정보가 있을 때만)
# - pull_statuses 비어있거나 선택 브랜치 중 status 미확인 브랜치 존재 → False (일반 "풀 받기" 표시)
# - 선택 브랜치 모두 is_uptodate=True → True ("받을 풀 없음" 표시)
_all_uptodate = False
if selected_branches and st.session_state.pull_statuses:
    _statuses = [status_map.get(b) for b in selected_branches]
    if all(s is not None for s in _statuses):
        _all_uptodate = all(s.is_uptodate for s in _statuses)

if _all_uptodate:
    pull_button_label = "✨ 받을 풀 없음"
    pull_button_disabled = True
else:
    pull_button_label = "🔽 풀 받기"
    pull_button_disabled = is_running or not selected_branches or checker_running

if st.button(
    pull_button_label,
    type="primary",
    disabled=pull_button_disabled,
    use_container_width=False,
):
    st.session_state.pending_pull = True
    st.session_state.pull_completion_acked = False  # 신규 pull 사이클 시작
    st.session_state.run_logs = []                   # 신규 pull 시 로그 클리어 (STEP 1 이동분)
    st.session_state.manual_status_check_done = False  # 이전 상태 확인 완료 표시 제거
    st.rerun()

# ─── Result 섹션 (상단) ───────────────────────────────────────────────────────
# 진행 중: "⏳ 진행중..." / 완료: 각 브랜치 성공/실패 표시
# 수동 상태 확인 완료: "✅ 상태 확인 완료" 단독 표시
if is_running or (puller_thread is not None and puller_thread.puller.results):
    st.subheader("결과")
    if is_running:
        st.info("⏳ 진행중...")
    else:
        for r in puller_thread.puller.results:
            if r.success:
                st.success(f"✅  {r.branch}")
            else:
                st.error(f"❌  {r.branch}  [{r.error_stage}]  {r.error_detail[:ERR_MSG_SLICE_LONG]}")
elif st.session_state.manual_status_check_done:
    st.subheader("결과")
    st.success("✅ 상태 확인 완료")

# ─── Progress 섹션 (하단) ─────────────────────────────────────────────────────
if is_running or st.session_state.run_logs:
    st.subheader("진행 상황")

    # 큐 드레인
    _drain_log_queue()

    st.code("\n".join(st.session_state.run_logs), language=None)

    if is_running:
        time.sleep(POLL_INTERVAL_SEC)
        st.rerun()

# ─── Status checker 폴링 rerun (UI 렌더 후 실행) ──────────────────────────────────

if checker is not None and not checker.is_done():
    _drain_log_queue()
    time.sleep(POLL_INTERVAL_SEC)
    st.rerun()
elif checker_done:
    st.rerun()

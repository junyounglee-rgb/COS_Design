"""
Excel Diff Preview — Compare local file vs Git remote file before commit
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import yaml

from diff_core import (
    compare_xlsx_side_by_side,
    load_xlsx_from_git,
    load_xlsx_from_path,
)

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.yaml"

DEFAULT_CONFIG: dict = {
    "repo_path": r"D:\COS_Project\cos-data",
    "excel_folder": "",
    "branches": ["main"],
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **data}
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


# ─── Git utils ────────────────────────────────────────────────────────────────

def is_git_repo(path: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path, capture_output=True, text=True,
        )
        return r.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def get_remote_branches(repo_path: str) -> list[str]:
    r = subprocess.run(
        ["git", "branch", "-r"],
        cwd=repo_path, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        return []
    branches = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or "HEAD" in line:
            continue
        branches.append(line[len("origin/"):] if line.startswith("origin/") else line)
    return branches


@st.cache_data(ttl=120, show_spinner=False)
def get_file_commits(
    repo_path: str, ref: str, rel_path: str,
    n: int = 20, skip: int = 0,
) -> list[dict]:
    result = subprocess.run(
        ["git", "log", ref, "--follow",
         f"--max-count={n}", f"--skip={skip}",
         "--format=%H|%h|%ai|%an|%s",
         "--", rel_path],
        cwd=repo_path, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        return []
    commits = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 4)
        if len(parts) >= 5:
            commits.append({
                "hash":       parts[0],
                "short_hash": parts[1],
                "date":       parts[2][:16],
                "author":     parts[3],
                "message":    parts[4],
            })
    return commits


_ERR_REMOTE = "__ERR_REMOTE__"
_ERR_LOCAL  = "__ERR_LOCAL__"


def _short_label(ref: str) -> str:
    if len(ref) >= 7 and all(c in "0123456789abcdef" for c in ref[:7].lower()):
        return ref[:7]
    return ref.replace("origin/", "")


@st.cache_data(ttl=300, show_spinner=False)
def _cached_compare_local(
    repo_path: str, ref: str, xlsx_rel_path: str,
    local_path: str, local_mtime: float = 0.0,
) -> dict[str, str] | str:
    remote_wb = load_xlsx_from_git(repo_path, ref, xlsx_rel_path)
    if remote_wb is None:
        return _ERR_REMOTE
    local_wb = load_xlsx_from_path(local_path)
    if local_wb is None:
        return _ERR_LOCAL
    return compare_xlsx_side_by_side(
        remote_wb, local_wb,
        left_label=f"◀ ① [{_short_label(ref)}]",
        right_label="▶ ② Local file",
    )


@st.cache_data(ttl=300, show_spinner=False)
def _cached_compare_versions(
    repo_path: str, ref1: str, ref2: str, xlsx_rel_path: str,
) -> dict[str, str] | str:
    wb1 = load_xlsx_from_git(repo_path, ref1, xlsx_rel_path)
    if wb1 is None:
        return _ERR_REMOTE
    wb2 = load_xlsx_from_git(repo_path, ref2, xlsx_rel_path)
    if wb2 is None:
        return _ERR_REMOTE
    return compare_xlsx_side_by_side(
        wb1, wb2,
        left_label=f"◀ ① [{_short_label(ref1)}]",
        right_label=f"▶ ② [{_short_label(ref2)}]",
    )


# ─── Path / search utils ──────────────────────────────────────────────────────

def try_get_rel_path(local_path: str, repo_path: str) -> str | None:
    try:
        rel = Path(local_path).resolve().relative_to(Path(repo_path).resolve())
        return rel.as_posix()
    except ValueError:
        return None


def resolve_excel_folder(repo_path: str, excel_folder_override: str) -> Path | None:
    ef = excel_folder_override.strip()
    p = Path(ef) if ef else Path(repo_path) / "excel"
    return p if p.exists() else None


def search_xlsx(folder: Path, query: str) -> list[Path]:
    q = query.lower()
    return sorted(
        [f for f in folder.rglob("*.xlsx")
         if q in f.name.lower() and not f.name.startswith("~")],
        key=lambda f: f.name.lower(),
    )


def _commit_label(c: dict) -> str:
    return f"[{c['short_hash']}]  {c['date']}  {c['author']}  —  {c['message'][:70]}"


def _render_diff_result(result, label: str) -> None:
    """Render diff result HTML — shared by both compare modes."""
    if result == _ERR_REMOTE:
        st.error("❌ Could not fetch one of the server versions. Try `git fetch origin` first.")
    elif result == _ERR_LOCAL:
        st.error("❌ Could not read local file.")
    elif isinstance(result, dict) and not result:
        st.success(f"✅ No differences  ({label})")
    elif isinstance(result, dict):
        st.success(f"✅ {len(result)} sheet(s) changed  —  {label}")
        for sheet_name, html in result.items():
            with st.expander(f"📊 **{sheet_name}**", expanded=True):
                components.html(html, height=560, scrolling=True)


# ─── Streamlit UI ─────────────────────────────────────────────────────────────

st.set_page_config(page_title="Excel Diff Preview", page_icon="📋", layout="wide")
st.title("📋 Excel Diff Preview")
st.caption("Select a file and a commit, then compare against your local copy.")

cfg = load_config()

# ── Settings ──────────────────────────────────────────────────────────────────
with st.expander("⚙️ Settings", expanded=False):
    repo_path_input = st.text_input(
        "cos-data repository path",
        value=cfg.get("repo_path", DEFAULT_CONFIG["repo_path"]),
    )
    excel_folder_input = st.text_input(
        "Excel folder path (optional)",
        value=cfg.get("excel_folder", ""),
        placeholder=rf"{cfg.get('repo_path', '')}\\excel  ← default if empty",
    )
    if st.button("💾 Save settings", key="save_cfg"):
        rb = []
        if repo_path_input and Path(repo_path_input).exists() and is_git_repo(repo_path_input):
            rb = get_remote_branches(repo_path_input)
        merged = list(dict.fromkeys(cfg.get("branches", DEFAULT_CONFIG["branches"]) + rb))
        save_config({"repo_path": repo_path_input, "excel_folder": excel_folder_input, "branches": merged})
        st.success("Settings saved.")
        st.rerun()

repo_path    = repo_path_input
excel_folder = resolve_excel_folder(repo_path, excel_folder_input)

# ── Branch selector ───────────────────────────────────────────────────────────
cfg_branches   = cfg.get("branches", DEFAULT_CONFIG["branches"])
remote_branches: list[str] = []
if repo_path and Path(repo_path).exists() and is_git_repo(repo_path):
    remote_branches = get_remote_branches(repo_path)

branch_options = list(dict.fromkeys(cfg_branches + remote_branches)) or ["main"]
branch = st.selectbox("Compare branch", options=branch_options)

st.divider()

# ── File search ───────────────────────────────────────────────────────────────
st.subheader("📁 File Search")

if "selected_file" not in st.session_state:
    st.session_state.selected_file = ""

search_query = st.text_input(
    "search",
    placeholder="Type a keyword  (e.g.  que  cookie  skill)",
    label_visibility="collapsed",
)

if search_query:
    if excel_folder:
        matches = search_xlsx(excel_folder, search_query)
        if matches:
            names = [f.name for f in matches[:30]]
            paths = [str(f) for f in matches[:30]]
            chosen = st.radio(
                "results", options=names, index=None,
                key=f"radio_{search_query}", label_visibility="collapsed",
            )
            if chosen is not None:
                new_path = paths[names.index(chosen)]
                if new_path != st.session_state.selected_file:
                    st.session_state.selected_file = new_path
                    # Reset commit state on file change
                    st.session_state._commit_ctx      = ""
                    st.session_state._commits         = []
                    st.session_state._commits_done    = False
                    st.session_state.selected_commit  = None
                    st.session_state._version_diff_mode = False
                    st.session_state._ver1_hash       = ""
                    st.session_state._ver2_hash       = ""
            if len(matches) > 30:
                st.caption(f"Showing 30 of {len(matches)} — refine your query.")
        else:
            st.caption(f"No xlsx files matching **{search_query}**")
    else:
        st.warning(rf"Excel folder not found. Ensure `{repo_path}\excel` exists.")

# ── Selected file ─────────────────────────────────────────────────────────────
local_path = st.session_state.selected_file
rel_path   = ""

if local_path:
    st.info(f"📄 **{Path(local_path).name}**  —  `{local_path}`")
    rel_path_auto = try_get_rel_path(local_path, repo_path) if repo_path else None
    if rel_path_auto:
        st.caption(f"📂 Repo path: `{rel_path_auto}`")
        rel_path = rel_path_auto
    else:
        st.warning("File is outside the repository path.")
        rel_path = st.text_input("Repo-relative path (manual)", placeholder="e.g. excel/cookie.xlsx")

st.divider()

# ── Commit history ────────────────────────────────────────────────────────────
selected_commit: dict | None = None
ver1_commit:     dict | None = None
ver2_commit:     dict | None = None

if local_path and rel_path and repo_path:

    # Init session state keys
    defaults = {
        "_commit_ctx":        "",
        "_commits":           [],
        "_commits_done":      False,
        "selected_commit":    None,
        "_version_diff_mode": False,
        "_ver1_hash":         "",
        "_ver2_hash":         "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Invalidate on file / branch change
    commit_ctx = f"{repo_path}||{rel_path}||{branch}"
    if st.session_state._commit_ctx != commit_ctx:
        st.session_state._commit_ctx      = commit_ctx
        st.session_state._commits         = []
        st.session_state._commits_done    = False
        st.session_state.selected_commit  = None
        st.session_state._version_diff_mode = False
        st.session_state._ver1_hash       = ""
        st.session_state._ver2_hash       = ""

    # Load first batch
    if not st.session_state._commits and not st.session_state._commits_done:
        with st.spinner(f"Loading commits for {Path(rel_path).name} ..."):
            first_batch = get_file_commits(repo_path, f"origin/{branch}", rel_path, n=20, skip=0)
        st.session_state._commits = first_batch
        if len(first_batch) < 20:
            st.session_state._commits_done = True
        # Set defaults
        if first_batch:
            if not st.session_state.selected_commit:
                st.session_state.selected_commit = first_batch[0]
            if not st.session_state._ver1_hash:
                st.session_state._ver1_hash = first_batch[0]["hash"]
            if not st.session_state._ver2_hash and len(first_batch) > 1:
                st.session_state._ver2_hash = first_batch[1]["hash"]

    commits: list[dict] = st.session_state._commits
    version_diff_mode: bool = st.session_state._version_diff_mode

    # ── Header ────────────────────────────────────────────────────────────────
    col_h, col_t = st.columns([5, 1])
    with col_h:
        badge = "  🔀 버전간 비교 모드" if version_diff_mode else ""
        st.subheader(f"📋 Commit History{badge}")
    with col_t:
        btn_label = "✕ 모드 종료" if version_diff_mode else "🔀 버전간 비교"
        if st.button(btn_label, key="toggle_vd", use_container_width=True):
            st.session_state._version_diff_mode = not version_diff_mode
            st.rerun()

    if not commits:
        st.caption("No commit history found for this file on this branch.")
    else:
        # ── Normal mode: radio list ────────────────────────────────────────────
        if not version_diff_mode:
            default_idx = 0
            if st.session_state.selected_commit:
                sel_hash = st.session_state.selected_commit["hash"]
                for i, c in enumerate(commits):
                    if c["hash"] == sel_hash:
                        default_idx = i
                        break

            labels = [_commit_label(c) for c in commits]
            chosen = st.radio(
                "commit_list", options=labels, index=default_idx,
                key=f"commit_radio_{commit_ctx}_{len(commits)}",
                label_visibility="collapsed",
            )
            if chosen is not None:
                st.session_state.selected_commit = commits[labels.index(chosen)]
            selected_commit = st.session_state.selected_commit

        # ── Version diff mode: same list, ① ② buttons per row ────────────────
        else:
            ver1_h = st.session_state._ver1_hash
            ver2_h = st.session_state._ver2_hash

            # Column header
            hc1, hc2, hc3, hc4 = st.columns([0.4, 7, 0.7, 0.7])
            hc3.markdown("<div style='text-align:center;font-weight:700;color:#1f77b4'>①</div>", unsafe_allow_html=True)
            hc4.markdown("<div style='text-align:center;font-weight:700;color:#ff7f0e'>②</div>", unsafe_allow_html=True)

            for c in commits:
                is_v1 = (c["hash"] == ver1_h)
                is_v2 = (c["hash"] == ver2_h)

                mc, lc, b1c, b2c = st.columns([0.4, 7, 0.7, 0.7])

                # Left marker
                with mc:
                    if is_v1 and is_v2:
                        st.markdown("**①②**")
                    elif is_v1:
                        st.markdown("<span style='color:#1f77b4;font-weight:700'>①</span>", unsafe_allow_html=True)
                    elif is_v2:
                        st.markdown("<span style='color:#ff7f0e;font-weight:700'>②</span>", unsafe_allow_html=True)

                # Commit label
                with lc:
                    label = _commit_label(c)
                    if is_v1:
                        st.markdown(f"<span style='color:#1f77b4'>{label}</span>", unsafe_allow_html=True)
                    elif is_v2:
                        st.markdown(f"<span style='color:#ff7f0e'>{label}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(label)

                # ① button
                with b1c:
                    btn1_style = "primary" if is_v1 else "secondary"
                    if st.button("✓①" if is_v1 else "①", key=f"v1_{c['hash']}",
                                 use_container_width=True, type=btn1_style):
                        st.session_state._ver1_hash = c["hash"]
                        st.rerun()

                # ② button
                with b2c:
                    btn2_style = "primary" if is_v2 else "secondary"
                    if st.button("✓②" if is_v2 else "②", key=f"v2_{c['hash']}",
                                 use_container_width=True, type=btn2_style):
                        st.session_state._ver2_hash = c["hash"]
                        st.rerun()

            # Current selection summary
            commit_map = {c["hash"]: c for c in commits}
            ver1_commit = commit_map.get(st.session_state._ver1_hash)
            ver2_commit = commit_map.get(st.session_state._ver2_hash)

            if ver1_commit or ver2_commit:
                st.markdown("---")
                if ver1_commit:
                    st.caption(f"◀ ① `{ver1_commit['short_hash']}`  {ver1_commit['date']}  {ver1_commit['author']}  —  {ver1_commit['message'][:60]}")
                if ver2_commit:
                    st.caption(f"▶ ② `{ver2_commit['short_hash']}`  {ver2_commit['date']}  {ver2_commit['author']}  —  {ver2_commit['message'][:60]}")

        # ── Load more ──────────────────────────────────────────────────────────
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            n = len(commits)
            done_tag = " (all)" if st.session_state._commits_done else ""
            st.caption(f"{n} commit{'s' if n != 1 else ''} loaded{done_tag}")
        with col_btn:
            if not st.session_state._commits_done:
                if st.button("⬇ Load 20 more", key="load_more"):
                    more = get_file_commits(
                        repo_path, f"origin/{branch}", rel_path,
                        n=20, skip=len(st.session_state._commits),
                    )
                    st.session_state._commits.extend(more)
                    if len(more) < 20:
                        st.session_state._commits_done = True

st.divider()

# ── Compare ───────────────────────────────────────────────────────────────────

version_diff_mode = st.session_state.get("_version_diff_mode", False)

if not version_diff_mode:
    # Normal mode: local vs selected commit
    run_disabled = not (local_path and rel_path and repo_path and branch and selected_commit)
    if st.button("🔍 Compare  (server → local)", type="primary", disabled=run_disabled):
        errors: list[str] = []
        if not Path(local_path).exists():
            errors.append(f"Local file not found: `{local_path}`")
        elif not local_path.lower().endswith(".xlsx"):
            errors.append("Only .xlsx files are supported.")
        if rel_path and not rel_path.lower().endswith(".xlsx"):
            errors.append("Repo path must point to an .xlsx file.")
        if not Path(repo_path).exists():
            errors.append(f"Repository path not found: `{repo_path}`")
        elif not is_git_repo(repo_path):
            errors.append(f"Not a valid git repository: `{repo_path}`")

        if errors:
            for e in errors:
                st.error(e)
        else:
            ref         = selected_commit["hash"]
            local_mtime = Path(local_path).stat().st_mtime if Path(local_path).exists() else 0.0
            with st.spinner(f"Fetching [{selected_commit['short_hash']}]:{rel_path} ..."):
                result = _cached_compare_local(repo_path, ref, rel_path, local_path, local_mtime=local_mtime)

            _render_diff_result(result, selected_commit["short_hash"])

else:
    # Version diff mode: commit A vs commit B
    commit_map  = {c["hash"]: c for c in st.session_state.get("_commits", [])}
    ver1_commit = commit_map.get(st.session_state.get("_ver1_hash", ""))
    ver2_commit = commit_map.get(st.session_state.get("_ver2_hash", ""))

    same        = ver1_commit and ver2_commit and ver1_commit["hash"] == ver2_commit["hash"]
    vd_disabled = not (rel_path and repo_path and ver1_commit and ver2_commit) or bool(same)

    if same:
        st.warning("① and ② are the same commit — please select different commits.")

    if st.button("🔀 버전 비교하기", type="primary", disabled=vd_disabled):
        errors: list[str] = []
        if not Path(repo_path).exists():
            errors.append(f"Repository path not found: `{repo_path}`")
        elif not is_git_repo(repo_path):
            errors.append(f"Not a valid git repository: `{repo_path}`")

        if errors:
            for e in errors:
                st.error(e)
        else:
            with st.spinner(
                f"Comparing [{ver1_commit['short_hash']}] ↔ [{ver2_commit['short_hash']}] ..."
            ):
                result = _cached_compare_versions(
                    repo_path, ver1_commit["hash"], ver2_commit["hash"], rel_path
                )

            _render_diff_result(result, f"{ver1_commit['short_hash']} ↔ {ver2_commit['short_hash']}")

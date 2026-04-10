"""
Cherry Pick Propagator — 핵심 로직
커밋 해시를 입력받아 선택한 브랜치에 cherry-pick + push 전파
"""

from __future__ import annotations

import difflib
import io
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import yaml
from openpyxl import load_workbook

# ─── 설정 ─────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "cherry_pick.yaml"
LOCK_FILE = Path(__file__).parent / ".cherry_pick.lock"

DEFAULT_CONFIG: dict = {
    "repo_path": r"D:\COS_Project\cos-data",
    "branches": [
        "main",
        "release_helsinki2",
        "release_helsinki3",
        "release_helsinki_vng",
    ],
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


# ─── git 헬퍼 ─────────────────────────────────────────────────────────────────

def run_git(args: list[str], cwd: str) -> tuple[int, str, str]:
    """(returncode, stdout, stderr) 반환"""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def current_branch(repo_path: str) -> str:
    _, out, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    return out.strip()


def validate_commit_hash(repo_path: str, commit_hash: str) -> bool:
    """커밋 해시 유효성 확인 (short hash 포함)"""
    if not commit_hash or ".." in commit_hash:
        return False
    code, _, _ = run_git(["cat-file", "-t", commit_hash], cwd=repo_path)
    return code == 0


def get_commit_info(repo_path: str, commit_hash: str) -> Optional[dict]:
    """커밋 메타정보 반환 — 실패 시 None"""
    code, out, _ = run_git(
        ["log", "-1", "--format=%H|%h|%s|%an|%ar", commit_hash],
        cwd=repo_path,
    )
    if code != 0 or not out:
        return None
    parts = out.split("|", 4)
    if len(parts) < 5:
        return None
    return {
        "hash": parts[0],
        "short": parts[1],
        "message": parts[2],
        "author": parts[3],
        "date": parts[4],
    }


def get_commit_files(repo_path: str, commit_hash: str) -> list[str]:
    """커밋에 포함된 파일 목록 반환"""
    code, out, _ = run_git(
        ["show", "--name-only", "--format=", commit_hash],
        cwd=repo_path,
    )
    if code != 0:
        return []
    return [line for line in out.splitlines() if line.strip()]


def get_source_branches(repo_path: str, commit_hash: str) -> list[str]:
    """
    해시가 포함된 원격 브랜치 목록 반환.
    'origin/branch' → 'branch' 형식으로 정제.
    HEAD 항목 제외.
    """
    code, out, _ = run_git(
        ["branch", "-r", "--contains", commit_hash],
        cwd=repo_path,
    )
    if code != 0 or not out:
        return []
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "HEAD" in line:
            continue
        if line.startswith("origin/"):
            line = line[len("origin/"):]
        branches.append(line)
    return branches


def get_remote_branches(repo_path: str) -> list[str]:
    """
    origin 원격 브랜치 전체 목록 반환.
    HEAD, claude/* 제외.
    """
    code, out, _ = run_git(["branch", "-r"], cwd=repo_path)
    if code != 0 or not out:
        return []
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "HEAD" in line:
            continue
        if line.startswith("origin/"):
            branch = line[len("origin/"):]
        else:
            branch = line
        if branch.startswith("claude/"):
            continue
        branches.append(branch)
    return branches


def fetch_origin(repo_path: str) -> None:
    """git fetch origin (한 번만 호출)"""
    run_git(["fetch", "origin", "--quiet"], cwd=repo_path)


def check_needs_pull(repo_path: str, branches: list[str]) -> list[str]:
    """
    pull이 필요한 브랜치 목록 반환 (behind > 0).
    fetch_origin()을 먼저 호출한 후 사용할 것.
    """
    needs_pull = []
    for branch in branches:
        code, out, _ = run_git(
            ["rev-list", "--count", f"origin/{branch}"],
            cwd=repo_path,
        )
        # origin/branch가 없으면 skip
        if code != 0:
            continue
        # 로컬 브랜치 존재 확인
        code2, _, _ = run_git(["rev-parse", "--verify", branch], cwd=repo_path)
        if code2 != 0:
            # 로컬 없음 → pull 필요
            needs_pull.append(branch)
            continue
        code3, count_str, _ = run_git(
            ["rev-list", "--count", f"{branch}..origin/{branch}"],
            cwd=repo_path,
        )
        try:
            behind = int(count_str)
        except ValueError:
            behind = 0
        if behind > 0:
            needs_pull.append(branch)
    return needs_pull


def run_autopull(target_branches: list[str], log_queue: queue.Queue) -> None:
    """autopull의 Puller를 직접 임포트하여 pull 실행"""
    autopull_dir = str(Path(__file__).parent.parent / "autopull")
    if autopull_dir not in sys.path:
        sys.path.insert(0, autopull_dir)
    from autopull import Puller, load_config as autopull_load_config  # type: ignore

    cfg = autopull_load_config()
    puller = Puller(
        repo_root=cfg["repo_root"],
        sibling_repos=cfg.get("sibling_repos", []),
        branches=target_branches,
        log_queue=log_queue,
    )
    puller.run()


# ─── Lock ─────────────────────────────────────────────────────────────────────

class LockError(Exception):
    pass


def acquire_lock() -> None:
    if LOCK_FILE.exists():
        raise LockError("이미 실행 중입니다. 잠시 후 다시 시도하세요.")
    LOCK_FILE.write_text("locked", encoding="utf-8")


def release_lock() -> None:
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


# ─── 데이터 클래스 ─────────────────────────────────────────────────────────────

@dataclass
class BranchResult:
    branch: str
    status: Literal["success", "failed", "skipped"] = "failed"
    message: str = ""
    new_commit: str = ""  # cherry-pick 후 새 커밋 해시


# ─── CherryPickPropagator ─────────────────────────────────────────────────────

class CherryPickPropagator:
    def __init__(
        self,
        repo_path: str,
        commit_hash: str,
        targets: list[str],
        log_queue: queue.Queue,
    ):
        self.repo_path = repo_path
        self.commit_hash = commit_hash
        self.targets = targets
        self.log_queue = log_queue
        self.results: list[BranchResult] = []

    def log(self, msg: str) -> None:
        self.log_queue.put(msg)

    def run(self) -> None:
        orig = current_branch(self.repo_path)
        try:
            acquire_lock()
            self._run_inner()
        except LockError as e:
            self.log(f"[오류] {e}")
        except Exception as e:
            self.log(f"[오류] 예상치 못한 오류: {e}")
        finally:
            release_lock()
            self.log(f"\n원래 브랜치로 복귀: {orig}")
            run_git(["checkout", orig], cwd=self.repo_path)
            self.log("✅ 모든 작업 완료!")

    def _run_inner(self) -> None:
        self.log(f"커밋: {self.commit_hash}")
        self.log(f"타겟 브랜치: {', '.join(self.targets)}\n")
        for branch in self.targets:
            self.log(f"══ {branch} {'═' * max(1, 40 - len(branch))}")
            result = self._process_branch(branch)
            self.results.append(result)

    def _process_branch(self, branch: str) -> BranchResult:
        result = BranchResult(branch=branch)

        # 1. checkout
        code, _, err = run_git(["checkout", branch], cwd=self.repo_path)
        if code != 0:
            result.status = "failed"
            result.message = f"checkout 실패: {err[:200]}"
            self.log(f"  ❌ {result.message}")
            return result

        # 2. pull
        code, _, err = run_git(["pull", "origin", branch], cwd=self.repo_path)
        if code != 0:
            result.status = "failed"
            result.message = f"pull 실패: {err[:200]}"
            self.log(f"  ❌ {result.message}")
            return result

        # 3. cherry-pick
        code, out, err = run_git(
            ["cherry-pick", "-x", self.commit_hash],
            cwd=self.repo_path,
        )

        if code == 0:
            # 성공
            _, new_hash, _ = run_git(
                ["rev-parse", "--short", "HEAD"], cwd=self.repo_path
            )
            result.new_commit = new_hash
            self.log(f"  ✅ cherry-pick 성공 [{new_hash}]")
        else:
            combined = (out + err).lower()

            # 이미 적용된 커밋 감지
            if "already applied" in combined or "now empty" in combined or "empty commit" in combined:
                run_git(["cherry-pick", "--skip"], cwd=self.repo_path)
                result.status = "skipped"
                result.message = "이미 적용된 커밋"
                self.log(f"  ⏭️ 스킵 — 이미 적용됨")
                return result

            # 충돌 발생 — 바이너리 자동 해결 시도
            self.log(f"  ⚠️ 충돌 감지, 자동 해결 시도...")
            resolved = self._resolve_binary_conflict()
            if resolved:
                # 계속 진행
                code2, out2, err2 = run_git(
                    ["cherry-pick", "--continue", "--no-edit"],
                    cwd=self.repo_path,
                )
                if code2 == 0:
                    _, new_hash, _ = run_git(
                        ["rev-parse", "--short", "HEAD"], cwd=self.repo_path
                    )
                    result.new_commit = new_hash
                    self.log(f"  ✅ 충돌 자동 해결 후 성공 [{new_hash}]")
                else:
                    run_git(["cherry-pick", "--abort"], cwd=self.repo_path)
                    result.status = "failed"
                    result.message = f"--continue 실패: {err2[:200]}"
                    self.log(f"  ❌ {result.message}")
                    return result
            else:
                # 텍스트 충돌 — abort
                run_git(["cherry-pick", "--abort"], cwd=self.repo_path)
                result.status = "failed"
                result.message = f"텍스트 충돌 — 수동 해결 필요: {err[:200]}"
                self.log(f"  ❌ {result.message}")
                return result

        # 4. push
        code, _, err = run_git(
            ["push", "origin", branch], cwd=self.repo_path
        )
        if code != 0:
            result.status = "failed"
            result.message = f"push 실패: {err[:200]}\n로컬 커밋 [{result.new_commit}] 수동 push 필요"
            self.log(f"  ❌ push 실패 [{result.new_commit}] — 수동 push 필요")
            return result

        self.log(f"  🚀 push 완료")
        result.status = "success"
        return result

    def _resolve_binary_conflict(self) -> bool:
        """
        충돌 파일 목록을 확인하여 전부 바이너리(xlsx/pb)이면
        --theirs로 자동 해결 후 True 반환.
        텍스트 충돌이 하나라도 있으면 False 반환.
        """
        code, out, _ = run_git(
            ["diff", "--name-only", "--diff-filter=U"],
            cwd=self.repo_path,
        )
        if code != 0 or not out:
            return False

        conflicted = [f for f in out.splitlines() if f.strip()]
        if not conflicted:
            return False

        BINARY_EXTS = {".xlsx", ".pb", ".bytes", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
        text_conflicts = [
            f for f in conflicted
            if Path(f).suffix.lower() not in BINARY_EXTS
        ]
        if text_conflicts:
            self.log(f"  텍스트 충돌 파일: {text_conflicts}")
            return False

        # 바이너리 전부 — theirs로 덮어쓰기
        self.log(f"  바이너리 충돌 파일: {conflicted} → theirs로 자동 해결")
        for f in conflicted:
            run_git(["checkout", "--theirs", f], cwd=self.repo_path)
        run_git(["add"] + conflicted, cwd=self.repo_path)
        return True


# ─── CherryPickThread ──────────────────────────────────────────────────────────

class CherryPickThread:
    def __init__(self, propagator: CherryPickPropagator):
        self.propagator = propagator
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        try:
            self.propagator.run()
        finally:
            self._done.set()

    def start(self) -> None:
        self._thread.start()

    def is_done(self) -> bool:
        return self._done.is_set()

    def join(self) -> None:
        self._thread.join()


# ─── Excel Diff ───────────────────────────────────────────────────────────────

def run_git_binary(args: list[str], cwd: str) -> tuple[int, bytes]:
    """바이너리 출력용 git 실행 (xlsx 로딩 등)"""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
    )
    return result.returncode, result.stdout


def load_xlsx_from_ref(
    repo_path: str, ref: str, xlsx_path: str
) -> Optional[object]:
    """git ref(커밋해시, 브랜치명 등)에서 xlsx를 openpyxl Workbook으로 로드"""
    code, data = run_git_binary(["show", f"{ref}:{xlsx_path}"], cwd=repo_path)
    if code != 0 or not data:
        return None
    try:
        return load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        return None


@dataclass
class CellChange:
    sheet: str
    row: int
    col: int
    col_header: str
    old_value: str
    new_value: str
    change_type: Literal["added", "changed", "removed"]


MAX_DIFF_CELLS = 500


def _read_sheet_data(ws) -> dict[tuple[int, int], str]:
    """시트의 모든 셀을 {(row, col): value_str} 딕셔너리로 반환"""
    data: dict[tuple[int, int], str] = {}
    for row in ws.iter_rows():
        for cell in row:
            val = cell.value
            if val is not None:
                data[(cell.row, cell.column)] = str(val)
    return data


def _get_headers(ws) -> dict[int, str]:
    """첫 번째 행에서 컬럼 헤더 추출"""
    headers: dict[int, str] = {}
    try:
        for cell in next(ws.iter_rows(min_row=1, max_row=1)):
            if cell.value is not None:
                headers[cell.column] = str(cell.value)
    except StopIteration:
        pass
    return headers


def diff_workbooks(
    old_wb, new_wb, old_label: str = "old", new_label: str = "new"
) -> list[CellChange]:
    """두 워크북의 모든 시트/셀을 비교하여 CellChange 목록 반환"""
    changes: list[CellChange] = []

    if old_wb is None and new_wb is None:
        return changes

    old_sheets = set(old_wb.sheetnames) if old_wb else set()
    new_sheets = set(new_wb.sheetnames) if new_wb else set()
    all_sheets = old_sheets | new_sheets

    for sheet_name in sorted(all_sheets):
        old_ws = old_wb[sheet_name] if old_wb and sheet_name in old_sheets else None
        new_ws = new_wb[sheet_name] if new_wb and sheet_name in new_sheets else None

        old_data = _read_sheet_data(old_ws) if old_ws else {}
        new_data = _read_sheet_data(new_ws) if new_ws else {}

        # 헤더는 new 우선, 없으면 old
        headers = _get_headers(new_ws) if new_ws else (_get_headers(old_ws) if old_ws else {})

        all_keys = set(old_data.keys()) | set(new_data.keys())
        for row, col in sorted(all_keys):
            old_val = old_data.get((row, col), "")
            new_val = new_data.get((row, col), "")
            if old_val == new_val:
                continue

            if not old_val:
                ct = "added"
            elif not new_val:
                ct = "removed"
            else:
                ct = "changed"

            changes.append(CellChange(
                sheet=sheet_name,
                row=row,
                col=col,
                col_header=headers.get(col, f"col{col}"),
                old_value=old_val,
                new_value=new_val,
                change_type=ct,
            ))

            if len(changes) >= MAX_DIFF_CELLS:
                return changes

    return changes


def _align_rows(
    old_data: dict[tuple[int, int], str],
    new_data: dict[tuple[int, int], str],
    header_row: int = 1,
) -> list[tuple[int | None, int | None]]:
    """
    LCS 기반 행 정렬. 첫 2컬럼 값 튜플을 키로 사용.
    반환: (old_row|None, new_row|None) 쌍 목록.
    None = 해당 쪽에 없는 행 (삽입 또는 삭제).
    """
    old_rows = sorted(set(r for r, c in old_data if r != header_row))
    new_rows = sorted(set(r for r, c in new_data if r != header_row))

    def row_key(data: dict, row: int) -> tuple:
        cols = sorted(c for r, c in data if r == row)
        key_cols = cols[:2]  # 최대 2컬럼
        return tuple(data.get((row, c), "") for c in key_cols)

    old_keys = [row_key(old_data, r) for r in old_rows]
    new_keys = [row_key(new_data, r) for r in new_rows]

    sm = difflib.SequenceMatcher(None, old_keys, new_keys, autojunk=False)
    aligned: list[tuple[int | None, int | None]] = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                aligned.append((old_rows[i], new_rows[j]))
        elif op == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                old_r = old_rows[i1 + k] if i1 + k < i2 else None
                new_r = new_rows[j1 + k] if j1 + k < j2 else None
                aligned.append((old_r, new_r))
        elif op == "delete":
            for i in range(i1, i2):
                aligned.append((old_rows[i], None))
        elif op == "insert":
            for j in range(j1, j2):
                aligned.append((None, new_rows[j]))

    return aligned


def compare_xlsx_side_by_side(
    old_wb, new_wb, max_rows: int = 200
) -> dict[str, str]:
    """
    두 워크북을 Beyond Compare 스타일 HTML 테이블로 비교.
    LCS 정렬로 삽입/삭제 행을 올바르게 처리. 변경 행만 표시.
    반환: {sheet_name: html_string}
    """
    results: dict[str, str] = {}

    if old_wb is None and new_wb is None:
        return results

    old_sheets = set(old_wb.sheetnames) if old_wb else set()
    new_sheets = set(new_wb.sheetnames) if new_wb else set()
    all_sheets = sorted(old_sheets | new_sheets)

    for sheet_name in all_sheets:
        old_ws = old_wb[sheet_name] if old_wb and sheet_name in old_sheets else None
        new_ws = new_wb[sheet_name] if new_wb and sheet_name in new_sheets else None

        old_data = _read_sheet_data(old_ws) if old_ws else {}
        new_data = _read_sheet_data(new_ws) if new_ws else {}
        headers = _get_headers(new_ws) if new_ws else (_get_headers(old_ws) if old_ws else {})

        # LCS 기반 행 정렬
        aligned = _align_rows(old_data, new_data)

        # 변경된 쌍만 필터 (equal 제외)
        changed_pairs: list[tuple[int | None, int | None]] = []
        for old_r, new_r in aligned:
            if old_r is None or new_r is None:
                changed_pairs.append((old_r, new_r))
                continue
            old_cols = {c: v for (r, c), v in old_data.items() if r == old_r}
            new_cols = {c: v for (r, c), v in new_data.items() if r == new_r}
            all_c = set(old_cols) | set(new_cols)
            if any(old_cols.get(c, "") != new_cols.get(c, "") for c in all_c):
                changed_pairs.append((old_r, new_r))

        if not changed_pairs:
            continue

        changed_pairs = changed_pairs[:max_rows]

        # 관련 컬럼 수집
        relevant_cols: set[int] = set(headers.keys())
        for old_r, new_r in changed_pairs:
            if old_r:
                relevant_cols.update(c for r, c in old_data if r == old_r)
            if new_r:
                relevant_cols.update(c for r, c in new_data if r == new_r)
        cols = sorted(relevant_cols)
        if not cols:
            continue

        html = _build_comparison_html(old_data, new_data, headers, cols, changed_pairs)
        results[sheet_name] = html

    return results


_compare_counter = 0


def _build_comparison_html(
    old_data: dict, new_data: dict, headers: dict,
    cols: list[int],
    aligned_pairs: list[tuple[int | None, int | None]],
) -> str:
    """좌우 비교 HTML — 단일 테이블 (행 높이 자동 일치)"""
    global _compare_counter
    _compare_counter += 1
    uid = f"bc{_compare_counter}"

    def _esc(v: str) -> str:
        return v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _trunc(v: str, n: int = 40) -> str:
        return v[:n] + "…" if len(v) > n else v

    def _get(data: dict, row: int | None, col: int) -> str:
        if row is None:
            return ""
        return _esc(_trunc(data.get((row, col), "")))

    n = len(cols)
    col_headers = [_esc(_trunc(headers.get(c, f"col{c}"), 20)) for c in cols]

    # --- thead: 2행 (레이블 + 컬럼 헤더) ---
    label_row = (
        f"<th colspan='{n + 1}' class='lbl'>◀ 이전 (왼쪽)</th>"
        f"<th class='dv' rowspan='2'></th>"
        f"<th colspan='{n + 1}' class='lbl'>▶ 이후 (오른쪽)</th>"
    )
    hdr_cells = "".join(f"<th>{h}</th>" for h in ["행"] + col_headers)
    header_html = (
        f"<thead><tr>{label_row}</tr>"
        f"<tr>{hdr_cells}{hdr_cells}</tr></thead>"
    )

    # --- tbody ---
    body_rows = []
    for old_r, new_r in aligned_pairs:
        row_added = old_r is None
        row_removed = new_r is None

        left_label = str(old_r) if old_r else ""
        right_label = str(new_r) if new_r else ""

        left_cells = [f"<td class='rn'>{left_label}</td>"]
        right_cells = [f"<td class='rn'>{right_label}</td>"]

        for c in cols:
            old_val = _get(old_data, old_r, c)
            new_val = _get(new_data, new_r, c)

            if row_added:
                left_cells.append("<td class='bg-del'></td>")
                right_cells.append(f"<td class='bg-add'>{new_val}</td>")
            elif row_removed:
                left_cells.append(f"<td class='bg-del'>{old_val}</td>")
                right_cells.append("<td class='bg-del'></td>")
            else:
                if old_val == new_val:
                    cls = ""
                elif not old_val:
                    cls = " class='bg-add'"
                elif not new_val:
                    cls = " class='bg-del'"
                else:
                    cls = " class='bg-chg'"
                left_cells.append(f"<td{cls}>{old_val}</td>")
                right_cells.append(f"<td{cls}>{new_val}</td>")

        body_rows.append(
            "<tr>"
            + "".join(left_cells)
            + "<td class='dv'></td>"
            + "".join(right_cells)
            + "</tr>"
        )

    css = f"""<style>
#{uid} table {{border-collapse:collapse;width:max-content}}
#{uid} th {{background:#f0f0f0;border:1px solid #ddd;padding:4px 6px;font-size:12px;white-space:nowrap;position:sticky;top:0;z-index:1}}
#{uid} th.lbl {{text-align:center;font-size:13px;background:#e8e8e8}}
#{uid} td {{border:1px solid #eee;padding:3px 6px;font-size:12px;white-space:nowrap}}
#{uid} td.dv, #{uid} th.dv {{width:4px;min-width:4px;max-width:4px;background:#999;border:none;padding:0}}
#{uid} td.rn {{font-weight:600;background:#fafafa}}
#{uid} .bg-add {{background:#d4edda}}
#{uid} .bg-del {{background:#f8d7da}}
#{uid} .bg-chg {{background:#fff3cd}}
#{uid} tr:hover td:not(.dv) {{background:#f5f5ff!important}}
</style>"""

    return (
        css
        + f"<div id='{uid}' style='overflow:auto;max-height:500px'>"
        + f"<table>{header_html}<tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )

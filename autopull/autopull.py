import subprocess
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml

# ─── Config ────────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "autopull_branches.yaml"

DEFAULT_CONFIG: dict = {
    "repo_root": "",
    "sibling_repos": [],
    "branches": [],
}

# 메시지 slice 상한 (git stderr 로그용)
ERR_MSG_SLICE_SHORT = 100
ERR_MSG_SLICE_MID = 150
ERR_MSG_SLICE_LONG = 200

# 로그 구분선 문자
DIVIDER_CHAR = "═"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **data}
    except (yaml.YAMLError, OSError):
        # 손상된 config 파일 → 기본값 fallback (앱 크래시 방지)
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> bool:
    """성공 시 True, 실패(권한/디스크 등) 시 False."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
        return True
    except OSError:
        return False


# ─── Git helpers ────────────────────────────────────────────────────────────────

def run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def current_branch(repo: str) -> str:
    r = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    return r.stdout.strip()


# ─── Pull status check ──────────────────────────────────────────────────────────

@dataclass
class BranchPullStatus:
    branch: str
    behind: int = 0  # 모든 저장소 behind 합산 (메인+sibling)
    local_missing: bool = False  # 메인 저장소 기준
    remote_missing: bool = False  # 메인 저장소 기준
    repo_behinds: dict[str, int] = field(default_factory=dict)  # 저장소 이름 → behind (상세)
    error: str = ""

    @property
    def is_uptodate(self) -> bool:
        return (
            self.behind == 0
            and not self.local_missing
            and not self.remote_missing
            and not self.error
        )


def _check_repo_behind(repo: str, branch: str) -> Optional[int]:
    """단일 저장소의 특정 브랜치에 대해 origin 대비 behind 커밋 수를 반환.

    반환값:
    - int: behind 커밋 수 (0이면 최신)
    - None: 원격 브랜치가 없거나 계산 불가 (skip 대상)

    로컬 브랜치가 없지만 원격에 있으면 1로 처리 (checkout 시 새로 생성되어야 함을 의미).

    성능: 사전 fetch 완료 상태를 전제로 로컬 ref만 조회 (네트워크 호출 없음).
    """
    # 원격 브랜치 존재 확인: fetch 이후 로컬 `origin/{branch}` ref 조회 (네트워크 X)
    # 이전 구현 `ls-remote`는 매번 network 호출 → 브랜치당 ~2초 병목 → rev-parse로 교체
    r_remote = run_git(["rev-parse", "--verify", f"origin/{branch}"], cwd=repo)
    if r_remote.returncode != 0:
        return None  # 이 저장소엔 해당 브랜치 없음

    # 로컬 존재 확인
    r_local = run_git(["rev-parse", "--verify", branch], cwd=repo)
    if r_local.returncode != 0:
        # 로컬 브랜치 없음 → checkout만 해도 할 일 → behind=1 처리 (sentinel)
        return 1

    # behind 카운트
    r_count = run_git(["rev-list", "--count", f"{branch}..origin/{branch}"], cwd=repo)
    try:
        return int(r_count.stdout.strip())
    except ValueError:
        return 0


def _fetch_repo(repo: str, log_queue: Optional[queue.Queue]) -> tuple[str, bool, str]:
    """단일 저장소 fetch. 병렬 실행용.

    `--prune`: 원격에서 삭제된 브랜치의 로컬 ref를 제거. 누락하면 stale `origin/{branch}`
    ref가 남아 `rev-parse --verify origin/{branch}`가 "존재함"으로 오판 → 원격 없는 브랜치를
    "최신"으로 잘못 표시하게 됨.

    반환: (repo_path, success, err_msg)
    """
    try:
        r = run_git(["fetch", "--all", "--prune", "--quiet"], cwd=repo)
        success = r.returncode == 0
        err = (r.stderr or "").strip()[:ERR_MSG_SLICE_MID] if not success else ""
    except (OSError, FileNotFoundError) as e:
        # 경로가 사라졌거나 git 실행 불가 — 병렬 map이 예외 전파로 중단되지 않도록 방어
        success = False
        err = f"경로 접근 불가: {str(e)[:ERR_MSG_SLICE_SHORT]}"
    if log_queue:
        if success:
            log_queue.put(f"원격 정보 가져오는 중: {Path(repo).name} ✓")
        else:
            log_queue.put(f"  [경고] {Path(repo).name} fetch 실패: {err}")
    return repo, success, err


def check_pull_status(
    repo: str,
    branches: list[str],
    sibling_repos: Optional[list[str]] = None,
    log_queue: Optional[queue.Queue] = None,
) -> list[BranchPullStatus]:
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)

    # 존재하는 sibling repo만 필터 (None/빈 문자열/경로 없음 제거)
    valid_siblings = [
        s for s in (sibling_repos or []) if s and Path(s).exists()
    ]
    all_repos = [repo] + valid_siblings

    # 모든 저장소 fetch 병렬 실행 (네트워크 I/O → ThreadPool로 Wall-clock 단축)
    log(f"원격 정보 가져오는 중 (병렬, {len(all_repos)}개 저장소)...")
    with ThreadPoolExecutor(max_workers=len(all_repos)) as ex:
        list(ex.map(lambda r: _fetch_repo(r, log_queue), all_repos))

    results: list[BranchPullStatus] = []
    for branch in branches:
        status = BranchPullStatus(branch=branch)

        # 메인 저장소: remote/local 존재 확인 (missing은 메인 기준으로만 판정)
        # 원격 존재 확인은 로컬 `origin/{branch}` ref로 판정 (fetch 이후엔 신뢰 가능)
        r_remote = run_git(
            ["rev-parse", "--verify", f"origin/{branch}"], cwd=repo
        )
        if r_remote.returncode != 0:
            status.remote_missing = True
            results.append(status)
            continue

        r_local = run_git(["rev-parse", "--verify", branch], cwd=repo)
        if r_local.returncode != 0:
            status.local_missing = True
            results.append(status)
            continue

        # 메인 저장소 behind 카운트
        r_count = run_git(
            ["rev-list", "--count", f"{branch}..origin/{branch}"], cwd=repo
        )
        try:
            status.repo_behinds[Path(repo).name] = int(r_count.stdout.strip())
        except ValueError:
            status.repo_behinds[Path(repo).name] = 0

        # Sibling 저장소도 검사 (버그 fix: 이전엔 누락되어 "최신"으로 오판)
        for sibling in valid_siblings:
            sibling_behind = _check_repo_behind(sibling, branch)
            if sibling_behind is None:
                continue  # 이 sibling엔 브랜치 없음 → 무관 repo, skip
            status.repo_behinds[Path(sibling).name] = sibling_behind

        # 모든 저장소 behind 합산
        status.behind = sum(status.repo_behinds.values())

        # 디버그 로그: 저장소별 상세
        if any(b > 0 for b in status.repo_behinds.values()):
            detail = ", ".join(
                f"{name}={n}" for name, n in status.repo_behinds.items() if n > 0
            )
            log(f"  {branch}: {detail}")

        results.append(status)

    log("상태 확인 완료.")
    return results


# ─── Pull logic ───────────────────────────────────────────────────────────────────

@dataclass
class BranchResult:
    branch: str
    success: bool = False
    error_stage: str = ""
    error_detail: str = ""


class Puller:
    def __init__(
        self,
        repo_root: str,
        sibling_repos: list[str],
        branches: list[str],
        log_queue: queue.Queue,
    ):
        self.repo_root = repo_root
        self.sibling_repos = [s for s in sibling_repos if s]
        # main을 항상 맨 앞으로
        ordered = [b for b in branches if b == "main"]
        ordered += [b for b in branches if b != "main"]
        self.branches = ordered
        self.log_queue = log_queue
        self.results: list[BranchResult] = []

    def log(self, msg: str) -> None:
        self.log_queue.put(msg)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.repo_root or not Path(self.repo_root).exists():
            errors.append(f"저장소 경로를 찾을 수 없음: {self.repo_root}")
        if not self.branches:
            errors.append("브랜치를 1개 이상 선택해주세요.")
        return errors

    def run(self) -> None:
        errors = self.validate()
        if errors:
            for e in errors:
                self.log(f"[오류] {e}")
            return

        orig = current_branch(self.repo_root)
        self.log(f"현재 브랜치: {orig}\n")

        for branch in self.branches:
            self.log(f"{DIVIDER_CHAR * 2} {branch} {DIVIDER_CHAR * (40 - len(branch))}")
            result = self._process_branch(branch)
            self.results.append(result)

        # 원래 브랜치 복원
        self.log(f"\n원래 브랜치로 복원: {orig}")
        r = run_git(["checkout", orig], cwd=self.repo_root)
        if r.returncode != 0:
            self.log(f"  [경고] 원래 브랜치 복원 실패: {r.stderr.strip()[:ERR_MSG_SLICE_SHORT]}")

        self.log("\n\u2705 모든 작업 완료!")

    def _process_branch(self, branch: str) -> BranchResult:
        result = BranchResult(branch=branch)

        # ── Sibling repos ──────────────────────────────────────────────────────────────
        for sibling_path in self.sibling_repos:
            if not Path(sibling_path).exists():
                self.log(f"  [건너뜀] 경로 없음: {sibling_path}")
                continue
            name = Path(sibling_path).name
            r = run_git(["checkout", branch], cwd=sibling_path)
            if r.returncode != 0:
                self.log(f"  [{name}] checkout 실패 (브랜치 없음?) - 건너뜀")
                continue
            r = run_git(["pull", "origin", branch], cwd=sibling_path)
            if r.returncode != 0:
                self.log(f"  [{name}] pull 실패: {r.stderr.strip()[:ERR_MSG_SLICE_MID]}")
            else:
                out = r.stdout.strip() or "Already up to date."
                self.log(f"  [{name}] {out}")

        # ── Main repo ──────────────────────────────────────────────────────────────
        repo_name = Path(self.repo_root).name
        r = run_git(["checkout", branch], cwd=self.repo_root)
        if r.returncode != 0:
            result.error_stage = "git checkout"
            result.error_detail = r.stderr.strip()
            self.log(f"  [{repo_name}] checkout 실패: {result.error_detail[:ERR_MSG_SLICE_LONG]}")
            return result

        r = run_git(["pull", "origin", branch], cwd=self.repo_root)
        if r.returncode != 0:
            result.error_stage = "git pull"
            result.error_detail = r.stderr.strip()
            self.log(f"  [{repo_name}] pull 실패: {result.error_detail[:ERR_MSG_SLICE_LONG]}")
            return result

        out = r.stdout.strip() or "Already up to date."
        self.log(f"  [{repo_name}] {out}")
        result.success = True
        return result


# ─── Threads ──────────────────────────────────────────────────────────────────────

class PullerThread:
    def __init__(self, puller: Puller):
        self.puller = puller
        self._thread = threading.Thread(target=puller.run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def is_done(self) -> bool:
        return not self._thread.is_alive()

    def join(self) -> None:
        self._thread.join()


class StatusCheckerThread:
    def __init__(
        self,
        repo: str,
        branches: list[str],
        log_queue: queue.Queue,
        sibling_repos: Optional[list[str]] = None,
    ):
        self.repo = repo
        self.branches = branches
        self.log_queue = log_queue
        self.sibling_repos = sibling_repos or []
        self.statuses: list[BranchPullStatus] = []
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self.statuses = check_pull_status(
            self.repo,
            self.branches,
            sibling_repos=self.sibling_repos,
            log_queue=self.log_queue,
        )

    def start(self) -> None:
        self._thread.start()

    def is_done(self) -> bool:
        return not self._thread.is_alive()

    def join(self) -> None:
        self._thread.join()

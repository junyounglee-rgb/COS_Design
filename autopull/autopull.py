import subprocess
import threading
import queue
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


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **data}
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


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
    behind: int = 0
    local_missing: bool = False
    remote_missing: bool = False
    error: str = ""

    @property
    def is_uptodate(self) -> bool:
        return (
            self.behind == 0
            and not self.local_missing
            and not self.remote_missing
            and not self.error
        )


def check_pull_status(
    repo: str,
    branches: list[str],
    log_queue: Optional[queue.Queue] = None,
) -> list[BranchPullStatus]:
    def log(msg: str):
        if log_queue:
            log_queue.put(msg)

    log("원격 정보 가져오는 중 (fetch)...")
    run_git(["fetch", "--all", "--quiet"], cwd=repo)

    results: list[BranchPullStatus] = []
    for branch in branches:
        # remote 존재 확인
        r_remote = run_git(["ls-remote", "--heads", "origin", branch], cwd=repo)
        if not r_remote.stdout.strip():
            results.append(BranchPullStatus(branch=branch, remote_missing=True))
            continue

        # local 존재 확인
        r_local = run_git(["rev-parse", "--verify", branch], cwd=repo)
        if r_local.returncode != 0:
            results.append(BranchPullStatus(branch=branch, local_missing=True))
            continue

        # behind 카운트
        r_count = run_git(["rev-list", "--count", f"{branch}..origin/{branch}"], cwd=repo)
        try:
            behind = int(r_count.stdout.strip())
        except ValueError:
            behind = 0
        results.append(BranchPullStatus(branch=branch, behind=behind))

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
            self.log(f"══ {branch} {'\u2550' * (40 - len(branch))}")
            result = self._process_branch(branch)
            self.results.append(result)

        # 원래 브랜치 복원
        self.log(f"\n원래 브랜치로 복깰: {orig}")
        r = run_git(["checkout", orig], cwd=self.repo_root)
        if r.returncode != 0:
            self.log(f"  [경고] 원래 브랜치 복깰 실패: {r.stderr.strip()[:100]}")

        self.log("\n\u2705 모든 작업 완료!")

    def _process_branch(self, branch: str) -> BranchResult:
        result = BranchResult(branch=branch)

        # ── Sibling repos ──────────────────────────────────────────────────────────────
        for sibling_path in self.sibling_repos:
            if not Path(sibling_path).exists():
                self.log(f"  [건너롁] 경로 없음: {sibling_path}")
                continue
            name = Path(sibling_path).name
            r = run_git(["checkout", branch], cwd=sibling_path)
            if r.returncode != 0:
                self.log(f"  [{name}] checkout 실패 (브랜치 없음?) - 건너롁")
                continue
            r = run_git(["pull", "origin", branch], cwd=sibling_path)
            if r.returncode != 0:
                self.log(f"  [{name}] pull 실패: {r.stderr.strip()[:150]}")
            else:
                out = r.stdout.strip() or "Already up to date."
                self.log(f"  [{name}] {out}")

        # ── Main repo ──────────────────────────────────────────────────────────────
        repo_name = Path(self.repo_root).name
        r = run_git(["checkout", branch], cwd=self.repo_root)
        if r.returncode != 0:
            result.error_stage = "git checkout"
            result.error_detail = r.stderr.strip()
            self.log(f"  [{repo_name}] checkout 실패: {result.error_detail[:200]}")
            return result

        r = run_git(["pull", "origin", branch], cwd=self.repo_root)
        if r.returncode != 0:
            result.error_stage = "git pull"
            result.error_detail = r.stderr.strip()
            self.log(f"  [{repo_name}] pull 실패: {result.error_detail[:200]}")
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
    def __init__(self, repo: str, branches: list[str], log_queue: queue.Queue):
        self.repo = repo
        self.branches = branches
        self.log_queue = log_queue
        self.statuses: list[BranchPullStatus] = []
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self.statuses = check_pull_status(self.repo, self.branches, self.log_queue)

    def start(self) -> None:
        self._thread.start()

    def is_done(self) -> bool:
        return not self._thread.is_alive()

    def join(self) -> None:
        self._thread.join()

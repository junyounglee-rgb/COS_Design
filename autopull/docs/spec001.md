# spec001 — autopull UX 개선

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-07 |
| 대상 파일 | `app_autopull.py`, `install.bat`, `사용가이드.txt` |
| 상태 | 완료 |

---

## 배경

autopull 프로그램(Streamlit 기반 Git 자동 풀 도구)의 UX 개선 및 버그 수정 2건 요청.

---

## 변경 1 — 상태 확인 버튼 로딩 피드백

### 문제
- 상태 확인 버튼 클릭 후 fetch 완료까지 무반응
- 버튼이 활성 상태여서 중복 클릭 가능

### 해결
- `pending_status_check` 플래그 도입 (`pending_pull` 패턴과 동일)
- 클릭 즉시 `pending=True` → rerun → UI 렌더 → 버튼 비활성화
- 버튼이 **"로딩중..."** 표시되는 시점에 thread 시작 (fetch 실행)
- 브랜치 목록 위에 `st.info()` 로딩 메시지 추가
- `st.rerun()`을 스크립트 맨 아래로 이동 (UI 렌더 전 조기 rerun 방지)

### 실행 흐름
```
클릭 → pending=True → rerun
  → thread 시작(rerun 없음) → UI 전체 렌더 → 버튼 "로딩중..." 표시
  → 맨 아래 폴링 rerun → fetch 진행
  → 완료 → checker_done → rerun → 상태 배지 갱신
```

### 수정 내용 (`app_autopull.py`)
| 위치 | 변경 내용 |
|------|-----------|
| `_init()` | `pending_status_check: False` 추가 |
| `checker_running` 계산 | `pending_status_check` 플래그 포함 |
| pending 핸들러 | thread 시작 후 rerun 없이 렌더 계속 |
| checker 완료 처리 | 상단에서 state 갱신만, rerun은 하단으로 이동 |
| 스크립트 하단 | status checker 폴링 rerun 블록 추가 |

---

## 변경 2 — install.bat Python 환경 생성 실패 안내

### 문제
- Step 2 실패 시 `[ERROR]` 메시지만 출력, 해결 방법 없음
- 비개발자 사용자가 대처 불가

### 해결
- Python 환경 생성 실패 시 python.org 다운로드 링크 안내

```bat
echo  Please install Python 3.12 manually and try again:
echo    https://www.python.org/downloads/
```

---

## 버그 수정 — install.bat 인코딩/줄바꿈 문제

### 문제
1. **LF 줄바꿈 혼입** — Write/Edit 도구로 수정 시 LF가 섞임
   cmd.exe가 줄을 파싱 못해 단어 조각(`xist`, `UV_EXE`, `_ok`, `tep2` 등)이 명령어로 실행됨

2. **`>/dev/null` 혼입** — bash 환경에서 `>nul`이 `>/dev/null`로 치환됨
   → 실행 시 "지정된 경로를 찾을 수 없습니다" 오류
   → `nulnif` 잔여 파일 생성

3. **한국어 인코딩 충돌** — bat 파일 내 한국어(UTF-8)가 cmd.exe CP949와 충돌해 글자 깨짐

### 해결
- bat 파일 전체를 PowerShell로 **ASCII + CRLF** 형식으로 재작성
- `>/dev/null` → `>nul` 전체 치환
- 한국어 echo 메시지 → 영어로 교체
- `nulnif` 잔여 파일 삭제
- bat 파일 작성 규칙 memory에 등록 (`feedback_bat_file_rules.md`)

---

## 문서 업데이트

**`사용가이드.txt`** — 트러블슈팅 섹션에 항목 추가
```
Q. install.bat 실행 시 Python 환경 생성 실패
→ https://www.python.org/downloads/ 에서 Python 3.12 설치 후 재시도
```

---

## 개선 2차 (2026-04-23)

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-23 |
| 대상 파일 | `app_autopull.py` |
| 상태 | 완료 (qa-tool 9개 TC PASS) |

### 배경

autopull UX 이슈 4건 동시 개선 요청.

### 변경 1 — 설정 저장 시 토스트 + expander 자동 닫힘

**문제**: 저장 버튼 클릭 후 "저장됨" 메시지가 expander 안에만 뜨고, 열린 설정 창이 닫히지 않음.

**해결**:
- `settings_expanded` controlled state 도입 (session_state)
- 저장 시 `settings_expanded=False` 설정 + `st.rerun()` → expander 자동 닫힘
- `show_save_toast` 플래그 → `st.toast("✅ 저장 완료", icon="💾")` 호출을 expander 바깥에 배치 → 창이 닫힌 뒤에도 사용자가 확인 가능

### 변경 2 — Pull UI 순서 재배치 (Result 상단, Progress 하단)

**문제**: 기존 순서는 "진행 상황 → 결과"였는데 사용자가 결과를 찾기 어려움.

**해결**:
- Result 섹션을 Pull 버튼 직후로 이동 (Progress 섹션보다 위)
- Result 렌더 조건: `is_running or (puller_thread is not None and puller_thread.puller.results)`
- 중복되는 `st.info("풀 받는 중...")` 메시지 삭제

### 변경 3 — Pull 중 "⏳ 진행중..." 표시

**문제**: Pull 중엔 Result 영역이 비어있어 사용자가 "잘 되고 있는지" 헷갈림.

**해결**:
- Result 섹션을 항상 렌더 (진행 중이거나 결과 존재 시)
- `is_running=True`일 때 `st.info("⏳ 진행중...")` 표시
- 완료 시 `puller_thread.puller.results` 순회하며 각 브랜치 ✅/❌ 전환

### 변경 4 — Pull 완료 후 브랜치 배지 자동 갱신

**문제**: Pull 정상 완료 후에도 브랜치 배지가 "🔄 N커밋 대기"로 남아있어 성공 여부가 불분명함.

**해결**:
- `pull_completion_acked` 플래그 도입 (1회성 완료 이벤트 감지)
- 완료 감지 블록에서 `pending_status_check=True` 자동 세팅 + `st.rerun()` → StatusCheckerThread 재실행 → 배지 갱신
- `last_status_check`는 건드리지 않아 수동 버튼 쿨다운에 영향 없음

### 구조적 개선 (부수 효과)

| 항목 | 내용 |
|------|------|
| 로그 클리어 책임 이동 | `run_logs=[]` 클리어를 `pending_*` 핸들러에서 **버튼 클릭 핸들러**로 이동 → 자동 재확인 시 Pull 로그 보존 |
| Pull 버튼 disabled 조건 | `checker_running` 추가 → status check 중 Pull 클릭 방지 (thread 충돌 차단) |
| Thread 동기화 | `pending_pull` 핸들러에서 새 thread 생성 후 로컬 `puller_thread` 변수를 즉시 동기화 → 완료 감지 블록이 OLD thread 오감지하는 버그 차단 |

### 구현 세부 (파일 내 위치)

| 위치 | 구현 |
|------|------|
| `_init()` | `pull_completion_acked`, `show_save_toast`, `settings_expanded` 3개 state 추가 |
| Expander | `_expanded_state` 변수 계산 → `expanded` prop에 전달 |
| 저장 버튼 | `show_save_toast=True`, `settings_expanded=False` 세팅 후 rerun |
| 토스트 렌더 | Expander 블록 직후 `st.toast` 호출 |
| Pending pull 핸들러 | 로컬 `puller_thread = thread` 동기화 |
| 완료 감지 블록 | `puller_thread.is_done() and not pull_completion_acked` 조건 |
| Pull 버튼 | `disabled` 조건에 `checker_running` 추가 + 클릭 시 `run_logs=[]` |
| Result 섹션 | Progress 섹션보다 위에 배치, is_running 분기 |
| Progress 섹션 | Result 섹션 아래 배치, 기존 로직 유지 |

### QA 검증

qa-tool 에이전트 9개 TC **전원 PASS**:
- TC-01 설정 저장 흐름 / TC-02 Pull UI 순서 / TC-03 완료 시 결과 표시
- TC-04 자동 status 재확인 / TC-05 무한 rerun 방어 / TC-06 로그 보존
- TC-07 수동 쿨다운 유지 / TC-08 Pull 중복 클릭 방어 / TC-09 오류 케이스

---

## 개선 3차 (2026-04-23, Pull 버튼 + 최적화)

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-23 |
| 대상 파일 | `app_autopull.py`, `autopull.py` |
| 상태 | 완료 (qa-tool 검증 통과) |

### 배경

optimizer 에이전트의 코드 품질 분석 + 사용자의 "받을 풀 없음" UX 요청.

### 신규 기능 — Pull 버튼 "받을 풀 없음" 상태

**문제**: 모든 브랜치가 "✅ 최신"인데도 "🔽 풀 받기" 버튼이 활성화되어 사용자가 불필요하게 클릭.

**해결**:
- 선택된 브랜치가 모두 `is_uptodate=True` (status 확인 완료 + behind=0)이면:
  - 버튼 라벨 `"✨ 받을 풀 없음"` + `disabled=True`
- status 미확인이거나 하나라도 pending이면 기존 "🔽 풀 받기" 유지

**구현** (app_autopull.py):
```python
_all_uptodate = False
if selected_branches and st.session_state.pull_statuses:
    _statuses = [status_map.get(b) for b in selected_branches]
    if all(s is not None for s in _statuses):
        _all_uptodate = all(s.is_uptodate for s in _statuses)
```

### 코드 품질 개선 (optimizer 권고 반영)

| 항목 | 변경 |
|------|------|
| 오타 수정 | `복깰` → `복원`, `건너롁` → `건너뜀` (autopull.py) |
| `load_config` 예외 처리 | YAMLError/OSError 시 DEFAULT_CONFIG fallback (크래시 방지) |
| `save_config` 예외 처리 | OSError 시 False 반환, 저장 성공 여부 호출처에 전달 |
| 저장 토스트 분기 | 성공 "✅ 저장 완료" / 실패 "⚠️ 저장 실패 (권한/디스크 확인)" |
| 상수 도입 | `STATUS_COOLDOWN_SEC`, `POLL_INTERVAL_SEC`, `ERR_MSG_SLICE_SHORT/MID/LONG`, `DIVIDER_CHAR` |
| 큐 드레인 헬퍼 | `_drain_log_queue()` 함수로 4곳 중복 제거 |
| 폴링 주기 통일 | 0.4s/0.5s → `POLL_INTERVAL_SEC=0.5` 단일값 |

### 미반영 (리스크 대비 효과 낮음)

- `check_pull_status` subprocess 호출 수 감소 (#4): 브랜치당 3회 → 1회로 감소 가능하나, 변경 범위가 크고 10 브랜치 이하에서는 체감 차이 없어 보류
- 쿨다운 `time.sleep(1)+st.rerun()` 루프 제거: 기존 동작이 안정적이라 유지

### 성능 영향 예측

| 항목 | Before | After | 체감 변화 |
|------|--------|-------|-----------|
| Pull 완료 후 배지 갱신 | 사용자가 수동으로 "📡 상태 확인" 클릭 | 자동 재확인 (pull 완료 ≥ 1초) | ✅ UX 개선 (전 세션 이미 반영) |
| 최신 상태에서 Pull 클릭 | 가능 (불필요 git fetch/pull) | 버튼 disabled → 클릭 불가 | ✅ UX 개선 + ~2~5초 절감 (5브랜치 기준) |
| git subprocess 호출 수 | 동일 (변경 없음) | 동일 | — |
| 폴링 rerun 주기 | 0.4s/0.5s 혼용 | 0.5s 통일 | 미세하게 느려짐 (~100ms/cycle, 체감 없음) |
| Config 파일 손상 시 | 크래시 → 앱 시작 실패 | 기본값 fallback → 정상 동작 | ✅ 안정성 향상 |
| 코드 중복 (큐 드레인) | 4곳 복사됨 | 1개 헬퍼로 통합 | 유지보수성 향상 |

**총평**: 이번 개선은 **체감 속도가 아닌 UX·안정성·가독성** 중심. 유일한 실질 단축은 "최신 상태에서 불필요 Pull 클릭 차단" (브랜치당 git fetch 0.5~1초 × N 절감). 본격적인 성능 개선(브랜치 수 증가 시 subprocess overhead 감소)은 `check_pull_status` 재설계가 필요하며 추후 과제로 남김.

### QA 검증

qa-tool 에이전트 TC 체크:
- TC-A1/A2/A3 "받을 풀 없음" 3개 케이스 **PASS**
- TC-B1/B2/B3 예외 처리 + 토스트 분기 **PASS**
- TC-C1 큐 드레인 헬퍼 4곳 적용 **PASS**
- TC-C2 상수 적용 **PASS** (초기 WARN `[:200]` 하나 발견 → `ERR_MSG_SLICE_LONG` 적용하여 해결)
- TC-D 이전 9개 TC 회귀 테스트 **PASS**

---

## 개선 4차 (2026-04-24, 수동 상태 확인 결과 초기화)

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-24 |
| 대상 파일 | `app_autopull.py` |
| 상태 | 완료 (qa-tool 8개 TC PASS + P2 WARN 1건 fix 반영) |

### 배경

사용자 피드백: "풀을 한번 받은 상태에서 상태 확인 누르면 결과도 초기화 시켜줘. 기존 결과가 남아 있으니까 이상해 (오히려 '상태 확인이 잘 되었다.' 이렇게 결과에 표시 되는게 맞는거 같아.)"

### 신규 기능 — 수동 상태 확인 시 결과 섹션 교체

**문제**:
- Pull 완료 후 Result 섹션에 각 브랜치 ✅/❌ 결과가 남아있음
- 사용자가 잠시 후 수동으로 📡 상태 확인 버튼 눌러도 결과 섹션은 이전 Pull 결과 그대로 유지
- "상태 확인이 잘 되었는지" 여부가 모호함

**해결**:
- 수동 상태 확인 시 Pull 결과를 지우고 "✅ 상태 확인 완료" 단독 표시
- 자동 상태 재확인(Pull 완료 직후 자동 트리거) 경로는 Pull 결과 유지 + 배지만 갱신 (기존 개선 2차 동작 보존)

### 구현 방식

**2개 플래그 추가** (session_state):
```python
"manual_status_check_pending": False,  # 수동 상태 확인 진행 플래그 (완료 감지용)
"manual_status_check_done": False,     # 수동 상태 확인 완료 표시 플래그 (Result 섹션용)
```

**흐름**:
1. 📡 상태 확인 버튼 클릭:
   - `puller_thread = None` (이전 Pull 결과 강제 초기화)
   - `manual_status_check_pending = True` / `manual_status_check_done = False`
2. StatusCheckerThread 완료 시:
   - `manual_status_check_pending == True`이면 → `pending=False`, `done=True` 전환
   - 자동 경로(`pending_status_check=True`만 세팅된 경우)는 위 조건 불일치 → `done` 불변
3. Result 섹션 렌더 우선순위:
   - `is_running or puller_thread.puller.results` → Pull 결과 표시
   - elif `manual_status_check_done` → "✅ 상태 확인 완료" 표시
4. Pull 버튼 클릭 시 `manual_status_check_done=False` 리셋 (이전 완료 표시 제거)

### QA 발견 이슈 — Pull 진행 중 상태 확인 버튼 가드 (P2 WARN → Fix)

**문제**: 기존 코드는 상태 확인 버튼이 `checker_running`일 때만 비활성화. `is_running`(Pull 진행 중) 시엔 활성 상태 → 사용자가 실수로 클릭하면:
- `puller_thread=None`으로 참조 해제 → 진행 중 UI 완전 사라짐
- daemon PullerThread는 백그라운드에서 계속 git 명령 실행 → StatusCheckerThread의 fetch와 git 리소스 경합 가능성

**Fix** (`col_actions` 블록):
```python
_current_puller = st.session_state.puller_thread
pull_in_progress = _current_puller is not None and not _current_puller.is_done()

if checker_running:
    st.button("📡 확인 중...", disabled=True)
elif pull_in_progress:
    st.button("📡 Pull 진행 중...", disabled=True)  # 신규
elif on_cooldown:
    ...
elif st.button("📡 상태 확인"):
    ...
```

### 구현 세부 (파일 내 위치, `app_autopull.py`)

| 위치 | 구현 |
|------|------|
| `_init()` | `manual_status_check_pending`, `manual_status_check_done` 2개 state 추가 |
| checker 완료 블록 | `manual_status_check_pending`이 True였다면 `pending=False`, `done=True` 전환 |
| col_actions (버튼 분기) | `pull_in_progress` 체크 추가 → Pull 진행 중 버튼 비활성화 (W-02 fix) |
| 📡 상태 확인 버튼 핸들러 | `puller_thread=None`, `manual_status_check_pending=True`, `manual_status_check_done=False` 세팅 |
| Pull 버튼 핸들러 | `manual_status_check_done=False` 리셋 추가 |
| Result 섹션 | `elif st.session_state.manual_status_check_done:` 분기 추가 → "✅ 상태 확인 완료" 단독 표시 |

### QA 검증

qa-tool 에이전트 8개 TC:
- TC-A1 최초 진입 후 상태 확인 → "✅ 상태 확인 완료" **PASS**
- TC-A2 Pull 후 자동 재확인 → Pull 결과 유지 + 배지 갱신 **PASS**
- TC-A3 Pull 후 수동 상태 확인 → "✅ 상태 확인 완료"로 교체 **PASS**
- TC-A4 완료 표시 → 새 Pull 시 "⏳ 진행중..." 표시 **PASS**
- TC-A5 무한 rerun 방어 **PASS**
- TC-A6 로그 클리어 기존 동작 유지 **PASS**
- TC-A7 수동 쿨다운 유지 **PASS**
- TC-A8 `_all_uptodate` 로직 회귀 없음 **PASS**
- W-02 (P2 WARN) Pull 진행 중 상태 확인 버튼 가드 누락 → **Fix 반영 완료**

---

## 개선 5차 (2026-04-24, **치명적 버그 fix**: sibling repo 상태 미검사)

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-24 |
| 대상 파일 | `autopull.py`, `app_autopull.py` |
| 상태 | 완료 (qa-tool 10개 TC + 4개 EC PASS) |
| 심각도 | **P0 — 기능 불일치 버그** |

### 버그 증상

- 설정: `repo_root = cos-data`, `sibling_repos = [cos-common, cos-client]`
- cos-data의 main은 최신, cos-client의 main은 2 behind (Fork에서 확인)
- Auto Pull 도구: main 브랜치 **"✅ 최신"**으로 표시 → 사용자가 "받을 풀 없음"으로 봄
- 그러나 실제로 Pull 누르면 cos-client가 업데이트됨 → **상태 확인과 Pull 대상의 불일치**

### Root Cause

`check_pull_status(repo, branches, ...)`가 **메인 저장소(`repo_root`)만** 검사하고 `sibling_repos`는 무시.
반면 `Puller.run()`은 sibling repos도 동일 브랜치로 checkout+pull 수행.
두 로직이 서로 다른 저장소 집합을 대상으로 동작 → 정보 격차 발생.

### Fix 내용

**`autopull.py`** — `BranchPullStatus` 구조 확장 + `check_pull_status` 다중 저장소 지원
```python
@dataclass
class BranchPullStatus:
    branch: str
    behind: int = 0                                 # 모든 저장소 behind 합산
    local_missing: bool = False                     # 메인 기준
    remote_missing: bool = False                    # 메인 기준
    repo_behinds: dict[str, int] = field(default_factory=dict)  # 저장소별 상세
    error: str = ""
```

- `_check_repo_behind(repo, branch) -> Optional[int]` 헬퍼 분리
  - 원격 없음: `None` → skip
  - 로컬 없음: `1` sentinel (checkout만 해도 pull 필요)
  - 정상: `rev-list --count branch..origin/branch` 결과
- `check_pull_status(repo, branches, sibling_repos=None, log_queue=None)` 시그니처 확장
- 모든 저장소(메인 + sibling) fetch → 각 브랜치별 `repo_behinds` 수집 → `behind = sum(...)`
- fetch 실패 시 경고 로그 출력 (git 저장소 아닌 경로 감지)
- `StatusCheckerThread.__init__`에 `sibling_repos=None` 파라미터 추가, `_run()`에서 키워드로 전달

**`app_autopull.py`** — 호출부 수정 + UI 상세 표시
- `StatusCheckerThread(... sibling_repos=cfg.get("sibling_repos", []))` 전달
- 브랜치 라벨 하단에 `st.caption(f"　　↳ cos-client: 14 · cos-common: 1")` 저장소별 상세
- 정렬: behind 내림차순(많이 뒤처진 순) → 핵심 저장소가 먼저 보임

### 실제 실행 검증 (사용자 환경, 2026-04-24)

```
main:              behind=16, uptodate=False, repos={cos-data: 1, cos-common: 1, cos-client: 14}
release_istanbul:  behind=2,  uptodate=False, repos={cos-data: 0, cos-common: 0, cos-client: 2}
release_istanbul2: behind=0,  uptodate=True,  repos={cos-data: 0, cos-common: 0, cos-client: 0}
```

→ 이전엔 `{cos-data만 보고} behind=0 → "✅ 최신"` 오판. fix 후 sibling behind 포함하여 정확히 "🔄 16커밋 대기" 표시.

### QA 검증 (qa-tool 에이전트)

**정적 분석 TC (10/10 PASS)**:
- TC-S1 sibling 경로 존재 확인 필터링
- TC-S2 원격 브랜치 없는 sibling skip
- TC-S3 로컬 브랜치 없는 sibling → behind=1 sentinel
- TC-S4 `behind = sum(repo_behinds)` 합산 정확성
- TC-S5 `is_uptodate` 판정: sibling 하나라도 뒤처지면 False
- TC-S6 `remote_missing`/`local_missing` 메인 기준 의미 일관성
- TC-S7 `StatusCheckerThread` → `check_pull_status` 키워드 전달
- TC-S8 `sibling_repos=[]` 기본값 → 단일 저장소 기존 동작 호환
- TC-S9 UI caption: `n>0` 필터링 + 내림차순 정렬
- TC-S10 기존 개선 1~4차 기능 회귀 없음

**Edge case (4/4 PASS)**:
- EC-1 sibling_repos=None → `(sibling_repos or [])` 안전 처리
- EC-2 git 저장소 아닌 경로 → fetch 실패 경고 로그 (추가 개선)
- EC-3 다수 sibling 가독성 → behind 내림차순 정렬 (추가 개선)
- EC-4 브랜치가 메인에만 있고 sibling엔 없음 → sibling skip, 메인만 정상 처리

### 영향도

- **정확성**: 상태 확인 결과가 Pull 실제 대상과 완전 일치 → 사용자 신뢰 회복
- **UX**: 어느 저장소가 얼마나 뒤처져 있는지 caption으로 즉시 확인 가능
- **확장성**: `repo_behinds` dict 구조로 N개 sibling까지 지원

---

## 개선 6차 (2026-04-24, **성능 최적화**: 상태 확인 6.9× 가속)

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-24 |
| 대상 파일 | `autopull.py` |
| 상태 | 완료 (qa-tool 검증 + P2 회귀 fix 반영) |
| 측정 환경 | 브랜치 3개 × 저장소 3개 (cos-data/common/client) |

### 배경

5차 개선(sibling repo 검사 추가)으로 `check_pull_status` 호출 시간이 증가. 사용자 체감 피드백: "원격 상태 확인이 기존보다 너무 느려졌다".

### 프로파일링 (Before 실측)

| 단계 | 소요 시간 | 비중 |
|------|----------|------|
| fetch 순차 실행 (3 저장소) | 6.33s | 25% |
| **`ls-remote --heads origin {branch}` × 9회** | **~18s** | **71%** |
| rev-parse / rev-list | 0.8s | 3% |
| **총합** | **25.28s** | 100% |

**병목 원인**: `git ls-remote`는 fetch와 달리 **매번 원격 서버에 접속**하여 브랜치 리스트 조회 (브랜치당 ~2초 × 9회).

### 최적화 적용

#### Fix 1 — `ls-remote` → `rev-parse --verify origin/{branch}` (P0)

**핵심 아이디어**: `fetch --all --prune` 이후엔 로컬에 `refs/remotes/origin/{branch}` ref가 정확히 존재. 네트워크 호출 없이 로컬 ref만 조회.

```python
# Before (네트워크 호출, ~2초/회)
r_remote = run_git(["ls-remote", "--heads", "origin", branch], cwd=repo)
if not r_remote.stdout.strip(): ...

# After (로컬 ref 조회, 즉시 반환)
r_remote = run_git(["rev-parse", "--verify", f"origin/{branch}"], cwd=repo)
if r_remote.returncode != 0: ...
```

**효과**: 18s → 0.4s (~45× 가속)

#### Fix 2 — fetch 순차 → 병렬 실행 (ThreadPoolExecutor)

```python
from concurrent.futures import ThreadPoolExecutor

def _fetch_repo(repo, log_queue):
    try:
        r = run_git(["fetch", "--all", "--prune", "--quiet"], cwd=repo)
        ...
    except (OSError, FileNotFoundError) as e:
        # 경로 무효 시 병렬 map 전체 중단 방지
        ...

with ThreadPoolExecutor(max_workers=len(all_repos)) as ex:
    list(ex.map(lambda r: _fetch_repo(r, log_queue), all_repos))
```

**효과**: fetch 6.3s → ~2.9s (max, wall-clock, 2.2× 가속)

#### Fix 3 — `fetch --prune` 필수 옵션 추가 (P2 회귀 fix)

**문제**: `fetch --all`만으로는 원격에서 삭제된 브랜치의 로컬 tracking ref(stale `origin/{branch}`)가 남음. 이전 `ls-remote` 방식은 매번 원격 조회라 무관했지만, **Fix 1로 로컬 ref 조회로 바꾼 이상** stale ref를 "존재함"으로 오판 → 원격 없는 브랜치를 "최신"으로 잘못 표시하는 회귀 발생.

**Fix**: `fetch --all --prune --quiet` → stale remote-tracking ref 자동 제거. `ls-remote` 시절과 의미 동일.

#### Fix 4 — `_fetch_repo` OSError 방어 (P3)

병렬 map 실행 중 한 저장소에서 경로/권한 예외 발생 시 전체 실행이 중단되지 않도록 try-except로 방어.

### 최종 성능 실측 (최적화 후 3회 평균)

| 측정 | After |
|------|-------|
| Run 1 | 3.91s |
| Run 2 | 3.53s |
| Run 3 | 3.55s |
| **평균** | **3.67s** |

### Before/After 종합

| 지표 | Before | After | 개선 |
|------|--------|-------|------|
| **check_pull_status 전체** | **25.28s** | **3.67s** | **6.9×** |
| fetch (순차→병렬) | 6.33s | ~2.9s | 2.2× |
| 브랜치 존재 확인 | ~18s (`ls-remote`) | ~0.4s (로컬 ref) | ~45× |
| rev-parse/rev-list | 0.8s | 0.8s | — |

### 정확성 회귀 검증

실제 실행 결과 (사용자 환경):
```
main:              behind=2, uptodate=False, repos={cos-data: 0, cos-common: 0, cos-client: 2}
release_istanbul:  behind=0, uptodate=True,  repos={cos-data: 0, cos-common: 0, cos-client: 0}
release_istanbul2: behind=2, uptodate=False, repos={cos-data: 0, cos-common: 0, cos-client: 2}
```

cos-client의 sibling behind가 정상 포함됨 → 5차 fix와 동일하게 정확.

### QA 검증 (qa-tool)

| TC/EC | 결과 |
|---|---|
| TC-P1 `rev-parse --verify origin/*` 의미 동일 | PASS |
| TC-P2 stale ref 회귀 | **P2 발견 → `--prune` 추가로 해결** |
| TC-P3 ThreadPool thread-safety (`queue.Queue`) | PASS |
| TC-P4 `max_workers` 동적 | WARN(P3, 실전 문제 없음) |
| TC-P5 부분 실패 허용 | PASS |
| TC-P6 `log_queue=None` 가드 | PASS |
| EC-1 저장소 1개만 | PASS |
| EC-2 전체 fetch 실패 | PASS (경고 로그) |
| EC-3 원격 삭제된 브랜치 stale | **Fix 3으로 해결** |

### 영향도

- **체감 속도**: 25s → 3.7s (1/7 시간) — "느려졌다"는 사용자 피드백 해결
- **정확성**: 5차 fix의 sibling behind 검사 정확성 + `--prune`으로 삭제된 브랜치 판정까지 복구
- **안정성**: `_fetch_repo` OSError 방어로 경로 오류가 전체 실행을 중단시키지 않음

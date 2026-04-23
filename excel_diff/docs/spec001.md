# spec001 — excel_diff 스펙

## 개요

| 항목 | 내용 |
|------|------|
| 프로젝트 | excel_diff |
| 목적 | 커밋 전 로컬 xlsx 파일과 Git 원격(origin) 파일을 비교하는 Streamlit 툴 |
| 작성일 | 2026-04-23 |
| 최종 업데이트 | 2026-04-23 (헤더 행 감지·DRY 최적화 반영) |
| 작성자 | 이준영 (기획), Claude Code (구현) |
| 저장 경로 | `D:\claude_make\excel_diff\` |

---

## 파일 구성

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit 메인 앱 |
| `diff_core.py` | xlsx diff 코어 (LCS 기반 행 정렬, HTML 렌더링) — **cherry_pick.py가 공유 import** |
| `config.yaml` | 설정 (repo_path, excel_folder, branches) |
| `requirements.txt` | 의존성 목록 |
| `install.bat` | uv 기반 설치 (Python 3.12 venv) |
| `run.bat` | 실행 (포트 8507) |

---

## 의존성

| 패키지 | 버전 조건 |
|--------|-----------|
| streamlit | `>=1.37` |
| openpyxl | `>=3.1` |
| pyyaml | `>=6.0` |

---

## 설정 (Settings 패널)

| 항목 | 기본값 | 저장 방식 |
|------|--------|-----------|
| cos-data 리포지토리 경로 | — | `config.yaml` 영구 저장 |
| Excel 폴더 경로 | `{repo_path}\excel` (미입력 시 자동) | `config.yaml` 영구 저장 |
| 브랜치 목록 | config 값 + origin 원격 브랜치 동적 병합 | 런타임 병합 |

---

## 기능 명세

### 브랜치 선택

- 메인 UI에 selectbox 노출
- 비교 기준: `origin/{branch}`

### 파일 검색

- 검색어 입력 → excel 폴더 `rglob("*.xlsx")` 실시간 필터
- 최대 30개 radio 리스트 표시
- 선택 시 `session_state.selected_file` 저장
- 리포 내 상대경로 자동 계산

### 커밋 히스토리

| 항목 | 내용 |
|------|------|
| 조회 명령 | `git log origin/{branch} --follow --max-count=20` |
| 표시 항목 | short_hash, date(YYYY-MM-DD HH:MM), author, message |
| 페이징 | 20개 단위, `⬇ Load 20 more` 버튼 |
| 캐시 | `@st.cache_data(ttl=120)` |
| 트리거 | 파일 선택 즉시 자동 실행 |

### 일반 비교 모드 (server → local)

| 항목 | 내용 |
|------|------|
| 선택 방식 | 커밋 히스토리 radio (기본: 최신) |
| 실행 버튼 | `🔍 Compare` |
| 원격 파일 조회 | `git show {hash}:{rel_path}` |
| 로컬 파일 | 디스크에서 직접 읽기 |
| 캐시 | `@st.cache_data(ttl=300)` + `local_mtime` 파라미터로 파일 변경 시 무효화 |

### 버전간 비교 모드

| 항목 | 내용 |
|------|------|
| 진입 | `🔀 버전간 비교` 토글 버튼 |
| ① 선택 | 파란색 버튼으로 마킹 |
| ② 선택 | 주황색 버튼으로 마킹 |
| 실행 버튼 | `🔀 버전 비교하기` |
| 비교 대상 | 두 서버 버전 (로컬 파일 무관) |

---

## Diff 렌더링 (diff_core.py)

| 항목 | 내용 |
|------|------|
| 행 정렬 알고리즘 | `difflib.SequenceMatcher` (LCS 기반) |
| 레이아웃 | Beyond Compare 스타일 좌우 HTML 테이블 |
| 인라인 diff | 문자 단위 (삭제: 빨간/굵음, 삽입: 초록/굵음) |
| 스크롤 동기화 | JS `syncHeights()` + `syncTableSize()` + 좌우 스크롤 이벤트 동기화 |
| 표시 범위 | 변경 행만 표시, 변경 없는 시트 제외 |
| 최대 행 수 | `MAX_DIFF_ROWS = 200` |

### 헤더 행 감지 규칙 (`_detect_header_row`)

| 시트명 조건 | 헤더 행 | 데이터 시작 행 | 비고 |
|---|---|---|---|
| 시트명에 `#` 포함 | **1행** | 2행 | 주석용 시트 패턴 |
| 그 외 (일반 게임 데이터) | **3행** | 4행 | 1·2행은 주석/경로 메타 데이터 |

- `_align_rows()`는 `r > header_row` 조건으로 헤더 행 이하 전부 제외
- 일반 시트의 경우 `$filter`, `^key`, `#설명` 등이 3행에 위치

### 공유 구조 (DRY)

`diff_core.py`는 `excel_diff/app.py`와 `cherry_pick/cherry_pick.py`가 함께 사용하는 단일 진실 공급원(SSOT).

| 공유 심볼 | 용도 |
|---|---|
| `run_git_binary` | git subprocess 바이너리 호출 |
| `_read_sheet_data` | 시트 → `{(row, col): str}` |
| `_detect_header_row` | 시트명 → 헤더 행 번호 |
| `_get_headers` | 헤더 행 → `{col: 헤더명}` |
| `_align_rows` | LCS 기반 행 정렬 |
| `_build_comparison_html` | 좌우 비교 HTML + JS 생성 |
| `compare_xlsx_side_by_side` | 시트별 diff HTML dict |

`cherry_pick.py`는 `sys.path.insert`로 `excel_diff/` 경로를 추가한 뒤 위 심볼을 import.

---

## 에러 처리

| 상황 | 처리 방식 |
|------|-----------|
| 원격 파일 없음 | `_ERR_REMOTE` 센티널 반환 → 에러 메시지 표시 |
| 로컬 파일 없음/손상 | `_ERR_LOCAL` 센티널 반환 → 에러 메시지 표시 |
| 잘못된 리포 경로 | `is_git_repo()` 검사 후 에러 |
| xlsx 아닌 파일 | 확장자 검사 후 에러 |
| 리포 외부 경로 | `try_get_rel_path()` → `None` → 수동 입력 UI |
| 원격 브랜치 조회 실패 | `get_remote_branches()` stderr 캡처 → `st.warning`으로 원인 표시 |

---

## 동작 흐름

```
[Settings 패널]
  └─ repo_path, excel_folder, branches 설정 → config.yaml 저장

[메인 UI]
  ├─ 브랜치 selectbox 선택
  ├─ 파일 검색창 입력 → radio 리스트 필터링
  ├─ 파일 선택 → git log 자동 조회 → 커밋 히스토리 표시
  │
  ├─ [일반 비교 모드]
  │    └─ 커밋 radio 선택 → 🔍 Compare → git show vs 로컬 → diff HTML 렌더링
  │
  └─ [버전간 비교 모드]
       └─ ①/② 버튼으로 커밋 마킹 → 🔀 버전 비교하기 → diff HTML 렌더링
```

---

## 의존 관계

| 모듈 | 의존 대상 |
|------|-----------|
| `app.py` | `diff_core.py`, `config.yaml`, Git CLI |
| `diff_core.py` | `openpyxl`, `difflib` (stdlib) |
| `config.yaml` | — |
| `install.bat` | `uv`, Python 3.12 |
| `run.bat` | `.venv` (install.bat 선행 필요) |
| `cherry_pick/cherry_pick.py` | `diff_core.py` (sys.path 주입 후 import) |

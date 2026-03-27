# Excel 검색 프로그램 상세 기술 명세서

> 작성일: 2026-03-27
> 버전: 3.0
> 변경 이력: spec002 대비 추가/수정 — SQLite 스레딩 수정, 자동 인덱싱, 행 단위 결과 표시, 파일 단위 그룹 렌더링, 매칭 컬럼 색상 강조, 파일명 스타일링

---

## 개요

여러 Excel 파일에서 특정 값(숫자/텍스트)이 어느 파일/시트/컬럼에 있는지 빠르게 찾는 검색 도구.

### 핵심 요구사항

| 항목 | 내용 |
|------|------|
| UI | Streamlit (크롬 브라우저에서 실행) |
| Excel 읽기 | pandas + openpyxl |
| 인덱스 저장 | SQLite (빠른 재검색) |
| 검색 모드 | 정확 일치 / 부분 일치 선택 |
| 중복 결과 | 동일 값이 여러 파일/시트/컬럼에 존재할 경우 **모두 표시** |
| 결과 렌더링 | 파일 단위로 그룹화, 시트별 expander, `st.dataframe` 사용 |
| 파일 열기 | 결과 행의 "열기" 버튼 클릭 시 해당 Excel 파일을 OS 기본 앱으로 즉시 실행 |
| 결과 출력 | 매칭된 행의 전체 컬럼 데이터를 테이블로 표시 |
| 자동 인덱싱 | 인덱스 없는 상태에서 검색 시 자동으로 인덱싱 후 검색 |
| 파일 규모 | 현재 약 120개 xlsx, 계속 증가 예정 |
| 헤더 위치 | 3번째 행 고정 (1~2행은 설명 영역) |
| 지원 형식 | .xlsx 전용 |
| 폴더 설정 | config.txt 파일에서 읽기/쓰기 |
| 검색 제외 | config.txt에서 제외 파일 목록 관리 |

---

## 프로젝트 구조

```
excel_search/
├── app.py           # Streamlit UI (메인 앱)
├── indexer.py       # 엑셀 → SQLite 인덱싱 엔진
├── searcher.py      # 검색 엔진
├── config.py        # config.txt 읽기/쓰기
├── config.txt       # 사용자 설정 파일
├── index.db         # 자동 생성되는 인덱스 DB
├── requirements.txt
└── doc/
    ├── spec001.md
    ├── spec002.md
    └── spec003.md
```

---

## 1. 설정 파일 (config.txt)

### 형식

```
# 엑셀 파일이 있는 폴더 경로
EXCEL_FOLDER=D:\excel_files

# 검색 제외 파일 목록 (쉼표로 구분, 파일명만 기재)
EXCLUDE_FILES=dialog_groups.xlsx, other_file.xlsx
```

### config.py 명세

#### `load_config(config_path: str = "config.txt") -> dict`

- 역할: config.txt 파싱하여 dict 반환
- `#`으로 시작하는 줄은 주석으로 무시
- 파일이 없으면 기본값 반환
- 반환값:
  ```python
  {
      "excel_folder": str,        # 폴더 경로 (없으면 빈 문자열)
      "exclude_files": list[str]  # 제외 파일명 리스트 (없으면 빈 리스트)
  }
  ```

#### `save_config(config: dict, config_path: str = "config.txt") -> None`

- 역할: dict를 config.txt 형식으로 저장
- `exclude_files`는 쉼표로 join하여 저장

---

## 2. SQLite DB 스키마

### 2.1 테이블 설계

#### `files` 테이블 — 인덱싱된 파일 메타데이터

```sql
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT    NOT NULL UNIQUE,   -- 절대 경로
    file_name   TEXT    NOT NULL,          -- 파일명 (표시용)
    file_mtime  REAL    NOT NULL,          -- os.path.getmtime() 반환값
    indexed_at  TEXT    NOT NULL           -- ISO8601 문자열
);
```

#### `cells` 테이블 — 셀 값 인덱스 본체

```sql
CREATE TABLE IF NOT EXISTS cells (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    sheet_name  TEXT    NOT NULL,
    col_name    TEXT    NOT NULL,          -- 헤더(3번째 행) 기준 컬럼명
    col_index   INTEGER NOT NULL,          -- 0-based 컬럼 인덱스
    cell_value  TEXT,                      -- 모든 타입을 TEXT로 변환 저장
    row_index   INTEGER NOT NULL           -- 0-based 행 인덱스 (헤더 제외)
);
```

#### `col_data` 테이블 — 열 전체 데이터 캐시 (미사용, 하위 호환 보존)

```sql
CREATE TABLE IF NOT EXISTS col_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    sheet_name  TEXT    NOT NULL,
    col_name    TEXT    NOT NULL,
    col_index   INTEGER NOT NULL,
    all_values  TEXT    NOT NULL           -- JSON 직렬화 리스트
);
```

> spec003부터 `col_data`는 조회에 사용되지 않음. 인덱싱 시 여전히 기록되며 스키마는 유지.

#### `schema_version` 테이블

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
-- 초기값: version = 1
```

### 2.2 인덱스 설계

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_files_path ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_cells_value ON cells(cell_value);
CREATE UNIQUE INDEX IF NOT EXISTS idx_col_data_lookup
    ON col_data(file_id, sheet_name, col_index);

-- FTS5 부분 일치 검색용 가상 테이블
CREATE VIRTUAL TABLE IF NOT EXISTS cells_fts
    USING fts5(cell_value, content='cells', content_rowid='id');

-- FTS 동기화 트리거 (빈 문자열 제외)
CREATE TRIGGER IF NOT EXISTS cells_ai AFTER INSERT ON cells
    WHEN new.cell_value != ''
BEGIN
    INSERT INTO cells_fts(rowid, cell_value) VALUES (new.id, new.cell_value);
END;

CREATE TRIGGER IF NOT EXISTS cells_ad AFTER DELETE ON cells BEGIN
    INSERT INTO cells_fts(cells_fts, rowid, cell_value)
    VALUES ('delete', old.id, old.cell_value);
END;
```

---

## 3. indexer.py 명세

### 역할

- 지정 폴더의 모든 `.xlsx` 파일 스캔
- 변경된 파일만 재인덱싱 (파일 수정시간 비교)
- 삭제된 파일 DB에서 자동 제거 (CASCADE)
- 진행 상황을 콜백 함수로 외부(app.py)에 전달

### 함수 목록

#### `get_connection(db_path: str) -> sqlite3.Connection`

- SQLite 연결 생성 및 설정 적용
- `check_same_thread=False` — Streamlit 멀티스레드 환경 대응 **(spec003 추가)**
- `PRAGMA foreign_keys = ON`
- `PRAGMA journal_mode = WAL` (인덱싱 중 검색 동시 가능)
- `PRAGMA synchronous = NORMAL`

#### `init_db(conn: sqlite3.Connection) -> None`

- 스키마 초기화 및 마이그레이션
- 모든 테이블/인덱스/트리거를 `CREATE IF NOT EXISTS`로 생성

#### `scan_folder(folder_path: str, exclude_files: list[str] = []) -> list[str]`

- 폴더 내 `.xlsx` 파일 절대 경로 목록 반환
- `~$`로 시작하는 임시 파일 자동 제외
- `exclude_files`에 있는 파일명 제외

#### `get_indexed_files(conn: sqlite3.Connection) -> dict[str, tuple[int, float]]`

- 반환: `{file_path: (file_id, file_mtime)}`

#### `index_file(conn: sqlite3.Connection, file_path: str) -> tuple[bool, str]`

- 단일 Excel 파일 파싱 후 DB 삽입
- `header=2` 고정 (3번째 행이 헤더)
- `sheet_name=None` — 모든 시트 인덱싱
- 빈 셀: `fillna('')`로 처리
- 기존 레코드 있으면 DELETE 후 재삽입 (CASCADE)
- 성공: `(True, "")`, 실패: `(False, 에러메시지)`
- 처리 후 `del df; gc.collect()` 메모리 해제

#### `run_indexing(folder_path: str, db_path: str, exclude_files: list[str] = [], progress_callback=None) -> dict`

- 전체 인덱싱 오케스트레이션
- 신규/변경 파일만 인덱싱, 삭제된 파일 DB에서 제거
- `progress_callback(current: int, total: int, filename: str)` 호출
- 반환: `{"total": int, "indexed": int, "skipped": int, "failed": list[str]}`

---

## 4. searcher.py 명세

### 데이터 클래스 **(spec003 변경)**

```python
@dataclass
class SearchResult:
    file_path:      str
    file_name:      str
    sheet_name:     str
    col_name:       str           # 매칭된 컬럼명 (색상 강조에 사용)
    col_index:      int
    matched_values: list[str]     # 매칭된 셀 값 목록
    col_headers:    list[str]     # 시트의 전체 컬럼 헤더 목록 (col_index 순서)
    matched_rows:   list[dict]    # 매칭된 행 전체 데이터 [{col_name: value}, ...]
    match_count:    int           # __post_init__에서 len(matched_rows)로 자동 계산
```

> `col_all_values` 제거됨. 행 단위 전체 데이터(`matched_rows`)로 대체.

### 내부 함수

#### `_fetch_matched_rows(conn, file_id, sheet_name, row_indices) -> tuple[list[str], list[dict]]`

- 매칭된 `row_index` 목록으로 해당 행들의 전체 컬럼 데이터 조회
- 반환: `(col_headers, matched_rows)`
  - `col_headers`: 시트의 컬럼명 목록 (col_index 오름차순)
  - `matched_rows`: `[{col_name: cell_value, ...}, ...]` (row_index 오름차순)

#### `_parse_rows(conn, file_id, ..., matched_raw, row_indices_raw) -> SearchResult`

- SQL 결과 row → SearchResult 변환 공통 로직
- `GROUP_CONCAT(row_index)` 파싱 → `_fetch_matched_rows()` 호출

### 함수 목록

#### `search(conn, query, mode='exact', limit=1000) -> list[SearchResult]`

- `mode`: `'exact'` | `'partial'`
- 빈 쿼리면 빈 리스트 반환

#### `search_exact(conn, query, limit=1000) -> list[SearchResult]`

- SQL:
  ```sql
  SELECT f.id, f.file_path, f.file_name,
         c.sheet_name, c.col_name, c.col_index,
         GROUP_CONCAT(c.cell_value, '||SEP||') AS matched_values,
         GROUP_CONCAT(c.row_index,  '||SEP||') AS matched_row_indices
  FROM cells c JOIN files f ON c.file_id = f.id
  WHERE c.cell_value = ?
  GROUP BY f.id, c.sheet_name, c.col_index
  LIMIT ?
  ```

#### `search_partial(conn, query, limit=1000) -> list[SearchResult]`

- FTS5 prefix 검색 우선: `"query"*`
- FTS5 실패/결과 없으면 LIKE fallback: `%query%`
- 동일 SQL 구조 (`GROUP_CONCAT(row_index)` 포함)

#### `get_index_stats(conn) -> dict`

- 반환: `{"file_count": int, "cell_count": int, "last_indexed": str}`

---

## 5. app.py 명세 (Streamlit UI)

### 실행 방법

```bash
streamlit run app.py
```

### 화면 구성

```
┌──────────────────────────────────────────────────────────────┐
│  Excel 검색 도구                                              │
├──────────────────────┬───────────────────────────────────────┤
│  [사이드바 - 설정]    │  [메인 영역]                          │
│                      │                                       │
│  엑셀 폴더:          │  검색어: [________________]           │
│  [______________]    │  모드: ◉ 정확  ○ 부분                 │
│  [저장]              │  결과 제한: [1000]  [검색]            │
│                      │                                       │
│  제외 파일:          │  총 12건 (5개 파일에서 발견)           │
│  [______________]    │                                       │
│  [저장]              │  파일명(bold, 120%)    매칭수  열기    │
│                      │  ─────────────────────────────────    │
│  [인덱스 업데이트]   │  file1.xlsx (bold)       4    [📂]   │
│                      │    > Sheet1 — 3행 매칭               │
│  상태:               │    > Sheet2 — 1행 매칭               │
│  파일 120개          │  ─────────────────────────────────    │
│  셀 234,500개        │  file2.xlsx (bold)       2    [📂]   │
│  최종: 2026-03-27    │    > Sheet1 — 2행 매칭               │
│                      │                                       │
│                      │  [CSV 내보내기]                       │
└──────────────────────┴───────────────────────────────────────┘
```

### 주요 기능 구현 방식

| 기능 | 구현 방식 |
|------|-----------|
| 설정 로드 | 앱 시작 시 `config.py`로 `config.txt` 읽기 |
| 설정 저장 | 사이드바 수정 후 저장 → `config.txt` 업데이트 |
| 인덱스 업데이트 | `st.spinner()` + `st.progress()` |
| **자동 인덱싱** | 검색 버튼 클릭 시 `file_count == 0`이면 자동으로 `run_indexing()` 실행 후 검색 |
| 결과 렌더링 | 파일 단위 그룹화 → `render_file_group()` |
| 파일명 스타일 | `<span style="font-weight:bold; font-size:1.2em">` |
| 매칭 컬럼 강조 | `df.style.apply()` — `rgba(0, 180, 80, 0.25)` 반투명 녹색 |
| 중복 결과 표시 | 결과 상단에 "총 N건 (M개 파일에서 발견)" 표시 |
| 파일 열기 버튼 | `st.button("📂", key=f"open_{i}")` → `open_file(file_path)` |
| CSV 내보내기 | `st.download_button()` — 전체 중복 결과 포함 |

### 세션 상태 (`st.session_state`)

| 키 | 타입 | 설명 |
|----|------|------|
| `conn` | `sqlite3.Connection` | DB 연결 (앱 시작 시 초기화, `check_same_thread=False`) |
| `search_results` | `list[SearchResult]` | 현재 검색 결과 |
| `last_query` | `str` | 마지막 검색어 |
| `config` | `dict` | 현재 설정 값 |
| `config_path` | `str` | config.txt 경로 |
| `stats` | `dict` | 인덱스 통계 (`file_count`, `cell_count`, `last_indexed`) |

---

## 5-1. 결과 렌더링 명세 **(spec003 전면 개편)**

### 그룹화 구조

결과를 `file_path` 기준으로 그룹화하여 같은 파일의 결과를 하나의 블록으로 표시한다.

```python
grouped: dict[str, list[SearchResult]] = {}
for r in results:
    grouped.setdefault(r.file_path, []).append(r)
```

### `render_file_group(idx, file_path, file_results)` 구조

```
st.columns([5, 1, 1])
  col1: <span style="font-weight:bold; font-size:1.2em">파일명</span>
  col2: 총 매칭 수 (해당 파일 모든 시트 합산)
  col3: st.button("📂", key=f"open_{idx}")

for result in file_results:
    st.expander(f"📋 {result.sheet_name} — {result.match_count}행 매칭")
        → st.dataframe(df.style.apply(highlight_matched), hide_index=True)
```

### 매칭 컬럼 색상 강조

```python
def highlight_matched(col):
    return [
        "background-color: rgba(0, 180, 80, 0.25);" if col.name == matched_col else ""
        for _ in col
    ]

styled = df.style.apply(highlight_matched, axis=0)
st.dataframe(styled, use_container_width=True, hide_index=True)
```

- 매칭된 컬럼(`result.col_name`)만 반투명 녹색으로 표시
- 나머지 컬럼은 기본 색상 유지

### 페이지네이션

- 파일 그룹 50개까지 직접 표시
- 51번째 파일부터 `st.expander("결과 더 보기 (N개 파일)")` 안에 표시

---

## 5-2. 파일 열기 기능 명세

#### `open_file(file_path: str) -> None`

```python
def open_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        st.error(f"파일을 찾을 수 없습니다: {Path(file_path).name}")
        return
    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
    except Exception as e:
        st.error(f"파일 열기 실패: {e}")
```

---

## 5-3. 자동 인덱싱 동작 **(spec003 추가)**

검색 버튼 클릭 시 `st.session_state.stats["file_count"] == 0`이면:

```
1. 엑셀 폴더 경로 확인
   → 미설정: st.warning() 후 st.stop()
   → 폴더 없음: st.error() 후 st.stop()
2. run_indexing() 실행 (progress_callback 없이)
3. update_stats() 호출
4. 인덱싱 완료 후 검색 진행
```

---

## 5-4. 중복 결과 표시 규칙

- 검색 결과는 **절대 첫 번째 매칭에서 중단하지 않음**
- 동일 값이 여러 파일/시트/컬럼에 존재하면 조합마다 별도 결과로 표시
- 결과 요약: **"총 N건 (M개 파일에서 발견)"**
  - N: 전체 `SearchResult` 수
  - M: 고유 파일 수 (`len(set(r.file_path for r in results))`)
- expander 클릭 시 해당 시트에서 매칭된 행들의 **전체 컬럼 데이터** 테이블로 표시
- CSV 내보내기 시 **모든 중복 결과** 포함

---

## 6. 엣지 케이스 처리

| 상황 | 처리 방안 |
|------|-----------|
| 깨진/암호화된 파일 | `try/except`로 skip, `failed` 리스트에 추가 후 UI에 경고 표시 |
| 빈 셀 | `fillna('')` 후 저장, FTS 트리거에서 빈 문자열 제외 |
| `~$` 임시 파일 | `scan_folder()`에서 자동 제외 |
| 제외 파일 | `config.txt`의 `EXCLUDE_FILES`로 관리 |
| 인덱싱 중 검색 | WAL 모드로 동시 읽기/쓰기 가능 |
| SQLite 스레딩 | `check_same_thread=False`로 Streamlit 멀티스레드 환경 대응 |
| 삭제된 파일 | CASCADE 삭제로 관련 데이터 자동 정리 |
| Windows 경로 | `pathlib.Path`로 처리 |
| 한글 CSV 내보내기 | `encoding='utf-8-sig'` 사용 |
| 파일 열기 실패 | `os.path.exists()` 사전 확인 후 `st.error()` 안내 |
| 인덱스 없이 검색 | 자동 인덱싱 후 검색 진행 |
| 결과 50개 파일 초과 | `st.expander()`로 나머지 묶어서 렌더링 성능 확보 |

---

## 7. 의존성 (requirements.txt)

```
streamlit>=1.32.0
pandas>=2.1.0
openpyxl>=3.1.2
```

> `sqlite3`, `os`, `subprocess`, `sys`, `gc`, `pathlib`, `datetime`, `csv`, `dataclasses`는 Python 표준 라이브러리

### Python 버전

- Python 3.10 이상 권장

---

## 8. 모듈 의존성

```
app.py
  ├── config.py     (설정 읽기/쓰기)
  ├── indexer.py    (인덱싱 호출)
  └── searcher.py   (검색 호출)

indexer.py   → sqlite3, pandas, openpyxl, json, gc, pathlib, datetime
searcher.py  → sqlite3, dataclasses
config.py    → pathlib
```

`open_file()` 함수는 `app.py` 내에만 존재. `os`, `subprocess`, `sys` 사용.
의존 방향 단방향, 순환 참조 없음.

---

## 9. spec002 → spec003 변경 요약

| 항목 | 변경 전 (spec002) | 변경 후 (spec003) |
|------|------------------|------------------|
| SQLite 연결 | `sqlite3.connect(db_path)` | `sqlite3.connect(db_path, check_same_thread=False)` |
| 자동 인덱싱 | 없음 | 검색 시 인덱스 없으면 자동 실행 |
| SearchResult | `col_all_values: list[str]` | `col_headers: list[str]` + `matched_rows: list[dict]` |
| match_count 계산 | `len(matched_values)` | `len(matched_rows)` |
| expander 내용 | 단일 컬럼 전체 값 목록 | 매칭된 행들의 전체 컬럼 테이블 (`st.dataframe`) |
| 결과 레이아웃 | (파일, 시트, 컬럼) 단위 행 | 파일 단위 그룹 + 시트별 expander |
| expander 제목 | `파일명 / 시트명 — N행 매칭` | `시트명 — N행 매칭` |
| 매칭 컬럼 표시 | 없음 | 반투명 녹색 (`rgba(0, 180, 80, 0.25)`) |
| 파일명 스타일 | 일반 텍스트 | bold + font-size 1.2em |
| 결과 헤더 컬럼 | 파일명/시트명/컬럼명/매칭수/열기 | 파일명/매칭수/열기 |

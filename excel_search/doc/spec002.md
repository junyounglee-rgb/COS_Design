# Excel 검색 프로그램 상세 기술 명세서

> 작성일: 2026-03-27
> 버전: 2.0
> 변경 이력: spec001 대비 추가 — 결과 HTML 렌더링, 파일 직접 열기 기능

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
| 결과 렌더링 | HTML 테이블로 스타일링하여 표시 (`st.markdown` + `unsafe_allow_html`) |
| 파일 열기 | 결과 행의 "열기" 버튼 클릭 시 해당 Excel 파일을 OS 기본 앱으로 즉시 실행 |
| 결과 출력 | 파일명 + 시트명 + 컬럼명 + 해당 열 전체 데이터 |
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
    └── spec002.md
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

#### `col_data` 테이블 — 열 전체 데이터 캐시

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

### 데이터 클래스

```python
@dataclass
class SearchResult:
    file_path:      str
    file_name:      str
    sheet_name:     str
    col_name:       str
    col_index:      int
    matched_values: list[str]   # 매칭된 셀 값 목록
    col_all_values: list[str]   # 해당 컬럼 전체 데이터
    match_count:    int         # __post_init__에서 자동 계산
```

### 함수 목록

#### `search(conn, query: str, mode: str = 'exact', limit: int = 1000) -> list[SearchResult]`

- `mode`: `'exact'` | `'partial'`
- 빈 쿼리면 빈 리스트 반환
- `search_exact()` 또는 `search_partial()`로 분기

#### `search_exact(conn, query: str, limit: int = 1000) -> list[SearchResult]`

- `WHERE cell_value = :query`
- `GROUP BY file_id, sheet_name, col_index` — 파일/시트/컬럼 조합마다 **모두** 결과에 포함
- **중복 허용**: 동일 값이 100개 파일에 있으면 100개 행 반환 (limit 내에서)
- 각 결과에 `_fetch_col_data()` 호출하여 열 전체 데이터 추가

#### `search_partial(conn, query: str, limit: int = 1000) -> list[SearchResult]`

- FTS5 우선 시도: `WHERE cells_fts MATCH :fts_query`
- FTS5 결과 없으면 LIKE fallback: `WHERE cell_value LIKE '%query%'`
- 마찬가지로 **모든 파일/시트/컬럼**에서 매칭된 결과 전부 반환

#### `_fetch_col_data(conn, file_id: int, sheet_name: str, col_index: int) -> list[str]`

- `col_data` 테이블에서 JSON → `list[str]` 변환 반환
- 레코드 없으면 빈 리스트 반환

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
│  [저장]              │  ┌──────────┬──────┬──────┬───┬─────┐ │
│                      │  │ 파일명   │ 시트 │ 컬럼 │ 수│     │ │
│  [인덱스 업데이트]   │  ├──────────┼──────┼──────┼───┼─────┤ │
│                      │  │ file1    │Sheet1│ 코드 │ 3 │[열기]│ │
│  상태:               │  │ file2    │Sheet1│ ID   │ 1 │[열기]│ │
│  파일 120개          │  │ file2    │Sheet2│ 코드 │ 2 │[열기]│ │
│  셀 234,500개        │  └──────────┴──────┴──────┴───┴─────┘ │
│  최종: 2026-03-27    │                                       │
│                      │  ▼ [file1 / Sheet1 / 코드] 전체 데이터│
│                      │    value1                             │
│                      │    value2  ← 검색어 강조 표시         │
│                      │    value3                             │
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
| 검색 결과 렌더링 | `st.markdown(html, unsafe_allow_html=True)` — HTML 테이블로 스타일링 |
| 중복 결과 표시 | 결과 상단에 "총 N건 (M개 파일에서 발견)" 표시 |
| 파일 열기 버튼 | `st.button("📂 열기", key=f"open_{i}")` → `os.startfile(file_path)` |
| 컬럼 상세 데이터 | `st.expander()` — 검색어 강조(bold) 포함 |
| CSV 내보내기 | `st.download_button()` — 전체 중복 결과 포함 |

### 세션 상태 (`st.session_state`)

| 키 | 타입 | 설명 |
|----|------|------|
| `conn` | `sqlite3.Connection` | DB 연결 (앱 시작 시 초기화) |
| `search_results` | `list[SearchResult]` | 현재 검색 결과 |
| `config` | `dict` | 현재 설정 값 |

---

## 5-1. 결과 HTML 렌더링 명세

결과 테이블은 `st.dataframe()` 대신 `st.markdown()` + HTML로 직접 렌더링한다.

### HTML 테이블 구조

```html
<table style="width:100%; border-collapse:collapse; font-size:14px;">
  <thead>
    <tr style="background:#f0f2f6;">
      <th style="padding:8px; border:1px solid #ddd; text-align:left;">파일명</th>
      <th style="padding:8px; border:1px solid #ddd; text-align:left;">시트명</th>
      <th style="padding:8px; border:1px solid #ddd; text-align:left;">컬럼명</th>
      <th style="padding:8px; border:1px solid #ddd; text-align:center;">매칭 수</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#ffffff;">
      <td style="padding:8px; border:1px solid #ddd;">file1.xlsx</td>
      <td style="padding:8px; border:1px solid #ddd;">Sheet1</td>
      <td style="padding:8px; border:1px solid #ddd;">코드</td>
      <td style="padding:8px; border:1px solid #ddd; text-align:center;">3</td>
    </tr>
    <!-- 홀짝 행 배경색 교차: #ffffff / #f8f9fa -->
  </tbody>
</table>
```

- 파일명 열은 HTML 테이블에서 표시만 하고, "열기" 버튼은 `st.columns()`로 HTML 테이블 옆에 별도 배치

### 열기 버튼 렌더링 방식

Streamlit의 제약(HTML 내 클릭 이벤트 → Python 호출 불가)으로 인해, 결과 행마다 `st.columns()`를 사용하여 HTML 셀 + 버튼을 혼합 렌더링한다.

```
각 결과 행 = st.columns([3, 2, 2, 1, 1])
  col1: 파일명 (st.markdown)
  col2: 시트명 (st.markdown)
  col3: 컬럼명 (st.markdown)
  col4: 매칭 수 (st.markdown)
  col5: st.button("📂 열기", key=f"open_{i}")
```

- 결과 건수가 많을 때 성능 고려: 50건 이상이면 `st.expander("결과 더 보기")`로 나머지 묶기

---

## 5-2. 파일 열기 기능 명세

#### `open_file(file_path: str) -> None`

- 역할: OS 기본 애플리케이션(Excel)으로 파일 즉시 실행
- 구현:
  ```python
  import os, subprocess, sys

  def open_file(file_path: str) -> None:
      if sys.platform == "win32":
          os.startfile(file_path)
      elif sys.platform == "darwin":
          subprocess.Popen(["open", file_path])
      else:
          subprocess.Popen(["xdg-open", file_path])
  ```
- 파일이 존재하지 않으면 `st.error("파일을 찾을 수 없습니다: {file_name}")` 표시
- 예외 발생 시 `st.error()` 로 안내 후 중단 (프로그램 crash 방지)
- `app.py` 내에 정의하며 `searcher.py`, `indexer.py`에는 포함하지 않음

#### 버튼 동작 흐름

```
[📂 열기] 클릭
  → st.session_state에서 해당 SearchResult의 file_path 조회
  → os.path.exists(file_path) 확인
    → True: open_file(file_path) 호출
    → False: st.error() 표시
```

---

## 5-3. 중복 결과 표시 규칙

- 검색 결과는 **절대 첫 번째 매칭에서 중단하지 않음**
- 동일 값이 여러 파일/시트/컬럼에 존재하면 조합마다 별도 행으로 표시
- 결과 테이블 상단에 **"총 N건 (M개 파일에서 발견)"** 요약 표시
  - N: 전체 결과 행 수 (파일×시트×컬럼 조합 수)
  - M: 결과에 포함된 고유 파일 수
- 결과 테이블 컬럼 구성:

| 컬럼 | 설명 |
|------|------|
| 파일명 | Excel 파일명 |
| 시트명 | 시트명 |
| 컬럼명 | 헤더(3행) 기준 컬럼명 |
| 매칭 수 | 해당 컬럼에서 검색어가 발견된 횟수 |
| 열기 | 파일 직접 열기 버튼 |

- 행 클릭(expander) 시 해당 컬럼의 **전체 데이터** 표시, 검색어 bold 강조
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
| 삭제된 파일 | CASCADE 삭제로 관련 데이터 자동 정리 |
| Windows 경로 | `pathlib.Path`로 처리 |
| 한글 CSV 내보내기 | `encoding='utf-8-sig'` 사용 |
| 파일 열기 실패 | `os.path.exists()` 사전 확인 후 `st.error()` 안내 |
| 결과 50건 초과 | `st.expander()`로 나머지 묶어서 렌더링 성능 확보 |

---

## 7. 의존성 (requirements.txt)

```
streamlit>=1.32.0
pandas>=2.1.0
openpyxl>=3.1.2
```

> `sqlite3`, `json`, `os`, `subprocess`, `sys`, `gc`, `pathlib`, `datetime`, `csv`, `dataclasses`는 Python 표준 라이브러리

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
searcher.py  → sqlite3, json, dataclasses
config.py    → pathlib
```

`open_file()` 함수는 `app.py` 내에만 존재. `os`, `subprocess`, `sys` 사용.
의존 방향 단방향, 순환 참조 없음.

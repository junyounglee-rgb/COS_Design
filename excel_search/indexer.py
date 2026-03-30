"""
indexer.py
----------
지정 폴더의 .xlsx 파일을 스캔하고 SQLite DB에 인덱싱하는 모듈.
변경된 파일만 재인덱싱하며, 삭제된 파일은 DB에서 자동 제거한다.
"""

import gc
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# DB 연결
# ---------------------------------------------------------------------------

def get_connection(db_path: str) -> sqlite3.Connection:
    """SQLite 연결을 생성하고 성능/무결성 PRAGMA를 설정한다."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")   # CASCADE 삭제 활성화
    conn.execute("PRAGMA journal_mode = WAL")  # 동시 읽기/쓰기 허용
    conn.execute("PRAGMA synchronous = NORMAL")  # WAL 모드에서 적절한 안전성
    return conn


# ---------------------------------------------------------------------------
# DB 초기화
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    """DB 스키마를 생성하고, schema_version 레코드가 없으면 삽입한다."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path   TEXT    NOT NULL UNIQUE,
            file_name   TEXT    NOT NULL,
            file_mtime  REAL    NOT NULL,
            indexed_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cells (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            sheet_name  TEXT    NOT NULL,
            col_name    TEXT    NOT NULL,
            col_index   INTEGER NOT NULL,
            cell_value  TEXT,
            row_index   INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS col_data (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            sheet_name  TEXT    NOT NULL,
            col_name    TEXT    NOT NULL,
            col_index   INTEGER NOT NULL,
            all_values  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        -- 파일 경로 유니크 인덱스
        CREATE UNIQUE INDEX IF NOT EXISTS idx_files_path ON files(file_path);

        -- 셀 값 검색용 인덱스
        CREATE INDEX IF NOT EXISTS idx_cells_value ON cells(cell_value);

        -- col_data 복합 유니크 인덱스
        CREATE UNIQUE INDEX IF NOT EXISTS idx_col_data_lookup
            ON col_data(file_id, sheet_name, col_index);

        -- FTS5 가상 테이블 (빈 문자열 제외)
        CREATE VIRTUAL TABLE IF NOT EXISTS cells_fts
            USING fts5(cell_value, content='cells', content_rowid='id');

        -- INSERT 후 FTS 동기화 트리거 (빈 문자열 제외)
        CREATE TRIGGER IF NOT EXISTS cells_ai AFTER INSERT ON cells
            WHEN new.cell_value != ''
        BEGIN
            INSERT INTO cells_fts(rowid, cell_value) VALUES (new.id, new.cell_value);
        END;

        -- DELETE 후 FTS 동기화 트리거
        CREATE TRIGGER IF NOT EXISTS cells_ad AFTER DELETE ON cells BEGIN
            INSERT INTO cells_fts(cells_fts, rowid, cell_value)
            VALUES ('delete', old.id, old.cell_value);
        END;
    """)

    # schema_version 레코드가 없을 때만 초기 버전 삽입
    cursor = conn.execute("SELECT COUNT(*) FROM schema_version")
    if cursor.fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version(version) VALUES (1)")

    conn.commit()


# ---------------------------------------------------------------------------
# 폴더 스캔
# ---------------------------------------------------------------------------

def scan_folder(folder_path: str, exclude_files: list[str] = []) -> list[str]:
    """
    folder_path 내 모든 .xlsx 파일의 절대 경로 목록을 반환한다.
    - ~$ 로 시작하는 Excel 임시 파일 제외
    - exclude_files에 포함된 파일명 제외 (대소문자 무시)
    """
    folder = Path(folder_path)

    # exclude_files를 소문자로 정규화해 빠른 비교
    exclude_lower = {name.lower() for name in exclude_files}

    result: list[str] = []
    for xlsx_path in folder.rglob("*.xlsx"):
        file_name = xlsx_path.name

        # Excel이 열려 있을 때 생성되는 임시 파일 제외
        if file_name.startswith("~$"):
            continue

        # 명시적으로 제외할 파일명 확인 (대소문자 무시)
        if file_name.lower() in exclude_lower:
            continue

        result.append(str(xlsx_path.resolve()))

    return result


# ---------------------------------------------------------------------------
# DB에서 인덱싱된 파일 목록 조회
# ---------------------------------------------------------------------------

def get_indexed_files(conn: sqlite3.Connection) -> dict[str, tuple[int, float]]:
    """
    DB에 저장된 파일 목록을 반환한다.
    반환 형식: {file_path: (file_id, file_mtime)}
    """
    cursor = conn.execute("SELECT file_path, id, file_mtime FROM files")
    return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}


# ---------------------------------------------------------------------------
# 단일 파일 인덱싱
# ---------------------------------------------------------------------------

def _detect_header_row(df_raw: pd.DataFrame) -> int:
    """
    첫 3행 중 헤더 행 인덱스를 감지한다.
    판단 기준: 비어있지 않은 셀 중 숫자 비율이 50% 미만인 첫 번째 행.
    해당하는 행이 없으면 기본값 2(3번째 행) 반환.
    """
    for i in range(min(3, len(df_raw))):
        row_vals = [
            str(v).strip()
            for v in df_raw.iloc[i]
            if pd.notna(v) and str(v).strip()
        ]
        if not row_vals:
            continue
        numeric = sum(
            1 for v in row_vals
            if v.replace(".", "", 1).replace("-", "", 1).isdigit()
        )
        if numeric / len(row_vals) < 0.5:
            return i
    return 2


def index_file(conn: sqlite3.Connection, file_path: str) -> tuple[bool, str]:
    """
    단일 .xlsx 파일을 읽어 cells / col_data / files 테이블에 저장한다.
    - 기존 레코드가 있으면 DELETE → CASCADE로 연관 데이터도 삭제
    - 헤더 행 자동 감지: 첫 3행 중 문자열 비율이 높은 행을 헤더로 사용
    - 성공 시 (True, ""), 실패 시 (False, 오류 메시지) 반환
    """
    try:
        file_name = Path(file_path).name
        file_mtime = os.path.getmtime(file_path)
        indexed_at = datetime.now(timezone.utc).isoformat()

        # 기존 레코드 삭제 (CASCADE로 cells, col_data도 함께 삭제됨)
        conn.execute("DELETE FROM files WHERE file_path = ?", (file_path,))

        # header=None으로 전체 시트를 raw하게 읽어 헤더 행을 직접 감지
        sheets_raw: dict[str, pd.DataFrame] = pd.read_excel(
            file_path,
            sheet_name=None,
            header=None,
            dtype=str,
            engine="openpyxl",
        )

        # 시트별 헤더 행 감지 후 정제된 DataFrame으로 변환
        sheets: dict[str, pd.DataFrame] = {}
        for sheet_name, df_raw in sheets_raw.items():
            if df_raw.empty:
                continue
            h = _detect_header_row(df_raw)
            df = df_raw.iloc[h + 1:].copy()

            # 헤더 행에서 컬럼명 추출 + 중복 컬럼명 자동 구분
            raw_cols = [str(v).strip() if pd.notna(v) else "" for v in df_raw.iloc[h]]
            seen: dict[str, int] = {}
            unique_cols = []
            for col in raw_cols:
                col = col or "col"
                if col in seen:
                    seen[col] += 1
                    unique_cols.append(f"{col}.{seen[col]}")
                else:
                    seen[col] = 0
                    unique_cols.append(col)

            df.columns = unique_cols
            df = df.reset_index(drop=True)
            sheets[sheet_name] = df

        # files 테이블에 메타데이터 삽입 후 file_id 획득
        cursor = conn.execute(
            "INSERT INTO files(file_path, file_name, file_mtime, indexed_at) "
            "VALUES (?, ?, ?, ?)",
            (file_path, file_name, file_mtime, indexed_at),
        )
        file_id = cursor.lastrowid

        cells_batch: list[tuple] = []
        col_data_batch: list[tuple] = []

        for sheet_name, df in sheets.items():
            # 빈 셀을 빈 문자열로 통일
            df = df.fillna("")

            columns = list(df.columns)

            for col_index, col_name in enumerate(columns):
                col_name_str = str(col_name)

                # --- cells 배치 준비 (인덱스 기반 접근으로 중복 컬럼명 문제 방지) ---
                col_series = df.iloc[:, col_index]
                for row_index, cell_value in enumerate(col_series):
                    cells_batch.append((
                        file_id,
                        sheet_name,
                        col_name_str,
                        col_index,
                        str(cell_value),
                        row_index,
                    ))

                # --- col_data 준비 (열 전체 값을 JSON 직렬화) ---
                all_values = json.dumps(
                    [str(v) for v in col_series.tolist()],
                    ensure_ascii=False,
                )
                col_data_batch.append((
                    file_id,
                    sheet_name,
                    col_name_str,
                    col_index,
                    all_values,
                ))

        # cells 배치 INSERT (트리거를 통해 FTS5도 자동 갱신됨)
        conn.executemany(
            "INSERT INTO cells(file_id, sheet_name, col_name, col_index, cell_value, row_index) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            cells_batch,
        )

        # col_data 배치 INSERT
        conn.executemany(
            "INSERT INTO col_data(file_id, sheet_name, col_name, col_index, all_values) "
            "VALUES (?, ?, ?, ?, ?)",
            col_data_batch,
        )

        # 메모리 해제
        del sheets, df, cells_batch, col_data_batch
        gc.collect()

        return (True, "")

    except Exception as e:
        return (False, str(e))


# ---------------------------------------------------------------------------
# 인덱싱 실행 (메인 진입점)
# ---------------------------------------------------------------------------

def run_indexing(
    folder_path: str,
    db_path: str,
    exclude_files: list[str] = [],
    progress_callback=None,
) -> dict:
    """
    폴더 전체를 스캔하고 변경/신규 파일만 재인덱싱한다.

    - 삭제된 파일은 DB에서 자동 제거 (CASCADE 적용)
    - 변경 판별: 디스크 mtime > DB에 저장된 mtime
    - progress_callback(current, total, filename) 형태로 진행 상황 전달
    - 반환: {"total": int, "indexed": int, "skipped": int, "failed": list[str]}
    """
    # 결과 변수 사전 초기화 (예외 발생 시에도 유효한 값 반환 보장)
    total = 0
    indexed = 0
    skipped = 0
    failed: list[str] = []

    conn = get_connection(db_path)
    init_db(conn)

    try:
        # 디스크의 현재 파일 목록
        disk_files: list[str] = scan_folder(folder_path, exclude_files)
        disk_set = set(disk_files)

        # DB에 저장된 파일 목록
        db_files: dict[str, tuple[int, float]] = get_indexed_files(conn)

        # DB에는 있지만 디스크에는 없는 파일 → 삭제
        for file_path in list(db_files.keys()):
            if file_path not in disk_set:
                conn.execute("DELETE FROM files WHERE file_path = ?", (file_path,))

        # 신규 또는 변경된 파일만 추출
        files_to_index: list[str] = []
        skipped = 0

        for file_path in disk_files:
            if file_path in db_files:
                _, db_mtime = db_files[file_path]
                disk_mtime = os.path.getmtime(file_path)
                # 디스크 mtime이 DB mtime보다 크면 변경된 파일로 판단
                if disk_mtime > db_mtime:
                    files_to_index.append(file_path)
                else:
                    skipped += 1
            else:
                # 신규 파일
                files_to_index.append(file_path)

        total = len(files_to_index)
        indexed = 0
        failed: list[str] = []

        for current, file_path in enumerate(files_to_index, start=1):
            file_name = Path(file_path).name

            # 진행 상황을 외부(app.py)로 전달
            if progress_callback is not None:
                progress_callback(current, total, file_name)

            success, error_msg = index_file(conn, file_path)

            if success:
                indexed += 1
            else:
                failed.append(f"{file_name}: {error_msg}")

        # 모든 처리 완료 후 한 번에 커밋 (WAL 모드 동시성 활용)
        conn.commit()

    finally:
        conn.close()

    return {
        "total": total,
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
    }

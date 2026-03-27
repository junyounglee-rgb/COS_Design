import sqlite3
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    file_path:      str
    file_name:      str
    sheet_name:     str
    col_name:       str
    col_index:      int
    matched_values: list[str]       # 매칭된 셀 값 목록
    col_headers:    list[str]       # 시트의 컬럼 헤더 목록 (순서 유지)
    matched_rows:   list[dict]      # 매칭된 행 전체 데이터 [{col_name: value}, ...]
    match_count:    int = field(init=False)

    def __post_init__(self):
        self.match_count = len(self.matched_rows)


def _fetch_matched_rows(conn, file_id: int, sheet_name: str, row_indices: list[int]):
    """매칭된 row_index들의 전체 행 데이터를 반환한다.

    Returns:
        (col_headers, matched_rows)
        col_headers: 컬럼명 목록 (col_index 순서)
        matched_rows: [{col_name: cell_value, ...}, ...] (row_index 순서)
    """
    if not row_indices:
        return [], []

    # 시트의 컬럼 목록 (col_index 오름차순)
    cur = conn.execute(
        "SELECT DISTINCT col_name, col_index FROM cells "
        "WHERE file_id = ? AND sheet_name = ? ORDER BY col_index",
        (file_id, sheet_name),
    )
    cols = cur.fetchall()
    if not cols:
        return [], []

    col_headers = [cn for cn, _ in cols]
    col_idx_to_name = {ci: cn for cn, ci in cols}

    # 매칭 행들의 모든 셀 조회
    placeholders = ",".join(["?"] * len(row_indices))
    params = [file_id, sheet_name] + list(row_indices)
    cur = conn.execute(
        f"SELECT col_index, row_index, cell_value FROM cells "
        f"WHERE file_id = ? AND sheet_name = ? AND row_index IN ({placeholders}) "
        f"ORDER BY row_index, col_index",
        params,
    )

    rows_map: dict[int, dict[str, str]] = {}
    for col_idx, row_idx, val in cur.fetchall():
        if row_idx not in rows_map:
            rows_map[row_idx] = {}
        col_name = col_idx_to_name.get(col_idx, "")
        rows_map[row_idx][col_name] = val or ""

    matched_rows = [
        {cn: rows_map[ri].get(cn, "") for cn in col_headers}
        for ri in sorted(rows_map.keys())
    ]
    return col_headers, matched_rows


def _parse_rows(conn, file_id, file_path, file_name, sheet_name,
                col_name, col_index, matched_raw, row_indices_raw) -> "SearchResult":
    """공통 파싱 로직: SQL row → SearchResult."""
    matched_values = matched_raw.split("||SEP||") if matched_raw else []
    row_indices = (
        [int(x) for x in row_indices_raw.split("||SEP||") if x.isdigit()]
        if row_indices_raw else []
    )
    col_headers, matched_rows = _fetch_matched_rows(conn, file_id, sheet_name, row_indices)
    return SearchResult(
        file_path=file_path,
        file_name=file_name,
        sheet_name=sheet_name,
        col_name=col_name,
        col_index=col_index,
        matched_values=matched_values,
        col_headers=col_headers,
        matched_rows=matched_rows,
    )


def search_exact(conn, query: str, limit: int = 1000) -> list[SearchResult]:
    """cell_value가 query와 정확히 일치하는 셀을 검색한다."""
    sql = """
        SELECT
            f.id AS file_id, f.file_path, f.file_name,
            c.sheet_name, c.col_name, c.col_index,
            GROUP_CONCAT(c.cell_value, '||SEP||') AS matched_values,
            GROUP_CONCAT(c.row_index,  '||SEP||') AS matched_row_indices
        FROM cells c
        JOIN files f ON c.file_id = f.id
        WHERE c.cell_value = ?
        GROUP BY f.id, c.sheet_name, c.col_index
        LIMIT ?
    """
    cur = conn.execute(sql, (query, limit))
    return [
        _parse_rows(conn, *row)
        for row in cur.fetchall()
    ]


def search_partial(conn, query: str, limit: int = 1000) -> list[SearchResult]:
    """query를 부분 일치로 검색한다. FTS5를 우선 시도하고 결과 없으면 LIKE로 fallback."""

    fts_query = '"' + query.replace('"', '""') + '"*'

    fts_sql = """
        SELECT
            f.id AS file_id, f.file_path, f.file_name,
            c.sheet_name, c.col_name, c.col_index,
            GROUP_CONCAT(c.cell_value, '||SEP||') AS matched_values,
            GROUP_CONCAT(c.row_index,  '||SEP||') AS matched_row_indices
        FROM cells_fts
        JOIN cells c ON cells_fts.rowid = c.id
        JOIN files f ON c.file_id = f.id
        WHERE cells_fts MATCH ?
        GROUP BY f.id, c.sheet_name, c.col_index
        LIMIT ?
    """
    rows = []
    try:
        cur = conn.execute(fts_sql, (fts_query, limit))
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        pass

    if not rows:
        like_sql = """
            SELECT
                f.id AS file_id, f.file_path, f.file_name,
                c.sheet_name, c.col_name, c.col_index,
                GROUP_CONCAT(c.cell_value, '||SEP||') AS matched_values,
                GROUP_CONCAT(c.row_index,  '||SEP||') AS matched_row_indices
            FROM cells c
            JOIN files f ON c.file_id = f.id
            WHERE c.cell_value LIKE ?
            GROUP BY f.id, c.sheet_name, c.col_index
            LIMIT ?
        """
        cur = conn.execute(like_sql, (f"%{query}%", limit))
        rows = cur.fetchall()

    return [_parse_rows(conn, *row) for row in rows]


def search(conn, query: str, mode: str = "exact", limit: int = 1000) -> list[SearchResult]:
    """엑셀 인덱스 DB에서 query를 검색한다.

    Args:
        conn:  sqlite3 연결 객체
        query: 검색할 문자열
        mode:  'exact' (정확히 일치) | 'partial' (부분 일치)
        limit: 최대 반환 행 수 (기본 1000)

    Returns:
        SearchResult 목록. 빈 쿼리면 빈 리스트 반환.
    """
    if query.strip() == "":
        return []

    if mode == "partial":
        return search_partial(conn, query, limit)
    else:
        return search_exact(conn, query, limit)


def get_index_stats(conn) -> dict:
    """인덱스 DB의 통계 정보를 반환한다."""
    file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    cell_count = conn.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
    last_indexed_raw = conn.execute("SELECT MAX(indexed_at) FROM files").fetchone()[0]
    last_indexed = last_indexed_raw if last_indexed_raw is not None else "없음"
    return {
        "file_count": file_count,
        "cell_count": cell_count,
        "last_indexed": last_indexed,
    }

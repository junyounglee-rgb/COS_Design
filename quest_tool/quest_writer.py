"""
quest_writer.py -- quests.xlsx Excel 읽기/쓰기 모듈.
Streamlit에 의존하지 않는 순수 Python 함수로 구현.
캐시는 app.py에서 @st.cache_data로 감쌀 예정.
"""
import random
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

_BASE_PATH_PREFIX = "quests/^0/"
_PATH_ROW = 2
_HEADER_ROW = 3


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _build_header_map(
    ws,
    path_row: int = _PATH_ROW,
    header_row: int = _HEADER_ROW,
    base_prefix: str = _BASE_PATH_PREFIX,
) -> dict[str, int]:
    """Row 2(경로) + Row 3(헤더) 조합으로 {고유키: 컬럼인덱스(1-based)} 반환.
    base_prefix와 일치하는 경로의 컬럼: 헤더 이름 그대로 사용.
    경로가 다른 컬럼: 경로suffix/헤더명 형식으로 고유 키 생성.
    base_prefix가 빈 문자열이면 path_row를 무시하고 헤더명만 사용.
    """
    paths: dict[int, str] = {}
    if base_prefix:
        for cell in ws[path_row]:
            if cell.value is not None:
                paths[cell.column] = str(cell.value)

    result: dict[str, int] = {}
    for cell in ws[header_row]:
        if cell.value is None:
            continue
        field = str(cell.value)
        col = cell.column
        path = paths.get(col, "")
        # base_prefix 제거 후 suffix 추출
        if base_prefix and path.startswith(base_prefix):
            suffix = path[len(base_prefix):].rstrip("/")
        elif base_prefix:
            suffix = path.rstrip("/")
        else:
            suffix = ""

        if suffix:
            key = f"{suffix}/{field}"
        else:
            key = field
        result[key] = col
    return result


# ---------------------------------------------------------------------------
# 공개 읽기 함수
# ---------------------------------------------------------------------------

def get_header_map(
    xlsx_path: str,
    sheet: str = "quests",
    path_row: int = _PATH_ROW,
    header_row: int = _HEADER_ROW,
) -> dict[str, int]:
    """헤더 행에서 {고유컬럼키: 컬럼인덱스} 반환."""
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        return _build_header_map(ws, path_row=path_row, header_row=header_row)
    finally:
        wb.close()


def get_existing_keys(xlsx_path: str) -> set[int]:
    """quests 시트 ^key 컬럼의 기존 값 전부 수집."""
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb["quests"]
        header_map = _build_header_map(ws, path_row=_PATH_ROW, header_row=_HEADER_ROW)
        key_col = header_map.get("^key")
        if key_col is None:
            return set()
        existing: set[int] = set()
        for row in ws.iter_rows(min_row=4, values_only=True):
            val = row[key_col - 1]  # 0-based index
            if val is not None:
                try:
                    existing.add(int(val))
                except (ValueError, TypeError):
                    pass
        return existing
    finally:
        wb.close()


def generate_unique_key(existing: set[int], lo: int = 100000, hi: int = 999999) -> int:
    """랜덤 6자리 정수, existing에 없을 때까지 재시도."""
    while True:
        candidate = random.randint(lo, hi)
        if candidate not in existing:
            return candidate


def load_items(items_path: str) -> list[dict]:
    """items.xlsx -> [{id: int, name: str, category: str}] 목록.
    헤더행 3, 컬럼: ^key, name, category를 _build_header_map()으로 동적 탐색.
    id가 없는 행 제외."""
    wb = load_workbook(items_path, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        header_map = _build_header_map(ws, header_row=3, base_prefix="")

        key_col = header_map.get("^key")
        name_col = header_map.get("name")
        cat_col = header_map.get("category")

        if key_col is None:
            return []

        items: list[dict] = []
        for row in ws.iter_rows(min_row=4, values_only=True):
            raw_id = row[key_col - 1]
            if raw_id is None:
                continue
            try:
                item_id = int(raw_id)
            except (ValueError, TypeError):
                continue

            name = row[name_col - 1] if name_col else None
            category = row[cat_col - 1] if cat_col else None

            items.append({
                "id": item_id,
                "name": str(name) if name is not None else "",
                "category": str(category) if category is not None else "",
            })
        return items
    finally:
        wb.close()


def load_keywords(keywords_path: str) -> dict[str, dict[str, str]]:
    """keywords.xlsx -> {"build": {id: value}, "timestamp": {id: value}}.
    build 시트: 헤더행 3, A=id, B=value.
    timestamp 시트: 헤더행 3, A=id, B=value.
    시트가 없으면 빈 dict 반환."""
    wb = load_workbook(keywords_path, read_only=True, data_only=True)
    result: dict[str, dict[str, str]] = {}
    try:
        for sheet_name in ["build", "timestamp"]:
            if sheet_name not in wb.sheetnames:
                result[sheet_name] = {}
                continue
            ws = wb[sheet_name]
            mapping: dict[str, str] = {}
            for row in ws.iter_rows(min_row=4, values_only=True):
                id_val = row[0]
                val = row[1]
                if id_val is not None:
                    mapping[str(id_val)] = str(val) if val is not None else ""
            result[sheet_name] = mapping
        return result
    finally:
        wb.close()


def load_quest_templates(quests_path: str) -> dict[str, str]:
    """#quest 시트 -> {B컬럼(quest텍스트): A컬럼(desc텍스트)}.
    헤더행 3, 데이터 행 4~."""
    wb = load_workbook(quests_path, read_only=True, data_only=True)
    try:
        if "#quest" not in wb.sheetnames:
            return {}
        ws = wb["#quest"]
        templates: dict[str, str] = {}
        for row in ws.iter_rows(min_row=4, values_only=True):
            # A=desc, B=quest
            desc = row[0]
            quest = row[1]
            if quest is not None and desc is not None:
                templates[str(quest)] = str(desc)
        return templates
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# 쓰기 함수
# ---------------------------------------------------------------------------

def _verify_written_key(
    xlsx_path: str,
    key: Any,
    expected_row: int,
    header_map: dict[str, int],
) -> None:
    """저장 후 검증: 해당 행 ^key 값이 일치하는지 확인. 불일치 시 RuntimeError."""
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb["quests"]
        key_col = header_map.get("^key")
        if key_col is None:
            raise RuntimeError("헤더에서 ^key 컬럼을 찾을 수 없습니다.")
        row = ws[expected_row]
        actual = row[key_col - 1].value
        if actual != key:
            raise RuntimeError(
                f"저장 검증 실패: Row {expected_row}의 ^key={actual!r}, 기대값={key!r}"
            )
    finally:
        wb.close()


def append_quest_row(xlsx_path: str, field_values: dict[str, Any]) -> int:
    """
    quests 시트 마지막 행 다음에 새 행 추가.
    반환: 추가된 행 번호.

    안전장치:
    1. 파일 열기 직전 ^key 재수집 (세션 캐시 미신뢰)
    2. ^key 중복 시 ValueError
    3. max_row + 1 위치에만 삽입
    4. 저장 후 _verify_written_key() 호출
    """
    # 안전장치 1: 파일 열기 직전 ^key 재수집
    existing_keys = get_existing_keys(xlsx_path)

    new_key = field_values.get("^key")
    if new_key is not None:
        try:
            new_key = int(new_key)
        except (ValueError, TypeError):
            pass
        # 안전장치 2: ^key 중복 확인
        if new_key in existing_keys:
            raise ValueError(f"^key {new_key!r} 는 이미 존재합니다.")

    # 쓰기 모드로 열기
    wb = load_workbook(xlsx_path, data_only=True)
    try:
        ws = wb["quests"]
        header_map = _build_header_map(ws, path_row=_PATH_ROW, header_row=_HEADER_ROW)

        # 안전장치 3: max_row + 1 에만 삽입
        target_row = ws.max_row + 1

        for col_name, value in field_values.items():
            col_idx = header_map.get(col_name)
            if col_idx is None:
                continue  # 헤더에 없는 필드는 건너뜀 (KeyError 대신)
            if value is None or value == "":
                continue  # 빈 값 skip
            ws.cell(row=target_row, column=col_idx, value=value)

        wb.save(xlsx_path)
    finally:
        wb.close()

    # 안전장치 4: 저장 후 검증
    header_map_verify = get_header_map(xlsx_path, sheet="quests", path_row=_PATH_ROW, header_row=_HEADER_ROW)
    _verify_written_key(xlsx_path, new_key, target_row, header_map_verify)

    return target_row

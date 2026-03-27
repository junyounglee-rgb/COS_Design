"""
Excel 기획 데이터 파서
- Row1: 컬럼 설명, Row2: 익스포트 경로, Row3: 컬럼 헤더
- FK 추출: ref_(.+?)_(id|key|type)$ 패턴
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
import yaml


# ─────────────────────────── 데이터 모델 ────────────────────────────

@dataclass
class ColumnInfo:
    name: str
    description: str        # Row1 설명
    export_path: str        # Row2 JSON 익스포트 경로
    is_pk: bool             # ^ 시작
    is_comment: bool        # # 시작
    is_filter: bool         # $ 시작
    fk_target: str | None   # ref_ 패턴 → target 테이블명


@dataclass
class CategoryInfo:
    name: str
    color: str
    visible: bool = True


@dataclass
class TableNode:
    file_name: str          # "cookies.xlsx"
    sheet_name: str         # "cookies"
    table_name: str         # sheet_name (논리 테이블명)
    category: str
    color: str
    columns: list[ColumnInfo] = field(default_factory=list)

    @property
    def fk_count(self) -> int:
        return sum(1 for c in self.columns if c.fk_target)

    @property
    def pk_column(self) -> str | None:
        for c in self.columns:
            if c.is_pk:
                return c.name
        return None


@dataclass
class GraphEdge:
    source: str
    target: str
    label: str              # FK 컬럼명
    source_file: str
    target_file: str


@dataclass
class GraphData:
    nodes: list[TableNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ─────────────────────────── 설정 로드 ──────────────────────────────

def load_config(yaml_path: str) -> tuple[str, dict[str, CategoryInfo]]:
    """YAML → (excel_folder, {category_name: CategoryInfo})"""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return "", {}

    excel_folder = data.get("excel_folder", "")
    raw_cats = data.get("categories", {})
    categories: dict[str, CategoryInfo] = {}
    for name, info in raw_cats.items():
        categories[name] = CategoryInfo(
            name=name,
            color=info.get("color", "#BDC3C7"),
            visible=info.get("visible", True),
        )
    return excel_folder, categories


def build_file_category_map(yaml_path: str) -> tuple[str, dict[str, tuple[str, str]], dict[str, bool], set[str]]:
    """
    반환:
      excel_folder,
      {file_name_no_ext: (category_name, color)},
      {category_name: visible},
      exclude_files: set[str]
    """
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return "", {}, {}, set()

    excel_folder = data.get("excel_folder", "")
    raw_cats = data.get("categories", {})
    exclude_files: set[str] = set(data.get("exclude_files", []))

    file_map: dict[str, tuple[str, str]] = {}
    visible_map: dict[str, bool] = {}

    for cat_name, info in raw_cats.items():
        color = info.get("color", "#BDC3C7")
        visible = info.get("visible", True)
        visible_map[cat_name] = visible
        for fname in info.get("files", []):
            file_map[fname] = (cat_name, color)

    return excel_folder, file_map, visible_map, exclude_files


def save_exclude_files(yaml_path: str, exclude_files: list[str]) -> None:
    """exclude_files 목록을 categories.yaml에 저장."""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["exclude_files"] = sorted(exclude_files)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise RuntimeError(f"categories.yaml 저장 실패: {e}")


def get_all_file_names(yaml_path: str) -> list[str]:
    """excel_folder 내 모든 xlsx 파일명(확장자 없이) 반환 — UI 자동완성용."""
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        folder = Path(data.get("excel_folder", ""))
        if not folder.exists():
            return []
        return sorted(
            p.stem for p in folder.glob("*.xlsx")
            if not p.name.startswith("~$") and "test" not in p.name.lower()
        )
    except Exception:
        return []


def get_file_category(
    file_name_no_ext: str,
    file_map: dict[str, tuple[str, str]],
) -> tuple[str, str]:
    """파일명 → (category_name, color). 없으면 미분류."""
    return file_map.get(file_name_no_ext, ("미분류", "#BDC3C7"))


# ─────────────────────────── Excel 파싱 ─────────────────────────────

_FK_PATTERN = re.compile(r"ref_(.+?)_(id|key|type)$")


def _to_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def extract_columns(ws) -> list[ColumnInfo]:
    """Row1(설명), Row2(익스포트경로), Row3(헤더) 읽어서 ColumnInfo 리스트 반환."""
    rows = list(ws.iter_rows(min_row=1, max_row=3, values_only=True))
    if len(rows) < 3:
        return []

    row1 = rows[0]  # 설명
    row2 = rows[1]  # JSON 익스포트 경로
    row3 = rows[2]  # 컬럼 헤더

    columns: list[ColumnInfo] = []
    for i, col_name_raw in enumerate(row3):
        if col_name_raw is None:
            continue
        name = _to_str(col_name_raw)
        if not name:
            continue

        description = _to_str(row1[i]) if i < len(row1) else ""
        export_path = _to_str(row2[i]) if i < len(row2) else ""

        is_pk = name.startswith("^")
        is_comment = name.startswith("#")
        is_filter = name.startswith("$")

        fk_target: str | None = None
        m = _FK_PATTERN.match(name)
        if m:
            fk_target = m.group(1)

        columns.append(ColumnInfo(
            name=name,
            description=description,
            export_path=export_path,
            is_pk=is_pk,
            is_comment=is_comment,
            is_filter=is_filter,
            fk_target=fk_target,
        ))

    return columns


def parse_file(
    file_path: str,
    category: str,
    color: str,
) -> list[TableNode]:
    """단일 xlsx → TableNode 리스트 (멀티시트 지원)."""
    file_name = Path(file_path).name
    nodes: list[TableNode] = []

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            sheet_name = ws.title
            if sheet_name.startswith("#"):
                continue
            columns = extract_columns(ws)
            nodes.append(TableNode(
                file_name=file_name,
                sheet_name=sheet_name,
                table_name=sheet_name,
                category=category,
                color=color,
                columns=columns,
            ))
        wb.close()
    except Exception as e:
        print(f"[WARN] parse_file failed: {file_name} — {e}", file=sys.stderr)

    return nodes


def extract_edges(
    nodes: list[TableNode],
    all_table_names: set[str],
) -> tuple[list[GraphEdge], list[str]]:
    """FK 컬럼 → GraphEdge. 반환: (edges, dangling_warnings)."""
    edges: list[GraphEdge] = []
    dangling: list[str] = []

    # table_name → file_name 역방향 맵
    table_to_file: dict[str, str] = {n.table_name: n.file_name for n in nodes}

    for node in nodes:
        for col in node.columns:
            if col.fk_target is None:
                continue

            target = col.fk_target
            # 1차: 그대로 매칭
            if target in all_table_names:
                matched = target
            # 2차: 복수형(s 추가) 재시도
            elif target + "s" in all_table_names:
                matched = target + "s"
            else:
                dangling.append(
                    f"{node.table_name}.{col.name} → '{target}' (테이블 없음)"
                )
                continue

            edges.append(GraphEdge(
                source=node.table_name,
                target=matched,
                label=col.name,
                source_file=node.file_name,
                target_file=table_to_file.get(matched, ""),
            ))

    return edges, dangling


# ───────────────────────── 전체 오케스트레이션 ───────────────────────

def parse_excel_folder(yaml_path: str) -> GraphData:
    """전체 Excel 폴더 파싱 → GraphData."""
    graph = GraphData()

    excel_folder, file_map, _, exclude_files = build_file_category_map(yaml_path)

    if not excel_folder:
        graph.warnings.append("categories.yaml에 excel_folder가 설정되지 않았습니다.")
        return graph

    folder = Path(excel_folder)
    if not folder.exists():
        graph.warnings.append(f"Excel 폴더를 찾을 수 없습니다: {excel_folder}")
        return graph

    xlsx_files = sorted(folder.glob("*.xlsx"))
    nodes: list[TableNode] = []

    for xlsx_path in xlsx_files:
        fname = xlsx_path.name
        fname_no_ext = xlsx_path.stem
        # 임시 파일 제외
        if fname.startswith("~$"):
            continue
        # 테스트 파일 제외
        if "test" in fname.lower():
            continue
        # exclude_files 제외
        if fname_no_ext in exclude_files:
            continue
        category, color = get_file_category(fname_no_ext, file_map)

        file_nodes = parse_file(str(xlsx_path), category, color)
        if not file_nodes:
            graph.warnings.append(f"파싱 실패 또는 빈 파일: {fname}")
        nodes.extend(file_nodes)

    graph.nodes = nodes

    all_table_names = {n.table_name for n in nodes}
    edges, dangling = extract_edges(nodes, all_table_names)
    graph.edges = edges
    for d in dangling:
        graph.warnings.append(f"[dangling FK] {d}")

    return graph


# ───────────────────────── 단독 실행 (테스트) ───────────────────────

if __name__ == "__main__":
    yaml_path = Path(__file__).parent / "categories.yaml"
    print(f"파싱 중: {yaml_path}")
    graph = parse_excel_folder(str(yaml_path))

    print(f"\n=== 파싱 결과 ===")
    print(f"테이블 수: {len(graph.nodes)}")
    print(f"FK 관계 수: {len(graph.edges)}")
    print(f"경고 수: {len(graph.warnings)}")

    print(f"\n=== 카테고리별 테이블 ===")
    from collections import defaultdict
    by_cat: dict[str, list[str]] = defaultdict(list)
    for n in graph.nodes:
        by_cat[n.category].append(n.table_name)
    for cat, tables in sorted(by_cat.items()):
        print(f"  {cat} ({len(tables)}개): {', '.join(tables[:5])}{'...' if len(tables)>5 else ''}")

    print(f"\n=== FK 관계 (상위 20개) ===")
    for e in graph.edges[:20]:
        print(f"  {e.source} --[{e.label}]--> {e.target}")

    if graph.warnings:
        print(f"\n=== 경고 (상위 10개) ===")
        for w in graph.warnings[:10]:
            print(f"  [!] {w}")

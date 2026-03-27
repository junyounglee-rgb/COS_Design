# excel_analyze 상세 기술 명세서

> 작성일: 2026-03-27
> 버전: 1.0
> 담당 에이전트: Agent1(Plan)

---

## 개요

Excel 기획 데이터 파일(~120개 xlsx) 간의 FK 관계를 인터랙티브 네트워크 그래프로 시각화하는 웹 UI.
기획자가 직접 사용. 아웃게임 데이터 우선, 이후 전체 확장.

---

## 프로젝트 구조

```
D:\claude_make\excel_analyze\
├── app.py              # Streamlit 메인 UI
├── parser.py           # Excel 파싱 + 관계 추출
├── categories.yaml     # 카테고리 분류 + 색상 설정
├── requirements.txt
└── doc/
    └── spec001.md
```

---

## 1. Excel 파일 규칙 (공통 전제)

| Row | 역할 | 예시 |
|-----|------|------|
| Row1 | 컬럼 설명/주석 (한국어) | `"쿠키 ID Sheet에 있는 Key값"` |
| Row2 | JSON 익스포트 경로 | `cookies/^0/`, `cookies/^0/items/0/` |
| Row3 | 컬럼 헤더 | `^key`, `$filter`, `#주석`, `ref_X_id` |
| Row4~ | 실제 데이터 | (파싱 불필요) |

**컬럼 헤더 접두사 규칙:**
- `^key` / `^id` → Primary Key
- `#` → 주석 컬럼 (데이터 무시)
- `$` → 필터 컬럼
- `ref_X_id` / `ref_X_key` / `ref_X_type` → Foreign Key (X = target table)

**FK 추출 패턴:** `ref_(.+?)_(id|key|type)$`

---

## 2. 데이터 모델

```python
from dataclasses import dataclass, field

@dataclass
class ColumnInfo:
    name: str               # Row3 컬럼명 원문
    description: str        # Row1 설명 (없으면 "")
    is_pk: bool             # ^key 또는 ^id 시작
    is_comment: bool        # # 시작
    is_filter: bool         # $ 시작
    fk_target: str | None   # ref_ 패턴 시 target table명, 없으면 None

@dataclass
class CategoryInfo:
    name: str
    color: str              # hex 색상 코드
    visible: bool = True    # 기본 표시 여부

@dataclass
class TableNode:
    file_name: str          # "cookies.xlsx"
    sheet_name: str         # "cookies"
    table_name: str         # sheet_name과 동일 (논리 테이블명)
    category: str           # categories.yaml 기반
    color: str              # 카테고리 색상
    columns: list[ColumnInfo] = field(default_factory=list)

    @property
    def fk_count(self) -> int:
        return sum(1 for c in self.columns if c.fk_target)

@dataclass
class GraphEdge:
    source: str             # source table_name
    target: str             # target table_name
    label: str              # FK 컬럼명 (ref_X_id)
    source_file: str        # source 파일명
    target_file: str        # target 파일명

@dataclass
class GraphData:
    nodes: list[TableNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
```

---

## 3. categories.yaml 명세

### 파일 구조

```yaml
excel_folder: D:\COS_Project\cos-data\excel

categories:
  아웃게임_경제상점:
    color: "#E74C3C"
    visible: true
    files:
      - items
      - item_boxes
      - item_groups
      - item_random_pools
      - shop
      - gacha_shops
      - product
      - inventory
      - drop_infos

  아웃게임_이벤트:
    color: "#E67E22"
    visible: true
    files:
      - event_infos
      - attendance_events
      - daily_fortune_events
      - invitation_events
      - nday_mission_events
      - step_mission_events
      - quest_gacha_events
      - pve_events
      - vault_mission_events

  아웃게임_퀘스트미션:
    color: "#F1C40F"
    visible: true
    files:
      - quests
      - cookie_masteries
      - achievements

  아웃게임_소셜:
    color: "#2ECC71"
    visible: true
    files:
      - social
      - nicknames
      - mail
      - word_filters
      - community_urls

  아웃게임_UI시스템:
    color: "#1ABC9C"
    visible: true
    files:
      - lobby_buttons
      - shortcuts
      - setting_menus
      - settings
      - screen_infos
      - contents_info
      - contents_unlocks
      - game_config
      - errors
      - rolling_banners

  아웃게임_번역:
    color: "#3498DB"
    visible: false
    files:
      - translations_ko
      - translations_en
      - translations_ja
      - translations_zh_hant
      - translations_id
      - translations_th
      - translations_vi
      - string_keywords
      - keywords
      - ui_strings

  아웃게임_로비타운:
    color: "#9B59B6"
    visible: true
    files:
      - town_config
      - town_items
      - town_npc_infos
      - thumbnails
      - portraits
      - profile_items

  아웃게임_모드맵:
    color: "#16A085"
    visible: true
    files:
      - modes
      - maps
      - matching_rules
      - jelly_race_modes
      - pve_round_modes
      - bounty_modes
      - escort_modes
      - castle_break_modes
      - death_match_modes
      - battle_royal_modes
      - battle_roads
      - gnome_battle_modes
      - drop_the_beat_modes
      - smash_levels
      - smash_pass

  아웃게임_잠금조건:
    color: "#8E44AD"
    visible: true
    files:
      - unlock_conditions
      - contents_unlocks

  인게임_캐릭터:
    color: "#95A5A6"
    visible: false
    files:
      - cookies
      - costumes
      - cookie_ranks
      - cookie_voices
      - cookie_npc_infos
      - expressions
      - highlights
      - cookie_bot
      - mvps

  인게임_전투:
    color: "#7F8C8D"
    visible: false
    files:
      - skill_infos
      - skill_charges
      - skill_area_of_effects
      - skill_basic_gauges
      - skill_collision_infos
      - skill_custom_fxs
      - skill_explosions
      - skill_projectiles
      - skill_summons
      - skill_tags
      - skill_tether_beams
      - status_effect_infos
      - status_effect_values
      - stats_infos
      - buff_cards
      - ai_infos
      - damage_fonts
      - camera_shakes
      - cameras
      - hit_fx_sockets
      - screen_effects
      - battle_boxes
      - battle_card
      - battle_points
      - kill_feeds
      - observes
      - parabola_guides
      - system_buffs

  미분류:
    color: "#BDC3C7"
    visible: false
    files: []
```

---

## 4. parser.py 명세

### 4.1 함수 목록

#### `load_categories(yaml_path: str) -> dict[str, CategoryInfo]`
- YAML 파싱 → `{category_name: CategoryInfo}` 반환
- 파일 미존재 시 빈 dict 반환 (예외 금지)
- `excel_folder` 경로도 별도로 반환: `load_config(yaml_path) -> tuple[str, dict]`

#### `get_file_category(file_name: str, categories: dict[str, CategoryInfo]) -> tuple[str, str]`
- `file_name` (확장자 없음) → `(category_name, color)` 반환
- 매칭 없으면 `("미분류", "#BDC3C7")` 반환

#### `extract_columns(ws) -> list[ColumnInfo]`
- `ws`: openpyxl worksheet (read_only)
- Row1, Row2, Row3를 읽어서 ColumnInfo 리스트 반환
- Row3이 없거나 비어있으면 빈 리스트 반환
- Row3 컬럼명이 None이면 해당 컬럼 skip
- `is_pk`: name이 `^` 로 시작
- `is_comment`: name이 `#` 로 시작
- `is_filter`: name이 `$` 로 시작
- `fk_target`: `re.match(r'ref_(.+?)_(id|key|type)$', name)` 캡처그룹1

#### `parse_file(file_path: str, category: str, color: str) -> list[TableNode]`
- 단일 xlsx 파싱 → TableNode 리스트
- `openpyxl.load_workbook(read_only=True, data_only=True)`
- `~$` 파일명 체크는 호출 전에 처리
- `#` 로 시작하는 시트명 skip
- 시트별로 `extract_columns()` 호출
- 예외 발생 시 `[]` 반환 + stderr 경고

#### `extract_edges(nodes: list[TableNode], all_table_names: set[str]) -> list[GraphEdge]`
- nodes 전체를 순회하며 `fk_target` 이 있는 컬럼 탐색
- target 매칭 순서:
  1. `fk_target` 그대로 `all_table_names`에 있는지
  2. `fk_target + 's'` 로 재시도
  3. 둘 다 없으면 skip (dangling ref 무시)
- 중복 edge 허용 (동일 source→target이라도 컬럼명이 다르면 별도 edge)

#### `parse_excel_folder(folder_path: str, yaml_path: str) -> tuple[GraphData, list[str]]`
- 전체 오케스트레이션
- `load_config()` → excel_folder + categories
- `~$` 임시파일 제외, `.xlsx` 만 처리
- 모든 파일 파싱 → `nodes` 수집
- `all_table_names` 구성 후 `extract_edges()` 호출
- 반환: `(GraphData, warnings)` — warnings는 파싱 실패 파일명 리스트

### 4.2 엣지케이스

| 상황 | 처리 |
|------|------|
| Row3이 비어있는 파일 | 빈 TableNode (columns=[]) |
| 멀티시트 파일 | 시트별 별도 TableNode |
| `#desc` 등 주석 시트 | skip |
| 파싱 실패 | skip + warnings 리스트에 추가 |
| FK target 미존재 | edge 미생성 (dangling ref 무시) |
| 동일 table_name 중복 | sheet_name 기준으로 구분 (file_name도 함께 저장) |

---

## 5. app.py 명세 (Streamlit + pyvis)

### 5.1 화면 구성

```
┌─────────────────┬──────────────────────────────────────────┐
│  [사이드바]       │  [메인 - 네트워크 그래프]                  │
│                 │                                          │
│ 표시 범위:       │  ┌────────────────────────────────────┐  │
│ ◉ 아웃게임만    │  │                                    │  │
│ ○ 전체          │  │   pyvis 인터랙티브 네트워크 그래프    │  │
│                 │  │   (드래그·줌·hover 지원)            │  │
│ 카테고리 필터:   │  │                                    │  │
│ ☑ 경제/상점     │  │   노드 = 테이블                     │  │
│ ☑ 이벤트       │  │   색상 = 카테고리                   │  │
│ ☑ 퀘스트/미션   │  │   크기 = FK 수 비례                 │  │
│ ☑ 소셜         │  │   엣지 = FK 관계 (방향 화살표)       │  │
│ ☑ UI/시스템    │  │                                    │  │
│ ☐ 번역 (기본꺼짐)│  └────────────────────────────────────┘  │
│ ☑ 로비/타운    │                                          │
│ ☑ 모드/맵      │  통계: 노드 N개 / 엣지 M개               │
│ ☑ 잠금조건     │                                          │
│ ─────────────  │                                          │
│ ☐ 인게임_캐릭터  │                                          │
│ ☐ 인게임_전투   │                                          │
│                 │                                          │
│ [그래프 새로고침] │                                          │
└─────────────────┴──────────────────────────────────────────┘
```

### 5.2 pyvis 설정

```python
from pyvis.network import Network

net = Network(height="700px", width="100%", directed=True, bgcolor="#1a1a2e", font_color="white")

# physics
net.set_options("""
{
  "physics": {
    "enabled": true,
    "barnesHut": {
      "gravitationalConstant": -8000,
      "centralGravity": 0.3,
      "springLength": 150
    }
  },
  "edges": {
    "arrows": {"to": {"enabled": true}},
    "smooth": {"type": "curvedCW", "roundness": 0.2}
  },
  "nodes": {
    "font": {"size": 12},
    "borderWidth": 2
  }
}
""")
```

### 5.3 노드/엣지 추가

```python
# 노드
for node in filtered_nodes:
    tooltip = f"{node.table_name}\n카테고리: {node.category}\n"
    tooltip += "\n".join(f"  {c.name}: {c.description}" for c in node.columns if not c.is_comment)
    net.add_node(
        node.table_name,
        label=node.table_name,
        color=node.color,
        size=10 + node.fk_count * 3,
        title=tooltip,   # hover tooltip
        shape="dot"
    )

# 엣지
for edge in filtered_edges:
    net.add_edge(
        edge.source, edge.target,
        label=edge.label,
        title=f"{edge.source} → {edge.target}\n({edge.label})",
        arrows="to"
    )
```

### 5.4 Streamlit 렌더링

```python
# pyvis → HTML 문자열 → st.components
html = net.generate_html()
st.components.v1.html(html, height=720, scrolling=False)
```

### 5.5 세션 상태

| 키 | 타입 | 설명 |
|----|------|------|
| `graph_data` | `GraphData` | 파싱된 전체 그래프 데이터 |
| `selected_categories` | `set[str]` | 현재 선택된 카테고리 |
| `show_outgame_only` | `bool` | 아웃게임만 표시 여부 |

### 5.6 필터링 로직

```python
def filter_graph(graph_data: GraphData, selected_categories: set[str]) -> GraphData:
    filtered_nodes = [n for n in graph_data.nodes if n.category in selected_categories]
    visible_names = {n.table_name for n in filtered_nodes}
    filtered_edges = [
        e for e in graph_data.edges
        if e.source in visible_names and e.target in visible_names
    ]
    return GraphData(nodes=filtered_nodes, edges=filtered_edges)
```

---

## 6. 엣지케이스 처리

| 상황 | 처리 |
|------|------|
| yaml 파일 없음 | 빈 그래프 + "categories.yaml를 설정해주세요" 안내 |
| excel 폴더 없음 | st.error() 표시 |
| 파싱 실패 파일 | 사이드바에 경고 목록 표시 (앱 crash 금지) |
| 필터링 후 노드 0개 | "표시할 테이블이 없습니다" 안내 |
| FK target 없음 | edge 미생성 (조용히 무시) |
| 노드 너무 많음 (100+) | physics 자동 비활성화 (성능) |

---

## 7. 의존성 (requirements.txt)

```
streamlit>=1.32.0
openpyxl>=3.1.2
pyvis>=0.3.2
pyyaml>=6.0
```

> Python 3.10 이상

---

## 8. 모듈 의존성

```
app.py
  └── parser.py     (GraphData 로딩)
      └── categories.yaml (카테고리 설정)

parser.py  → openpyxl, re, yaml, dataclasses, pathlib
app.py     → streamlit, pyvis, parser
```

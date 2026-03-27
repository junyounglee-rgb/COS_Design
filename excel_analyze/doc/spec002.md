# excel_analyze 상세 기술 명세서

> 작성일: 2026-03-27
> 버전: 2.0
> 변경 이력: spec001 대비 — 누락 24개 파일 분류 추가, pyvis API 수정, 텍스트 출력 1단계 추가

---

## 개요

Excel 기획 데이터 파일(~120개 xlsx) 간의 FK 관계를 분석하는 웹 UI.
**1단계: 텍스트 출력으로 파싱 결과 검증 → 2단계: pyvis 네트워크 시각화**
기획자 직접 사용. 아웃게임 데이터 기본 표시, 인게임 선택 표시.

---

## 개발 단계

```
1단계 (텍스트):  parser.py + app_text.py  → 파싱 결과 텍스트로 검증
2단계 (시각화):  app.py                   → pyvis 네트워크 그래프
```

---

## 프로젝트 구조

```
D:\claude_make\excel_analyze\
├── app_text.py         # 1단계: 텍스트 출력 Streamlit UI
├── app.py              # 2단계: pyvis 시각화 Streamlit UI
├── parser.py           # Excel 파싱 + 관계 추출 (공통)
├── categories.yaml     # 카테고리 분류 + 색상 설정
├── requirements.txt
└── doc/
    ├── spec001.md
    └── spec002.md
```

---

## 1. Excel 파일 규칙 (공통 전제)

| Row | 역할 | 예시 |
|-----|------|------|
| Row1 | 컬럼 설명/주석 (한국어) | `"쿠키 ID Sheet에 있는 Key값"` |
| Row2 | JSON 익스포트 경로 | `cookies/^0/` |
| Row3 | 컬럼 헤더 | `^key`, `$filter`, `#주석`, `ref_X_id` |
| Row4~ | 실제 데이터 | (파싱 불필요) |

**컬럼 헤더 접두사 규칙:**
- `^` → Primary Key
- `#` → 주석 컬럼 (skip)
- `$` → 필터 컬럼
- `ref_X_id` / `ref_X_key` / `ref_X_type` → Foreign Key

**FK 추출 패턴:** `re.match(r'ref_(.+?)_(id|key|type)$', col_name)` → 캡처그룹1 = target

---

## 2. 데이터 모델

```python
from dataclasses import dataclass, field

@dataclass
class ColumnInfo:
    name: str               # Row3 원문
    description: str        # Row1 설명 (없으면 "")
    is_pk: bool             # ^ 시작
    is_comment: bool        # # 시작
    is_filter: bool         # $ 시작
    fk_target: str | None   # ref_ 패턴 → target 테이블명 (없으면 None)

@dataclass
class CategoryInfo:
    name: str
    color: str              # hex 색상
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
    source: str             # source table_name
    target: str             # target table_name
    label: str              # FK 컬럼명
    source_file: str
    target_file: str

@dataclass
class GraphData:
    nodes: list[TableNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # 파싱 실패 파일명
```

---

## 3. categories.yaml 명세

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
      - dialog_groups

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
      - haptics
      - mode_tool_tips
      - themes
      - tutorials
      - ui_sounds

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
      - miya_dialogs

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
      - play_block_rules
      - relays

  아웃게임_잠금조건:
    color: "#8E44AD"
    visible: true
    files:
      - unlock_conditions
      - contents_unlocks

  아웃게임_랭킹:
    color: "#D35400"
    visible: true
    files:
      - ovencrown

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
      - power_sands
      - voices

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
      - action_objects
      - fog_zone_areas
      - ingame_exps
      - interaction_infos
      - minimap_configs
      - npc_infos
      - pattern_items
      - spots
      - virtual_pads
      - win_lose_poss

  미분류:
    color: "#BDC3C7"
    visible: false
    files: []
```

---

## 4. parser.py 명세

### 4.1 함수 목록

#### `load_config(yaml_path: str) -> tuple[str, dict[str, CategoryInfo]]`
- YAML 파싱 → `(excel_folder, {category_name: CategoryInfo})`
- 파일 미존재 시 `("", {})` 반환 (예외 금지)

#### `get_file_category(file_name_no_ext: str, categories: dict) -> tuple[str, str]`
- `(category_name, hex_color)` 반환
- 매칭 없으면 `("미분류", "#BDC3C7")`

#### `extract_columns(ws) -> list[ColumnInfo]`
- Row1(설명), Row3(헤더) 읽기
- Row3 None 컬럼 skip
- `fk_target`: `re.match(r'ref_(.+?)_(id|key|type)$', name)` → 그룹1
- Row3 없거나 비어있으면 `[]`

#### `parse_file(file_path: str, category: str, color: str) -> list[TableNode]`
- `openpyxl.load_workbook(read_only=True, data_only=True)`
- `#` 시작 시트명 skip
- 시트별 `extract_columns()` → TableNode 생성
- 예외 시 `[]` 반환 + 호출자가 warnings에 추가

#### `extract_edges(nodes: list[TableNode], all_table_names: set[str]) -> tuple[list[GraphEdge], list[str]]`
- FK 컬럼 → target 매칭 순서:
  1. `fk_target` 그대로
  2. `fk_target + 's'`
  3. 없으면 skip
- 반환: `(edges, dangling_warnings)` — dangling은 "ref_X → 대상 없음" 목록

#### `parse_excel_folder(yaml_path: str) -> GraphData`
- 전체 오케스트레이션
- `~$` 임시파일 제외, `.xlsx` 만 처리
- 파싱 실패/dangling 경고 → `GraphData.warnings`에 누적
- `test_jun1` 등 test 파일 skip (파일명에 `test` 포함 시)

### 4.2 엣지케이스

| 상황 | 처리 |
|------|------|
| yaml 없음 | `("", {})` 반환, app에서 안내 |
| excel 폴더 없음 | GraphData(warnings=["폴더 없음"]) 반환 |
| Row3 비어있음 | 빈 TableNode (columns=[]) |
| `#` 시트 | skip |
| 멀티시트 | 시트별 별도 TableNode |
| 파싱 실패 파일 | skip + warnings 추가 |
| FK target 미존재 | edge 미생성 + dangling warning |
| test 파일 | skip (파일명 소문자에 'test' 포함) |

---

## 5. 1단계: app_text.py 명세 (텍스트 출력)

### 목적
parser.py 파싱 결과를 텍스트로 검증. 시각화 이전에 데이터 정합성 확인.

### 화면 구성

```
┌─────────────────┬──────────────────────────────────────────────┐
│  [사이드바]       │  [메인]                                       │
│                 │                                              │
│ [파싱 실행]      │  ## 파싱 요약                                  │
│                 │  - 총 파일: N개 / 총 테이블: M개               │
│ 표시 필터:       │  - 총 FK 관계: K개                             │
│ ◉ 아웃게임만    │  - 경고: W개                                   │
│ ○ 전체          │                                              │
│                 │  ## 카테고리별 테이블 목록                       │
│ 카테고리 선택:   │  ### 아웃게임_경제상점 (9개 테이블)               │
│ ☑ 경제/상점     │  | 테이블 | PK | FK수 | FK 관계 |               │
│ ☑ 이벤트       │  |-------|-----|------|---------|              │
│ ...             │  | items | ^key | 2 | → unlock_conditions |  │
│                 │  | shop  | ^key | 1 | → items |              │
│                 │  ...                                         │
│                 │                                              │
│                 │  ## FK 관계 전체 목록                           │
│                 │  | source | target | 컬럼명 |                  │
│                 │  |--------|--------|--------|                 │
│                 │  | cookies | unlock_conditions | ref_unlock.. |│
│                 │  ...                                         │
│                 │                                              │
│                 │  ## 경고 목록                                  │
│                 │  - dangling: ref_X → 대상 없음               │
│                 │  - 파싱 실패: Y.xlsx                           │
└─────────────────┴──────────────────────────────────────────────┘
```

### 함수 목록

#### `render_summary(graph_data: GraphData) -> None`
- 총 파일·테이블·FK·경고 수 `st.metric()` 4개 표시

#### `render_category_tables(filtered: GraphData) -> None`
- 카테고리별로 묶어서 `st.expander(카테고리명 + 테이블수)`
- 내부: `st.dataframe()` — 컬럼: 테이블명 / PK / FK수 / FK 관계 목록

#### `render_edge_list(filtered: GraphData) -> None`
- 전체 FK 관계를 `st.dataframe()` 표
- 컬럼: source 테이블 / target 테이블 / FK 컬럼명 / source 카테고리 / target 카테고리

#### `render_warnings(graph_data: GraphData) -> None`
- `graph_data.warnings` 가 있으면 `st.warning()` 로 목록 표시

#### `filter_graph(graph_data: GraphData, selected_categories: set[str]) -> GraphData`
- 선택된 카테고리의 노드만 포함
- 양쪽 노드 모두 visible일 때만 edge 포함

### 세션 상태

| 키 | 타입 | 설명 |
|----|------|------|
| `graph_data` | `GraphData \| None` | 파싱 결과 (None = 미실행) |
| `selected_categories` | `set[str]` | 현재 선택 카테고리 |
| `show_outgame_only` | `bool` | 아웃게임만 표시 여부 |

---

## 6. 2단계: app.py 명세 (pyvis 시각화)

> **선행 조건:** app_text.py에서 텍스트 출력 검증 완료 후 진행

### pyvis 설정

```python
from pyvis.network import Network
import tempfile, os

net = Network(height="700px", width="100%", directed=True,
              bgcolor="#1a1a2e", font_color="white")

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
  "nodes": {"font": {"size": 12}, "borderWidth": 2}
}
""")
```

### pyvis HTML 생성 (수정된 방식)

```python
# net.generate_html() 없음 — 파일 경유 방식 사용
with tempfile.NamedTemporaryFile(mode='w', suffix='.html',
                                  delete=False, encoding='utf-8') as f:
    tmp_path = f.name

net.show(tmp_path, notebook=False)

with open(tmp_path, 'r', encoding='utf-8') as f:
    html = f.read()

os.unlink(tmp_path)
st.components.v1.html(html, height=720, scrolling=False)
```

### 노드/엣지 추가

```python
for node in filtered.nodes:
    tooltip = f"<b>{node.table_name}</b><br>카테고리: {node.category}<br><br>"
    tooltip += "<br>".join(
        f"{c.name}: {c.description}" for c in node.columns
        if not c.is_comment and c.name
    )
    net.add_node(
        node.table_name,
        label=node.table_name,
        color=node.color,
        size=10 + node.fk_count * 3,
        title=tooltip,
        shape="dot"
    )

for edge in filtered.edges:
    net.add_edge(
        edge.source, edge.target,
        label=edge.label,
        title=f"{edge.source} → {edge.target} ({edge.label})",
        arrows="to", width=1.5
    )
```

### 성능 처리

```python
# 노드 100개 초과 시 physics 비활성화
if len(filtered.nodes) > 100:
    net.toggle_physics(False)
```

---

## 7. 엣지케이스 처리

| 상황 | 처리 |
|------|------|
| yaml 없음 | "categories.yaml을 설정해주세요" st.error + 종료 |
| excel 폴더 없음 | st.error() 표시 |
| 파싱 실패 파일 | 사이드바 경고 목록 (앱 crash 금지) |
| 필터링 후 노드 0개 | "표시할 테이블이 없습니다" st.info |
| dangling FK | warnings에 포함, app_text에서 표시 |
| 노드 100+ | physics 비활성화 |
| test 파일 | parser에서 자동 skip |

---

## 8. 의존성 (requirements.txt)

```
streamlit>=1.32.0
openpyxl>=3.1.2
pyvis>=0.3.2
pyyaml>=6.0
```

---

## 9. 모듈 의존성

```
app_text.py  ─┐
              ├── parser.py → categories.yaml, openpyxl, re, yaml
app.py       ─┘
```

---

## 10. 개발 순서

```
Step 1: categories.yaml 생성
Step 2: parser.py 구현 → 단위 테스트 (python parser.py 직접 실행)
Step 3: app_text.py 구현 → 텍스트 출력 검증
         ↓ 데이터 정합성 확인 후
Step 4: app.py 구현 → pyvis 시각화
```

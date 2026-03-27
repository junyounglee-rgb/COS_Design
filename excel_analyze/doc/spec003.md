# excel_analyze 상세 기술 명세서

> 작성일: 2026-03-27
> 버전: 3.0 (최종)
> 변경 이력: spec002 대비 — ColumnInfo.export_path 추가, 제외 파일 GUI 구현, 2단계 시각화 미진행 결정

---

## 개요

Excel 기획 데이터 파일(~120개 xlsx) 간의 FK 관계를 분석하는 웹 UI.
기획자 직접 사용. 텍스트 출력으로 파싱 결과 검증 → **시각화 없이 텍스트만으로 충분하다고 판단, 1단계로 완료.**

---

## 개발 완료 상태

```
완료: parser.py + app_text.py (텍스트 출력 UI)
미진행: app.py (pyvis 시각화) — 텍스트만으로 충분, 필요 시 추후 추가
```

**파싱 결과 (실측):** 약 239 테이블, 67 FK 관계, 76 경고 (dangling FK 포함)

---

## 프로젝트 구조

```
D:\claude_make\excel_analyze\
├── app_text.py         # 텍스트 출력 Streamlit UI (완료)
├── parser.py           # Excel 파싱 + 관계 추출 (완료)
├── categories.yaml     # 카테고리 분류 + 제외 파일 설정
├── requirements.txt
└── doc/
    ├── spec001.md
    ├── spec002.md
    └── spec003.md      # 현재
```

---

## 1. Excel 파일 규칙

| Row | 역할 | 예시 |
|-----|------|------|
| Row1 | 컬럼 설명/주석 (한국어) | `"쿠키 ID Sheet에 있는 Key값"` |
| Row2 | JSON 익스포트 경로 | `cookies/^0/` or `quests/^0/rewards/0/` |
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
@dataclass
class ColumnInfo:
    name: str               # Row3 원문
    description: str        # Row1 설명 (없으면 "")
    export_path: str        # Row2 JSON 익스포트 경로 (없으면 "")
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
    @property fk_count -> int
    @property pk_column -> str | None

@dataclass
class GraphEdge:
    source: str; target: str; label: str   # FK 컬럼명
    source_file: str; target_file: str

@dataclass
class GraphData:
    nodes: list[TableNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

---

## 3. categories.yaml 명세

```yaml
excel_folder: D:\COS_Project\cos-data\excel

exclude_files:          # GUI에서 관리, save_exclude_files()로 자동 저장
  - ai_infos
  - camera_shakes
  - ...

categories:
  아웃게임_경제상점:
    color: "#E74C3C"
    visible: true
    files: [items, item_boxes, item_groups, item_random_pools, shop,
            gacha_shops, product, inventory, drop_infos]

  아웃게임_이벤트:
    color: "#E67E22"
    files: [event_infos, attendance_events, daily_fortune_events,
            invitation_events, nday_mission_events, step_mission_events,
            quest_gacha_events, pve_events, vault_mission_events]

  아웃게임_퀘스트미션:
    color: "#F1C40F"
    files: [quests, cookie_masteries, achievements]

  아웃게임_소셜:
    color: "#2ECC71"
    files: [social, nicknames, mail, word_filters, community_urls, dialog_groups]

  아웃게임_UI시스템:
    color: "#1ABC9C"
    files: [lobby_buttons, shortcuts, setting_menus, settings, screen_infos,
            contents_info, contents_unlocks, game_config, errors,
            rolling_banners, haptics, mode_tool_tips, themes, tutorials, ui_sounds]

  아웃게임_번역:
    color: "#3498DB"
    visible: false
    files: [translations_ko, translations_en, translations_ja, translations_zh_hant,
            translations_id, translations_th, translations_vi,
            string_keywords, keywords, ui_strings]

  아웃게임_로비타운:
    color: "#9B59B6"
    files: [town_config, town_items, town_npc_infos, thumbnails,
            portraits, profile_items, miya_dialogs]

  아웃게임_모드맵:
    color: "#16A085"
    files: [modes, maps, matching_rules, jelly_race_modes, pve_round_modes,
            bounty_modes, escort_modes, castle_break_modes, death_match_modes,
            battle_royal_modes, battle_roads, gnome_battle_modes,
            drop_the_beat_modes, smash_levels, smash_pass, play_block_rules, relays]

  아웃게임_잠금조건:
    color: "#8E44AD"
    files: [unlock_conditions, contents_unlocks]

  아웃게임_랭킹:
    color: "#D35400"
    files: [ovencrown]

  인게임_캐릭터:
    color: "#95A5A6"
    visible: false
    files: [cookies, costumes, cookie_ranks, cookie_voices, cookie_npc_infos,
            expressions, highlights, cookie_bot, mvps, power_sands, voices]

  인게임_전투:
    color: "#7F8C8D"
    visible: false
    files: [skill_infos, skill_charges, skill_area_of_effects, skill_basic_gauges,
            skill_collision_infos, skill_custom_fxs, skill_explosions,
            skill_projectiles, skill_summons, skill_tags, skill_tether_beams,
            status_effect_infos, status_effect_values, stats_infos, buff_cards,
            ai_infos, damage_fonts, camera_shakes, cameras, hit_fx_sockets,
            screen_effects, battle_boxes, battle_card, battle_points, kill_feeds,
            observes, parabola_guides, system_buffs, action_objects, fog_zone_areas,
            ingame_exps, interaction_infos, minimap_configs, npc_infos,
            pattern_items, spots, virtual_pads, win_lose_poss]

  미분류:
    color: "#BDC3C7"
    visible: false
    files: []
```

---

## 4. parser.py 함수 목록

| 함수 | 반환 | 비고 |
|------|------|------|
| `load_config(yaml_path)` | `(excel_folder, {name: CategoryInfo})` | 예외 시 `("", {})` |
| `build_file_category_map(yaml_path)` | `(folder, file_map, visible_map, exclude_files)` | GUI용 |
| `save_exclude_files(yaml_path, list)` | `None` | yaml 저장, 실패 시 RuntimeError |
| `get_all_file_names(yaml_path)` | `list[str]` | xlsx 전체 목록 (UI 자동완성용) |
| `get_file_category(name, file_map)` | `(category, color)` | 없으면 미분류 |
| `extract_columns(ws)` | `list[ColumnInfo]` | Row1/Row2/Row3 파싱 |
| `parse_file(path, category, color)` | `list[TableNode]` | 멀티시트, `#` 시트 skip |
| `extract_edges(nodes, all_names)` | `(edges, dangling_warns)` | 복수형(+s) 재시도 |
| `parse_excel_folder(yaml_path)` | `GraphData` | ~$ / test / exclude_files 제외 |

**엣지케이스:**
- Row3 비어있음 → `columns=[]`
- FK target 미존재 → edge 미생성 + dangling warning
- 멀티시트 → 시트별 별도 TableNode

---

## 5. app_text.py 구성 (구현 완료)

### 사이드바

```
[🔄 파싱 실행]          ← 최상단
─────────────────────
제외 파일 관리  [↺ 초기화]
[selectbox 파일 선택] [추가]
  fname1  [✕]
  fname2  [✕]
  ...
─────────────────────
표시 범위: 아웃게임만 [toggle]
카테고리 필터: [checkbox × N]
```

- 초기화 버튼: `session_state["confirm_reset"]` 플래그 → 확인 다이얼로그 (✅네 / ❌아니오)
- 제외 파일 추가/삭제 즉시 `save_exclude_files()` → `st.rerun()`
- DEFAULT_EXCLUDE_FILES 31개 하드코딩 (초기화 기준값)

### 메인 탭

| 탭 | 내용 |
|----|------|
| 📁 카테고리별 테이블 | 카테고리 expander → 테이블 expander → 컬럼 상세 (이름/Row1설명/Row2익스포트경로/PK/FK) |
| 🔗 FK 관계 목록 | source·target·FK컬럼·카테고리 dataframe |
| ⚠️ 경고 | 파싱경고(st.warning) + dangling FK(st.caption, collapsed) |

### 세션 상태

| 키 | 타입 |
|----|------|
| `graph_data` | `GraphData \| None` |
| `confirm_reset` | `bool` |

---

## 6. 데이터 분석 인사이트

### 배틀박스 아이템 구성 데이터 체인

```
battle_boxes (^key=1000110)
  └─ box_grade_id=1000111
        ↓
battle_box_grade_tables (battle_boxes.xlsx 내 별도 시트)
  └─ key=1000111, reward_item/id=1000111
        ↓
items.xlsx
  └─ id=1000111 → "배틀박스 1단계 보상 확인 아이템" (ITEM_CATEGORY_ITEM_R)
        ↓
item_random_pools.xlsx   ← 실제 상품 목록
  └─ key=1000111 → candidates 배열 (weight 기반 랜덤 보상)
```

ITEM_CATEGORY_ITEM_R 타입 아이템 = 랜덤 보상 티켓 역할. 2단계 간접 참조 구조.

---

## 7. 의존성

```
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.2
pyvis>=0.3.2    # 현재 미사용, 추후 시각화 시 사용
pyyaml>=6.0
```

# 에이전트 정의 (excel_search 프로젝트)

## 실행 흐름
```
Plan → Agent2(config) → Agent3(indexer) → Agent4(searcher) → Agent5(app)
각 단계 완료 후 → Explore(검증)
```

## 모듈-에이전트 매핑

| 에이전트 | 타입 | 모듈 | 단계 | 핵심 포인트 |
|----------|------|------|------|-------------|
| Agent1 | Plan | spec 작성 | 0 | DB스키마·함수시그니처·엣지케이스·의존성 |
| Agent2 | general-purpose | config.py | 1 | config.txt 파싱/저장, pathlib, 기본값 반환 |
| Agent3 | general-purpose | indexer.py | 2 | WAL모드, executemany, gc.collect, header=2 |
| Agent4 | general-purpose | searcher.py | 3 | FTS5+LIKE fallback, GROUP BY, 중복 전체반환 |
| Agent5 | general-purpose | app.py | 4 | HTML테이블, open_file, st.columns 혼합렌더링 |
| Agent6 | Explore | 검증 | 각단계후 | 명세일치·엣지케이스·인터페이스호환 |

---

## Agent1 — Plan
명세서 작성: DB스키마 / 함수시그니처 / UI구성 / 엣지케이스 / 의존성
→ 파일명: `spec001.md`, 수정 시 번호 증가

**프롬프트:**
```
[요구사항]과 [프로젝트구조]를 바탕으로 [프로그램명] 상세 기술 명세서 작성.
항목: DB스키마(테이블·인덱스) / 모듈별 함수명세(시그니처·로직) / UI·이벤트 / 엣지케이스 / 의존성
실제 개발자가 바로 구현 가능한 수준으로.
```

---

## Agent2 — config.py
- `load_config` / `save_config` 구현
- `#` 주석 처리, KEY=VALUE 파싱, `EXCLUDE_FILES` 리스트
- 파일 미존재 시 기본값 반환 (예외 금지)

---

## Agent3 — indexer.py
- SQLite 스키마 초기화 + FTS5 트리거
- `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`
- `executemany` 배치 INSERT, `del df; gc.collect()` 필수
- `~$` 임시파일 제외, `header=2` 고정

---

## Agent4 — searcher.py
- `search_exact`: `WHERE cell_value=:q`, GROUP BY file_id·sheet_name·col_index
- `search_partial`: FTS5 → LIKE fallback
- FTS5 특수문자 이스케이프, 빈 쿼리 early return
- 동일 값 N개 파일 → N행 전부 반환 (limit 내)

---

## Agent5 — app.py
- `st.markdown(html, unsafe_allow_html=True)` HTML 테이블 렌더링
- 각 결과행: `st.columns([3,2,2,1,1])` = 파일명|시트|컬럼|매칭수|[열기]
- `open_file()`: win=`os.startfile` / mac=`open` / linux=`xdg-open`
- 결과 50건↑: `st.expander()` 분할
- 요약: "총 N건 (M개 파일에서 발견)"

**체크리스트:**
- [ ] 사이드바: 폴더경로·제외파일 설정/저장
- [ ] 검색UI: 입력·모드선택·결과제한·인덱스업데이트
- [ ] HTML테이블 + 열기버튼 혼합렌더링
- [ ] expander: 컬럼 전체데이터 (검색어 bold강조)
- [ ] CSV 내보내기 (utf-8-sig)

---

## Agent6 — Explore (검증)
**공통:** 명세함수 전부 구현 여부 / 시그니처 일치 / 엣지케이스 / 인터페이스 호환 / 잠재버그

**app.py 추가:** HTML렌더링 정상 / open_file 호출 / st.columns 정렬 / expander 50건분할 / 파일없음 st.error / 요약 정확성

**프롬프트:**
```
[명세서]와 [구현파일]을 비교 검토. 위 검증항목 기준으로 문제점과 수정방법 구체적으로.
```

---

## 재사용 가이드
1. Plan → spec001.md 저장
2. 수정 시 spec번호 증가 (버전이력 유지)
3. 모듈 유형별 에이전트 선택 (표 참조)
4. 각 모듈 완료 후 Explore 검증

---

# 에이전트 정의 (excel_analyze 프로젝트)

## 실행 흐름
```
Plan → Agent-P(parser.py) → Agent2(categories.yaml) → Agent5(app.py)
각 단계 완료 후 → Explore(검증)
```

## 모듈-에이전트 매핑

| 에이전트 | 타입 | 모듈 | 단계 | 핵심 포인트 |
|----------|------|------|------|-------------|
| Agent1 | Plan | spec 작성 | 0 | 데이터모델·함수시그니처·엣지케이스·의존성 |
| Agent-P | general-purpose | parser.py | 1 | Row1~3파싱, FK추출(ref_패턴), GraphData생성 |
| Agent2 | general-purpose | categories.yaml | 2 | YAML 카테고리·색상 설정, 파일분류 |
| Agent5 | general-purpose | app.py | 3 | pyvis 네트워크그래프, 카테고리필터, 툴팁 |
| Agent6 | Explore | 검증 | 각단계후 | 명세일치·FK추출정확성·그래프렌더링 |

---

## Agent-P — parser.py (신규, excel_analyze 전용)

**타입:** `general-purpose`

**역할:** Excel Row1~3 파싱으로 테이블 스키마 + FK 관계 추출 → GraphData 생성

**Excel 파일 규칙 (필수 숙지):**
- Row1: 컬럼 설명/주석 (한국어)
- Row2: JSON 익스포트 경로 (`sheet_name/^0/` 형태)
- Row3: 컬럼 헤더 (`^key`/`^id`=PK, `#`=주석, `$`=필터, `ref_X_id/key`=FK)
- Row4~: 데이터 (파싱 불필요)
- `~$` 임시파일 제외

**FK 추출 규칙:**
- 패턴: `ref_(.+?)_(id|key|type)$` → 캡처그룹1이 target table
- 복수형 처리: `cookie` → `cookies`, `item` → `items` (s 붙여서 매칭 재시도)
- target이 실제 파일에 없으면 edge 생성 안 함 (dangling ref 무시)

**함수 목록:**
- `load_categories(yaml_path) -> dict[str, CategoryInfo]`
- `parse_excel_folder(folder_path, categories) -> GraphData`
- `parse_file(file_path, category) -> list[TableNode]`
- `extract_columns(ws) -> list[ColumnInfo]`
- `extract_edges(nodes, all_table_names) -> list[GraphEdge]`

**특이사항:**
- 멀티시트 파일: 시트별로 별도 TableNode 생성 (`#`으로 시작하는 시트명 제외)
- openpyxl `read_only=True, data_only=True` 사용 (성능)
- 파싱 실패 파일은 skip + 경고 로그 (crash 금지)

---

## Agent5 확장 — app.py (excel_analyze용 추가 사항)

기존 Agent5에 추가:
- `pyvis.Network` → HTML 생성 → `st.components.v1.html(html, height=700)`
- 노드: label=table_name, color=카테고리색상, size=10+(FK수×3), title=컬럼목록(tooltip)
- 엣지: arrows="to", label=FK컬럼명, title=source→target 설명
- physics: `barnes_hut` (초기), 사이드바에서 토글 가능
- 사이드바: 카테고리별 체크박스 필터, "아웃게임만" 토글
- pyvis 클릭 이벤트는 미지원 → hover tooltip으로 컬럼 상세 표시

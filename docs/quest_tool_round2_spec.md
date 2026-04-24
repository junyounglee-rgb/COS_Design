# quest_tool TPL_C Round 2 스펙

## 개요

| 항목 | 값 |
|---|---|
| 문서번호 | spec-quest_tool-round2 |
| 대상 | `quest_tool/quest_validator.py` (신규), `quest_tool/quest_writer.py` (변경), `quest_tool/app.py` (변경) |
| 작성일 | 2026-04-24 |
| 작성자 | PM |
| 관련 커밋 | `b2a5d16` |
| 히스토리 | `D:\claude_make\docs\quest_tool_round2_history.md` |

## 파일 구성

| 파일 | 역할 |
|---|---|
| `quest_tool/quest_validator.py` | write-path 검증 모듈 (신규) |
| `quest_tool/quest_writer.py` | xlsx append + atomic save + key 할당 |
| `quest_tool/app.py` | Streamlit UI, GOAL_TYPES/CONDITIONS 카탈로그, 탭 라우팅 |
| `quest_tool/tests/test_quest_validator.py` | 검증 규칙 45건 (신규) |
| `quest_tool/tests/test_quest_writer.py` | writer 92건 |

## quest_validator.py 공개 API

| 식별자 | 종류 | 시그니처 | 반환 |
|---|---|---|---|
| `ValidationRefs` | NamedTuple | 5 필드 (아래 표) | - |
| `build_refs_from_paths` | 함수 | `(items_path, keywords_path, dialog_groups_path, quests_path) -> ValidationRefs` | `ValidationRefs` |
| `validate_quest_row` | 함수 | `(row: dict, refs: ValidationRefs) -> list[str]` | 위반 메시지 리스트 (빈 리스트=통과) |
| `validate_daily_set` | 함수 | `(parent: dict, children: list[dict], refs: ValidationRefs) -> list[str]` | 위반 메시지 리스트 |

### ValidationRefs NamedTuple

| 필드 | 타입 | 출처 |
|---|---|---|
| `item_ids` | `frozenset[int]` | items.xlsx `^id` |
| `keyword_ids` | `frozenset[int]` | keywords.xlsx `^id` |
| `dialog_group_ids` | `frozenset[int]` | dialog_groups.xlsx `^id` |
| `quest_keys` | `frozenset[int]` | quests.xlsx `^key` (순환 참조 차단용) |
| `goal_type_map` | `dict[str, set[str]]` | GoalType -> 허용 CountType 집합 |

## validate_quest_row 규칙 매트릭스

| 항목 | 규칙 | 위반 예 |
|---|---|---|
| `^key` | int, 1~999999, 중복 금지 | `"73000"`, `-1`, `1000000` |
| `$filter` | `{HELSINKI, LAUNCH_0, NONE, ...}` 화이트리스트 | `""`, `"helsinki"` |
| `reset_type` | `{DAILY, WEEKLY, NONE, REPEAT}` | `"daily"`, `None` |
| `goal_type` | `goal_type_map` 키 일치 | `finish_town_dialog:dialog_group_id` (Goal 영역) |
| `count_type` | `goal_type_map[goal_type]` 허용 집합 | `play` + `HIGHEST` (SUM/LATEST 만 허용) |
| `goal_count` | int, >=1 | `0`, `-5` |
| `ref_*` FK | 각 `*_ids` 집합에 존재 | `ref_dialog_group_id=9999` (없는 id) |
| `ref_quest_ids` | `quest_keys` 전부 존재 | child 가 parent 자기 자신 참조 |

## validate_daily_set 불변식 매트릭스

| 불변식 | 규칙 | 위반 예 |
|---|---|---|
| parent.count_type | `HIGHEST` 고정 | `SUM` |
| parent.goal_type | `reward_quest:ref_quest_ids` 고정 | `play` |
| parent.goal_count | `len(children)` 와 동일 | 5 child 인데 3 |
| parent.reset_type == child.reset_type | 전원 동일 | parent=DAILY, child 일부 NONE |
| parent.$filter == child.$filter | 전원 동일 | parent=HELSINKI, child 일부 LAUNCH_0 |
| parent.ref_quest_ids == child.^key set | 누락/추가 없음 | child 3개, parent ref_quest_ids 에 2개만 기재 |
| 각 child | `validate_quest_row` 전체 통과 | - |

## quest_writer.py 공개 API

| 식별자 | 시그니처 | 변경점 |
|---|---|---|
| `append_quest_row` | `(xlsx_path, sheet, row: dict, *, validate: bool = True, refs: ValidationRefs \| None = None) -> int` | `validate` 기본 True, refs 자동 로드 지원 |
| `append_daily_set` | `(xlsx_path, parent: dict, children: list[dict], *, validate: bool = True, refs: ValidationRefs \| None = None) -> tuple[int, list[int]]` | 신규 원자 삽입 |
| `allocate_child_keys` | `(existing: Iterable[int], parent_key: int, n: int, *, category: str \| None = None, reset_type: str \| None = None) -> list[int]` | 가드 강화 |
| `suggest_next_parent_key` | `(existing: Iterable[int], *, step: int = 1000, category: str \| None = None, reset_type: str \| None = None, existing_by_filter: Iterable[int] \| None = None) -> int` | filter-scoped 재작성 |
| `get_existing_keys_by_filter` | `(xlsx_path, sheet, filter_value: str) -> list[int]` | 신설 |
| `_atomic_save` | `(wb, xlsx_path) -> None` | 내부, mkstemp + os.replace |
| `_coerce_key_to_int` | `(raw) -> int` | 내부, bool 거부, str 정수 변환 |

### allocate_child_keys 동작

| 입력 조건 | 결과 |
|---|---|
| `parent_key <= 0` | `ValueError` |
| `parent_key > 999999` | `ValueError` |
| `isinstance(parent_key, bool)` | `TypeError` (int 서브타입 차단) |
| `n <= 0` | `ValueError` |
| 정상 | `[parent_key+1, parent_key+2, ...]` 중 `existing` 과 충돌 제외하여 `n` 개 반환 |

### suggest_next_parent_key 동작

```
existing_by_filter != None -> max(existing_by_filter, default=base) + step
existing_by_filter == None -> 기존 전역 scan fallback (비권장)
base = category/reset_type 별 hardcoded 구간 시작값
```

| 조건 | 반환 |
|---|---|
| filter=LAUNCH_0, reset_type=NONE, `existing_by_filter` 빈 값 | 해당 구간 base 값 |
| filter=HELSINKI 내 max=73755, step=1000 | 74000 (step round-up) |
| filter 경계 넘김 | 방지 (다음 구간 base 미만으로 고정) |

## _atomic_save 패턴

| 단계 | 동작 |
|---|---|
| 1 | `tempfile.mkstemp(suffix='.xlsx', dir=os.path.dirname(xlsx_path))` |
| 2 | `os.close(fd)` |
| 3 | `wb.save(tmp_path)` |
| 4 | `os.replace(tmp_path, xlsx_path)` |
| 실패 시 | 임시파일 삭제, 원본 xlsx 는 변동 없음 |

## GOAL_TYPES / CONDITIONS 이원 설계

| 영역 | 키 | 실데이터 SUM | 비고 |
|---|---|---|---|
| `GOAL_TYPES[136]` (Round 1) | `finish_town_dialog:dialog_group_id` | 0건 | 오표기 |
| `GOAL_TYPES[136]` (Round 2) | `town_finish_dialog:ref_dialog_group_id` | 6건 | 교체 |
| `CONDITIONS[*]` | `finish_town_dialog:dialog_group_id` | 596건 | Condition entity, 유지 |

> Goal 과 Condition 은 서로 다른 entity 이므로 키 이름이 유사해도 **양쪽 모두 유지**. 혼동 방지를 위해 `GOAL_TYPES` 는 `ref_` 접두 유지.

## app.py 변경 요약

| 변경 위치 | 변경 내용 |
|---|---|
| `GOAL_TYPES[136]` | `town_finish_dialog:ref_dialog_group_id` 로 교체 |
| `main()` | `st.session_state["daily_children"]` pre-init 라인 삭제 |
| `render_tab_daily_set` | 탭 진입 시 `daily_children` 단일 초기화 |
| filter 변경 감지 | `_last_daily_filter` != 현재 filter -> `daily_parent_key` 삭제 후 재제안 |
| 저장 성공 후 | `daily_parent_desc`, `daily_parent_key`, `_last_daily_filter` session_state 3종 삭제 |
| writer 호출 | `append_daily_set(..., validate=True)` (기본값) |

## 테스트 구성 (137건)

| 파일 | 클래스/그룹 | 건수 | 설명 |
|---|---|---|---|
| `test_quest_writer.py` | 기존 테스트 | 74 | Round 1 유지 |
| `test_quest_writer.py` | `TestReproPriorFailures` | 5 | S4/S7/S8/S9/S11 회귀 |
| `test_quest_writer.py` | `TestAllocateChildKeysGuards` | 6 | 음수/0/999999+/bool |
| `test_quest_writer.py` | `TestSuggestFilterScoped` | 3 | filter-scoped 제안 |
| `test_quest_writer.py` | `TestStrKeyRejected` | 2 | str `^key` 거부 |
| `test_quest_writer.py` | `TestAtomicSave` | 2 | mkstemp 실패 시 원본 보존 |
| `test_quest_validator.py` | `TestValidateQuestRow` | ~25 | 항목별 규칙 (키/FK/goal/count/reset) |
| `test_quest_validator.py` | `TestValidateDailySet` | ~15 | parent/child 불변식 7종 |
| `test_quest_validator.py` | `TestBuildRefs` | ~5 | 경로 로드/누락 처리 |

## 상수 / 설정값

| 상수 | 값 | 위치 |
|---|---|---|
| `KEY_MIN` | 1 | `quest_writer.py` |
| `KEY_MAX` | 999999 | `quest_writer.py` |
| `DEFAULT_STEP` | 1000 | `suggest_next_parent_key` |
| DAILY reset_type | `DAILY` | 문서 §3.5 정정 |
| parent count_type | `HIGHEST` | `validate_daily_set` |
| parent goal_type | `reward_quest:ref_quest_ids` | `validate_daily_set` |
| allowed `$filter` | `{HELSINKI, LAUNCH_0, NONE, ...}` | `validate_quest_row` |
| allowed `reset_type` | `{DAILY, WEEKLY, NONE, REPEAT}` | `validate_quest_row` |

## 동작 흐름

### DAILY SET 신규 등록

| 단계 | 동작 |
|---|---|
| 1 | 사용자가 탭 진입, `daily_children` 빈 리스트로 초기화 |
| 2 | $filter 선택 -> `_last_daily_filter` 저장, `get_existing_keys_by_filter` 로 filter-scoped key 집합 확보 |
| 3 | `suggest_next_parent_key(existing_by_filter=...)` 로 parent_key 제안 |
| 4 | child 개수 n 입력 -> `allocate_child_keys(existing, parent_key, n)` 로 child key 배열 |
| 5 | parent/child dict 구성 후 `append_daily_set(xlsx_path, parent, children, validate=True)` 호출 |
| 6 | `validate_daily_set` 통과 시 `_atomic_save` 로 원자 저장, 실패 시 원본 유지 |
| 7 | 저장 성공 후 session_state 3종 삭제, 사용자에게 저장 완료 피드백 |

### 검증 실패 시 사용자 피드백

| 조건 | 표시 |
|---|---|
| parent 불변식 위반 | "부모 행 규칙 위반: ..." 리스트 |
| child FK 누락 | "자식 N번째 행: ref_* 이 참조 테이블에 없음" |
| 중복 `^key` | "기존 키와 충돌: [...]" |

## 의존성

| 모듈 | 용도 |
|---|---|
| `openpyxl` | xlsx read/write |
| `tempfile` | `_atomic_save` 임시 파일 |
| `os.replace` | 원자 치환 |
| `streamlit` | UI, session_state |
| `typing.NamedTuple` | `ValidationRefs` |
| `collections.abc.Iterable` | 인터페이스 타입 |

## 비고

- `validate=False` 를 통한 검증 우회는 writer 시그니처에서 제공하되, UI 기본값은 `True`. CLI/배치 사용 시에도 기본 True 유지.
- `_atomic_save` 는 동일 파일시스템 가정. 네트워크 드라이브 사용 시 `os.replace` semantics 재확인 필요.
- GOAL_TYPES 교체 이력은 Round 2 이후 변경 시 반드시 실데이터 SUM 스냅샷과 대조.
- Round 1 의 pytest 74건은 유지하되, Round 2 에서 추가된 18 regression 을 먼저 실행하여 빠른 실패 확보.

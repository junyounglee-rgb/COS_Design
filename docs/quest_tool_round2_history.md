# quest_tool TPL_C Round 2 개발 히스토리

## 개요

| 항목 | 값 |
|---|---|
| 문서번호 | his-quest_tool-round2 |
| 프로젝트 | quest_tool (TPL_C 데일리 세트 탭) |
| 작성일 | 2026-04-24 |
| 작성자 | PM |
| 관련 커밋 | `b136b98` (Round 1) -> `b2a5d16` (Round 2) |
| 선행 리포트 | `D:\claude_make\docs\tpl_c_data_qa_report_2026-04-24.md` |

## 개발 배경

| 구분 | 내용 |
|---|---|
| 기존 | Round 1 (`b136b98`) 74 pytest 전부 통과, 3축 하네스 중 qa-tool 만 검증 |
| 목적 | Generator-Evaluator 분리 원칙으로 독립 재검토 수행, 아키텍처 결함 선식별 |
| 결정 | `git reset --soft HEAD~1` 후 10건 아키텍처 결함을 단일 재커밋(`b2a5d16`)으로 통합 수정 |

## Round 1 실패 모드 요약

| 구분 | 건수 | 비고 |
|---|---|---|
| 전체 실패 모드 | 17 | HIGH 8 / MED 6 / LOW 3 |
| pytest 탐지 | 0 | write-path 검증 전무 |
| qa-tool 탐지 | 8 | HIGH 전부 |
| quest-data-qa 탐지 | 3 | GoalType 매핑, reset_type, parent/child 불변식 |
| content-evaluator | 17/40 PASS | Round 1 기준선 |

## 주요 개발 단계

| 단계 | 작업 | 산출 |
|---|---|---|
| 1 | Round 1 3축 하네스 재구동 | 17 실패 모드 매트릭스 확정 |
| 2 | `git reset --soft HEAD~1` | b136b98 되돌림, 파일 변경 유지 |
| 3 | `quest_validator.py` 신설 | `validate_quest_row`, `validate_daily_set`, `ValidationRefs`, `build_refs_from_paths` |
| 4 | `quest_writer.py` write-path 검증 배선 | `append_quest_row(validate=True)`, `append_daily_set(validate=True)` 기본값 |
| 5 | `_atomic_save()` 도입 | `tempfile.mkstemp` + `os.replace` 원자 저장 |
| 6 | `allocate_child_keys()` 가드 강화 | 음수/0/999999 초과, `bool` 거부, str `^key` 차단 |
| 7 | `suggest_next_parent_key()` 재작성 | filter-scoped max+step, LAUNCH_0 NONE 오탐 해결 |
| 8 | `app.py` GOAL_TYPES 136 교체 | `finish_town_dialog:dialog_group_id` -> `town_finish_dialog:ref_dialog_group_id` |
| 9 | `app.py` daily_children 이중 초기화 제거 | `render_tab_daily_set` 단일 초기화 |
| 10 | filter 변경/저장 성공 후 session_state 정리 | `_last_daily_filter`, `daily_parent_key`, `daily_parent_desc` 삭제 |
| 11 | 문서 교정 | 기획 draft §3.5 `reset_type=DAILY`, quest-data-qa 에이전트 매핑 표 보강 |
| 12 | 테스트 추가 | 137 PASS (writer 92 + validator 45) |
| 13 | 3축 하네스 재검증 | qa-tool PASS, quest-data-qa 8/8 PASS, content-evaluator 35/40 PASS |
| 14 | 단일 재커밋 `b2a5d16` | 10건 결함 통합 수정 |

## 10건 결함 매트릭스 (R-01 ~ R-10)

| ID | 위치 | 결함 | 심각도 | 해결 |
|---|---|---|---|---|
| R-01 | `quest_writer.py` | write-path 검증 미배선, 잘못된 row도 저장 가능 | HIGH | `append_quest_row(validate=True)` 기본값, validator 주입 |
| R-02 | `quest_writer.py` | xlsx 저장 중 프로세스 중단 시 파일 손상 | HIGH | `_atomic_save()` - tempfile.mkstemp + os.replace |
| R-03 | `quest_writer.py` `allocate_child_keys` | 음수/0/999999 초과/bool parent_key 허용 | HIGH | TypeError/ValueError 가드, bool 명시 거부 |
| R-04 | `quest_writer.py` `suggest_next_parent_key` | 전체 스캔으로 filter 무시, LAUNCH_0 NONE 영역에 HELSINKI 번호 제안 | HIGH | `existing_by_filter` 주입, filter-scoped max+step 재작성 |
| R-05 | `quest_writer.py` | str 형식 `^key` (예: "73000") 허용, int 혼재 | HIGH | `_coerce_key_to_int()` 전처리 후 타입 재검증 |
| R-06 | `app.py` GOAL_TYPES | `finish_town_dialog:dialog_group_id` 표기 (실데이터 0건), Condition 키와 이름 충돌 | HIGH | `town_finish_dialog:ref_dialog_group_id` (실 SUM 6건) 교체, Condition 영역은 596건 유지하여 이원화 |
| R-07 | `app.py` | `daily_children` 이중 초기화로 탭 전환 시 잔여 child 병합 | HIGH | `main()` pre-init 삭제, `render_tab_daily_set` 단일 초기화 |
| R-08 | `app.py` | filter 변경 후에도 이전 `daily_parent_key` 유지 -> 동일 parent_key 중복 | HIGH | `_last_daily_filter` 감지, 변경 시 `daily_parent_key` 삭제하여 재제안 |
| R-09 | `app.py` | 저장 성공 후 stale 값(parent_key/parent_desc) 잔존 | MED | 저장 직후 session_state 3종 삭제 |
| R-10 | `quest_validator.py` | parent/child 불변식(count_type=HIGHEST, goal_type=reward_quest, parent/child 동일 $filter·reset_type) 미검증 | HIGH | `validate_daily_set()` 신설, 5개 불변식 매트릭스 체크 |

> Round 1 리포트 `tpl_c_data_qa_report_2026-04-24.md` 의 S4/S7/S8/S9/S11 5 시나리오는 R-01, R-03, R-04, R-07, R-08 과 매핑됨.

## 3축 하네스 판정 전후 비교

| 축 | Round 1 | Round 2 | 증감 |
|---|---|---|---|
| qa-tool | HIGH 8 FAIL | PASS (HIGH 8 전부 차단) | -8 FAIL |
| quest-data-qa | 3/8 FAIL | 8/8 PASS | +3 PASS |
| content-evaluator | 17/40 PASS | 35/40 PASS | +18 PASS |
| pytest | 74 PASS | 137 PASS | +63 |

## 테스트 추가 내역

| 테스트 클래스 | 건수 | 목적 |
|---|---|---|
| `TestReproPriorFailures` | 5 | Round 1 S4/S7/S8/S9/S11 회귀 방지 |
| `TestAllocateChildKeysGuards` | 6 | 음수/0/999999 초과/bool parent_key 거부 |
| `TestSuggestFilterScoped` | 3 | filter-scoped 제안, LAUNCH_0 NONE 재현 |
| `TestStrKeyRejected` | 2 | str `^key` 강제 int 변환/거부 |
| `TestAtomicSave` | 2 | mkstemp/os.replace 실패 시 원본 보존 |

## 주요 발견 사항

- Generator-Evaluator 분리 후 독립 하네스(quest-data-qa, content-evaluator)가 pytest 커버리지 공백을 드러냄.
- `finish_town_dialog` vs `town_finish_dialog` 는 **동일 이름이 아닌 서로 다른 entity (Goal vs Condition)** 로, 두 키를 동시에 유지해야 함 (app.py CONDITIONS 596건, GOAL_TYPES 6건).
- `reset_type=REPEAT` 를 DAILY 퀘스트 기본값으로 문서화했던 기존 draft 는 실데이터와 모순(실제는 `DAILY`). §3.5 정정.
- session_state 기반 UI 상태는 filter/탭 전환 경계에서 반드시 명시적 무효화 필요.
- Write-path validation 을 UI 계층이 아닌 writer 계층에 두어야 CLI/배치 사용 시에도 동일 보호 확보.

## 환경 이슈 및 해결

| 이슈 | 원인 | 해결 |
|---|---|---|
| xlsx 저장 중 중단 시 파일 0바이트 | openpyxl `wb.save()` 단일 write 로 중간 실패 취약 | `tempfile.mkstemp` 로 임시 파일 작성 후 `os.replace` 로 원자 치환 |
| LAUNCH_0 NONE 영역에 HELSINKI 키 제안 | `max(all_keys)+step` 로직으로 filter 경계 무시 | `get_existing_keys_by_filter()` 신설, filter-scoped max 계산 |
| pytest 74 PASS 에도 실제 결함 | write-path 검증 부재, boundary test 부족 | validator 모듈 신설 + 파라미터화 regression suite 18건 추가 |
| GoalType 오표기 | 실데이터 0건 매핑을 UI 노출 | xlsx 전수 스캔으로 실 SUM 기준 교체 |

## 파일 위치

| 파일 | 종류 | 비고 |
|---|---|---|
| `quest_tool/quest_validator.py` | 신규 | write-path 검증 모듈 |
| `quest_tool/quest_writer.py` | 변경 | validate 기본값, atomic save, guards |
| `quest_tool/app.py` | 변경 | GOAL_TYPES, daily_children, filter 변경 감지 |
| `quest_tool/tests/test_quest_writer.py` | 변경 | 92건 (+18) |
| `quest_tool/tests/test_quest_validator.py` | 신규 | 45건 |
| `docs/quest_event_template_designer_draft.md` | 변경 | §3.5 reset_type 정정 |
| `C:\Users\Devsisters\.claude\agents\quest-data-qa.md` | 변경 | GoalType↔CountType 매핑 4행 추가 |
| `docs/tpl_c_data_qa_report_2026-04-24.md` | 참조 | Round 1 실패 모드 원본 |
| `docs/quest_tool_round2_history.md` | 본 문서 | Round 2 히스토리 |
| `docs/quest_tool_round2_spec.md` | 신규 | Round 2 스펙 |

## Round 1 리포트 상호참조

| Round 1 시나리오 | 증상 | Round 2 해결 ID |
|---|---|---|
| S4 | 잘못된 GoalType/CountType 조합 저장 | R-01, R-10 |
| S7 | str `^key` 가 int 와 혼재 | R-05 |
| S8 | filter 변경 후 stale parent_key 재사용 | R-08, R-09 |
| S9 | LAUNCH_0 NONE 제안값이 HELSINKI 대역 | R-04 |
| S11 | daily_children 이중 초기화로 잔여 child 병합 | R-07 |

## 미구현 / 차기 과제

| 항목 | 상태 | 비고 |
|---|---|---|
| content-evaluator 35 -> 40 잔여 5건 | 보류 | 기획 템플릿 서술 보강 (코드 외 영역) |
| CLI 진입점 `quest_tool daily-set-append` | 미착수 | writer 계층은 준비 완료 |
| GoalType 실데이터 자동 스냅샷 정합성 검사 | 미착수 | GOAL_TYPES 하드코딩 dirft 감지용 |
| xlsx 백업 정책 | 미착수 | atomic save 는 손상 방지, 이력 백업은 별도 |

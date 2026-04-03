# UI String 브랜치 전파 도구 — 개발 히스토리

## 개요

| 항목 | 내용 |
|------|------|
| 문서 번호 | his001 |
| 프로젝트 | Cookie Run: Oven Smash (COS) |
| 도구명 | UI String 브랜치 전파 도구 |
| 작성일 | 2026-04-03 |

---

## 개발 배경

| 구분 | 내용 |
|------|------|
| 기존 방식 | 기획자가 `ui_strings.xlsx` 수정 후 각 브랜치에 수동 cherry-pick 또는 직접 복붙 |
| 문제 | 브랜치 수 증가(main + release_helsinki2/3/vng)로 반복 작업 부담 및 누락 위험 |
| 목적 | 브랜치 전파 + datasheet.exe 실행 + 커밋/푸시를 버튼 하나로 자동화 |
| 결정 | Python + Streamlit 기반 GUI 도구 개발, 비개발직군도 단독 사용 가능하도록 설계 |

---

## 주요 개발 단계

| 단계 | 날짜 | 내용 |
|------|------|------|
| v0.1 — 초기 설계 | 2026-04-03 | worktree 방식으로 브랜치별 병렬 처리 시도 |
| v0.2 — worktree 폐기 | 2026-04-03 | checkout 방식 전환, Propagator 클래스 구현 |
| v0.3 — sibling 최신화 | 2026-04-03 | cos-common/cos-client 자동 checkout+pull 추가 |
| v0.4 — diff 기준 수정 | 2026-04-03 | HEAD 기준 → main 브랜치 고정 비교로 변경 |
| v0.5 — 오류 표시 개선 | 2026-04-03 | panic 핵심 메시지 강조, 스택트레이스 접기 |
| v1.0 — 안정화 | 2026-04-03 | 잠금 파일, 롤백 로그, 일괄 롤백 기능 추가 |

---

## 주요 발견 사항

### worktree 방식 폐기

- **시도**: 브랜치별 병렬 처리를 위해 `git worktree add` 방식으로 각 브랜치를 별도 디렉토리에 체크아웃
- **문제**: `datasheet.exe`가 worktree 환경에서 `translations/` 처리 실패 (panic 에러)
- **원인**: `datasheet.exe`가 내부적으로 저장소 루트 기준의 절대 경로를 사용하며, worktree 환경의 경로 구조를 인식하지 못함
- **결정**: worktree 방식 폐기 → 현재 저장소에서 순차 `git checkout` 방식으로 전환

### diff 비교 기준 수정

- **기존**: `HEAD` (현재 체크아웃된 브랜치의 최신 커밋) 기준 비교
- **문제**: 사용자가 `release_helsinki2` 브랜치에 체크아웃한 상태에서 실행 시, `release_helsinki2`의 `ui_strings`와 비교하여 main과의 실제 차이를 반영하지 못함
- **결정**: 항상 `git show main:excel/ui_strings.xlsx`로 main 브랜치 고정 비교
- **효과**: 현재 체크아웃 브랜치에 무관하게 일관된 diff 제공

### sibling 저장소 최신화 필요성 발견

- **문제**: `datasheet.exe` 실행 시 `cos-common`, `cos-client`의 최신 코드를 참조하는데, sibling 저장소가 다른 브랜치에 있거나 pull이 안 된 상태면 변환 실패
- **결정**: 각 브랜치 전파 시작 전 sibling 저장소에 동일 브랜치명으로 `checkout + pull` 수행

### panic 에러 표시 개선

- **문제**: `datasheet.exe` 실패 시 Go의 panic 스택트레이스 전체가 노출되어 기획자가 원인 파악 어려움
- **결정**: `panic:` 으로 시작하는 첫 줄만 강조 표시, 전체 스택트레이스는 "스택 트레이스 보기" expander로 접기

---

## 환경 이슈 및 해결

| 이슈 | 증상 | 원인 | 해결 |
|------|------|------|------|
| datasheet.exe + worktree | `translations` 처리 중 panic | worktree 경로 미인식 | checkout 방식으로 전환 |
| xlsx 읽기 실패 | `openpyxl` 오류 | Excel에서 파일 열린 채 실행 | 사용 가이드에 주의사항 명시 |
| 잠금 파일 잔여 | 전파 시작 불가 | 이전 실행 비정상 종료 | 수동 삭제 가이드 제공, GUI에서 실행 완료 후 잔여 잠금 자동 정리 |
| sibling 브랜치 없음 | checkout 실패 | sibling 저장소에 해당 브랜치 미존재 | 사전 검증(`validate()`)에서 원격 브랜치 존재 여부 확인 후 오류 반환 |
| Streamlit 비동기 | UI 블로킹 | 메인 스레드에서 동기 실행 시 화면 갱신 불가 | `threading.Thread` + `queue.Queue` 기반 `PropagatorThread` 래퍼 도입 |

---

## 파일 위치

| 파일 | 경로 |
|------|------|
| 핵심 로직 | `D:\claude_make\ui_string_propagate\string_propagate.py` |
| GUI | `D:\claude_make\ui_string_propagate\app_propagate.py` |
| 설정 | `D:\claude_make\ui_string_propagate\propagate_branches.yaml` |
| 실행 스크립트 | `D:\claude_make\ui_string_propagate\run_propagate.bat` |
| 설치 스크립트 | `D:\claude_make\ui_string_propagate\install.bat` |
| 의존성 목록 | `D:\claude_make\ui_string_propagate\requirements.txt` |
| 사용 가이드 | `D:\claude_make\ui_string_propagate\사용가이드.txt` |
| 롤백 로그 (자동 생성) | `D:\claude_make\ui_string_propagate\last_propagation.json` |
| 잠금 파일 (자동 생성) | `D:\claude_make\ui_string_propagate\.ui_string_propagate.lock` |

---

## 미구현 항목

| 항목 | 내용 | 비고 |
|------|------|------|
| 병렬 전파 | 브랜치별 동시 처리 | datasheet.exe 제약으로 현재 순차 처리 |
| 충돌 자동 해결 | pull 시 merge conflict 자동 처리 | 현재 충돌 발생 시 해당 브랜치 실패 처리 |
| Slack 알림 | 전파 완료/실패 시 채널 알림 | |
| 전파 이력 보관 | `last_propagation.json`은 1건만 유지 | 히스토리 누적 기능 미제공 |

# UI String 브랜치 전파 도구 — 기능 명세

## 개요

| 항목 | 내용 |
|------|------|
| 문서 번호 | spec001 |
| 프로젝트 | Cookie Run: Oven Smash (COS) |
| 도구명 | UI String 브랜치 전파 도구 |
| 최초 작성일 | 2026-04-03 |
| 최종 수정일 | 2026-04-03 |
| 저장 위치 | `D:\claude_make\ui_string_propagate\` |

## 목적

- `cos-data` 저장소의 `excel/ui_strings.xlsx` 수정 후, 복수의 git 브랜치에 수동 cherry-pick 없이 자동 전파
- `datasheet.exe` 실행(xlsx → protobuf 변환) 및 커밋/푸시 자동화
- 비개발직군(기획자) 대상 GUI 제공

## 사용 대상

- COS 기획팀 (ui_strings.xlsx 담당자)
- 다중 브랜치 동시 관리가 필요한 상황 (릴리즈 브랜치 병렬 운영 시)

## 제약 사항

- `main` 브랜치는 항상 필수 포함, 가장 먼저 처리됨
- 동시에 한 명만 실행 가능 (잠금 파일 기반)
- worktree 방식 미사용 — `datasheet.exe`가 worktree 환경에서 `translations` 처리 실패
- 브랜치 전환은 현재 `cos-data` 저장소에서 순차 `git checkout` 방식으로 동작
- 전파 중 `ui_strings.xlsx`를 Excel에서 열어 두면 읽기 오류 발생
- 실행 환경: Windows (Python 3.x, 로컬 git)

---

## 파일 구성

| 파일 | 역할 |
|------|------|
| `string_propagate.py` | 핵심 로직 (전파, 롤백, diff, 잠금) |
| `app_propagate.py` | Streamlit GUI |
| `propagate_branches.yaml` | 브랜치 목록 및 경로 설정 |
| `run_propagate.bat` | Streamlit 앱 실행 스크립트 |
| `install.bat` | 의존성 패키지 설치 스크립트 |
| `requirements.txt` | Python 패키지 목록 |
| `사용가이드.txt` | 비개발직군 대상 사용 설명서 |
| `docs/spec001.md` | 기능 명세 (현재 문서) |
| `docs/his001.md` | 개발 히스토리 |
| `last_propagation.json` | 마지막 전파의 브랜치별 커밋 해시 (자동 생성) |
| `.ui_string_propagate.lock` | 중복 실행 방지 잠금 파일 (자동 생성) |

---

## 설정값 (propagate_branches.yaml)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `branches` | `[release_helsinki2, release_helsinki3, release_helsinki_vng, main]` | 전파 대상 브랜치 목록 |
| `repo_root` | `D:\COS_Project\cos-data` | cos-data 저장소 루트 |
| `datasheet` | `D:\COS_Project\cos-data\datasheet.exe` | datasheet 실행 파일 경로 |
| `sibling_repos` | `[D:\COS_Project\cos-common, D:\COS_Project\cos-client]` | datasheet 실행 전 최신화할 연동 저장소 목록 |
| `author` | `""` | 작업자 이름 (커밋 메시지 자동 포함, GUI에서 저장 가능) |
| `dry_run` | `false` | `true` 시 커밋/푸시 없이 결과만 확인 |

---

## 기능 명세

### 실행 버튼 구분

| 버튼 | 동작 |
|------|------|
| 🔽 선택 브랜치 풀 받기 | sibling repos + cos-data를 선택 브랜치로 checkout+pull만 수행. xlsx 복사/datasheet/커밋/푸시 없음 |
| 🚀 string 파일 전파 | 풀 받기 포함 전체 전파 흐름 실행 (xlsx 복사 → datasheet → 커밋 → 푸시) |
| 🧪 string 파일 전파 [DRY-RUN] | dry_run 활성화 시 표시. 커밋/푸시 없이 전파 흐름만 확인 |

### 다중 브랜치 전파

- 브랜치 선택: GUI 체크박스, `main` 강제 포함 (비활성화)
- 처리 순서: `main` 우선, 이후 선택 순서대로 순차 처리
- 각 브랜치별 처리 단계는 [전파 흐름] 참조

### 변경 사항 미리보기

- 비교 기준: 항상 `main` 브랜치의 `excel/ui_strings.xlsx` (`git show main:excel/ui_strings.xlsx`)
- 현재 체크아웃된 브랜치와 무관하게 동일한 기준 유지
- 표시 항목: 추가(➕) / 변경(✏️) / 삭제(➖) 키-값 목록
- GUI에서 수동 새로고침 버튼 제공

### sibling 저장소 자동 최신화

- 대상: `sibling_repos`에 등록된 저장소 (`cos-common`, `cos-client`)
- 시점: 각 브랜치의 처리 시작 직전 (풀 받기 모드 포함)
- 동작: 동일 브랜치명으로 `git checkout` → `git pull origin <branch>`
- 이유: `datasheet.exe`가 `cos-common`, `cos-client`의 최신 코드를 참조해야 정상 변환
- 브랜치 미존재 시: 사전 검증(`validate()`)에서 오류 반환하여 실행 차단

### datasheet.exe 자동 실행

- `cos-data` 루트에서 실행
- 성공 시: `protobuf/*.pb` 파일 갱신
- 실패 시: 해당 브랜치 처리 중단, 이후 브랜치 계속 진행
- 풀 받기 모드에서는 실행 안 함

### 커밋/푸시 자동화

- 커밋 메시지 포맷: `[작업자][브랜치1,브랜치2,...] ui_strings 업데이트[#CL]`
- `git add -A` → `git commit` → `git push origin <branch>`
- 변경 파일 없으면 해당 브랜치 스킵 (커밋 생략)

### Dry-run 모드

- GUI 체크박스 또는 yaml `dry_run: true`로 활성화
- `datasheet.exe` 실행 건너뜀
- 커밋/푸시 없이 전파 흐름 검증

### 설정 저장

- GUI 설정 섹션에서 경로, 작업자 이름, sibling_repos, dry_run 편집
- 💾 설정 저장 버튼으로 `propagate_branches.yaml`에 영구 저장
- 앱 재시작 시 저장된 설정 자동 로드 (작업자 이름 포함)

### 잠금 파일

- 경로: `.ui_string_propagate.lock`
- 내용: `PID=<pid> TIME=<datetime>`
- 전파 시작 시 생성, 종료 시 삭제 (정상/비정상 종료 모두)
- 잠금 파일 잔류 시: GUI 상단 경고 표시 + 🗑️ 잠금 파일 삭제 버튼으로 수동 해제 가능

### 일괄 롤백

- 대상: `last_propagation.json`에 기록된 마지막 전파
- 방법: 각 브랜치에 `git checkout` → `git pull` → `git revert --no-edit <commit_hash>` → `git push`
- 완료 후 원래 브랜치로 복원
- GUI에서 2단계 확인 다이얼로그 후 실행 (확인 → 취소 선택)
- 풀 받기 모드로 실행한 경우 롤백 로그 저장 안 함

### 에러 표시

- `panic:` 포함 에러: 첫 번째 `panic:` 줄만 강조 표시, 전체 스택트레이스는 "스택 트레이스 보기"(접힘)로 제공
- 일반 에러: 첫 줄 요약 강조 표시, 전체 내용은 "상세 메시지 보기"(펼침)로 제공

---

## 전파 흐름

```
[풀 받기 모드 — 각 브랜치]

1. sibling_repos 순서대로:
   - git checkout <branch>
   - git pull origin <branch>

2. cos-data:
   - git checkout <branch>
   - git pull origin <branch>
   → 완료 (이하 생략)

[전파 모드 — 각 브랜치]

1. sibling_repos 순서대로:
   - git checkout <branch>
   - git pull origin <branch>

2. cos-data:
   - git checkout <branch>
   - git pull origin <branch>

3. xlsx 복사:
   - <xlsx_path> → cos-data/excel/ui_strings.xlsx

4. datasheet.exe 실행:
   - cwd: cos-data 루트
   - 출력: protobuf/*.pb 갱신

5. 변경 파일 확인:
   - git diff --name-only
   - git ls-files --others --exclude-standard
   - 변경 없으면 스킵

6. 커밋 및 푸시:
   - git add -A
   - git commit -m <commit_msg>
   - git push origin <branch>
   - 커밋 해시 → last_propagation.json 기록

7. 원래 브랜치 복원 (모든 브랜치 처리 완료 후):
   - cos-data: git checkout <원래 브랜치>
```

---

## 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `streamlit` | >=1.32.0 | GUI 프레임워크 |
| `openpyxl` | >=3.1.2 | xlsx 파싱 (diff 계산) |
| `pyyaml` | >=6.0 | 설정 파일 로드/저장 |
| `pandas` | >=2.0.0 | diff 결과 표 표시 |

| 외부 의존 | 설명 |
|-----------|------|
| `git` | PATH에 등록된 git CLI |
| `datasheet.exe` | cos-data 루트의 xlsx→protobuf 변환 도구 |
| `cos-common`, `cos-client` | sibling 저장소 (datasheet 참조 대상) |

---

## 클래스 및 모듈 구조

```
string_propagate.py
├── load_config() / save_config()           설정 파일 I/O
├── run_git()                               git 서브프로세스 래퍼
├── find_header_row() / load_strings_*      xlsx 파싱
├── compute_diff()                          변경 사항 계산 (main 기준)
├── StringDiff                              added / changed / removed 컨테이너
├── BranchResult                            브랜치별 실행 결과
├── acquire_lock() / release_lock()         잠금 파일 관리
├── Propagator                              전파 실행기 (pull_only 모드 포함)
├── PropagatorThread                        Streamlit 비동기 래퍼
├── Rollbacker                              롤백 실행기 (checkout 방식)
├── RollbackerThread                        롤백 비동기 래퍼
└── save_rollback_log() / load_rollback_log()  롤백 로그 I/O

app_propagate.py
├── 설정 섹션              repo_root, datasheet, sibling_repos, author, dry_run, 💾 저장 버튼, 잠금 감지
├── 브랜치 선택 섹션       체크박스, YAML 인라인 편집
├── 변경 사항 섹션         diff 표, 새로고침
├── 커밋 메시지 섹션       자동 생성 + 직접 편집
├── 실행 버튼 섹션         🔽 풀 받기 / 🚀 전파 (2버튼 분리)
├── 진행 상황 섹션         큐 기반 실시간 로그, 브랜치별 결과, 에러 표시
└── 롤백 섹션              last_propagation.json 표시, 2단계 확인, 진행 로그
```

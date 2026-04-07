# spec001 — autopull UX 개선

| 항목 | 내용 |
|------|------|
| 작성일 | 2026-04-07 |
| 대상 파일 | `app_autopull.py`, `install.bat`, `사용가이드.txt` |
| 상태 | 완료 |

---

## 배경

autopull 프로그램(Streamlit 기반 Git 자동 풀 도구)의 UX 개선 및 버그 수정 2건 요청.

---

## 변경 1 — 상태 확인 버튼 로딩 피드백

### 문제
- 상태 확인 버튼 클릭 후 fetch 완료까지 무반응
- 버튼이 활성 상태여서 중복 클릭 가능

### 해결
- `pending_status_check` 플래그 도입 (`pending_pull` 패턴과 동일)
- 클릭 즉시 `pending=True` → rerun → UI 렌더 → 버튼 비활성화
- 버튼이 **"로딩중..."** 표시되는 시점에 thread 시작 (fetch 실행)
- 브랜치 목록 위에 `st.info()` 로딩 메시지 추가
- `st.rerun()`을 스크립트 맨 아래로 이동 (UI 렌더 전 조기 rerun 방지)

### 실행 흐름
```
클릭 → pending=True → rerun
  → thread 시작(rerun 없음) → UI 전체 렌더 → 버튼 "로딩중..." 표시
  → 맨 아래 폴링 rerun → fetch 진행
  → 완료 → checker_done → rerun → 상태 배지 갱신
```

### 수정 내용 (`app_autopull.py`)
| 위치 | 변경 내용 |
|------|-----------|
| `_init()` | `pending_status_check: False` 추가 |
| `checker_running` 계산 | `pending_status_check` 플래그 포함 |
| pending 핸들러 | thread 시작 후 rerun 없이 렌더 계속 |
| checker 완료 처리 | 상단에서 state 갱신만, rerun은 하단으로 이동 |
| 스크립트 하단 | status checker 폴링 rerun 블록 추가 |

---

## 변경 2 — install.bat Python 환경 생성 실패 안내

### 문제
- Step 2 실패 시 `[ERROR]` 메시지만 출력, 해결 방법 없음
- 비개발자 사용자가 대처 불가

### 해결
- Python 환경 생성 실패 시 python.org 다운로드 링크 안내

```bat
echo  Please install Python 3.12 manually and try again:
echo    https://www.python.org/downloads/
```

---

## 버그 수정 — install.bat 인코딩/줄바꿈 문제

### 문제
1. **LF 줄바꿈 혼입** — Write/Edit 도구로 수정 시 LF가 섞임
   cmd.exe가 줄을 파싱 못해 단어 조각(`xist`, `UV_EXE`, `_ok`, `tep2` 등)이 명령어로 실행됨

2. **`>/dev/null` 혼입** — bash 환경에서 `>nul`이 `>/dev/null`로 치환됨
   → 실행 시 "지정된 경로를 찾을 수 없습니다" 오류
   → `nulnif` 잔여 파일 생성

3. **한국어 인코딩 충돌** — bat 파일 내 한국어(UTF-8)가 cmd.exe CP949와 충돌해 글자 깨짐

### 해결
- bat 파일 전체를 PowerShell로 **ASCII + CRLF** 형식으로 재작성
- `>/dev/null` → `>nul` 전체 치환
- 한국어 echo 메시지 → 영어로 교체
- `nulnif` 잔여 파일 삭제
- bat 파일 작성 규칙 memory에 등록 (`feedback_bat_file_rules.md`)

---

## 문서 업데이트

**`사용가이드.txt`** — 트러블슈팅 섹션에 항목 추가
```
Q. install.bat 실행 시 Python 환경 생성 실패
→ https://www.python.org/downloads/ 에서 Python 3.12 설치 후 재시도
```

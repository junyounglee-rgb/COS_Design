# branch_strategy

cos-data git 운영 개선 분석 문서 모음.

## 문서 맵

| 파일 | 역할 | 우선순위 |
|------|------|---------|
| `기획 데이터 잘쓰기.md` | 현황 진단 + Phase 1~3 로드맵 | **1** |
| `svn_pattern_analysis.md` | 실측 수치 원본 | 2 |
| `diagnosis_and_recommendations.md` | CI 구조 기술 상세 | 3 |
| `presentation_git_as_git.md` | 발표용 6슬라이드 | 참조 |
| `planning_team_guide.md` | 기획팀 실용 가이드 | 참조 |
| `기획데이터개선.md.md` | CSV+VBA 방식 | 비교만 |

## 핵심 컨텍스트

**문제:** `.xlsx`/`.pb` 바이너리 → git merge 불가 → 브랜치 분리 + 수동 전파 강제 (git을 SVN처럼 운영)

**실측 수치 (4개월):** CI 오류 ~820건(일 평균 6.7건) / PR 사용률 1.5% / .git 크기 4.6GB

**브랜치:** `main` / `release_helsinki2` / `release_helsinki3` / `release_helsinki_vng`

**로드맵:**
- Step 1: git 로그 규칙 정하기 (커밋 컨벤션 + pre-push hook)
- Step 2: 기획 데이터를 main 브랜치 단일 작업으로 전환 ($filter + CI 자동화 — 개발팀 협의)
- Step 3: git을 git답게 쓰기 (PR·feature branch·히스토리 추적 정착)

## 주의

- `svn_excel/` JSON — 구버전, 사용 금지
- `기획데이터개선.md.md` — 채택 방향 아님
- `datasheet --build` — 현재 미존재, 개발 요청 대상
- Phase 2는 개발팀 협의 필요 (즉시 적용 불가)

## 에이전트

| 파일 | 역할 |
|------|------|
| `agents/diagnosis-roadmap.md` | 현황 진단 + 로드맵 검토 |
| `agents/presentation-onboarding.md` | 발표 콘텐츠 + 팀 교육 |

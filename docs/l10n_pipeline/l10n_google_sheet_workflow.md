# Google Sheet 기반 번역 파이프라인 워크플로우

> 출처: `D:\claude_make\docs\l10n_pipeline\l10n_pipeline_redesign.md`
> 상태: 개선 제안 (현재 미전환 — lokalise 방식 운영 중)

---

## 현재 vs 개선 방식 한눈 비교

| 항목 | 현재 (lokalise) | 개선 (Google Sheet) |
|------|----------------|-------------------|
| 스트링 추출 | PM이 Fork → 버튼 → 수동 분류 | 자동 감지 |
| 번역 플랫폼 | lokalise (계정 한정) | Google Sheet (공유 링크) |
| 번역팀 알림 | PM이 직접 연락 | Slack 자동 알림 |
| 게임 반영 | PM이 Sync 수동 실행 + 10분 대기 | 자동 (CI cron) |
| PM 1회 소요 | 46분 | **0분** |
| 단일 장애점 | ✅ PM 부재 시 전체 중단 | ❌ 없음 |

---

## 개선안 전체 흐름

```
┌──────────────────────────────────────────────────────────┐
│ 기획자                                                    │
│  1. excel에 str_id 참조 입력                               │
│     (ex. name = str_cookie_power)                        │
│  2. Google Sheet에 str_id + ko + tag=new 입력             │
└────────────────────┬─────────────────────────────────────┘
                     │
       ┌─────────────┴──────────────┐
       ▼                            ▼
┌─────────────────┐      ┌─────────────────────────┐
│ CI 자동 (5분)    │      │ 번역팀                   │
│ Google Sheet    │      │ 워크벤치 툴 접속          │
│ 변경 감지        │      │ tag=new/re 항목만 로드    │
│ ko CSV 생성      │      │ en/ja/zh-TW/... 입력     │
│ cos-client 배포  │      │ tag=done 자동 변경        │
│ Unity 즉시 반영  │      │ (배포 관여 없음)          │
└─────────────────┘      └─────────────────────────┘
                     │
       ┌─────────────┴──────────────┐
       ▼                            ▼
┌─────────────────┐      ┌─────────────────────────┐
│ CI 자동 (새벽 4시)│      │ 기획 팀장 (긴급 시)      │
│ 전체 언어 pb 생성 │      │ 배포 툴 → "전체 배포"    │
│ Portal 업로드    │      │ 버튼 클릭                │
│ Slack 완료 알림  │      │ CI 즉시 트리거           │
└─────────────────┘      └─────────────────────────┘
```

---

## 역할별 작업

### 기획자

| 작업 | 방법 |
|------|------|
| 게임 데이터 스트링 | `excel/*.xlsx`에 `str_id` 참조 입력 (한글 직접 입력 X) |
| 신규 스트링 등록 | Google Sheet에 `str_id + ko + tag=new` 한 줄 추가 |
| 수정 스트링 | Google Sheet `ko` 수정 후 `tag=re`로 변경 |
| 확인 | 5분 내 Unity Editor에 자동 반영됨 |

### 번역팀

| 작업 | 방법 |
|------|------|
| 번역 대상 확인 | Google Sheet → `tag=new/re` 필터 |
| 번역 입력 | 워크벤치 툴 접속 → 각 언어 컬럼 입력 |
| 완료 처리 | 저장 시 `tag=done` 자동 변경 |
| 배포 | 관여 없음 (CI가 자동 처리) |

### 기획 팀장

| 작업 | 방법 |
|------|------|
| 정기 배포 | 자동 (매일 새벽 4시 CI) |
| 긴급 배포 | 배포 툴 접속 → "전체 언어 배포" 클릭 |

### PM

| 작업 | 상태 |
|------|------|
| 번역키 추출 | ❌ 없어짐 |
| 파일 분류 | ❌ 없어짐 |
| lokalise 업로드 | ❌ 없어짐 |
| Sync 수동 실행 | ❌ 없어짐 |
| 10분 대기 + 확인 | ❌ 없어짐 |

---

## Google Sheet 구조

```
| str_id           | tag  | ko        | en           | ja               | zh-TW | zh-CN | th | id |
|------------------|------|-----------|--------------|------------------|-------|-------|----|----|
| str_cookie_power | done | 힘쎈쿠키   | Brave Cookie | ブレイブクッキー   | ...   | ...   |    |    |
| str_new_event    | done | 신규이벤트 | New Event    | ...              | ...   | ...   |    |    |
| str_skill_blast  | new  | 블라스트   |              |                  |       |       |    |    |  ← 번역 대기
| str_item_shield  | re   | 보호막(수정)| Shield      | ...              | ...   | ...   |    |    |  ← 재번역 필요
```

**tag 정의**

| tag | 의미 |
|-----|------|
| `new` | 신규 — 번역 필요 |
| `re` | ko 수정됨 — 재번역 필요 |
| `done` | 번역 완료 |
| `hold` | 기획 확정 전 보류 |

---

## CI 파이프라인 구성

### ko CSV 자동 배포 (5분 cron)

```
Google Sheet hash 비교
  ├── 동일 → skip
  └── 다름 → ko_csv 생성 → cos-client 배포 → Unity Editor 즉시 반영
```

### 전체 언어 pb 자동 배포 (매일 새벽 4시)

```
Google Sheet 전체 읽기 (ko + en + ja + zh-TW + zh-CN + th + id)
  → 전체 언어 pb 생성
  → Portal 업로드
  → Slack 배포 완료 알림
```

> GitHub Actions UTC 주의: KST 04:00 = UTC `0 19 * * *`

---

## VNG 외부 법인 번역 (별도 대응)

내부 번역팀과 달리 외부 법인이므로 Google Sheet 직접 접근 불가.

| 옵션 | 방식 | 구현 난이도 |
|------|------|-----------|
| **A — 파일 교환** | COS팀이 xlsx/csv 추출 → VNG 전달 → 반환 → 시트 머지 | 낮음 |
| **B — 전용 시트** | VNG 전용 Google Sheet 별도 운영 → 메인 시트 자동 머지 | 중간 |

> 빈도 낮으면 옵션 A, 빈도 높으면 옵션 B 권장

---

## 없어지는 것 / 남는 것

### 없어지는 것

- lokalise 구독 및 계정 관리
- PM의 번역 추출·분류·업로드·Sync 작업 전체
- `translations/changes/*.xlsx` 수동 관리
- cos-data git의 번역 pb 누적 (repo 경량화)

### 남는 것 (자동화 불가)

- 번역팀의 실제 번역 입력
- 번역 품질 검수

### 히스토리 보관 방식 변경

| 현재 | 개선 |
|------|------|
| git 커밋마다 번역 pb 바이너리 누적 | 배포 시점 스냅샷 S3 저장 |
| git diff 불가 (바이너리) | xlsx 스냅샷 → 바로 열어서 비교 가능 |

---

## 전환 로드맵

```
Week 1       Phase 0 — 사전 준비 (Google Sheet 구조 설계, API 발급)
Week 2~4     Phase 1 — 병행 개발 (feat/l10n-* 브랜치 4개 병행)
Week 5       Phase 2 — 통합 QA (8,546개 항목 검증)
Week 6       Phase 3 — D-day 일괄 cut-over + D+7 안정화
────────────────────────────────────────────
총 기간: 약 5~6주
```

**D-day 순서 (반드시 이 순서로)**

```
1. lokalise Sync Lambda 비활성화
2. 마이그레이션 스크립트 실행 (translations.xlsx + lokalise → Google Sheet)
3. validate_diff.mjs + .gitignore 수정 커밋 (번역 pb 추적 해제)
4. feat/* 브랜치 → main 머지
5. 기획팀 워크플로우 전환 공지
6. 전체 언어 pb cron 첫 실행 확인
D+7: 1주 안정화 확인 후 lokalise 구독 종료
```

---

## 구현 컴포넌트 목록

| # | 컴포넌트 | 난이도 |
|---|---------|--------|
| 1 | 초기 마이그레이션 스크립트 (translations.xlsx + lokalise → Google Sheet) | 낮음 |
| 2 | str_id 참조 검증 CI | 낮음 |
| 3 | ko CSV 자동 배포 파이프라인 (5분 cron) | 중간 |
| 4 | 전체 언어 pb 자동 배포 파이프라인 (새벽 4시 cron) | 중간 |
| 5 | 번역팀 워크벤치 툴 | 중간 |
| 6 | 기획 팀장 긴급 배포 툴 | 낮음 |
| 7 | Slack 알림 | 낮음 |
| 8 | 배포 시점 스냅샷 S3 자동 백업 | 낮음 |

---

## 관련 문서

- 전체 분석: `D:\claude_make\docs\l10n_pipeline\l10n_pipeline_redesign.md`
- 현재 파이프라인: `translation_pipeline.md` (lokalise 방식)
- lokalise Notion: [로컬라이즈 시작하기_협업부서용](https://www.notion.so/1e0de3da8956807088ecd57d5485e063)

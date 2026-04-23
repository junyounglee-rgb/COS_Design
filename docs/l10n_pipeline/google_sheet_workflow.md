# Google Sheet 번역 파이프라인

> 상태: 개선 제안 (현재 미전환)
> 출처: `l10n_pipeline_redesign.md`

---

## 전체 흐름

### 기획자 — 스트링 등록

```
excel/*.xlsx에 str_id 참조 입력
  (예: name = str_cookie_power)
  ↓
Google Sheet에 str_id + ko + tag=new 추가
  ↓
5분 내 Unity Editor에 자동 반영 (ko CSV cron)
```

### 번역팀 — 번역 입력

```
Slack 알림 수신 (tag=new/re 항목 발생)
  ↓
워크벤치 툴 접속
  ↓
tag=new / tag=re 항목만 로드
  ↓
en / ja / zh-TW / zh-CN / th / id 입력
  ↓
저장 → tag=done 자동 변경
  (배포 관여 없음)
```

### CI — 자동 배포

```
[5분 cron]
Google Sheet hash 비교
  ├─ 동일 → skip
  └─ 다름 → ko CSV 생성 → cos-client 배포 → Unity Editor 반영

[매일 새벽 4시 cron]
Google Sheet 전체 읽기 (전 언어)
  ↓
전체 언어 pb 생성
  ↓
Portal 업로드
  ↓
Slack 배포 완료 알림
```

### 기획 팀장 — 긴급 배포 (필요 시)

```
배포 툴 접속
  ↓
"전체 언어 배포" 실행
  ↓
CI 즉시 트리거 → 전체 언어 pb → Portal 업로드
```

---

## 단계별 상세

### 1. Google Sheet 구조

```
| str_id           | tag  | ko        | en           | ja              | zh-TW | zh-CN | th | id |
|------------------|------|-----------|--------------|-----------------|-------|-------|----|----|
| str_cookie_power | done | 힘쎈쿠키   | Brave Cookie | ブレイブクッキー  | ...   | ...   |    |    |
| str_skill_blast  | new  | 블라스트   |              |                 |       |       |    |    |
| str_item_shield  | re   | 보호막(수정)| Shield      | ...             | ...   | ...   |    |    |
```

| tag | 의미 |
|-----|------|
| `new` | 신규 — 번역 필요 |
| `re` | ko 수정됨 — 재번역 필요 |
| `done` | 번역 완료 |
| `hold` | 기획 확정 전 보류 |

### 2. 번역팀 워크벤치 툴

- Google Sheet에서 `tag=new/re` 항목만 필터링해서 표시
- 번역 입력 후 저장 시 Google Sheet 해당 셀 업데이트 + `tag=done` 자동 변경
- 배포 권한 없음 — 번역 입력만 담당

### 3. CI cron 주의사항

| 항목 | 내용 |
|------|------|
| ko CSV 최소 간격 | GitHub Actions 최소 5분 (`*/5 * * * *`) |
| 새벽 4시 cron | KST 04:00 = UTC `0 19 * * *` (전날 19시) |
| 배포 스냅샷 | Portal 업로드 시 `translations_snapshot_vX.X.X_날짜.xlsx` S3 자동 저장 |

### 4. VNG 외부 법인 번역

| 옵션 | 방식 | 권장 상황 |
|------|------|---------|
| A — 파일 교환 | xlsx/csv 추출 → VNG 전달 → 반환 → 시트 머지 | 번역 빈도 낮음 |
| B — 전용 시트 | VNG 전용 Google Sheet 운영 → 메인 시트 자동 머지 | 번역 빈도 높음 |

---

## 없어지는 것

| 항목 | 현재 | 개선 후 |
|------|------|--------|
| 번역키 추출 | PM이 Fork → 버튼 클릭 | 자동 감지 |
| 파일 분류 | PM이 7종 카테고리 수동 분류 | 없어짐 |
| lokalise 업로드 | PM이 파일별 수동 업로드 | 없어짐 |
| Sync 실행 | PM이 수동 클릭 + 10분 대기 | CI 자동 처리 |
| 번역팀 알림 | PM이 직접 연락 | Slack 자동 알림 |
| 번역 pb git 누적 | 커밋마다 바이너리 적재 | 빌드 타임 생성 + S3 스냅샷 |
| lokalise 구독 | 유지 | 종료 |

---

## 전환 일정

```
Week 1     Phase 0 — 사전 준비 (Google Sheet 구조 설계, API 발급)
Week 2~4   Phase 1 — 병행 개발 (feat/l10n-* 브랜치 4개 병행)
Week 5     Phase 2 — 통합 QA (8,546개 항목 검증)
Week 6     Phase 3 — D-day cut-over + D+7 안정화
────────────────────────────────────────
총 기간: 약 5~6주
```

**D-day 순서 (반드시 이 순서로)**

```
1. lokalise Sync Lambda 비활성화
2. 마이그레이션 스크립트 실행 (translations.xlsx + lokalise → Google Sheet)
3. validate_diff.mjs + .gitignore 수정 커밋
4. feat/* 브랜치 → main 머지
5. 기획팀 워크플로우 전환 공지
6. 전체 언어 pb cron 첫 실행 확인
D+7. 안정화 확인 후 lokalise 구독 종료
```

---

## 관련 문서

- 전체 분석: `l10n_pipeline_redesign.md`
- 현재 파이프라인: `translation_pipeline.md`

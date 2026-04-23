# Translations 최신화 파이프라인

> 기준일: 2026-04-16
> 출처: Figma 순서도 («Translations 최신화» 순서도)

---

## 전체 흐름

```
시작
  ↓
translations.xlsx 작업 완료
  ↓
Fork → Repository → '번역키 추출' 클릭 (cos-common 대상)
  ↓
Fork 내 최신화 키도 (pull)
  ↓
번역 데이터 확인 및 검수
  ↓
오탈자 & 누락값 존재?
  ├─ YES → 해당 데이터 직접 수정 → 검수 재실행
  └─ NO ↓
번역키 분류 (New / Updated 항목별)
  ↓
Lokalise 접속
  ↓
Upload 진행
  ↓
Lokalise 업로드 완료
  ↓
'Skipped' 번역키 존재?
  ├─ YES → Skipped 키워드 처리 → 재확인
  └─ NO ↓
설명 변경 사항 존재?
  ├─ YES → 번호 사항 수행
  └─ NO ↓
'로컬 키' 작업 탭 등록
  ↓
기획팀 & PM팀 작업 완료 공지
  ↓
기획팀 공지 완료 → PM 팀원들 시작
  ↓
Lokalise Task 진행
  ↓
'Sync' 진행 (All Keys: main / Specific Keys: 브랜치별)
  ↓
Sync 결과 및 검수
  ↓
전체 번역 작업 완료 (Fork에 자동 push)
```

---

## 단계별 상세

### 1. 번역키 추출 (Fork)

- 경로: `cos-data/translations/translations.xlsx` 수정 후
- Fork → Repository → **번역키 추출 (cos-common)** 클릭
- `exports/` 폴더에 날짜+시간 폴더명으로 NEW / UPDATED 파일 생성

| 파일 종류 | 내용 |
|----------|------|
| `NEW_*.xlsx` | 신규 추가된 번역키 목록 |
| `UPDATED_*.xlsx` | 변경된 번역키 목록 |

### 2. 번역 데이터 검수

- 오탈자, 누락값 확인
- [New] 항목: 신규 작업 시 Task 전달 문서 참조, 키 종류별 분류 (dialog / cookie / quests / ui / item / skill / product 등)
- [Updated] 항목: 업데이트 대상 키 목록 파악 후 Upload 진행

### 3. Lokalise Upload

| 주의사항 | 내용 |
|---------|------|
| ⚠️ **필수 해제** | "Differentiate keys by file" 옵션 반드시 **체크 해제** |
| Tag Keys | 정해진 규칙에 따라 태그 적용 |
| Skipped 키 | 업로드 후 Skipped 항목 있으면 키워드 처리 후 재업로드 |

### 4. Sync 진행

| 대상 | Sync 방식 |
|------|---------|
| main 브랜치 전체 | All Keys (main) |
| 특정 브랜치 | Specific Keys (브랜치 지정) |

- Sync 완료까지 약 10분 소요
- 완료 후 Fork에 자동 push

---

## git 워크플로우 연관 포인트

| 상황 | 내용 |
|------|------|
| exports diff 미커밋 | CI 에러 발생: **번역 diff 미커밋** → 해당 브랜치 서버 접속 차단 |
| exports diff 커밋 필요 | `exports/` 폴더 변경 파일을 번역 작업과 함께 커밋해야 함 |
| Sync 완료 후 | Fork가 자동으로 push — 별도 수동 push 불필요 |

### exports 커밋 예시

```
[ALL] 번역키 추가 — 까망베르 스킬 설명 [Wrike:4421234]
```
> exports/ diff 파일 포함하여 커밋

---

## 관련 문서

- Notion: [Translations 최신화](https://www.notion.so/devsisters/Translations-32bde3da895680508bb7fabc80f6645e)
- Figma 순서도: `https://www.figma.com/design/WXQSnsAcPudnHN4ZWKhjLc/`

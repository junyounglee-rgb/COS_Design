# Redesign v1

> 기준일: 2026-04-18
> 입력: `spec.md`(v1), `iteration-contract-v1.md`, `case_study_2026-04-17_rev_pollution.md`
> 작성: l10n-pipeline-architect (Step 4~7만 수행)
> 원칙 근거: spec.md 해결 원칙 1~6 (P1 단일 쓰기 원천 / P2 비용 역전 / P3 기술적 봉쇄 / P4 파생물 재생성 / P5 경계 분리 / P6 점진 전환)

---

## Step 4 — 후보안

### 공통 전제

- 5건 편법 경로 정의 (iteration-contract 규정):
  - **E1**: Lokalise 웹 한국어 직수정 (사례 03-26 지희, 04-17 재오염)
  - **E2**: 대표키 병합 옵션(Differentiate keys) 체크 실수 (02-20, 04-17 mail_template^19/20)
  - **E3**: `.pb` 직접 편집 커밋 (04-17 23:15/23:37 `번역키 강제동기화`)
  - **E4**: git 커밋 누락 상태로 로컬 datasheet 실행 (03-07 skill_description 잔여물)
  - **E5**: VNG 편집값이 메인에 역류 (04-17 `Indonésia` 악센트)
- 차단 등급 3단계:
  - **차단** = 기술적으로 해당 행위 자체가 거부됨 (권한/CI fail/단방향/스키마)
  - **탐지** = 경고·알림·로그만 남고 사람이 승인·무시 가능 → contract상 합격 불가 카운트
  - **통과** = 아무 변화 없이 현재와 동일하게 사고 재현

---

### 후보 A — Lokalise 권한 강등 + CI 단방향 동기화

- **축**: SaaS 유지·권한 축소형 (원칙 P1/P3 중심)
- **한 줄**: Lokalise는 읽기 전용 번역 입력 UI로만 유지, 한국어 원문은 OAuth 역할로 쓰기 차단, Excel → Lokalise 일방향만 허용.

**구조 (3레이어)**:

```
[원문 레이어]   excel/translations.xlsx (한국어 컬럼만 수정 가능)
                    │
                    │ datasheet CLI (로컬) + CI pre-receive hook
                    ▼
[번역 입력]      Lokalise 프로젝트 (한국어 = 읽기전용, 타언어만 쓰기)
                    │                             ▲
                    │ Lokalise API 단방향 pull     │ 번역팀 웹 UI (en/ja/zh/th/id만)
                    ▼
[배포 레이어]    protobuf/*.pb (CI 빌드에서 생성, git 커밋 제거)
                    ▼
              클라이언트/서버 런타임
```

**권한 설계**:
- Lokalise 역할: `translator(타언어 only)`, `reviewer`, `admin(API 전용)` 3종. 어떤 인간 UI 계정도 한국어 필드 쓰기 권한 없음.
- 한국어 수정은 Lokalise API `update_translation` 호출 시 서버측 미들웨어가 `target_language=ko` 요청을 403 거부. 미들웨어는 Lokalise 앞단 프록시(자체 Lambda).
- Admin 계정 API 토큰은 CI Secret만 보유. 발급은 PM 2인 승인 + 자동 만료.

**원칙 만족 체크 (6개)**:

| 원칙 | O/X | 근거 |
|------|-----|------|
| P1 단일 쓰기 원천 | O | 한국어 쓰기는 `translations.xlsx`에서만 가능. Lokalise는 프록시 차단으로 read-only. |
| P2 비용 역전 | △ | Excel 5단계 중 datasheet/업로드/Sync는 CI가 대체하지만 기획자는 여전히 Excel 열기 필요. 3초 수렴은 불가. |
| P3 기술적 봉쇄 | O | 프록시가 403으로 거부 (탐지 아님, 거부). |
| P4 파생물 재생성 | O | `.pb`를 `.gitignore`에 추가, CI가 매 빌드 재생성. rev 누적은 datasheet rev-dedup(04-18 a1cfe43c8) 기능 내재화. |
| P5 경계 분리 | △ | 단일 Lokalise 프로젝트 유지 → VNG는 별도 프로젝트로 분리 필수. 후보 A 자체엔 분리 규정 없음 → 옵션으로 추가. |
| P6 점진 전환 | O | Lokalise 구독·UI·번역팀 워크플로 모두 유지 → 전환비용 최저. |

**편법 경로 × 차단 여부**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 Lokalise 웹 한국어 직수정 | 프록시가 `target_language=ko` PUT 거부, 웹 UI도 역할상 필드 비활성 | **차단** |
| E2 대표키 병합 옵션 실수 | Lokalise 업로드는 CI만 수행. CI 스크립트가 `differentiate_by_file=true` 하드코딩. 수동 업로드 창 자체 제거(관리자만 가능). | **차단** |
| E3 `.pb` 직접 편집 커밋 | `.gitignore`에 `protobuf/*.pb` 추가 + pre-receive hook이 pb diff 존재 시 push reject | **차단** |
| E4 git 커밋 누락 + 로컬 datasheet | `.pb`가 git에서 빠졌으므로 로컬 실행은 빌드 영향 없음. CI만이 pb 생성하므로 "로컬 바이너리 잔여물" 개념 소멸. | **차단** |
| E5 VNG 역류 | 단일 Lokalise 프로젝트 구조라 VNG가 메인 필드 쓰기 가능 → 기본 구조에선 **통과**. P5 옵션을 Phase 2에 추가해야 **차단**. | **통과**(기본) → **차단**(옵션) |

---

### 후보 B — Lokalise 폐기 + 자체 번역 워크벤치 (Excel 단일 소스)

- **축**: SaaS 교체·자체 개발형 (원칙 P1/P2/P3 전면 재설계)
- **한 줄**: Lokalise 구독 종료, Excel 단일 소스 + 인하우스 번역 웹 툴(read KO → write 타언어).

**구조**:

```
[원문]     excel/translations.xlsx (ko 컬럼 = 진실의 원천)
              │
              ▼ CI push → 워크벤치 백엔드 캐시
[입력]     자체 워크벤치 (React + FastAPI), tag=new/re 필터, ko read-only
              │
              ▼ write back: excel/translations_{lang}.xlsx (en/ja/zh/th/id만)
[배포]     CI가 모든 xlsx → protobuf/*.pb 재생성 (.pb 커밋 제외)
```

**원칙 만족 체크**:

| 원칙 | O/X | 근거 |
|------|-----|------|
| P1 | O | ko 쓰기는 Excel뿐, 워크벤치는 ko read-only 엄격. |
| P2 | O | 발견자가 워크벤치의 "ko 오타 신고" 버튼 → 기획 담당자에 자동 PR 생성(3초 수렴). |
| P3 | O | 워크벤치 스키마에 ko 필드 write endpoint 자체 없음. |
| P4 | O | `.pb` CI 재생성, 워크벤치 캐시는 CI가 xlsx에서 매번 동기화. |
| P5 | O | VNG는 별도 워크벤치 테넌트(RBAC)로 완전 격리. |
| P6 | X | 4~6주 개발 한도에 자체 워크벤치 + 번역팀 재교육 + 구독 해지 동시 수행 부담 큼. **고정 제약 6종 중 "번역팀 Lokalise UI 의존"과 "개발 4~6주" 2건 위반**. |

**편법 경로 × 차단 여부**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise 자체 폐기 → 경로 소멸 | **차단** |
| E2 | 대표키 병합 개념 자체 없음 (str_id 1:1) | **차단** |
| E3 | `.pb` git 제외 + pre-receive | **차단** |
| E4 | `.pb` git 제외, CI만 빌드 | **차단** |
| E5 | VNG 테넌트 RBAC 분리 + 메인 ko 필드 쓰기 불가 | **차단** |

---

### 후보 C — Git 저장소 직접 편집형 (번역팀 PR 방식)

- **축**: Git 저장소 직접 편집형 (원칙 P1 극단 해석)
- **한 줄**: 번역팀이 `excel/translations_{lang}.xlsx`를 Fork/GitHub Desktop으로 직접 수정, PR 올려 머지. Lokalise 제거.

**구조**:

```
[원문]     excel/translations.xlsx
              │ PR (ko 수정 = 기획자만)
              ▼
[입력]     excel/translations_{lang}.xlsx (번역팀이 PR)
              │ PR review + CI validator
              ▼
[배포]     CI → protobuf/*.pb (.pb 커밋 제외)
```

**원칙 만족 체크**:

| 원칙 | O/X | 근거 |
|------|-----|------|
| P1 | O | ko 쓰기는 translations.xlsx PR만. |
| P2 | △ | 기획자 소환 비용은 해결되나, 번역팀의 PR 오버헤드가 3초에서 수십 분으로 증가 (번역팀 비용 구조 역행). |
| P3 | O | CODEOWNERS로 `translations.xlsx` ko 수정을 기획팀만 승인 가능. |
| P4 | O | `.pb` CI 재생성. |
| P5 | O | VNG 별도 브랜치/fork로 격리. |
| P6 | X | **번역팀 Lokalise UI 의존(고정 제약)** 직접 위반. 번역팀에 Git 숙련도 요구 = 재교육 비용 폭증. |

**편법 경로 × 차단 여부**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise 제거 → 경로 소멸 | **차단** |
| E2 | 병합 옵션 개념 없음 | **차단** |
| E3 | `.pb` `.gitignore` + pre-receive | **차단** |
| E4 | CI만 빌드 | **차단** |
| E5 | VNG fork/브랜치 CODEOWNERS로 메인 쓰기 차단 | **차단** |

---

### 후보 D — Lokalise 단방향 래퍼형 (Excel 단일 소스 + Lokalise는 입력 UI만)

- **축**: Lokalise 단방향 래퍼형 (원칙 P1 + P3 + P4 조합)
- **한 줄**: Excel이 원문, Lokalise는 한국어를 **자동 주기적 덮어쓰기** 대상 필드로 강등. 웹 직수정해도 10분 내 Excel 값으로 복귀.

**구조**:

```
[원문]     excel/translations.xlsx (ko) ─── SOT
              │ CI: xlsx → lokalise 한국어 PUT (10분 cron)
              ▼
[입력]     Lokalise 프로젝트
            - ko: CI가 주기적 덮어쓰기 (웹 수정해도 10분 뒤 복귀)
            - 타언어: 번역팀 자유 편집
              │ CI: lokalise → translations_{lang}.xlsx pull
              ▼
[배포]     excel/translations_{lang}.xlsx + CI pb 생성
```

**원칙 만족 체크**:

| 원칙 | O/X | 근거 |
|------|-----|------|
| P1 | O | Excel ko가 유일한 쓰기 원천. Lokalise ko는 매 10분 덮어쓰기. |
| P2 | △ | 기획자 소환 비용 여전. 단 오타 발견 시 "엑셀만 고치면 10분 내 반영"으로 공식 경로 비용 절감. |
| P3 | △ | "쓰기 거부"가 아니라 "쓰기 후 복귀" → P3의 "Block, Don't Warn"과 어긋남 (덮어쓰기는 사실상 탐지+자동복구). 다만 사람 개입 0이므로 실질 차단과 동등. |
| P4 | O | Lokalise ko는 재생성 파생물로 정의. 손수정은 자동 덮어쓰기로 폐기. |
| P5 | △ | VNG 프로젝트 분리 옵션 필요. |
| P6 | O | Lokalise UI 그대로, 번역팀 재교육 0, 개발 공수는 CI 동기화 Lambda 1개 + rev-dedup datasheet 패치뿐. |

**편법 경로 × 차단 여부**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 Lokalise 웹 ko 직수정 | 10분 cron이 Excel 값으로 강제 복귀. rev 누적 방지: CI는 수정 전 기존 rev를 `delete_rev` API로 제거 후 삽입. | **차단**(자동 복구) |
| E2 | CI 업로드 스크립트가 `differentiate_by_file=true` 고정. 수동 업로드 경로는 Lokalise 프로젝트에서 admin-only로 제한. | **차단** |
| E3 | `.pb` `.gitignore` + pre-receive | **차단** |
| E4 | `.pb` CI-only | **차단** |
| E5 | VNG 프로젝트 분리(Phase 2에 포함) | **차단**(분리 후) |

---

### 후보 E — Google Sheet 단일 소스형 (기존 제안)

- **축**: SaaS 교체·Sheet 단일 (원칙 P1/P2 극대화)
- **한 줄**: Lokalise 폐기, translations.xlsx 폐기. Google Sheet가 ko + 타언어 전부 보유, CI가 모든 pb 재생성.

**구조**: `google_sheet_workflow.md` 참조 (str_id + tag + ko + en/ja/zh/th/id, 5분 cron).

**원칙 만족 체크**:

| 원칙 | O/X | 근거 |
|------|-----|------|
| P1 | O | Sheet 단일. |
| P2 | O | 발견자가 Sheet에 직접 5분 내 수정 가능 (3초~5분 수렴). |
| P3 | O | Sheet 편집 권한 분리 + onEdit 트리거로 ko 이외 변경 시 복원. |
| P4 | O | xlsx/pb 모두 CI 재생성. |
| P5 | O | VNG 전용 Sheet 또는 필터 컬럼 분리. |
| P6 | X | **Excel 친숙도 고정 제약**과 상충 (기획팀이 Excel → Sheet 전환). **개발 4~6주** 제약도 Sheet-xlsx 양방향 동기화 층이 두꺼워 빠듯함. 번역팀도 Lokalise → 워크벤치 전환 필요. |

**편법 경로 × 차단 여부**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise 제거 → 경로 소멸 | **차단** |
| E2 | 병합 옵션 개념 없음 (str_id 1:1) | **차단** |
| E3 | `.pb` `.gitignore` + pre-receive | **차단** |
| E4 | CI만 빌드 | **차단** |
| E5 | VNG 전용 Sheet/필터 | **차단** |

---

### 후보 F — 하이브리드 DB형 (Postgres/DynamoDB 원문 DB + Excel·Lokalise 뷰)

- **축**: 원문을 DB에 저장, Excel과 Lokalise는 DB에서 파생되는 **뷰**
- **한 줄**: 한국어 원문은 중앙 DB에 저장, Excel 파일·Lokalise 프로젝트·pb는 모두 DB에서 재생성되는 파생물.

**구조**:

```
[원문]     Central DB (translation_strings 테이블)
            - PK: str_id
            - ko (NOT NULL, unique) = SOT
            - metadata: tag(new/re/done/hold), owner, rev history
            │
            ├─ view 1: excel/translations_ko.xlsx (read-only export, 기획 참조용)
            ├─ view 2: Lokalise 프로젝트 (ko = mirror, 타언어 write)
            └─ view 3: protobuf/*.pb (CI 재생성)

[입력]     기획자 = DB 수정 UI (경량 관리자 페이지) or Excel 업로드 → DB 반영
           번역팀 = Lokalise 그대로
```

**원칙 만족 체크**:

| 원칙 | O/X | 근거 |
|------|-----|------|
| P1 | O | DB가 단일 쓰기 원천. |
| P2 | O | 발견자가 관리자 UI 또는 Slack 봇으로 DB 수정 가능 (3초 수렴). |
| P3 | O | DB 스키마·권한으로 쓰기 차단. Lokalise/Excel은 DB에서 파생. |
| P4 | O | 모든 파생물 재생성 가능. |
| P5 | O | DB `tenant` 컬럼으로 VNG 완전 격리. |
| P6 | △ | DB 인프라 구축 + Excel 업로드 컨버터 개발 필요, 개발 공수 가장 큼. 4~6주 빠듯 (Phase 5 이후 선택지로 더 적합). |

**편법 경로 × 차단 여부**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise ko 필드는 DB mirror, 수정 API 403. CI 후보 D와 동일한 덮어쓰기도 병행. | **차단** |
| E2 | DB str_id 1:1로 병합 개념 없음 | **차단** |
| E3 | `.pb` CI-only | **차단** |
| E4 | CI only | **차단** |
| E5 | DB tenant 분리 | **차단** |

---

## Step 5 — 평가 매트릭스

### 5-1. 편법 × 후보 교차표 (contract 필수)

| 편법 \ 후보 | A Lokalise 권한강등 | B 자체 워크벤치 | C Git PR | D Lokalise 래퍼 | E Google Sheet | F DB 하이브리드 |
|--|--|--|--|--|--|--|
| E1 Lokalise 웹 ko | 차단 | 차단(제거) | 차단(제거) | 차단(복귀) | 차단(제거) | 차단 |
| E2 대표키 병합 옵션 | 차단 | 차단(개념無) | 차단(개념無) | 차단 | 차단(개념無) | 차단(개념無) |
| E3 pb 직접 커밋 | 차단 | 차단 | 차단 | 차단 | 차단 | 차단 |
| E4 git 커밋 누락 + 로컬 datasheet | 차단 | 차단 | 차단 | 차단 | 차단 | 차단 |
| E5 VNG 역류 | 통과(기본)/차단(옵션) | 차단 | 차단 | 차단(분리 후) | 차단 | 차단 |

→ A만 E5 기본 통과 (VNG 분리 옵션 없으면 사고 재현 가능). 나머지는 5/5 차단 달성.

### 5-2. 6축 평가 (contract 점수 기준: 각 0~5점, 총 30점)

| 후보 | (1) 고정제약 준수 | (2) 5건 차단률 | (3) 개발공수 4~6주 | (4) 번역팀 UI 학습 | (5) VNG 충격도 | (6) 롤백 용이성 | 합계 |
|------|-------|------|-------|------|-------|-------|------|
| A Lokalise 권한강등 | 5 | 4 | 5 | 5 | 4 | 5 | **28** |
| B 자체 워크벤치 | 2 | 5 | 1 | 1 | 4 | 2 | **15** |
| C Git PR | 1 | 5 | 3 | 1 | 4 | 3 | **17** |
| D Lokalise 단방향 래퍼 | 5 | 5 | 4 | 5 | 4 | 4 | **27** |
| E Google Sheet | 2 | 5 | 2 | 2 | 5 | 2 | **18** |
| F DB 하이브리드 | 3 | 5 | 1 | 4 | 5 | 2 | **20** |

**점수 산출 근거 (객관 지표)**:

- **(1) 고정제약 준수**: Lokalise 구독/VNG/Protobuf/Excel 친숙도/번역팀 UI/4~6주 총 6건 중 준수 개수를 5점 스케일로.
  - A: 6/6 준수 → 5
  - B: Lokalise 구독 해지(-1), 번역팀 UI 재교육(-1), 4~6주 초과(-1) = 3/6 → 2 (올림 보정 없음)
  - C: Lokalise 유지되나 번역팀 UI 근본 변경(-2), Excel 친숙도는 유지되나 번역팀 Git 학습(-1), VNG는 브랜치(-1) = 2/6 → 1
  - D: 6/6 → 5
  - E: Lokalise 구독 해지, Excel 친숙도 위반, 번역팀 UI 변경, 4~6주 빠듯 = 2/6 → 2
  - F: Excel 친숙도 부분 유지(업로드), Lokalise 유지, 번역팀 UI 유지, 4~6주 빠듯, DB 신규 = 3/6 → 3
- **(2) 5건 차단률**: 5×5 매트릭스에서 "차단"으로 분류된 건수 / 5 × 5.
  - A: 4/5 (E5 기본 통과) = 4
  - B~F: 5/5 = 5
- **(3) 개발공수 4~6주 적합도**: 1~2명으로 완성 가능성.
  - A: Lokalise API 프록시 Lambda + .pb gitignore + rev-dedup(이미 a1cfe43c8로 부분 존재) = 2~3주 → 5
  - B: 자체 워크벤치 풀스택 = 10주 이상 → 1
  - C: CODEOWNERS 설정 + CI validator = 3주지만 번역팀 재교육 별도 = 3
  - D: CI cron Lambda 1개 + datasheet rev-dedup = 4주 → 4
  - E: xlsx↔Sheet 양방향 migration + CI = 6~8주 → 2
  - F: DB 설계 + 관리자 UI + 3개 뷰 싱크 = 10주 이상 → 1
- **(4) 번역팀 UI 학습비용**: Lokalise 그대로 유지 = 5, 완전 교체 = 1.
  - A: 그대로 = 5
  - B: 자체 워크벤치 = 1
  - C: Git 학습 = 1
  - D: 그대로 = 5
  - E: Sheet 워크벤치 = 2
  - F: Lokalise 유지 = 4 (관리자 페이지 일부 노출)
- **(5) VNG 충격도**: VNG 현행 흐름 유지 = 5, 중단 리스크 高 = 1.
  - A: 단일 프로젝트 유지면 충격 0, 분리 시 소프트 마이그 = 4
  - B: 신규 워크벤치 테넌트로 VNG 작업 흐름 변경 = 4
  - C: VNG도 Git 학습 = 4
  - D: 프로젝트 분리 필요 = 4
  - E: 전용 Sheet로 격리, VNG 영향 최소 = 5
  - F: tenant 분리로 VNG 자체 운영 가능 = 5
- **(6) 롤백 용이성**: Lokalise 구독/워크벤치/DB 구축 등을 되돌리는 비용.
  - A: 프록시 Lambda off → 원상복구 = 5
  - B: 구독 해지 + 워크벤치 폐기 = 2
  - C: PR 플로우 복구 쉬우나 번역팀 재학습 롤백 = 3
  - D: Lambda off → 즉시 원상복구 = 4 (단, Lokalise rev 누적 재발 가능)
  - E: Sheet → xlsx 역마이그 + 구독 재가입 = 2
  - F: DB 폐기 + 전 파이프라인 리배선 = 2

> 점수는 객관 지표(건수/주 단위/스케일 환산)이며, 자기 작품에 가점하지 않았음. Critic이 재검증 권장.

---

## Step 6 — 추천안 (파레토 프론티어 1~2개)

### 주력 추천안: **후보 D (Lokalise 단방향 래퍼) + 후보 A 권한강등 일부 흡수**

- **선정 이유**:
  - 5건 사례 **모두 차단** (5/5) 달성하는 후보 중 고정 제약 6/6 준수 + 4~6주 개발 공수 내 = D만 유일.
  - A는 P3(Block)에 가장 충실하나 P5(VNG 분리) 기본 구조에서 E5 통과 리스크. D는 E5도 차단(프로젝트 분리 Phase에 포함) 가능.
  - A의 "API 프록시 403 차단"을 D에 병합하면 10분 cron 사이 Lokalise 웹 수정으로 임시 배포된 값이 런타임에 노출될 0~10분 틈을 막을 수 있음 → **D + A의 API 프록시 = 최강 조합**.
- **파레토 포지션**:
  - D는 (고정제약 5, 차단률 5) 프론티어 상단.
  - A는 (고정제약 5, 차단률 4) — D가 우위.
  - B/C/E/F는 차단률 5지만 고정제약 1~3점대로 프론티어에서 지배당함.

### 대안 추천안: **후보 A 단독 (보수적 전환)**

- **선정 이유**: 개발 리소스 극소 시 (1명 × 2주) 최소 변경으로 E1~E4를 차단. 단, E5 VNG는 별도 Phase 2에 분리 약속 필수.
- **D와의 선택 기준**:

| 상황 | 선택 |
|------|------|
| 개발 리소스 1명 × 2주만 확보 | **A** |
| 개발 리소스 1~2명 × 4~6주 | **D + A 프록시 흡수** |
| VNG 분리가 다음 분기 과제로 확정 | **A → D 순차 상향** |

### 사람이 결정해야 할 포인트 (3건)

1. **Lokalise 구독 장기 유지 여부**: D는 구독 의존도가 더 커짐. 6개월 후 재검토 시점을 못박을지, 구독 종료를 Phase 5 옵션으로 남길지 결정.
2. **VNG 프로젝트 분리의 D-day**: D의 기본 구성은 단일 프로젝트 → E5 완전 차단에 프로젝트 분리 필요. VNG 협의 리드타임 (2~4주 추정) 확보 여부.
3. **Lokalise API 프록시 운영 책임**: A의 프록시 Lambda를 누가 운영하는가 (dev팀 vs 인프라팀). 단일장애점 리스크 수용 범위.

---

## Step 7 — 전환 경로 (Phase 0~5)

> 주력 추천(D + A 프록시 흡수) 기준. 대안 A 단독은 Phase 0~2에서 중단하는 축소판.

### Phase 0 — 관찰·측정 (Week 0, 3~5일)

- **Entry**: 스펙 승인, 추천안 D+A 확정
- **작업**:
  - Lokalise API rate limit / webhook 용량 측정
  - 현재 Lokalise rev 누적 현황 스냅샷 (a1cfe43c8 datasheet로 덤프)
  - VNG 편집 빈도 7일치 로그 수집 (프로젝트 분리 필요성 수치화)
  - `.pb` 파일들을 `.gitignore` 임시 예약 PR 준비 (미머지)
- **Exit**:
  - 측정 리포트 1건
  - VNG 분리 필요성 결론 (yes/no)
- **롤백 포인트**: 측정만 수행, 기존 파이프라인에 영향 없음. 스냅샷/PR 폐기만으로 원상복구.

### Phase 1 — Lokalise ko 필드 읽기전용 + API 프록시 (Week 1~2)

- **Entry**: Phase 0 완료, Lokalise admin 접근 확보
- **작업**:
  - Lokalise 역할 재정의: `translator_nonko`, `reviewer`, `admin_api`
  - 모든 인간 계정을 `translator_nonko` 이하로 강등 (admin은 CI 토큰만)
  - 자체 Lambda 프록시 구축: `/api/lokalise/*` 요청에서 `target_language=ko` PUT/PATCH 403 리젝
  - Slack 알림: ko 쓰기 시도 감지 시 `#l10n-ops`에 차단 로그
- **Exit**:
  - Lokalise 웹에서 ko 필드 편집 버튼 비활성 확인
  - 프록시 로그에 최근 7일 ko 쓰기 시도 차단 건수 > 0 (실전 동작 증명)
- **롤백 포인트**: Lokalise 역할 일괄 복원 (스크립트 저장). 프록시 Lambda 비활성화 토글.

### Phase 2 — datasheet rev-dedup 내재화 + pb gitignore + CI pb 생성 (Week 2~3)

- **Entry**: Phase 1 안정화 (프록시 7일 무사고)
- **작업**:
  - 04-18 a1cfe43c8 datasheet rev-dedup 로직을 메인 빌드 경로에 정식 편입 (현재는 임시 패치)
  - `.gitignore`에 `protobuf/*.pb` 추가, 히스토리 BFG로 슬림화 (선택)
  - CI (Actions)에 `build-pb` 워크플로 추가: main push 시 pb 생성 → artifact 업로드 → 클라이언트/서버 릴리스 파이프라인과 연결
  - pre-receive hook: `protobuf/` 경로 diff 있는 push 거부
- **Exit**:
  - pb를 빼고도 클라이언트/서버 빌드 성공
  - pre-receive가 테스트 push 거부 확인
- **롤백 포인트**: `.gitignore` 되돌리기 + 이전 pb 파일 백업 복원. BFG 히스토리 슬림화는 롤백 불가 → BFG는 Phase 4 이후로 미룰 수 있음 (선택 작업).

### Phase 3 — Excel → Lokalise ko 단방향 cron (Week 3~4)

- **Entry**: Phase 2 완료, pb CI 생성 안정
- **작업**:
  - Lambda cron (10분): `translations.xlsx` ko 컬럼 해시 비교 → 변경 시 Lokalise API `delete_rev` → `create_translation` 호출 (rev 누적 차단)
  - 업로드 스크립트에 `differentiate_by_file=true` 하드코딩 (E2 차단)
  - Lokalise 수동 업로드 버튼은 프로젝트 설정에서 admin-only, 개별 계정 권한 제거
  - 번역팀 공지: "영어 이하만 수정" (이미 04-18 00:42 상유 확정 규칙 재확인)
- **Exit**:
  - cron 7일 무사고
  - Lokalise ko 값이 Excel과 실시간(10분 이내) 동일 확인
  - 인위 테스트: 웹에서 ko 수정 시도 → 10분 내 자동 복귀 확인
- **롤백 포인트**: cron Lambda 비활성화 → Phase 1 상태로 복귀 (프록시는 유지). cron 폐기해도 E1은 프록시가 차단.

### Phase 4 — VNG 프로젝트 분리 (Week 4~5)

- **Entry**: Phase 3 완료, VNG 협의 완료
- **작업**:
  - Lokalise에 `cos-main` / `cos-vng` 2개 프로젝트 생성
  - VNG 권한을 `cos-vng`만 부여, `cos-main`에서 VNG 계정 제거
  - 메인 → VNG 단방향 반영 cron (ko/en 한정, VNG → 메인 방향은 없음)
  - 04-17 `Indonésia` 같은 VNG값이 메인에 섞이지 않도록 구조 차단
- **Exit**:
  - VNG가 `cos-vng`에서만 편집 가능 확인
  - 메인의 id/vi 필드에 VNG 수정값 반영 0건 확인 (7일)
- **롤백 포인트**: VNG 계정에 `cos-main` 권한 임시 복원 (스크립트). 단방향 cron off.

### Phase 5 — 고정 제약 재검토 (Week 5~6 이후, 선택)

- **Entry**: Phase 1~4 전부 안정화 (D+7 무사고)
- **작업 (선택지)**:
  - (a) Lokalise 구독 유지 여부 재평가 (6개월 리뷰 약속)
  - (b) 후보 E(Google Sheet)나 후보 F(DB) 부분 도입 PoC
  - (c) 번역팀 워크벤치 후보 B PoC (Lokalise 보완용)
- **Exit**: 차기 iteration(v2) Planner로 이관
- **롤백 포인트**: Phase 5는 모두 PoC이므로 언제든 중단. Phase 4까지의 구조는 계속 동작.

### D-day 순서 (Phase 3 cut-over 기준)

```
Phase 3 D-day (예: Week 3 금요일 저녁)
  1. 프록시 Lambda 완전 활성화 (Phase 1은 warn 모드 → enforce)
  2. Excel → Lokalise ko cron 첫 실행
  3. Lokalise 웹에서 ko 수정 테스트 → 10분 내 복귀 확인
  4. 번역팀 공지 (이미 확정 규칙 재고지, 재교육 불필요)
  5. D+7까지 rev 누적 0건 확인
  6. D+7 통과 시 Phase 4 킥오프
```

### 전체 일정

| Phase | 주차 | 핵심 산출 | 롤백 지점 |
|-------|------|----------|----------|
| 0 | W0 | 측정 리포트 | N/A (무영향) |
| 1 | W1~2 | API 프록시 + ko 역할 강등 | 프록시 off |
| 2 | W2~3 | datasheet rev-dedup + pb CI | .gitignore 되돌리기 |
| 3 | W3~4 | 단방향 ko cron | cron off |
| 4 | W4~5 | VNG 분리 | VNG 계정 권한 복원 |
| 5 | W5~6+ | 재검토 PoC | PoC 중단 |

총 4~6주 개발 공수 내 소화 가능.

---

## 참고: 추천안이 5건 사례를 차단하는 시뮬레이션

| 사례 | 재현 시도 | 추천안(D+A) 차단 지점 |
|------|----------|---------------------|
| 2026-02-05 Modes^1303 이중 소스 | modes.xlsx와 translations.xlsx에 같은 키 다른 값 | translations.xlsx가 유일 ko 원천, modes.xlsx에는 str_id 참조만 — CI validator가 이중 정의 거부 (Phase 2) |
| 2026-02-20 VNG 중복 등록 | VNG가 메인 프로젝트에 신규 키 업로드 | Phase 4에서 VNG 별도 프로젝트, 메인 쓰기 불가 |
| 2026-03-07 skill_description 잔여물 | 로컬 datasheet + git 커밋 누락 → pb에 과거 값 남음 | Phase 2에서 pb는 CI-only, 로컬 바이너리 개념 소멸 |
| 2026-03-11 303건 태깅 누락 | Lokalise 태깅을 PM이 수동으로 누락 | Phase 3에서 업로드는 CI 자동, `differentiate_by_file` 하드코딩, 태깅도 자동 |
| 2026-04-17 rev 누적 | Lokalise 웹 ko 수정 + Excel 미갱신 | Phase 1 프록시 403 + Phase 3 10분 cron 자동 복귀 (이중 방어) |

→ 5/5 구조적 차단. "탐지"로 분류된 사례 없음.

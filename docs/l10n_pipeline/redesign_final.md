# Redesign v2

> 기준일: 2026-04-18
> 입력: `spec.md`(v2), `iteration-contract-v2.md`, `handoff-v1.md`, `review-v1.md`, `case_study_2026-04-17_rev_pollution.md`
> 작성: l10n-pipeline-architect (Step 4~8)
> 이전: `iter-1/redesign-v1.md` (40/60 미수렴)
> 원칙 근거: spec.md v2 해결 원칙 P1~P6 (P3는 "0초 절" 강화)

---

## v1 → v2 변경 요약

| 구간 | v1 | v2 | 근거 |
|------|-----|-----|------|
| 추천안 순서 | D 기본 + A 프록시 흡수 | **A 프록시 기본 + D cron 보강** | review-v1 치명 4, handoff-v1 (D) |
| Phase 0 범위 | 관찰·측정만 | **VNG cos-main 쓰기 권한 회수** Exit | handoff-v1 A-3, review-v1 치명 3 |
| Phase 2 Validator | 시뮬레이션 표에만 등장 | 본문 **Entry/Exit**로 정식 편입 (3종) | handoff-v1 A-1, review-v1 치명 1 |
| 태깅 자동화 | `differentiate_by_file` 한 줄 | Phase 3 `tag` 컬럼 + publish/unpublish 1:1 매핑 | handoff-v1 A-2, review-v1 치명 2 |
| 편법 매트릭스 | 5후보 × 5편법 = 25셀 | **6후보 × 8편법 = 48셀** | contract v2 DoD-2 |
| 점수 스케일 | 6축 × 5점 = 30점 | **6축 × 10점 = 60점** | contract v2 |
| 10분 cron 분류 | "차단(자동 복구)" | **탐지** (0초만 차단) | contract v2 DoD-3, spec P3-a |
| M2 "3초 수렴" | 사실상 포기 | Phase 2 **일상 PR 경로 통합** (`tag=re` → translations_ko.xlsx 직접 수정 → 신규 등록과 동일 흐름) | handoff-v1 (C) |
| 프록시 Lambda | 단일장애점 미정의 | **fail-close 명시 + 복구 SOP** (부록) | handoff-v1 (C), review-v1 치명 5 |
| Phase 3 D-day | 프록시 enforce + cron 첫 실행 동일일 | **D+3 간격 분리** | handoff-v1 (C), review-v1 축 2 |

---

## Step 4 — 후보안 (6개)

### 공통 전제 — 편법 경로 8종 (contract v2 확장)

| 코드 | 편법 경로 | 출처 |
|------|----------|------|
| E1 | Lokalise 웹 한국어 직수정 | 사례 03-26, 04-17 |
| E2 | 대표키 병합 옵션 체크 실수 | 사례 02-20, 04-17 |
| E3 | `.pb` 직접 편집 커밋 | 사례 04-17 23:15/23:37 |
| E4 | git 커밋 누락 + 로컬 datasheet | 사례 03-07 |
| E5 | VNG 편집값 메인 역류 | 사례 04-17 Indonésia |
| F1 | `translations.xlsx` 외 xlsx(modes/dialog_groups/ui_strings)에 ko 텍스트 이중 입력 | review-v1 편법 1 |
| F2 | Lokalise 개인 API 토큰 발급·사용 (프록시 우회) | review-v1 편법 2 |
| F4 | pre-receive hook bypass (repo admin --no-verify / GitHub bypass) | review-v1 편법 4 |

> **차단 등급 정의 (contract v2 DoD-3)**
> - **차단**: 원복 지연 0초, 해당 행위 자체가 거부됨
> - **탐지**: 원복 지연 1분 이상, 사후 복구·덮어쓰기·알림·로그
> - **통과**: 아무 변화 없이 현재와 동일하게 사고 재현

---

### 후보 A — Lokalise 권한 강등 + API 프록시 (Excel 단일 쓰기 원천)

- **축**: SaaS 유지·권한 축소형 (P1/P3 중심)
- **한 줄**: Lokalise 웹·API 양쪽에서 ko 쓰기를 0초 차단. Excel → Lokalise ko 단방향 pull은 배포 파이프라인에서 **제거** (ko는 Excel에서 직접 읽음, Lokalise ko는 번역팀 참고용 mirror).

**구조**:

```
[원문]       excel/translations.xlsx (ko 컬럼 = SOT, 쓰기 유일 경로)
              │
              │ datasheet CLI + CI
              ▼
[배포 소비]   protobuf/*.pb  ← Excel ko 직접 변환 (Lokalise ko 거치지 않음)
              │
              ▼
          클라이언트/서버 런타임
              ▲
              │
[번역 UI]    Lokalise 프로젝트 (ko = read-only mirror, 타언어만 write)
              ▲                         ▲
              │ CI: xlsx→lokalise       │ 번역팀 웹 UI (en/ja/zh/th/id만)
              │ 타언어 pull              │
              └── Lambda 프록시
                  (target_language=ko PUT/PATCH → 403)
                  (IP allowlist: 프록시 Lambda IP만 Lokalise API 호출 가능)
```

**권한·네트워크 설계**:
- Lokalise 역할: `translator_nonko`, `reviewer`, `admin_api`. 인간 UI 계정의 ko 필드 쓰기 권한 전면 제거.
- `translator_nonko` 이하는 **개인 API 토큰 발급 불가** (Lokalise 역할 기능 설정).
- Lokalise API IP allowlist: **프록시 Lambda EIP만 등록**. 개인 토큰이 탈취돼도 외부 IP는 전부 거부 (F2 차단).
- Admin API 토큰은 CI Secret만 보유 + AWS KMS 암호화.
- **배포 파이프라인이 Lokalise에서 ko를 pull하는 코드 제거** (F3 차단의 핵심): ko는 `translations.xlsx → datasheet → pb`만 흐름.

**편법 차단표 (8종)**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 Lokalise 웹 ko 직수정 | 웹 UI에서 ko 필드 비활성 + 프록시 `target_language=ko` PUT 403 | 차단 (0초) |
| E2 대표키 병합 옵션 실수 | 업로드는 CI만, 스크립트에 `differentiate_by_file=true` 하드코딩, 수동 업로드 UI admin-only | 차단 (0초) |
| E3 `.pb` 직접 편집 커밋 | `.gitignore`에 `protobuf/*.pb` + 서버 pre-receive hook이 pb diff 거부 | 차단 (0초) |
| E4 git 커밋 누락 + 로컬 datasheet | pb가 git 제외, CI만 빌드, 로컬 바이너리 잔여물 영향 0 | 차단 (0초) |
| E5 VNG 역류 | Phase 0에서 VNG `cos-main` 쓰기 권한 회수 (과도기 Slack 대리 입력) | 차단 (0초, Phase 0 Exit 이후) |
| F1 xlsx 이중 소스 | CI validator (a): `translations.xlsx` 외 xlsx에서 ko 자연어 컬럼 금지 → datasheet 변환 거부 | 차단 (0초) |
| F2 개인 API 토큰 | `translator_nonko` 이하 토큰 발급 권한 제거 + Lokalise API IP allowlist (프록시 IP만) | 차단 (0초) |
| F4 pre-receive bypass | 서버 hook은 `--no-verify` 영향 없음 + GitHub repo admin bypass 설정 OFF + Phase 2 Exit에 "admin push reject" 테스트 | 차단 (0초) |

**원칙 만족 체크**:

| 원칙 | 결과 | 근거 |
|------|------|------|
| P1 단일 쓰기 원천 | O | ko 쓰기는 `translations.xlsx`만. Lokalise는 read-only mirror. |
| P2 비용 역전 | △ → O (D 보강 시) | 단독 A는 여전히 Excel 5단계. Phase 2 `tag=re` 일상 PR 경로 통합(오타 수정 = 신규 등록과 동일 흐름)으로 3초 수렴 달성. |
| P3 기술적 봉쇄 (0초) | O | 프록시 403은 원복 지연 0초. |
| P4 파생물 재생성 | O | `.pb`·Lokalise ko 모두 Excel에서 재생성되는 파생물. |
| P5 경계 분리 | O (Phase 0 Exit 이후) | VNG `cos-main` 쓰기 권한 0, Phase 4 `cos-vng` 분리로 완성. |
| P6 점진 전환 | O | Lokalise 구독·UI·번역팀 워크플로 유지, 4~6주 내 소화. |

---

### 후보 B — Lokalise 폐기 + 자체 번역 워크벤치

- **축**: SaaS 교체·자체 개발형 (P1/P2/P3 전면 재설계)
- **한 줄**: Lokalise 구독 종료, Excel 단일 소스 + 인하우스 React+FastAPI 워크벤치(ko read-only, 타언어 write).

**구조**:

```
[원문]   excel/translations.xlsx
            │ CI push
            ▼
[입력]   자체 워크벤치 (React + FastAPI)
           - ko: read-only (DB 미러)
           - 타언어: write
            │ CI: 워크벤치 → excel/translations_{lang}.xlsx
            ▼
[배포]   CI → protobuf/*.pb (.pb 커밋 제외)
```

**편법 차단표**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise 제거 → 경로 소멸 | 차단 (0초) |
| E2 | 대표키 병합 개념 없음 (str_id 1:1) | 차단 (0초) |
| E3 | `.gitignore` + pre-receive | 차단 (0초) |
| E4 | CI only | 차단 (0초) |
| E5 | VNG는 워크벤치 별도 RBAC tenant | 차단 (0초) |
| F1 | datasheet validator로 차단 | 차단 (0초) |
| F2 | API 토큰 개념 자체 부재 | 차단 (0초, 해당 없음) |
| F4 | pre-receive (서버 hook) | 차단 (0초) |

**고정 제약 위반**: 번역팀 Lokalise UI 의존 (-1), Lokalise 구독 해지 (-1), 개발 4~6주 초과 (-1) → 3건 위반.

---

### 후보 C — Git 저장소 직접 편집형 (번역팀 PR 방식)

- **축**: Git 직접 편집형 (P1 극단 해석)
- **한 줄**: 번역팀이 `excel/translations_{lang}.xlsx`를 GitHub Desktop/Fork로 수정 → PR → CI 머지. Lokalise 제거.

**구조**:

```
[원문]   excel/translations.xlsx (ko, CODEOWNERS=기획팀)
            │
            ▼
[입력]   excel/translations_{lang}.xlsx (번역팀 PR)
            │ CI validator + CODEOWNERS
            ▼
[배포]   CI → protobuf/*.pb
```

**편법 차단표**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise 제거 | 차단 (0초) |
| E2 | 병합 개념 없음 | 차단 (0초) |
| E3 | `.gitignore` + pre-receive | 차단 (0초) |
| E4 | CI only | 차단 (0초) |
| E5 | VNG fork + CODEOWNERS 차단 | 차단 (0초) |
| F1 | validator | 차단 (0초) |
| F2 | 해당 없음 (Lokalise 제거) | 차단 (0초) |
| F4 | 서버 hook + GitHub bypass 차단 | 차단 (0초) |

**고정 제약 위반**: 번역팀 Lokalise UI 의존 (-1), 번역팀 Git 재교육 (-1), Lokalise 구독 해지는 아니나 활용 불가.

---

### 후보 D — Lokalise 단방향 래퍼 (Excel → Lokalise ko 10분 cron 덮어쓰기)

- **축**: Lokalise 단방향 래퍼형 (P1 + P4 조합, P3는 **탐지 수준**)
- **한 줄**: Excel이 원문, Lokalise ko는 10분 cron이 Excel 값으로 주기 덮어쓰기. 웹 수정은 10분 내 사라짐.

**구조**:

```
[원문]   excel/translations.xlsx (ko SOT)
            │ 10분 cron: xlsx → lokalise ko PUT
            ▼
[UI]    Lokalise (ko: cron 덮어쓰기 대상, 타언어 자유 편집)
            │ CI: lokalise → translations_{lang}.xlsx pull
            ▼
[배포]   excel/translations_{lang}.xlsx + CI pb 생성
```

> **중요 (v2 재분류)**: D 단독은 10분 cron만이므로 E1에 대해 **탐지(원복 지연 10분)**. contract v2 DoD-3 정의에 따라 "차단"이 아님.

**편법 차단표**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 Lokalise 웹 ko | 10분 cron이 Excel 값으로 복귀 (원복 지연 ≤ 10분) | **탐지** |
| E2 | CI 업로드 `differentiate_by_file=true` 고정, 수동 업로드 admin-only | 차단 (0초) |
| E3 | `.gitignore` + pre-receive | 차단 (0초) |
| E4 | CI only | 차단 (0초) |
| E5 | VNG 프로젝트 분리 (Phase 4 전까지 Phase 0 권한 회수 필요) | 차단 (Phase 0 Exit 이후) |
| F1 | validator (별도 Phase 2 작업) | 차단 (0초) |
| F2 | 프록시 없음 → IP allowlist 설계 부재 시 개인 토큰 직접 Lokalise API 호출 가능 | **통과** |
| F4 | 서버 hook + GitHub bypass 차단 | 차단 (0초) |

**단독 한계**: E1 10분 창 + F2 통과 → 5건 차단률 4/5, 8편법 차단률 6/8.

---

### 후보 E — Google Sheet 단일 소스형

- **축**: SaaS 교체·Sheet 단일 (P1/P2 극대화)
- **한 줄**: Lokalise 폐기, translations.xlsx 폐기. Google Sheet가 ko + 타언어 전부 보유, CI가 모든 pb 재생성.

**편법 차단표**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise 제거 | 차단 (0초) |
| E2 | 병합 개념 없음 | 차단 (0초) |
| E3 | `.gitignore` + pre-receive | 차단 (0초) |
| E4 | CI only | 차단 (0초) |
| E5 | VNG 전용 Sheet 또는 필터 | 차단 (0초) |
| F1 | Sheet 단일 소스 → xlsx 이중 입력 개념 없음 | 차단 (0초) |
| F2 | Lokalise API 개념 없음 | 차단 (해당 없음) |
| F4 | 서버 hook | 차단 (0초) |

**고정 제약 위반**: Lokalise 구독 해지 (-1), Excel 친숙도 위반 (-1), 번역팀 Lokalise UI 전환 (-1), 개발 4~6주 빠듯 (-1).

---

### 후보 F — 하이브리드 DB형 (Postgres 원문 DB + Excel·Lokalise 뷰)

- **축**: DB 원문 + 파생 뷰
- **한 줄**: 한국어 원문은 중앙 DB, Excel·Lokalise·pb는 DB에서 파생되는 뷰·mirror.

**편법 차단표**:

| 편법 | 차단 방식 | 등급 |
|------|----------|------|
| E1 | Lokalise ko = DB mirror, 쓰기 403 + 프록시 | 차단 (0초) |
| E2 | DB str_id 1:1 | 차단 (0초) |
| E3 | `.gitignore` + pre-receive | 차단 (0초) |
| E4 | CI only | 차단 (0초) |
| E5 | DB `tenant` 컬럼 격리 | 차단 (0초) |
| F1 | DB가 단일 소스, xlsx는 뷰로만 생성 | 차단 (0초) |
| F2 | Lokalise API IP allowlist (A와 동일 적용) | 차단 (0초) |
| F4 | 서버 hook | 차단 (0초) |

**고정 제약 위반**: DB 인프라 신규 (-1), 개발 4~6주 초과 (-2), Excel 친숙도 부분 위반 (-1).

---

## Step 5-1 — 편법 × 후보 매트릭스 (6 × 8 = 48셀)

| 편법 \ 후보 | A 프록시+권한강등 | B 자체 워크벤치 | C Git PR | D 10분 cron | E Google Sheet | F DB 하이브리드 |
|------------|-----------|---------|---------|------------|-------------|---------------|
| E1 Lokalise 웹 ko | 차단 (프록시 403, 0초) | 차단 (Lokalise 제거) | 차단 (Lokalise 제거) | **탐지 (10분 cron)** | 차단 (Lokalise 제거) | 차단 (mirror+403) |
| E2 대표키 병합 | 차단 (CI 하드코딩) | 차단 (개념 부재) | 차단 (개념 부재) | 차단 (CI 하드코딩) | 차단 (개념 부재) | 차단 (DB str_id) |
| E3 pb 직접 커밋 | 차단 (.gitignore+hook) | 차단 | 차단 | 차단 | 차단 | 차단 |
| E4 git 커밋 누락 | 차단 (CI only) | 차단 | 차단 | 차단 | 차단 | 차단 |
| E5 VNG 역류 | 차단 (Phase 0 Exit 이후) | 차단 (tenant RBAC) | 차단 (fork+CODEOWNERS) | 차단 (Phase 0 Exit 이후) | 차단 (전용 Sheet) | 차단 (DB tenant) |
| F1 xlsx 이중 소스 | 차단 (datasheet validator) | 차단 (validator) | 차단 (validator) | 차단 (validator) | 차단 (Sheet 단일) | 차단 (DB 단일) |
| F2 개인 API 토큰 | 차단 (토큰 금지+IP allowlist) | 차단 (Lokalise 부재) | 차단 (Lokalise 부재) | **통과** (allowlist 부재) | 차단 (Lokalise 부재) | 차단 (IP allowlist) |
| F4 pre-receive bypass | 차단 (GitHub bypass OFF+테스트) | 차단 | 차단 | 차단 | 차단 | 차단 |

**차단 건수 / 8편법**: A 8/8 · B 8/8 · C 8/8 · D 6/8 (E1 탐지, F2 통과) · E 8/8 · F 8/8
**5건 사례 차단 (E1~E5)**: A 5/5 · B 5/5 · C 5/5 · D 4/5 (E1 탐지) · E 5/5 · F 5/5

---

## Step 5-2 — 6축 점수 매트릭스 (60점 만점)

> contract v2 기준: 각 축 0~10점, 총 60점. 합격선 55/60 또는 50/60+5건 전차단.

| 후보 | (1) 고정제약 준수 /10 | (2) 5건 차단률 /10 | (3) 개발공수 /10 | (4) 번역팀 UI 학습 /10 | (5) VNG 충격도 /10 | (6) 롤백 용이성 /10 | 합계 /60 |
|------|--------------|-------------|----------|-----------------|-------------|--------------|--------|
| **A 프록시+권한강등** | **10** (6/6) | **10** (5/5) | **9** (2~3주) | **10** (UI 유지) | **9** (Phase 0 회수 Slack 대리) | **10** (프록시 off 즉시) | **58** |
| B 자체 워크벤치 | 4 (3/6) | 10 | 2 (10주+) | 2 (재교육) | 7 (tenant 마이그) | 3 (워크벤치 폐기) | 28 |
| C Git PR | 3 (2/6) | 10 | 6 (3주+재교육) | 2 (Git 학습) | 7 (fork 학습) | 5 (PR 되돌리기) | 33 |
| **D 10분 cron (단독)** | 10 (6/6) | 8 (4/5, E1 탐지) | 8 (4주) | 10 | 9 | 8 | 53 |
| E Google Sheet | 4 (2/6) | 10 | 4 (6~8주) | 4 (Sheet 학습) | 10 (전용 Sheet) | 3 (Sheet→xlsx) | 35 |
| F DB 하이브리드 | 5 (3/6) | 10 | 2 (10주+) | 8 (Lokalise 유지) | 10 (DB tenant) | 3 (DB 폐기) | 38 |

**점수 산출 근거 (객관 지표)**:

- **(1) 고정제약 준수** (6/6 만점 = 10점, 1건 위반당 -2점 base)
  - A: Lokalise 구독 유지, VNG 권한 Phase 0 회수(ko 쓰기만, UI 접근 유지), Protobuf 유지, Excel 친숙도 유지, 번역팀 Lokalise UI 유지, 개발 4~6주 내 → 6/6
  - B: 구독 해지(-), 번역팀 UI 변경(-), 개발 초과(-) → 3/6
  - C: 번역팀 UI 근본 변경(-), 번역팀 Git 학습(-), Lokalise 사실상 해지(-) → 2/6
  - D 단독: 6/6 (A와 동일 고정제약 프로파일)
  - E: 구독 해지(-), Excel 친숙도 위반(-), 번역팀 UI(-), 개발 빠듯(-) → 2/6
  - F: Excel 친숙도 부분(-), 개발 초과(-), DB 신규(-) → 3/6

- **(2) 5건 차단률** (5건 전체 차단=10, 1건당 2점, 탐지는 0점 처리)
  - A/B/C/E/F: 5/5 = 10
  - D 단독: 4/5 (E1 탐지) = 8

- **(3) 개발공수 4~6주 적합도** (1~2명 기준)
  - A: 프록시 Lambda(1주) + 권한 재설계(1주) + validator(0.5주) + `tag=re` CI 핸들러(0.5주) = 3주 → 9
  - D 단독: cron Lambda(1주) + datasheet rev-dedup(이미 존재) + validator(0.5주) = 4주 → 8
  - B/F: 10주 이상 → 2
  - C: 3주 + 번역팀 재교육 별도 → 6
  - E: 6~8주 → 4

- **(4) 번역팀 UI 학습비용** (Lokalise 유지=10, 완전 교체=2)
  - A/D: 10 (ko 필드만 비활성, 나머지 UI 동일)
  - B: 2 (자체 워크벤치)
  - C: 2 (Git 학습)
  - E: 4 (Sheet UI)
  - F: 8 (Lokalise 유지 + 관리자 페이지 일부)

- **(5) VNG 충격도** (현행 유지=10, 중단 리스크=1)
  - A: Phase 0 권한 회수 + Slack 대리 입력 창구 → 9 (과도기 비용 있음)
  - D 단독: 9 (A와 동일 Phase 0 구조 공유 가능)
  - B/C: 7 (신규 플랫폼 온보딩)
  - E/F: 10 (전용 Sheet / DB tenant로 VNG 자체 운영)

- **(6) 롤백 용이성**
  - A: 프록시 Lambda off → 권한 복원 스크립트 → 원상복구 → 10
  - D: cron off → 원상복구 8 (단, rev 누적 재발 가능)
  - B/F: 워크벤치/DB 폐기 복잡 → 2~3
  - C: PR 롤백 자체는 쉬우나 번역팀 재학습 → 5
  - E: Sheet→xlsx 역마이그 + 구독 재가입 → 3

**자기 작품 가점 없음**. 편법 차단률·개발 주차는 객관 계측 가능.

---

## Step 6 — 추천안 (v2 재정렬)

### 주력 추천안: **A 프록시 기본 + D cron 보강** (**58 + D 결합 시 6/6 프로파일 유지**)

> **v1 → v2 순서 역전 근거**: review-v1 치명 4 — v1은 "D 기본 + A 프록시 흡수"였으나, D가 첫 방어선이면 10분 공백이 항상 열림. contract v2 DoD-3("0초만 차단")을 준수하려면 **A가 첫 방어선(거부, 0초), D가 이중 방어선(복구, 10분)** 순서여야 함.

**결합 구조**:

```
              ┌─────────────────────────────────────┐
              │ 첫 방어선: A 프록시 Lambda          │
              │ - target_language=ko PUT/PATCH 403  │
              │ - IP allowlist (프록시 IP only)     │
              │ - 원복 지연 0초 → 차단              │
              └──────────────┬──────────────────────┘
                             │ (만에 하나 우회 발생 시)
              ┌──────────────▼──────────────────────┐
              │ 이중 방어선: D 10분 cron            │
              │ - xlsx ko 해시 비교 → delete_rev +  │
              │   create_translation                │
              │ - 원복 지연 ≤ 10분 → 탐지(복구)     │
              └─────────────────────────────────────┘
```

- **선정 이유**:
  - 5건 사례 5/5 **차단** + 8편법 8/8 **차단** 동시 달성
  - 고정 제약 6/6 준수 (Lokalise 구독/VNG/Protobuf/Excel/번역팀 UI/개발 4~6주 전부 O)
  - 첫 방어선 0초 + 이중 방어선 복구 = P3 "0초 절" 준수
  - M2 "3초 수렴"은 Phase 2 `tag=re` 일상 PR 경로 통합(translations_ko.xlsx ko 직접 수정 + tag=re → 신규 등록과 동일한 PR·머지)으로 달성 — 별도 커맨드·예외 경로 없음

- **파레토 포지션**:
  - A 단독: (고정제약 10, 차단률 10, 공수 9) — 프론티어 상단
  - D 단독: (고정제약 10, 차단률 8) — A가 지배
  - A+D 결합: A의 차단력 + D의 복구력 → **첫/이중 방어선 구조**

### 대안 추천안: **A 단독 (초경량 전환)**

- 1명 × 2~3주만 확보 가능 시
- A 단독 차단률 8/8 (프록시가 웹·API 양쪽 봉쇄) → 5건 5/5
- D의 10분 cron은 Phase 3에 추가 옵션으로 보류

| 상황 | 선택 |
|------|------|
| 리소스 1명 × 2~3주 | **A 단독** |
| 리소스 1~2명 × 4~6주 | **A + D 결합** (주력) |
| VNG 분리 다음 분기 확정 | Phase 0 회수만 우선, A → A+D 순차 상향 |

### 사람이 결정해야 할 포인트 (3건)

1. **Lokalise 구독 6개월 재검토 시점** — Phase 5 리뷰로 못박을지, 무기한 유지할지
2. **Phase 0 VNG 과도기 Slack 창구 운영 책임** — 기획팀 대리 입력 담당자 1명 지정 (주 10~15건 예상)
3. **프록시 Lambda 운영 주체** — dev팀 vs 인프라팀. 단일장애점 SOP(부록)를 어느 팀이 owner인가

---

## Step 7 — 전환 경로 (Phase 0~5)

> 주력 추천(A + D) 기준. 대안 A 단독은 Phase 0~2에서 중단하는 축소판.

### Phase 0 — 관찰·측정 + **VNG 권한 회수** (Week 0, 3~5일)

- **Entry**:
  - 스펙 v2 승인, 추천안 A+D 확정
  - VNG 협의 개시 (과도기 Slack 창구 합의)

- **작업**:
  - Lokalise API rate limit / webhook 용량 측정
  - 현재 Lokalise rev 누적 현황 스냅샷 (a1cfe43c8 datasheet rev-dedup으로 덤프)
  - VNG 편집 빈도 7일치 로그 수집
  - `.pb` 파일들을 `.gitignore` 예약 PR 준비 (미머지)
  - **VNG 계정 `cos-main` 쓰기 권한 회수 스크립트 작성 및 실행** (DoD-5 핵심)
  - **과도기 Slack 창구 개설**: `#l10n-vng-requests` 채널, 기획팀 대리 입력 담당자 지정
  - **cos-vng 프로젝트 생성 착수** (리드타임 2~4주, Phase 4까지)

- **Exit**:
  - 측정 리포트 1건
  - **VNG 계정의 `cos-main` 쓰기 권한 0 확인** (Lokalise admin 로그로 검증) — DoD-5 필수
  - VNG 과도기 Slack 창구 첫 요청 처리 1건 완료
  - `cos-vng` 프로젝트 생성 킥오프 (완성은 Phase 4)

- **롤백 포인트**: VNG 권한 복원 스크립트 (Phase 0 전 snapshot). Slack 창구 폐쇄.

### Phase 1 — Lokalise ko 필드 읽기전용 + API 프록시 + IP allowlist (Week 1~2)

- **Entry**: Phase 0 Exit 통과 (VNG 쓰기 권한 0, 측정 완료)

- **작업**:
  - Lokalise 역할 재정의: `translator_nonko`, `reviewer`, `admin_api`
  - 모든 인간 계정을 `translator_nonko` 이하로 강등 (admin은 CI 토큰만)
  - **`translator_nonko` 이하 역할에서 API 토큰 발급 권한 제거** (F2 차단)
  - **Lokalise API IP allowlist 활성화**: 프록시 Lambda EIP만 등록 (F2 차단)
  - 자체 Lambda 프록시 구축: `/api/lokalise/*` 요청에서 `target_language=ko` PUT/PATCH 403 리젝
  - **프록시 fail-close 모드 명시** (Lambda 장애 시 503 → 쓰기 전면 거부, 부록 SOP 참조)
  - Slack 알림: ko 쓰기 시도 감지 시 `#l10n-ops`에 차단 로그

- **Exit**:
  - Lokalise 웹에서 ko 필드 편집 버튼 비활성 확인
  - **인위 테스트**: 개인 API 토큰으로 외부 IP에서 Lokalise API 호출 → 거부 확인 (F2 테스트)
  - 프록시 로그에 최근 7일 ko 쓰기 시도 차단 건수 > 0 (실전 동작 증명)

- **롤백 포인트**: Lokalise 역할 일괄 복원 (Phase 0 snapshot). 프록시 Lambda 비활성화 토글. IP allowlist 해제.

### Phase 2 — **Validator 3종 + pb gitignore + CI pb 생성 + `tag=re` 일상 PR 경로 통합** (Week 2~3)

- **Entry**: Phase 1 프록시 7일 무사고

- **작업 (validator 3종, handoff-v1 A-1 핵심 반영)**:
  - **Validator (a)**: `translations.xlsx` 외 xlsx(modes/dialog_groups/ui_strings 등)에서 **ko 자연어 텍스트 컬럼 금지**. datasheet 변환 스키마에 화이트리스트, 위반 시 변환 거부. pre-commit hook도 동일 검사 추가.
  - **Validator (b)**: `translations.xlsx` 내 ko 컬럼 **중복값 검사** (unique constraint, warn-then-fail). 동일 ko가 서로 다른 str_id에 등록되면 `differentiate_by_file` 하드코딩과 결합해 Lokalise 대표키 병합 사고 차단.
  - **Validator (c)**: validator 실패 시 **CI 전면 중단, pb artifact 미생성**. 클라이언트/서버 릴리스 파이프라인이 빈 artifact 받아 배포 중단.
  - 04-18 a1cfe43c8 datasheet rev-dedup 로직을 메인 빌드 경로에 정식 편입
  - `.gitignore`에 `protobuf/*.pb` 추가 (BFG 히스토리 슬림화는 Phase 4 이후 선택)
  - CI (Actions) `build-pb` 워크플로 추가
  - **서버측 pre-receive hook**: `protobuf/` 경로 diff 있는 push 거부 (F4 서버 hook)
  - **GitHub repo admin bypass OFF 설정** (F4 GitHub 정책)
  - **M2 일상 PR 경로 통합** (handoff-v1 (C) 핵심 대체): 별도 Slack 커맨드 없이 발견자가 `translations_ko.xlsx`에서 ko 수정 + `tag=re` 기입 → **신규 원문 등록과 동일한 git commit → PR → main 머지** 경로 사용. CI가 `tag=re` 감지 시 Lokalise ko 자동 덮어쓰기 + 번역팀 Slack 알림. 공식 경로는 "일상 기획 워크플로우 = 3초 수렴 경로"로 단일화 (spec v2 M2 달성, 예외 경로·별도 커맨드 없음).

- **Exit**:
  - pb를 빼고도 클라이언트/서버 빌드 성공
  - pre-receive가 테스트 push 거부 확인
  - **Validator 실제 위반 케이스 테스트 (handoff-v1 A-1 필수)**:
    - 테스트 1: modes.xlsx name 컬럼에 ko 자연어 주입 → CI reject 확인 (F1)
    - 테스트 2: translations.xlsx에 동일 ko 중복 str_id 주입 → CI reject 확인
    - 테스트 3: validator 실패 시 pb artifact 0 생성 확인
  - **F4 bypass 테스트 (handoff-v1 F4 핵심)**: admin 계정으로 pb 커밋 push 시도 → reject 확인, GitHub bypass 설정 OFF 확인
  - `tag=re` 경로 종단 테스트: translations_ko.xlsx 수정 + `tag=re` 기입 → PR 머지 → CI가 Lokalise ko 덮어쓰기 + Changed since last review 필터 진입 + 번역팀 Slack 알림 도착 확인

- **롤백 포인트**: `.gitignore` 되돌리기 + 이전 pb 파일 백업 복원. validator 비활성화 토글. `tag=re` CI 핸들러 off (기존 일상 PR 경로는 계속 동작). BFG는 적용 전이므로 롤백 가능.

### Phase 3 — Excel → Lokalise ko 단방향 cron + **태깅 자동화** (Week 3~4 + D+3 분리)

- **Entry**: Phase 2 완료, pb CI 생성 안정

- **작업 (태깅 자동화, handoff-v1 A-2 핵심 반영)**:
  - **(a) `translations.xlsx`에 `tag` 컬럼 도입**: 스키마 강제 (값 예: new / re / done / hold). datasheet validator에 "tag 컬럼 필수" 추가.
  - **(b) CI 업로드 스크립트가 tag → Lokalise API 호출 1:1 매핑**:
    - `tag=new` → 업로드 + `publish`
    - `tag=re` → 업로드 + `publish` (재업로드)
    - `tag=done` → 태깅 skip
    - `tag=hold` → 업로드 + `unpublish` (게시 해제)
  - **(c) CI가 매 빌드마다 자동 동기화**: Lokalise publish 상태가 Excel tag와 불일치 시 CI가 Lokalise → Excel 방향 쓰기 금지, **Excel → Lokalise 방향으로만 강제 동기화** (Lokalise 상태 = Excel tag로 덮어쓰기)
  - Lambda cron (10분): `translations.xlsx` ko 컬럼 해시 비교 → 변경 시 Lokalise API `delete_rev` → `create_translation`
  - 수동 업로드 UI admin-only

- **D-day 순서 (복합 리스크 분리, handoff-v1 (C) 반영)**:

```
D-day:      Phase 1 프록시 warn → enforce 전환 (API PUT 403 강제)
            + 번역팀 공지 (영/일/중/태/인니만 수정 재확인 — 사례 00:42 상유 확정 규칙 인용)

D+3:        Excel → Lokalise ko cron 첫 실행
            + 태깅 자동화 CI 첫 동기화

D+7:        rev 누적 0건 확인, publish/태그 불일치 0건 확인, Phase 4 킥오프
```

> **D+3 간격 분리 근거**: 프록시 enforce 전환과 cron 첫 실행을 같은 날 묶으면 둘 중 하나 실패 시 양쪽 롤백 필요. D+3 간격이 있으면 프록시 독립 검증 후 cron 추가 → 장애 격리.

- **Exit**:
  - cron 7일 무사고
  - Lokalise ko 값이 Excel과 실시간(10분 이내) 동일 확인
  - 인위 테스트: 웹 ko 수정 시도 → 프록시 403(차단) + (우회 성공 시) cron 10분 내 복귀(탐지) 이중 확인
  - **태깅 자동화 인위 테스트**: `tag=hold`로 설정된 키가 Lokalise에서 `unpublish` 상태 확인, `tag=new`가 `publish` 상태 확인 (03-11 재현 차단)

- **롤백 포인트**: cron Lambda 비활성화 → Phase 1+2 상태로 복귀. 태깅 자동화 off (수동 운영 회귀). 프록시는 유지.

### Phase 4 — cos-vng 프로젝트 생성 완료 + VNG 단방향 반영 (Week 4~5)

- **Entry**: Phase 3 완료, `cos-vng` 프로젝트 생성 완료 (Phase 0~3 기간에 병행 준비)

- **작업**:
  - Lokalise `cos-main` / `cos-vng` 2개 프로젝트 공식 가동
  - VNG 권한을 `cos-vng`만 부여 (이미 Phase 0에서 `cos-main` 쓰기는 0)
  - 메인 → VNG 단방향 반영 cron (ko/en 한정, VNG → 메인 방향 없음)
  - Phase 0의 Slack 대리 입력 창구 **폐쇄** (VNG가 `cos-vng`에서 자체 작업 재개)
  - VNG 자체 프로젝트에도 Phase 1~3의 프록시/validator/태깅 자동화 복제 적용

- **Exit**:
  - VNG가 `cos-vng`에서만 편집 가능 확인
  - 메인의 id/vi 필드에 VNG 수정값 반영 0건 확인 (7일)
  - `cos-vng`에도 프록시·validator·태깅 자동화 복제 완료

- **롤백 포인트**: VNG 계정에 `cos-main` 권한 임시 복원 (Phase 0 복원 스크립트 재사용). 단방향 cron off. Slack 창구 재개.

### Phase 5 — 고정 제약 재검토 (Week 5~6+, 선택)

- **Entry**: Phase 1~4 전부 안정화 (D+7 무사고)

- **작업 (선택지)**:
  - (a) Lokalise 구독 유지 여부 재평가 (6개월 리뷰)
  - (b) 후보 E(Google Sheet) / F(DB) 부분 도입 PoC
  - (c) 번역팀 워크벤치 후보 B PoC (Lokalise 보완용)
  - (d) 장기 실패 모드 대응: translations.xlsx 분할(6개월) / Lokalise API v4 호환 레이어(12개월) / tenant 모델(24개월)

- **Exit**: 차기 iteration(v3) Planner로 이관

- **롤백 포인트**: Phase 5는 PoC이므로 언제든 중단. Phase 4 구조는 계속 동작.

### 전체 일정

| Phase | 주차 | 핵심 산출 | 롤백 지점 |
|-------|------|----------|----------|
| 0 | W0 | 측정 + **VNG cos-main 쓰기 권한 0 + Slack 대리창구 + cos-vng 생성 킥오프** | VNG 권한 복원 스크립트 |
| 1 | W1~2 | API 프록시 + 역할 강등 + **IP allowlist + fail-close** | 프록시 off + 역할 복원 |
| 2 | W2~3 | **Validator 3종 + pb gitignore + CI pb + `tag=re` 일상 PR 경로 통합** | `.gitignore` 되돌리기 |
| 3 | W3~4 (D+3 분리) | 단방향 ko cron + **태깅 자동화 tag 컬럼** | cron off |
| 4 | W4~5 | cos-vng 완성 + VNG 단방향 cron | VNG 권한 복원 |
| 5 | W5~6+ | 재검토 PoC | PoC 중단 |

총 4~6주 개발 공수 내 소화 가능 (A + D 결합).

---

## Step 7.5 — DoD-1 일관성 검증표

> contract v2 DoD-1: 시뮬레이션 표의 "차단" 근거가 Step 7 본문 작업 목록·Entry/Exit Criteria에 실재하는지 줄 단위 매핑.

| 편법 | 차단 주장 | Step 7 본문 근거 줄 |
|------|---------|-------------------|
| E1 프록시 403 | A 프록시 | Phase 1 작업 "`target_language=ko` PUT/PATCH 403 리젝" + Exit "웹 ko 필드 편집 버튼 비활성 확인" |
| E1 10분 cron | D cron | Phase 3 작업 "Lambda cron(10분) xlsx ko 해시 비교 → delete_rev + create_translation" + Exit "ko 실시간 10분 이내 동일" |
| E2 대표키 병합 | `differentiate_by_file` 고정 | Phase 3 작업 "CI 업로드 스크립트 `differentiate_by_file=true`" + Phase 2 validator (b) "ko 중복값 unique" |
| E3 pb 커밋 | `.gitignore` + pre-receive | Phase 2 작업 "`.gitignore`에 `protobuf/*.pb`" + "서버측 pre-receive hook: protobuf/ diff push 거부" |
| E4 git 커밋 누락 | CI only | Phase 2 작업 "CI `build-pb` 워크플로 추가" + Exit "pb를 빼고도 빌드 성공" |
| E5 VNG 역류 | Phase 0 권한 회수 | Phase 0 작업 "VNG 계정 `cos-main` 쓰기 권한 회수 스크립트" + Exit "VNG 쓰기 권한 0 확인" |
| F1 xlsx 이중 소스 | validator (a) | Phase 2 작업 "Validator (a) translations.xlsx 외 xlsx ko 금지" + Exit "modes.xlsx ko 주입 → CI reject" |
| F2 개인 API 토큰 | 토큰 금지 + IP allowlist | Phase 1 작업 "`translator_nonko` 이하 API 토큰 발급 권한 제거" + "Lokalise API IP allowlist 활성화" + Exit "외부 IP API 호출 거부 확인" |
| F4 pre-receive bypass | 서버 hook + GitHub bypass OFF | Phase 2 작업 "서버측 pre-receive hook" + "GitHub repo admin bypass OFF 설정" + Exit "admin push reject 확인" |
| 태깅 자동화 (03-11) | tag 컬럼 + 1:1 매핑 | Phase 3 작업 (a)(b)(c) "tag 컬럼 스키마 강제 + Lokalise API publish/unpublish 1:1 매핑" + Exit "tag=hold → unpublish 확인" |
| M2 3초 수렴 | 일상 PR 경로 통합 | Phase 2 작업 "translations_ko.xlsx ko 수정 + `tag=re` → 일상 PR 머지 → CI가 Lokalise ko 자동 덮어쓰기 + 번역팀 알림" + Exit "`tag=re` 경로 종단 테스트 (Lokalise 덮어쓰기 + Changed since last review 필터 진입 확인)" |

→ 모든 "차단" 주장이 Step 7 본문의 실재 줄에 매핑됨. DoD-1 충족.

---

## Step 8 — 5건 사례 시뮬레이션 (주차 단위 명시)

| 사례 | 재현 시도 | 차단 Phase | 주차 | 등급 |
|------|----------|-----------|------|------|
| **2026-02-05** Modes^1303 이중 소스 (modes.xlsx vs translations.xlsx) | 기획자가 modes.xlsx `name` 컬럼에 ko 자연어 주입 | **Phase 2 Exit** (validator (a) reject) | **Week 2~3 종료 시점** | 차단 (0초, datasheet 변환 거부) |
| **2026-02-20** VNG 대표키 병합 중복 등록 | VNG가 `cos-main`에 인니/베트남어 신규 업로드 → 병합 실수 | **Phase 0 Exit** (VNG `cos-main` 쓰기 권한 0) | **Week 0 종료 시점** | 차단 (0초, Phase 0 이후 VNG는 Slack 창구로 대리 입력 → 기획팀이 `differentiate_by_file=true` 자동 적용) |
| **2026-03-07** skill_description 잔여물 (git 커밋 누락 + 로컬 pb 잔여) | 기획자가 로컬 datasheet 실행 → pb만 수정 후 커밋 누락 | **Phase 2 Exit** (pb `.gitignore` + pre-receive reject) | **Week 2~3 종료 시점** | 차단 (0초, pb 커밋 자체 거부) |
| **2026-03-11** 303건 태깅 누락 (Lokalise publish 상태 미반영) | PM이 애플스토어 검수용 303건을 업로드만 하고 태깅 누락 | **Phase 3 Exit** (tag 컬럼 + 1:1 매핑 + 매 빌드 자동 동기화) | **Week 3~4 종료 시점 + D+3** | 차단 (0초, Excel `tag=new` 없으면 업로드 안 됨, 있으면 publish 자동) |
| **2026-04-17** rev 누적 복합 (Lokalise 웹 ko 수정 + Excel 미갱신 + rev 누적) | 지희가 Lokalise 웹에서 ko `못했어~` 수정 | **Phase 1 Exit** (프록시 403 첫 방어선) + Phase 3 (cron 이중 방어선) | **Week 1~2 종료 시점** | 차단 (0초, 프록시가 PUT/PATCH 거부) |

**전체 차단률**: 5/5 (탐지 0, 통과 0)

**각 Phase Exit 후 재현 가능성**:
- Phase 0 Exit 후 (W0): E5(VNG 역류) 차단
- Phase 1 Exit 후 (W2): + E1(Lokalise 웹 ko), F2(개인 토큰) 차단 → 04-17형 재현 불가
- Phase 2 Exit 후 (W3): + F1(xlsx 이중), E3/E4(pb 잔여), F4(bypass), M2(3초 수렴) 달성 → 02-05, 03-07형 재현 불가
- Phase 3 Exit 후 (W4 + D+3): + E2(병합 옵션), 03-11형 태깅 자동화 → 03-11, 02-20 완전 차단
- Phase 4 Exit 후 (W5): + cos-vng 프로젝트 완성 → E5 장기 구조 완결

---

## 고정 제약 6종 × 추천안(A+D) 준수 테이블

| 고정 제약 | 준수 여부 | 근거 |
|----------|----------|------|
| Lokalise 유료 구독 잔여 | O | Phase 1~4 모두 Lokalise 유지, 구독 해지 없음 |
| VNG 법인 Lokalise 직접 편집 권한 | O | `cos-vng` 프로젝트에서 VNG 자체 편집 유지 (Phase 4 완성), `cos-main` 쓰기만 회수 |
| Protobuf 바이너리 소비 | O | `.pb` CI 생성 + 런타임 소비 동일 |
| 기획팀 Excel 친숙도 | O | `translations.xlsx`만 쓰기 소스, Excel UI 변경 없음 |
| 번역팀 Lokalise UI 의존 | O | Lokalise 웹 UI 유지, ko 필드만 비활성, 타언어 UX 동일 |
| 개발 리소스 1~2명 × 4~6주 | O | Phase 0~4 총 5주, 1~2명 (프록시 Lambda 1주 + 권한 재설계 1주 + validator 0.5주 + `tag=re` CI 핸들러 0.5주 + cron 1주 + 태깅 자동화 1주 = 5주) |

→ 6/6 준수.

---

## 부록 1 — 프록시 Lambda Fail-Close SOP (1페이지)

> review-v1 치명 5 + handoff-v1 (C) 필수 반영

### 기본 원칙

- **Fail-close**: Lambda 장애·레이턴시 timeout·rate limit 초과·응답 503 시 **Lokalise API 호출 전면 거부**.
- 근거: fail-open은 편법 경로(F2) 부활, fail-close는 번역팀 타언어 작업 일시 중단만 발생.
- 번역팀 타언어 작업도 프록시를 경유하는가? → **프록시는 ko 쓰기 요청만 검사**. 타언어 PUT/PATCH는 통과(`target_language ≠ ko`). 즉 fail-close는 ko 쓰기에 대해서만 "거부(차단)" 유지, 타언어는 정상.
- 단, **프록시 자체가 다운**이면 Lokalise API 전체가 IP allowlist로 막혀 있어 타언어도 거부됨. 이 경우 **긴급 bypass**는 아래 SOP 참조.

### 장애 시나리오별 대응

| 시나리오 | 증상 | 대응 |
|---------|------|------|
| Lambda 콜드 스타트 지연 | 첫 요청 3~5초 지연 | 무조치 (정상 범위) |
| Lambda timeout (>30초) | API 호출 503 | fail-close 유지, 번역팀 대기 안내 |
| Lambda 장애 (함수 크래시) | 전체 503 | CloudWatch 알람 → `#l10n-ops` Slack 자동 알림 → on-call 엔지니어 5분 내 Lambda 재기동 |
| Lokalise 쪽 장애 | 프록시는 정상, Lokalise 503 | 프록시는 그대로 passthrough, 번역팀 대기 |
| IP allowlist 실수 블록 | 프록시 EIP 교체 시 누락 | Phase 1 Exit에 "allowlist EIP 기록 필수", EIP 변경 시 SRE 체크리스트 |

### 긴급 bypass 절차 (Phase 1 이후 1회성)

1. 사건 Slack 스레드 개설 (`#l10n-incident`)
2. PM 2인 + dev 리드 **3인 동의** 확인
3. AWS 콘솔에서 IP allowlist 임시 해제 (5분 한정)
4. 번역팀 긴급 작업 수행
5. 5분 후 allowlist 자동 재적용 (Lambda 스케줄 트리거)
6. 사후 리포트 24시간 내 `#l10n-ops` 공유

> bypass는 규율 의존이 아니라 **IaC(Lambda 스케줄 자동 재적용)로 강제**. 사람이 재적용을 잊어도 5분 후 자동 복귀.

### 운영 owner

- **Primary**: 인프라팀 (AWS Lambda 계정 owner)
- **Secondary**: 백엔드 dev팀 (Lambda 함수 소스 owner)
- 이중 on-call, 월 1회 장애 drill 수행

---

## 부록 2 — 장기 실패 모드 예방 (6/12/24개월)

### 6개월 — translations.xlsx 거대화로 편집 충돌

- 예방: Phase 5 (d) "translations.xlsx 도메인별 분할 + datasheet 논리 통합" PoC 준비
- 현 구조 유지 시 임계점: str_id 10,000건 / 동시 편집자 4명 이상 시 merge conflict 주간 빈발

### 12개월 — Lokalise API v3 → v4 호환성 단절

- 예방: Phase 5 (b)(c) PoC로 Google Sheet / 자체 워크벤치 비상 스위치 상시 빌드 가능 상태
- 프록시 Lambda가 추상화 레이어 역할 — API 계약 변경 시 프록시만 수정하면 내부 사용자 영향 최소

### 24개월 — VNG 외 추가 법인 (싱가포르/유럽) 확장

- 예방: Phase 5에서 tenant 모델(F 후보 발상)을 `translations.xlsx` 스키마에 도입. `tenant` 컬럼 필터로 법인 추가 = 컬럼 값 추가
- `cos-main` / `cos-vng` 구조에서 `cos-*` N개로 증식되기 전, 논리적 tenant로 전환

---

## 요약

- **추천**: A 프록시 기본(첫 방어선 0초 차단) + D cron 보강(이중 방어선 복구)
- **5건 사례**: 5/5 차단 (Phase 0~3 Exit 이후 전부 구조적 차단, 탐지 0, 통과 0)
- **8편법 경로**: 8/8 차단 (E1~E5 + F1/F2/F4 모두 0초)
- **고정 제약**: 6/6 준수 (4~6주 내 1~2명 소화)
- **DoD**: 5항목 (contract v2) + Step 7 본문 일관성 검증 + Phase 0 VNG 회수 + 태깅 자동화 + 10분 창 재분류 + validator 3종 전부 반영

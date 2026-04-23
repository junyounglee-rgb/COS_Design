# Self-Check v2

> 작성: l10n-pipeline-architect
> 대상: `redesign-v2.md`
> 기준: `spec.md`(v2), `iteration-contract-v2.md`, `handoff-v1.md` "Architect에게" / "자가 점검 시 반드시 확인"
> 기준일: 2026-04-18

---

## 1. Planner 규약 준수

- [x] **spec.md v2의 메타-원인 M1/M2를 재작성하지 않고 인용·참조만 함**
  - 근거: `redesign-v2.md`는 M1/M2를 재정의·재분해하지 않고 "편법 차단표"·"시뮬레이션" 섹션에서 spec.md L117~123(사례 매핑)을 인용만 함.
- [x] **P3 "0초 절"을 준수하는 추천안 구조**
  - 근거: 주력 추천 "A 프록시 기본(0초 차단) + D cron 보강(탐지 복구)". D 단독을 "차단"이라 명명하지 않고 Step 5-1 매트릭스에서 **탐지(10분)**로 분류.
- [x] **제약 지도 "네트워크 경계"(IP allowlist)를 F2 대응에 반영**
  - 근거: Step 4 후보 A "Lokalise API IP allowlist: 프록시 Lambda EIP만 등록" + Phase 1 작업 목록 "Lokalise API IP allowlist 활성화" + Phase 1 Exit "외부 IP API 호출 거부 확인".
- [x] **M2 각주 준수 — "수동 단계 0"만으로 만족 주장 안 함**
  - 근거: Step 7 Phase 2 "Slack `/ko-typo` 커맨드 → 자동 PR 30초 SLA → CI 머지. 공식 경로 **종단 시간** 3초 수렴" 명시. Exit에 "종단 시간 측정 < 3초" 테스트 포함.

---

## 2. iteration-contract v2 DoD 준수

- [x] **DoD-1: Step 7 본문과 시뮬레이션 표 일관**
  - 근거: Step 7.5 "DoD-1 일관성 검증표"에서 각 차단 근거 phrase를 Step 7 본문의 Phase 작업 목록/Entry/Exit 줄에 매핑. Validator 3종이 Phase 2 본문에 실재.
- [x] **DoD-2: 편법 경로 8종 × 후보 매트릭스 완성 (6×8 = 48셀)**
  - 근거: Step 5-1 매트릭스에 E1~E5 + F1/F2/F4 전 8종 × 6후보(A~F) = 48셀.
- [x] **DoD-3: 10분 이상 자동 복구를 "탐지"로 표기, 0초만 "차단"**
  - 근거: 후보 D 편법 차단표에서 E1을 **탐지(10분 cron)**로 명시. Step 5-1 매트릭스에서도 D열 E1이 탐지. 주력 추천 A+D 결합에서 A 프록시만 차단, D cron은 "이중 방어선(복구)".
- [x] **DoD-4: 추천안에 `tag` 컬럼 + Lokalise publish/unpublish 매핑**
  - 근거: Phase 3 작업 (a)(b)(c) — `tag` 컬럼 스키마 강제 + tag 값별 Lokalise API 호출 1:1 매핑(new→publish, re→publish, done→skip, hold→unpublish) + 매 빌드 자동 동기화 (Excel→Lokalise 방향만).
- [x] **DoD-5: Phase 0 Exit에 VNG 권한 회수 포함**
  - 근거: Phase 0 Exit "**VNG 계정의 `cos-main` 쓰기 권한 0 확인** (Lokalise admin 로그로 검증) — DoD-5 필수". 과도기 Slack 창구 명시.

---

## 3. handoff-v1 "자가 점검 시 반드시 확인"

- [x] **Step 7 본문 작업 목록에 없는 차단 메커니즘을 시뮬레이션 표에서 주장하지 않음**
  - 근거: Step 7.5 검증표에서 11건 전부 Step 7 본문 줄에 매핑 확인. v1 치명 약점 1(validator 없는데 주장)과 동일 결함 재발 없음.
- [x] **"자동 복구"를 "차단"으로 재분류하지 않음 (10분 창 = 탐지)**
  - 근거: 후보 D E1 = "탐지(10분 cron)" 명시. v1의 "차단(자동 복구)" 작명 폐기.
- [x] **Planner 정의를 자의적으로 축소하지 않음 (특히 M2 "3초 수렴")**
  - 근거: M2를 "수동 단계 0"이 아니라 **종단 시간 3초 수렴**으로 해석. Phase 2 Slack 커맨드 Exit에 "종단 시간 측정 < 3초" 테스트.
- [x] **5건 사례가 Phase N Exit 이후 차단되는지 주차 단위로 명시**
  - 근거: Step 8 시뮬레이션 표 "차단 Phase" + "주차" 컬럼 — 02-05(W2~3), 02-20(W0), 03-07(W2~3), 03-11(W3~4 + D+3), 04-17(W1~2) 명시.

---

## 4. handoff-v1 "Architect에게" 치명 약점 해소

### A-1. CI validator 3종 Phase 2 본문 정식 추가
- [x] **(a) translations.xlsx 외 xlsx ko 자연어 컬럼 금지 (datasheet 변환 거부)**
  - 근거: Phase 2 작업 "Validator (a)" + pre-commit hook 동일 검사.
- [x] **(b) translations.xlsx ko 중복값 검사 (unique + warn-then-fail)**
  - 근거: Phase 2 작업 "Validator (b) ko 중복값 검사 (unique constraint, warn-then-fail)".
- [x] **(c) validator 실패 시 CI 전면 중단 (pb artifact 미생성)**
  - 근거: Phase 2 작업 "Validator (c) CI 전면 중단, pb artifact 미생성".
- [x] **Phase 2 Exit에 실제 위반 케이스 1건 → CI reject 테스트 포함**
  - 근거: Phase 2 Exit "테스트 1: modes.xlsx name 컬럼 ko 주입 → CI reject 확인" / "테스트 2: ko 중복 주입 → reject" / "테스트 3: validator 실패 시 pb 0 생성".

### A-2. Phase 3 태깅 자동화 구조 추가
- [x] **(a) `tag` 컬럼(new/re/done/hold) 도입 및 스키마 강제**
  - 근거: Phase 3 작업 "(a) `translations.xlsx`에 `tag` 컬럼 도입 — 스키마 강제, 값 예 new/re/done/hold".
- [x] **(b) CI 업로드 스크립트가 tag → API publish/unpublish 호출 1:1 매핑**
  - 근거: Phase 3 작업 "(b) CI 업로드 스크립트 tag → Lokalise API 1:1 매핑" 표 포함.
- [x] **(c) Lokalise publish 상태-Excel tag 불일치 시 CI 매 빌드 자동 동기화 (0초 드리프트)**
  - 근거: Phase 3 작업 "(c) CI가 매 빌드마다 자동 동기화, Excel→Lokalise 방향만 강제".

### A-3. VNG 분리 Phase 0 앞당김
- [x] **(a) Phase 4 cos-vng 프로젝트 생성은 리드타임 유지**
  - 근거: Phase 0 작업 "cos-vng 프로젝트 생성 착수 (리드타임 2~4주)" + Phase 4 "cos-vng 프로젝트 공식 가동".
- [x] **(b) VNG cos-main 쓰기 권한 회수는 Phase 0 Exit로 이관**
  - 근거: Phase 0 Exit "VNG 계정 `cos-main` 쓰기 권한 0 확인 — DoD-5 필수".
- [x] **(c) 과도기 Slack 창구 → 기획팀 대리 입력**
  - 근거: Phase 0 작업 "과도기 Slack 창구 개설: `#l10n-vng-requests` 채널, 기획팀 대리 입력 담당자 지정".

---

## 5. 편법 F1~F5 구조 설계 반영

- [x] **F1 xlsx 이중 소스 → Phase 2 validator (a)**
  - 근거: Step 5-1 매트릭스 A열 F1 = "차단(datasheet validator)" + Phase 2 Validator (a).
- [x] **F2 개인 API 토큰 → Phase 1 토큰 발급 금지 + IP allowlist**
  - 근거: Phase 1 작업 "`translator_nonko` 이하 역할에서 API 토큰 발급 권한 제거" + "Lokalise API IP allowlist 활성화: 프록시 Lambda EIP만" + Exit "외부 IP API 호출 거부 확인".
- [x] **F3 Excel+Lokalise 동시 수정 → 배포 파이프라인이 Lokalise에서 ko 당기는 경로 제거**
  - 근거: Step 4 후보 A 구조도 "배포 파이프라인이 Lokalise에서 ko를 pull하는 코드 제거. ko는 translations.xlsx → datasheet → pb만 흐름. Lokalise ko는 read-only mirror".
- [x] **F4 pre-receive bypass → Phase 2 Exit admin push reject 테스트 + GitHub bypass OFF**
  - 근거: Phase 2 작업 "GitHub repo admin bypass OFF 설정" + Exit "admin 계정 pb 커밋 push → reject 확인".
- [x] **F5 VNG 잔존 권한 → Phase 0 권한 회수 (A-3 통합)**
  - 근거: Phase 0 Exit와 동일.

---

## 6. 추가 설계 이슈 3건

- [x] **프록시 Lambda fail-close 명시 + SOP**
  - 근거: Phase 1 작업 "프록시 fail-close 모드 명시" + 부록 1 "프록시 Lambda Fail-Close SOP (1페이지)" — 장애 시나리오별 대응, 긴급 bypass 절차, owner.
- [x] **Phase 3 D-day 프록시 enforce와 cron 첫 실행 D+3 분리**
  - 근거: Phase 3 "D-day 순서" — D-day 프록시 enforce, D+3 cron 첫 실행 + 태깅 자동화 첫 동기화, D+7 Phase 4 킥오프.
- [x] **Slack 커맨드 "ko 오타 신고 → 자동 PR" Phase 2 추가**
  - 근거: Phase 2 작업 "M2 Slack 커맨드 추가: `/ko-typo <str_id> <수정후>` → 자동 PR 30초 SLA" + Exit "종단 시간 < 3초 + 자동 PR 생성 확인".

---

## 7. 추천안 재정렬

- [x] **추천안이 "A 프록시 기본 + D cron 보강" 순서로 명시**
  - 근거: Step 6 주력 추천안 제목 "A 프록시 기본 + D cron 보강". v1의 "D + A 흡수" 역전 명시.
- [x] **이유 서술에 "첫 방어선 0초 / 이중 방어선 복구" 구조 설명**
  - 근거: Step 6 결합 구조 다이어그램 "첫 방어선: A 프록시 Lambda — 원복 지연 0초 → 차단" / "이중 방어선: D 10분 cron — 원복 지연 ≤ 10분 → 탐지(복구)".

---

## 8. 고정 제약 6종 × 추천안 준수 테이블

- [x] **Lokalise 구독 O**
- [x] **VNG 권한 O** (cos-main 쓰기만 회수, cos-vng 유지, UI 접근 유지)
- [x] **Protobuf O**
- [x] **Excel 친숙도 O** (translations.xlsx 유지)
- [x] **번역팀 UI O** (Lokalise 웹, ko 필드만 비활성)
- [x] **개발 4~6주 O** (총 5주, 1~2명)

→ `redesign-v2.md` "고정 제약 6종 × 추천안(A+D) 준수 테이블" 6/6.

---

## 9. 5건 사례 시뮬레이션

- [x] **02-05 차단** (Phase 2 Exit, W2~3, validator (a))
- [x] **02-20 차단** (Phase 0 Exit, W0, VNG 권한 회수 + Phase 3 `differentiate_by_file` 고정)
- [x] **03-07 차단** (Phase 2 Exit, W2~3, pb `.gitignore` + pre-receive)
- [x] **03-11 차단** (Phase 3 Exit, W3~4+D+3, tag 컬럼 + publish/unpublish 1:1 매핑)
- [x] **04-17 차단** (Phase 1 Exit, W1~2, 프록시 403 첫 방어선)

→ **5/5 차단** (탐지 0, 통과 0) — 기준 B(50/60 + 5건 전차단) 자격 확보.

---

## 10. 규율 의존 단어 금지

- [x] **"교육" 차단 메커니즘으로 0회 사용**
- [x] **"주의" 차단 메커니즘으로 0회 사용**
- [x] **"혼내기" 차단 메커니즘으로 0회 사용**
- [x] **"합의" 차단 메커니즘으로 0회 사용** (VNG 협의는 "과도기 Slack 창구 합의"이나 이는 "운영 전환 합의"이지 차단 메커니즘이 아님 — 차단은 권한 회수 스크립트가 수행)
- [x] **"공지" 차단 메커니즘으로 0회 사용** (Phase 3 D-day 작업에 "번역팀 공지"는 "영/일/중/태/인니만 수정 재확인"으로 차단 메커니즘이 아니라 운영 안내. 실제 차단은 프록시 403)
- [x] **"주기적 리뷰" 차단 메커니즘으로 0회 사용** (Phase 5 "6개월 리뷰"는 고정 제약 재검토이지 차단 메커니즘 아님)

**사례 인용은 허용**: 사례 분석의 마재의 "혼내야 한다" 발언 인용은 "규율 의존 접근의 한계" 맥락이며 차단 메커니즘으로 쓰지 않음.

---

## 11. v1 → v2 개선 요약

| 항목 | v1 결함 | v2 해소 | 근거 줄 |
|------|---------|---------|--------|
| validator 3종 부재 | 시뮬레이션 표에만 등장 | Phase 2 본문 Entry/Exit 편입 + 3종 테스트 | redesign-v2 Phase 2 |
| 태깅 자동화 부재 | `differentiate_by_file` 한 줄 | `tag` 컬럼 + 1:1 매핑 + 매 빌드 동기화 | redesign-v2 Phase 3 (a)(b)(c) |
| VNG 분리 Phase 4 지연 | E5 재현 창 4주 | Phase 0 Exit로 이관 | redesign-v2 Phase 0 Exit |
| 10분 창 "차단" 오분류 | 자기 모순 | 탐지(10분)로 재분류 | redesign-v2 후보 D E1 |
| M2 "3초 수렴" 포기 | "수동 단계 0" 축소 | Slack 커맨드 종단 3초 | redesign-v2 Phase 2 M2 |
| 프록시 fail-close 미정의 | 단일장애점 | fail-close + SOP 1페이지 | redesign-v2 Phase 1 + 부록 1 |
| Phase 3 D-day 복합 리스크 | enforce+cron 동일일 | D+3 간격 분리 | redesign-v2 Phase 3 D-day |
| 추천안 순서 | D 기본 + A 흡수 | A 기본 + D 보강 | redesign-v2 Step 6 |
| 편법 매트릭스 | 5종 × 5후보 | 8종 × 6후보 = 48셀 | redesign-v2 Step 5-1 |
| 점수 스케일 | 30점 | 60점 | redesign-v2 Step 5-2 |

---

## 12. 최종 자가 점수 (60점 기준)

| 후보 | /60 |
|------|-----|
| **A 프록시+권한강등** | **58** |
| D 단독 | 53 |
| F DB | 38 |
| E Google Sheet | 35 |
| C Git PR | 33 |
| B 자체 워크벤치 | 28 |

**주력 A (58/60)** — 합격선 55/60 초과. 추가로 **D 보강 시 5건 전차단 + 8편법 전차단** 달성 → 기준 A·B 동시 만족.

---

## 13. 최종 체크리스트 요약

| 범주 | 항목 수 | 통과 |
|------|---------|------|
| 1. Planner 규약 | 4 | 4/4 |
| 2. contract v2 DoD | 5 | 5/5 |
| 3. handoff "자가 점검" | 4 | 4/4 |
| 4. 치명 약점 해소 | 9 (A-1~3 세부) | 9/9 |
| 5. 편법 F1~F5 | 5 | 5/5 |
| 6. 추가 설계 이슈 | 3 | 3/3 |
| 7. 추천안 재정렬 | 2 | 2/2 |
| 8. 고정 제약 6종 | 6 | 6/6 |
| 9. 5건 사례 | 5 | 5/5 |
| 10. 규율 단어 금지 | 6 | 6/6 |
| **합계** | **49** | **49/49** |

→ Acceptance Criteria 전부 충족. Critic 평가 투입 준비 완료.

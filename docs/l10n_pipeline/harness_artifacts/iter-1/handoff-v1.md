# Handoff v1 → v2

> 작성: l10n-pipeline-critic
> 기준일: 2026-04-18
> 입력: `review-v1.md`

---

## 수렴 판단

- 이번 점수: **40/60**
- 이전 점수: 없음 (첫 회)
- 상승폭: 해당 없음
- 수렴 여부: [ ] 수렴 (재호출 불필요) / [x] **미수렴 (재호출 필요)**

**미수렴 사유**:
- 합격선 55/60 미달 (40점)
- 대안 기준(50점 + 5건 전부 차단) 두 조건 모두 미달 — 2건 확정 재현, 2건 부분 재현, 1건만 확정 차단
- 특히 02-05·03-11 사례는 "탐지조차 없음" 상태 → iteration-contract L67 "탐지 분류 시 합격 불가" 기준에서 실질 탈락

---

## Planner에게

### spec.md에서 바꿀 항목

1. **원칙 P3 "Block, Don't Warn"의 정의 강화**
   - 현 정의(L58~60)는 "경고가 아닌 거부"만 언급. Architect가 "자동 복구"를 "차단"으로 재해석하는 여지를 남김.
   - 변경안: 원칙 P3에 다음 절 추가 — "**차단의 시간 창(window)은 0초여야 한다. 편법 행위와 원복 사이 임의 N분 지연이 있는 설계는 '탐지+복구'이며 본 원칙에서 차단으로 분류하지 않는다.**"

2. **변경 가능 항목 L40에 "Lokalise API를 프록시 없이 호출 가능한 IP 범위"를 명시**
   - 현 제약 지도는 "권한"만 다루고 "네트워크 경계"를 누락. 편법 F2(개인 토큰) 대응에 필수.

3. **메타-원인 M2 해석 범위 명시**
   - Architect가 M2를 "수동 단계 0"으로 자의 축소하지 않도록 spec.md L55~56에 각주 추가: "3초 수렴은 공식 경로의 **종단 시간**을 뜻하며, '수동 단계 수'가 아니다. 수동 단계가 0이어도 비동기 대기가 10분이면 미충족."

### iteration-contract에 추가할 Definition of Done

1. **Step 7 본문과 시뮬레이션 표의 일관성 검증**
   - 추가 항목: "추천안의 5건 사례 차단 근거가 Step 7 Phase 0~5 **작업 목록**에 실재해야 한다 (Phase Entry/Exit 항목으로 구현 가능 수준)."
   - 의도: redesign-v1의 "CI validator가 거부" 주장이 Phase 2 작업 목록에 없는 현재 상황 재발 방지.

2. **편법 경로 최소 개수 8종으로 확장**
   - 현 5종(E1~E5)에서 8종으로 확장: 기존 5종 + F1(xlsx 이중 소스) + F2(개인 API 토큰) + F4(pre-receive bypass).
   - 의도: Critic이 5종 외 추가 탐지한 편법을 v2에서 선제 차단.

3. **10분 이상의 "자동 복구 창"은 탐지로 분류**
   - 현 contract L15 "차단/탐지/통과" 정의에 각주 추가: "원복 지연이 1분 이상이면 탐지, 0초이면 차단."
   - 의도: 후보 D의 "10분 cron" 모호함 제거.

4. **태깅 자동화 필수 포함**
   - 추가 항목: "추천안은 Lokalise publish/태그 상태를 translations.xlsx의 `tag` 컬럼으로 원격 결정짓는 구조를 포함해야 한다 (사례 03-11 재현 방지)."

5. **VNG 권한 회수 시점 명시**
   - 추가 항목: "추천안의 Phase 0 Exit에 VNG 계정의 cos-main 쓰기 권한 0 확인이 포함되어야 한다."

---

## Architect에게

### 반드시 해소할 약점 (review의 치명적 약점 top 3)

1. **CI validator 3종을 Step 7 Phase 2 본문에 정식 추가** (review 치명 1)
   - (a) translations.xlsx 외 xlsx의 ko 텍스트 컬럼 금지 — datasheet 변환 또는 pre-commit hook으로 reject
   - (b) translations.xlsx ko 컬럼 중복값 검사 (unique constraint + warn-then-fail)
   - (c) validator 실패 시 CI 파이프라인 전면 중단 (pb artifact 미생성)
   - **금지 사항**: "시뮬레이션 표에만 등장"시키지 말고 Phase 작업 목록에 Entry/Exit Criteria로 포함.

2. **Phase 3에 태깅 자동화 구조 추가** (review 치명 2)
   - (a) translations.xlsx에 `tag` 컬럼(new/re/done/hold) 도입 및 스키마 강제
   - (b) CI 업로드 스크립트가 tag 값을 Lokalise API publish/unpublish 호출에 1:1 매핑
   - (c) Lokalise의 publish 상태가 Excel tag와 불일치 시 CI가 매 빌드마다 자동 동기화
   - **금지 사항**: "번역팀이 수동으로 체크"류 규율 의존.

3. **VNG 분리를 Phase 0(권한 강등)로 앞당기기** (review 치명 3)
   - Phase 4의 "cos-vng 프로젝트 생성"은 리드타임(2~4주) 탓에 Week 4~5 유지 가능.
   - 그러나 VNG의 cos-main 쓰기 권한 회수는 Phase 0 Exit Criteria로 이관 필수.
   - 과도기 동안 VNG 요청은 Slack 창구로 기획팀 대리 입력 (비용 있으나 E5 재현 창 제거).

### 편법 경로 중 구조 설계에 반영해야 할 것

1. **편법 F1 (xlsx 이중 소스)** — 치명 약점 1과 동일 해결책으로 통합 차단.

2. **편법 F2 (개인 API 토큰)** — Phase 1 작업에 추가
   - Lokalise 역할 `translator_nonko` 이하는 API 토큰 발급 권한 제거
   - Lokalise API 엔드포인트를 IP allowlist로 제한 (프록시 Lambda IP만 허용)
   - "승인 + 자동 만료"(redesign L52)는 규율 의존이므로 기술적 차단으로 대체

3. **편법 F3 (Excel 커밋 지연 + Lokalise 동시 수정)** — 추천안 구조 변경
   - 런타임 소비 구조에서 ko는 **translations.xlsx → datasheet → pb 경로로만** 흐르도록 강제
   - Lokalise ko 필드는 mirror로만 보존, 배포 파이프라인이 Lokalise에서 ko를 당기는 경로 제거
   - 후보 D의 "Lokalise ko = 자동 덮어쓰기"를 "Lokalise ko = 배포 미참여 mirror"로 격상

4. **편법 F4 (pre-receive bypass)** — Phase 2 Exit Criteria에 추가
   - GitHub repo admin bypass 설정 명시 차단
   - Exit Criteria: "admin 계정으로 pb 커밋 push 시도 → reject 확인" 테스트 1건 포함

5. **편법 F5 (VNG 잔존 권한 남용)** — 치명 약점 3과 동일 해결책으로 통합 차단.

### 추가로 다뤄야 할 설계 이슈 (review에서 추출)

- **프록시 Lambda 단일장애점 fallback**: fail-close 명시 + 장애 시 복구 SOP 1페이지 (review 치명 5)
- **Phase 3 D-day의 복합 전환 리스크**: 프록시 enforce 전환과 cron 첫 실행을 같은 날에 묶지 말고 최소 D+3 간격으로 분리 (review 축 2 근거)
- **M2 "3초 수렴"을 포기하지 않는 최소 구현**: Slack 커맨드 또는 경량 웹 폼으로 "ko 오타 신고 → 자동 PR" 구조. 고정 제약 "Excel 친숙도"와 양립 가능 (review 우선순위 2)

### 자가 점검 시 반드시 확인

- [ ] Step 7 본문 작업 목록에 없는 "차단 메커니즘"을 시뮬레이션 표에서 주장하지 않았는가
- [ ] "자동 복구"를 "차단"으로 재분류하지 않았는가 (10분 창은 탐지)
- [ ] Planner 정의를 자의적으로 축소하지 않았는가 (특히 M2 "3초 수렴")
- [ ] 5건 사례가 각각 "Phase N Exit 이후" 차단되는지 연도가 아닌 주차 단위로 명시했는가

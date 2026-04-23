# Handoff v2

> 발행: l10n-pipeline-critic → 오케스트레이터 / (필요 시) Planner·Architect
> 기준일: 2026-04-18
> 이전: `handoff-v1.md` (40/60 미수렴)

---

## 1. 수렴 판단

| 항목 | 값 |
|------|----|
| 이번 점수 | **52/60** |
| 이전 점수 | 40/60 |
| 상승폭 | **+12** |
| 5건 사례 차단 | 5/5 (탐지 0, 통과 0) |
| 편법 F1~F5 차단 | 5/5 |
| 감점 트리거 누적 | 0점 |
| 수렴 기준 | 합격선 A (55/60) 미달 / **합격선 B (50/60 + 전차단) 충족** |
| 수렴 여부 | **[x] 수렴 (재호출 불필요)** |

### 1.1 수렴 사유

- **합격선 B 3조건 동시 충족**:
  - 총점 52 >= 50
  - 5건 사례 전부 차단 (탐지·통과 0건)
  - 편법 F1~F5 전부 차단
- v1 치명 약점 5건 **전부 해소** (validator 본문 편입, 태깅 자동화, VNG Phase 0 이관, 추천안 재정렬, Fail-Close SOP).
- v1 편법 F1~F5 **전부 구조적 차단** (0초 또는 Phase 0 Exit 이후 0초).
- 감점 트리거 적발 0건 (10분 창 "탐지" 정직 표기, 롤백 포인트 전 Phase 실재, 규율 의존 단어 무등장).

### 1.2 합격선 A 미달 사유 (55/60 미달, -3점)

- **M2 "3초 수렴" 부분 달성** (-2): Slack 커맨드 응답은 3초지만 PR 머지 종단은 30초, 플레이어 반영은 분~시간. spec v2 [M2-a]의 "종단 시간(end-to-end)" 정의가 모호하나 엄격 해석 시 Slack 응답 국한.
- **Phase 0 리드타임 비현실성** (-1): 3~5일 내 VNG 권한 회수 + 측정 + Slack 창구 개설 + cos-vng 킥오프 5종 동시 수행 주장. VNG 법인간 조율 리드타임 미반영.
- **Slack 대리 입력 창구 지속성 모호** (합산 처리): 주 10~15건 × 4주+ 담당자 1명 모델의 주말·야간·휴가 대응 미정의.

합격선 B 경로가 열려 있어 재호출 없이 수렴 처리.

---

## 2. 최종 확정 지시사항 (수렴 시)

### 2.1 산출물 확정

- [ ] `D:\claude_make\docs\l10n_pipeline\harness_artifacts\iter-2\redesign-v2.md` → `redesign_final.md` 사본 생성 (경로: `D:\claude_make\docs\l10n_pipeline\redesign_final.md`)
- [ ] `D:\claude_make\docs\l10n_pipeline\harness_artifacts\iter-2\review-v2.md` → 본 review를 최종 합격 근거로 보관
- [ ] `D:\claude_make\docs\l10n_pipeline\README.md` 갱신 포인트:
  - 상단 배지/상태: "iter-1 40/60 미수렴 → iter-2 52/60 수렴 (합격선 B)"
  - 링크: iter-2 `redesign-v2.md` / `review-v2.md` / `handoff-v2.md`
  - 최종 추천안 요약: "A 프록시 기본 + D cron 보강"

### 2.2 Phase 0 실행 시작 전 준비 사항

- [ ] **VNG 법인 사전 조율** (리드타임 확보 목적): Phase 0 공식 착수 1주 전 VNG PM과 과도기 Slack 창구 합의 선행. Phase 0 기간 3~5일은 권한 회수 스크립트 실행·검증에 한정.
- [ ] **Slack 대리 입력 담당자 지정 + 백업 담당자**: 기획팀 당번제 2인 구성 (주말/야간 대응 포함).
- [ ] **VNG 편집 빈도 사전 측정**: Phase 0 진입 전 7일치 Lokalise admin 로그 확보.
- [ ] **프록시 Lambda 운영 owner 지정**: Primary 인프라팀, Secondary 백엔드 dev팀 (부록 1 L640~643 기준).
- [ ] **`cos-vng` 프로젝트 생성 킥오프**: Phase 0 진입과 동시에 Lokalise 신규 프로젝트 신청 (리드타임 2~4주, Phase 4 전 완료 목표).
- [ ] **Phase 2 Slack 커맨드 `/ko-typo` 스펙 확정**: 종단 시간 정의를 Slack 응답(3초) / PR 머지(30초) / 배포 반영(분 단위) 중 무엇으로 측정할지 PM·dev 리드 합의.

### 2.3 v3(차기 iteration)로 이관할 숙제

Phase 0 실행 중 신규 편법 경로 식별 시 Planner가 차기 iteration에서 다룰 것:

1. **M2 "종단 시간" 정의 확정** — Slack 응답 vs PR 머지 vs 플레이어 반영 중 어느 것을 "3초 수렴" 기준으로 채택할지 spec.md v3에서 명문화.
2. **Phase 0 리드타임 현실화** — Phase -1(사전 VNG 조율) 신설 또는 Phase 0 기간을 1~2주로 확장하는 contract 조정.
3. **Slack 대리 입력 창구 구조화** — 담당자 1명 의존 → 당번제(2인) 또는 자동 폼 + SLA 24시간으로 전환하는 DoD 추가.
4. **장기 실패 모드 선제 대응** — Phase 5 PoC만으로 미뤄둔 3건(translations.xlsx 분할 / Lokalise API v3→v4 / tenant 모델)의 선제 측정 항목을 Phase 0 측정에 포함.

---

## 3. (참고) 재호출 시나리오

본 iteration은 수렴 처리되므로 Planner·Architect 재호출 불필요. 단 Phase 0 실행 중 아래 사건 발생 시 v3 재개:

| 재개 트리거 | 즉시 호출 대상 | 입력 |
|------------|--------------|------|
| Phase 0 Exit(VNG 쓰기 권한 0) 1주 내 미달성 | Planner v3 | Phase 0 리드타임 contract 조정 |
| Phase 1~3 중 신규 편법 경로 발견 (8종 외) | Planner v3 + Architect v3 | 편법 경로 8 → 9+종 확장 |
| Lokalise API v4 배포 조기화 (예정보다 6개월 앞당김) | Architect v3 | 비상 스위치 Phase 5 → Phase 3 상향 |
| Phase 3 D+7까지 rev 누적 > 0건 | Architect v3 | cron 간격 단축 / 프록시 로직 보강 |

---

## 4. 감사 결과 요약

| 범주 | 결과 |
|------|------|
| v1 치명 약점 5건 | 5/5 해소 (validator / 태깅 / VNG Phase 0 / 추천안 재정렬 / Fail-Close) |
| 편법 F1~F5 | 5/5 차단 |
| 5건 사례 재현 | 5/5 차단 (탐지 0, 통과 0) |
| 감점 트리거 | 0건 적발 |
| 고정 제약 6종 | 6/6 준수 |
| DoD-1~5 (contract v2) | 5/5 충족 |
| 합격선 A | 미달 (52 < 55) |
| 합격선 B | 충족 (52 >= 50 + 전차단 + F1~F5 전차단) |

**최종 결론**: iter-2 수렴. Phase 0 실행 착수 가능.

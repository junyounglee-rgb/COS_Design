# L10N Pipeline Redesign — Harness Engineering

> COS 게임의 한국어(ko) 번역 파이프라인 2.5개월간 5건 오염 사고 재발 방지 재설계 프로젝트
> 2026-04-18 Iteration v2 **수렴** (52/60, 합격선 B) → 3-way 비교 문서로 **의사결정 준비 완료**

---

## 현재 상태

| 항목 | 값 |
|------|-----|
| 최종 iteration | **iter-2** (수렴) |
| 총점 | **52/60** (합격선 B 충족: 50/60 + 5건 전부 차단 + 편법 F1~F5 전부 차단) |
| v1 대비 상승폭 | +12 (v1=40 → v2=52) |
| 추천안 | **A 프록시 기본 + D cron 보강** |
| 5건 사례 차단 | 5/5 (탐지 0, 통과 0) |
| 편법 F1~F5 차단 | 5/5 (0초 또는 Phase 0 Exit 이후 0초) |
| 고정 제약 | 6/6 준수 |
| 실행 착수 | Phase 0 준비 단계 (v2 handoff-v2.md §2.2 참조) |

---

## 최종 산출물

| 순서 | 파일 | 역할 |
|------|------|------|
| 🚪 **진입점 (의사결정)** | **[workflow_comparison_3way.md](./workflow_comparison_3way.md)** | **현재 vs Claude v2 A+D vs Google Sheet** 3-way 비교 + 추천 + 구현 체크리스트 |
| 📊 v2 개선 요약 | [workflow_comparison_v2.md](./workflow_comparison_v2.md) | "현상황 → v2 개선 → 개선 효과" 2-way 비교 (보조 자료) |
| 📘 상세 | [redesign_final.md](./redesign_final.md) | 최종 추천안 + Phase 0~5 Entry/Exit/롤백 (iter-2 redesign-v2.md 복사본) |
| 📂 근거 | [case_study_2026-04-17_rev_pollution.md](./case_study_2026-04-17_rev_pollution.md) | 5건 사고 원인 분석 (입력 근거) |
| 🧬 프로토콜 | [harness_protocol.md](./harness_protocol.md) | 3-Agent 하네스 협업 규약 |
| 📐 원본 | [harness_artifacts/](./harness_artifacts/) | Iteration별 산출물 (iter-1, iter-2) |

### 읽는 순서 (첫 방문자)

1. **`workflow_comparison_3way.md`** (10~15분) — 현재 / v2 / Google Sheet 중 **무엇을 선택할지** 의사결정
2. `workflow_comparison_v2.md` (5~10분) — v2 채택 시 현재 대비 6단계로 무엇이 바뀌는지 (보조)
3. `redesign_final.md` Step 7 Phase 0~5 (15분) — 실제 전환 계획
4. `harness_artifacts/iter-2/handoff-v2.md` §2.2 (5분) — Phase 0 착수 전 준비 사항

---

## 최종 추천안 요약

### A 프록시 기본 + D cron 보강

- **A (첫 방어선, 0초 차단)**: Lokalise 권한 강등 + Lambda API 프록시 + IP allowlist
  - Excel `translations.xlsx` ko = 단일 쓰기 원천 (SOT)
  - 배포 파이프라인이 Lokalise ko를 pull하지 않음 (Lokalise ko = read-only mirror)
  - Lokalise API `target_language=ko` PUT/PATCH → 프록시에서 403
  - 개인 API 토큰 발급 권한 제거 + IP allowlist (프록시 Lambda EIP만)

- **D (이중 방어선, ≥1분 탐지 후 복구)**: 10분 cron Excel→Lokalise ko 덮어쓰기
  - 프록시 우회로 생긴 표류를 10분 간격으로 자동 복구
  - 10분 창은 **탐지**로 분류 (spec v2 P3 "0초 절" 준수)

### Phase 0~5 개요

| Phase | 기간 | 핵심 Exit Criteria |
|-------|------|------------------|
| **Phase 0** (W0) | 3~5일 | VNG `cos-main` 쓰기 권한 0 확인 (F5/E5 차단) |
| **Phase 1** (W1~2) | 1~2주 | 프록시 Lambda fail-close + IP allowlist (F2/04-17 차단) |
| **Phase 2** (W2~3) | 1주 | CI validator 3종 + pre-receive hook + `tag=re` 일상 PR 경로 통합 (F1/F4/02-05/03-07 차단) |
| **Phase 3** (W3~4 + D+3) | 1주 + 분리 | `tag` 컬럼 + Lokalise publish/unpublish 1:1 매핑 (03-11 차단) |
| **Phase 4** | 2~4주 리드타임 | `cos-vng` 프로젝트 분리 |
| **Phase 5** | 선택 | PoC: translations.xlsx 분할 / tenant 모델 / API v4 대비 |

---

## 하네스 구조 (Anthropic 3-Agent Pattern)

| 에이전트 | 역할 | 산출물 |
|---------|------|-------|
| **Planner** | 스펙 결정 + Definition of Done 정의 | `spec.md` / `iteration-contract-v{N}.md` |
| **Architect** (Generator) | 후보안 생성 + 평가 매트릭스 + Phase 전환 경로 | `redesign-v{N}.md` / `self-check-v{N}.md` |
| **Critic** (Evaluator) | 독립 채점(60점) + 수렴 판정 | `review-v{N}.md` / `handoff-v{N}.md` |

**iteration 사이 Context Reset**: Architect는 매 iteration마다 fresh context로 시작, handoff 파일만 re-read.

---

## Iteration 기록

### iter-1 (2026-04-18 초반): **40/60 미수렴**

| 점검 항목 | 결과 |
|---------|------|
| 치명 약점 | 5건 식별 (validator 본문 누락, 태깅 부재, VNG Phase 4, P3 자가 모순, Fail-Close 미정의) |
| 편법 경로 | F1~F5 식별 (기존 E1~E5에 추가) |
| 5건 사례 | 2건 확정 재현 / 2건 부분 재현 / 1건만 확정 차단 |

### iter-2 (2026-04-18 후반): **52/60 수렴**

| 점검 항목 | 결과 |
|---------|------|
| 치명 5건 | 5/5 해소 |
| 편법 F1~F5 | 5/5 차단 |
| 5건 사례 | 5/5 차단 (탐지 0, 통과 0) |
| 감점 트리거 | 0건 적발 |
| Architect 자가 점수 | 58/60 (참고) |
| Critic 독립 점수 | **52/60** (실제) — 자기평가 편향 감지 (Δ=-6) |

---

## v3 숙제 (이관 사항)

iter-2에서 해결되지 않은 3건. Phase 0 실행 중 신규 이슈 발생 시 v3 재개:

1. **M2 "3초 수렴" 종단 시간 정의 확정** — Slack 응답(3초) / PR 머지(30초) / 플레이어 반영(분 단위) 중 어느 것을 기준으로 할지 spec.md에서 명문화
2. **Phase 0 리드타임 현실화** — VNG 법인 조율 3~5일은 짧음. Phase -1(사전 조율) 신설 또는 Phase 0 기간 1~2주로 확장
3. **Slack 대리 입력 창구 지속성** — 담당자 1명 → 당번제(2인) 또는 자동 폼 + SLA 24시간 구조화

### v3 재개 트리거

| 트리거 | 호출 대상 |
|-------|---------|
| Phase 0 Exit 1주 내 미달성 | Planner v3 |
| Phase 1~3 중 신규 편법 경로(9번째) 발견 | Planner v3 + Architect v3 |
| Lokalise API v4 배포 조기화 | Architect v3 |
| Phase 3 D+7까지 rev 누적 > 0건 | Architect v3 |

---

## 기존 문서와의 관계

| 문서 | 상태 | 관계 |
|------|-----|------|
| [translation_pipeline.md](./translation_pipeline.md) | 현행 | 현재 파이프라인 기술 문서 (as-is, 비교 기반) |
| [workflow_comparison_3way.md](./workflow_comparison_3way.md) | **현행 진입점** | 현재 / Claude v2 A+D / Google Sheet 3-way 의사결정 자료 |
| [workflow_comparison_v2.md](./workflow_comparison_v2.md) | **현행 보조** | 현재 vs v2 2-way 비교 (v2 채택 시 상세 플로우) |
| [redesign_final.md](./redesign_final.md) | **현행 상세** | v2 A+D + Phase 0~5 상세 (구현 기반 문서) |
| [workflow_comparison.md](./workflow_comparison.md) | 히스토리 | 구 Lokalise vs Google Sheet 2-way (3-way로 대체됨) |
| [google_sheet_workflow.md](./google_sheet_workflow.md) | 참고만 | Google Sheet 8 컴포넌트 상세 (3-way §4·§10-B 근거) |
| [l10n_google_sheet_workflow.md](./l10n_google_sheet_workflow.md) | 참고만 | Google Sheet 축 검토 기록 |
| [l10n_pipeline_redesign.md](./l10n_pipeline_redesign.md) | 참고만 | 하네스 이전 초기 검토 메모 |

본 하네스 결과(`workflow_comparison_3way.md` + `redesign_final.md` + `workflow_comparison_v2.md`)가 **우선**. 기존 문서는 과거 맥락·근거 자료 보관용.

---

## 실행 착수 준비 (handoff-v2.md §2.2 발췌)

- [ ] VNG 법인 사전 조율: Phase 0 공식 착수 1주 전 VNG PM과 과도기 Slack 창구 합의 선행
- [ ] Slack 대리 입력 담당자 2인(당번제) 지정 — 주말/야간 대응 포함
- [ ] VNG 편집 빈도 사전 측정: 7일치 Lokalise admin 로그 확보
- [ ] 프록시 Lambda 운영 owner 지정: Primary 인프라팀, Secondary 백엔드 dev팀
- [ ] `cos-vng` 프로젝트 생성 킥오프: Phase 0 진입과 동시에 Lokalise 신청 (리드타임 2~4주)
- [ ] Phase 2 `tag=re` 경로 종단 시간 정의 합의: PR 머지 / CI Lokalise publish / 배포 반영 중 어느 시점까지를 "수렴"으로 볼지 확정

---

## 관련 링크

- [Iteration Contract v2](./harness_artifacts/iter-2/iteration-contract-v2.md) — DoD·감점 트리거
- [Review v2](./harness_artifacts/iter-2/review-v2.md) — Critic 독립 채점 근거
- [Handoff v2](./harness_artifacts/iter-2/handoff-v2.md) — 수렴 판정 + v3 숙제
- [Spec v2](./harness_artifacts/iter-2/spec.md) — 메타-원인·원칙·제약 지도

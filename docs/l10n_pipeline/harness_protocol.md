# Harness Protocol — L10N 파이프라인 재설계 3-Agent 협업 규약

> 버전: v1.0
> 근거: Anthropic 2026-03-24 «Harness Design for Long-Running Apps»
> 적용 범위: L10N 파이프라인 재설계 전용 (복제 시 다른 도메인에도 활용 가능)

---

## 목적

- 3개 에이전트(Planner / Architect / Critic)의 **호출 순서·파일 규격·수렴 판단**을 단일 문서로 고정
- 사람(Human Operator)이 중간에 개입할 포인트를 명시
- 향후 L10N 이외 재설계(밸런스, 콘텐츠 등)에도 템플릿으로 복제 가능

---

## 에이전트 요약

| 에이전트 | 역할 | Input | Output |
|---------|------|-------|--------|
| `l10n-pipeline-planner` | 메타-원인 축약 · 제약 지도 · 원칙 도출 · 계약 작성 | 사례 파일 + 고정 제약 + 이전 handoff | `spec.md` + `iteration-contract-v{N}.md` |
| `l10n-pipeline-architect` | 후보안 5개+ · 추천안 · 전환 경로 | spec + contract + 이전 review | `redesign-v{N}.md` + `self-check-v{N}.md` |
| `l10n-pipeline-critic` | 점수 부여 · 편법 사냥 · 사례 재현 | redesign + spec + 사례 | `review-v{N}.md` + `handoff-v{N}.md` |

---

## 호출 순서 (반드시 준수)

```
[human 입력]
   ↓
Planner 호출 ── spec.md ── iteration-contract-v{N}.md
   ↓                              ↓
[human 검토 2분]                   │
   ↓                              │
Architect 호출 ←── (이전 review 있으면 포함)
   ↓
redesign-v{N}.md ── self-check-v{N}.md
   ↓
Critic 호출
   ↓
review-v{N}.md ── handoff-v{N}.md
   ↓
[human 수렴 판단]
   ├─ 미수렴 → Planner 재호출 (handoff 반영)
   └─ 수렴   → redesign_final.md 확정
```

**금지:**
- Architect가 Planner 없이 단독 호출
- Critic이 redesign 없이 호출
- 동일 iteration 내 Architect 두 번 호출 (context reset 원칙 위반)

---

## 파일 규격

### 디렉토리 구조

```
D:\claude_make\docs\l10n_pipeline\harness_artifacts\
├── iter-1\
│   ├── spec.md
│   ├── iteration-contract-v1.md
│   ├── redesign-v1.md
│   ├── self-check-v1.md
│   ├── review-v1.md
│   └── handoff-v1.md
├── iter-2\
│   └── ... (동일 구조)
└── iter-N\
    └── ...
```

### 파일명 규칙

| 파일명 | 작성자 | 버전 접미사 |
|--------|--------|-----------|
| `spec.md` | Planner | 없음 (iteration마다 갱신) |
| `iteration-contract-v{N}.md` | Planner | `v{N}` |
| `redesign-v{N}.md` | Architect | `v{N}` |
| `self-check-v{N}.md` | Architect | `v{N}` |
| `review-v{N}.md` | Critic | `v{N}` |
| `handoff-v{N}.md` | Critic | `v{N}` (다음 iter로 전달) |

### 최종 산출물

- `D:\claude_make\docs\l10n_pipeline\redesign_final.md` — 수렴된 `redesign-v{N}.md`의 복사본
- README 업데이트: 기존 Google Sheet 안과 병치

---

## Iteration 프로토콜

### 1회 사이클

```
1. [human] 제약·사례 입력
2. [Planner] spec + contract 작성 (5~10분)
3. [human] 2분 검토 → OK / 수정 지시
4. [Architect] redesign + self-check 작성 (10~15분)
5. [Critic] review + handoff 작성 (10분)
6. [human] 수렴 판단 → 진행/종료
```

### Iteration 수 가이드

| 항목 | 값 |
|------|-----|
| 목표 | 3~7회 |
| 최대 | 10회 (초과 시 문제 재정의) |
| 회당 시간 | 15~30분 |
| 전체 예상 | 1.5~3시간 (3회 기준) / 5시간 (10회 기준) |

---

## Context Reset 원칙

Anthropic 가이드라인에 따라:

- **Architect는 iteration 사이 context 리셋** — 새 iteration에서 fresh하게 시작
- handoff-v{N-1}.md를 **다시 읽어서** 이전 피드백 로드
- Planner는 context 유지 가능 (메타-원인 일관성)
- Critic은 context 유지 가능 (평가 기준 일관성)

**이유:**
- Architect가 context를 유지하면 "지난번에 좋다고 한 부분" 고집 → 편향 누적
- 리셋 후 handoff만 보면 critic이 지적한 약점에 집중하기 쉬움

---

## 수렴 판단 기준

### 수렴 (Architect 재호출 불필요)

다음 **중 하나**라도 만족:

1. 총점 **55/60 이상**
2. **3회 연속** 점수 상승폭 < 3점 (plateau)
3. **5건 사례 재현 시뮬레이션 전부 "차단됨"** + 총점 50/60 이상

### 다이버전스 경보 (Planner 개입)

다음 **중 하나**라도 발생하면 Planner가 spec 재작성:

- 2회 연속 점수 하락
- 동일 약점이 3회 반복 지적
- 메타-원인과 상관없는 약점이 상위 3에 계속 등장

---

## Human Operator 개입 포인트

### 필수 개입

| 시점 | 역할 |
|------|------|
| Planner 호출 전 | 고정 제약 확정 (Lokalise 만료일, VNG, 번역팀 캐파 등) |
| Planner 산출물 확인 후 | spec/contract의 **스코프 타당성** 2분 검토 |
| Critic handoff 확인 후 | 수렴 판단 (진행/종료) |
| 최종 확정 직전 | 추천안 중 1~2개 중 **실행안 선택** |

### 선택 개입

- Architect 산출물 읽기 (Critic 전에 미리 검토하고 싶을 때)
- Iteration 3 이후에도 수렴 신호 없으면 문제 재정의

---

## 검증 방법 요약

| 단계 | 테스트 |
|------|--------|
| V1 | Planner 단독 — 메타-원인 1~2개, 원칙 4~6개, 규율 단어 0회 |
| V2 | Architect 단독 — 후보 5개+, 편법+차단 명시, self-check 통과 |
| V3 | Critic 단독 — 칭찬 0개, 사례 5건 재현, 편법 3개+ |
| V4 | 3자 End-to-End — v1→v2 점수 +10 이상 OR 치명적 약점 50%+ 해소 |
| V5 | 회귀 테스트 — 신규 L10N 사고 발생 시 동일 하네스 재호출 |

---

## Git 관리 정책

| 대상 | Git 정책 |
|------|---------|
| `harness_artifacts/iter-*/` | `.gitignore` (iteration 중간 산출물 축적 방지) |
| `redesign_final.md` | **commit 필수** (최종 추천안) |
| agent 파일 3개 | **commit 필수** (재사용 자산) |
| `harness_protocol.md` | **commit 필수** (이 문서) |

---

## 복제 가이드 (다른 도메인 적용 시)

본 프로토콜을 밸런스·콘텐츠 등 다른 도메인에 복제할 때 필요한 수정 포인트:

1. **에이전트 3개 파일명** — `{domain}-planner` / `{domain}-architect` / `{domain}-critic`
2. **사례 파일** — 해당 도메인의 사고/이슈 기록
3. **평가 루브릭** — 축 2개(원칙/현실성) 유지, 세부 요소는 도메인 맞춤
4. **사례 재현 시뮬레이션** — 최소 3건 이상 도메인 사례
5. **artifacts 디렉토리** — `D:\claude_make\docs\{domain}\harness_artifacts\`

---

## 주의 / 트레이드오프

- 3-Agent는 초기 비용 ↑ — 단발 호출보다 2~3배 시간. 반복 사용에서 회수
- Planner 오작동 시 전체 꼬임 — Opus 모델 필수
- Handoff 파일 누적 — 5회면 30개 파일, .gitignore 필수
- Anthropic 가이드 버전 변경 대응 — 하네스 복잡도 감소 권고 나오면 Planner 제거 검토

---

## 관련 문서

- 현재 파이프라인: `translation_pipeline.md`
- 개선 파이프라인 (기존 Google Sheet 안): `google_sheet_workflow.md`
- 비교: `workflow_comparison.md`
- 사고 사례: `case_study_2026-04-17_rev_pollution.md`
- 수렴 후 최종안: `redesign_final.md` (수렴 후 작성)

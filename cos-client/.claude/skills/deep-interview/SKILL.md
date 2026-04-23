---
name: deep-interview
description: "작업 시작 전 소크라틱 인터뷰로 요구사항을 정제합니다. 수학적 ambiguity 점수가 임계값(20%) 이하로 떨어질 때까지 한 번에 하나씩 질문하여 숨겨진 가정을 드러내고, 명확한 스펙 문서를 생성합니다. 복잡한 기능 구현 전 요구사항 정리, 모호한 아이디어 구체화, 스펙 작성 시 사용합니다. '인터뷰 해줘', '요구사항 정리', '스펙 만들어줘', 'interview me', '질문부터 해줘', '계획서 만들어줘' 같은 요청에도 트리거됩니다."
argument-hint: "<아이디어 또는 기능 설명>"
---

# Deep Interview

소크라틱 질문 + 수학적 ambiguity 게이팅으로, 모호한 아이디어를 명확한 스펙으로 변환합니다.

`$ARGUMENTS`를 초기 아이디어로 사용합니다.

## Rules

- **한 번에 하나의 질문만** — 여러 질문을 묶지 않음
- **가장 약한 clarity 차원**을 타겟으로 질문
- **코드베이스를 먼저 탐색** — 코드에서 알 수 있는 것을 사용자에게 묻지 않음
- 매 답변 후 ambiguity 채점하고 투명하게 표시
- ambiguity ≤ 임계값(기본 0.2)이 될 때까지 진행
- 사용자가 조기 종료를 원하면 경고 후 허용
- **한국어**로 질문하고 응답

## Phase 1: Initialize

1. `$ARGUMENTS`에서 사용자의 아이디어를 파싱
2. **이 프로젝트는 항상 brownfield**: Cookie Run: Oven Smash Unity 모바일 PVP 게임 클라이언트이므로 greenfield 분기는 사용하지 않음
3. 관련 소스 파일과 기존 시스템을 탐색하여 컨텍스트 파악 (CLAUDE.md의 프로젝트 구조 참조)
4. 인터뷰 시작 안내:

```
Deep Interview를 시작합니다. 구현 전에 요구사항을 명확히 하기 위해 질문하겠습니다.
매 답변 후 clarity 점수를 표시하며, ambiguity가 20% 이하가 되면 스펙을 작성합니다.

**아이디어:** "{initial_idea}"
**현재 ambiguity:** 100%
```

## Phase 2: Interview Loop

`ambiguity ≤ threshold` 또는 사용자 조기 종료까지 반복:

### 2a: Generate Next Question

**가장 낮은 clarity 점수**의 차원을 타겟으로 질문 생성. 기능 목록이 아닌 **가정(assumptions)**을 드러내는 질문을 한다.

| Dimension | Weight | Question Style | Example |
|-----------|--------|---------------|---------|
| Goal Clarity | 0.30 | "정확히 어떤 일이 일어나야 하나요?" | "관리한다고 했는데, 사용자가 첫 번째로 하는 구체적인 액션은?" |
| Context Clarity | 0.25 | "기존 시스템과 어떻게 맞물리나요?" | "기존 XXManager가 YY를 처리하는데, 이 기능은 거기에 추가? 별도 시스템?" |
| Constraint Clarity | 0.25 | "경계와 제한은?" | "이 기능이 배틀 중에 동작? 로비 UI에서 동작? 타운에서 동작?" |
| Success Criteria | 0.20 | "완성을 어떻게 판단하나요?" | "이 기능이 되면 구체적으로 어떤 화면/동작이 보여야 하나요?" |

### 2b: Ask the Question

```
Round {n} | 타겟: {weakest_dimension} | Ambiguity: {score}%

{question}
```

### 2c: Score Ambiguity

답변을 받은 후 모든 차원을 내부적으로 채점 (0.0–1.0):

1. **Goal Clarity:** 목표가 한 문장으로 명확한가?
2. **Context Clarity:** 기존 시스템(MonoBehaviour/ScriptableObject/gRPC/Addressables 등)과의 관계가 명확한가?
3. **Constraint Clarity:** 경계, 제한, non-goals가 명확한가?
4. **Success Criteria:** 테스트로 검증 가능한 수준인가?

**Ambiguity 계산:**

```
ambiguity = 1 - (goal × 0.30 + context × 0.25 + constraints × 0.25 + criteria × 0.20)
```

### 2d: Report Progress

```
Round {n} 완료.

| Dimension        | Score | Weight | Weighted | Gap           |
|------------------|-------|--------|----------|---------------|
| Goal             | {s}   | 0.30   | {s*w}    | {gap or "✓"}  |
| Context          | {s}   | 0.25   | {s*w}    | {gap or "✓"}  |
| Constraints      | {s}   | 0.25   | {s*w}    | {gap or "✓"}  |
| Success Criteria | {s}   | 0.20   | {s*w}    | {gap or "✓"}  |
| **Ambiguity**    |       |        | **{%}**  |               |

{≤ threshold → "✅ Clarity 임계값 도달! 스펙을 작성합니다."}
{> threshold → "다음 질문 타겟: {weakest_dimension}"}
```

### 2e: Soft Limits

- **Round 3+:** 사용자가 "됐어", "시작하자", "만들어" 등으로 조기 종료 가능
- **Round 10:** "10라운드째입니다. 현재 ambiguity: {score}%. 계속할까요?"
- **Round 20:** "최대 라운드 도달. 현재 clarity({score}%)로 진행합니다."

## Phase 3: Challenge Modes

특정 라운드에서 관점 전환. 각 모드는 **1회만** 사용 후 일반 질문으로 복귀.

| Mode | Round | Trigger | Purpose |
|------|-------|---------|----------|
| **Contrarian** | 4+ | 항상 | 핵심 가정에 도전. "반대라면? 이 제약이 실제로 없다면?" |
| **Simplifier** | 6+ | 항상 | 제거 가능한 복잡성 탐색. "가치 있는 최소 버전은?" |
| **Ontologist** | 8+ | ambiguity > 30% | 문제 재정의. "이걸 한 문장으로 동료에게 설명한다면?" |

**정체 감지:** 3회 연속 ambiguity 변동 ±5% 이내 시 Ontologist 조기 발동.

## Phase 4: Crystallize Spec

ambiguity ≤ threshold (또는 hard cap / 조기 종료) 시, 스펙을 작성하여 사용자에게 제시:

```markdown
# Deep Interview Spec: {title}

## Metadata
- Rounds: {count}
- Final Ambiguity: {score}%
- Generated: {timestamp}
- Status: PASSED | EARLY_EXIT

## Clarity Breakdown
| Dimension        | Score | Weight | Weighted |
|------------------|-------|--------|----------|
| Goal             | {s}   | 0.30   | {s*w}    |
| Context          | {s}   | 0.25   | {s*w}    |
| Constraints      | {s}   | 0.25   | {s*w}    |
| Success Criteria | {s}   | 0.20   | {s*w}    |
| **Ambiguity**    |       |        | **{%}**  |

## Goal
{명확한 목표 문장}

## Context
{기존 시스템과의 관계, 관련 파일/클래스}

## Constraints
- {constraint 1}
- ...

## Non-Goals
- {명시적으로 제외된 범위}
- ...

## Acceptance Criteria
- [ ] {테스트 가능한 기준 1}
- [ ] {테스트 가능한 기준 2}
- ...

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| {가정} | {어떻게 도전} | {결정된 내용} |

## Technical Context
{관련 파일, 시스템, 아키텍처 결정}

<details>
<summary>Full Interview Transcript ({n} rounds)</summary>

### Round 1
**Q:** {question}
**A:** {answer}
**Ambiguity:** {score}%

...
</details>
```

## Phase 5: Handoff

스펙 작성 후 사용자에게 선택지 제시:

```
스펙이 준비되었습니다 (ambiguity: {score}%).

1. **바로 실행** — 이 스펙 기반으로 구현 시작
2. **추가 정제** — 인터뷰 계속
3. **스펙만 저장** — 나중에 사용
```

선택에 따라 진행. 이 스킬의 역할은 **스펙이 명확해지면 완료**됩니다.

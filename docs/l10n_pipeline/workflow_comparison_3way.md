# 번역 워크플로우 3-way 비교: 현재 Lokalise vs Claude v2 A+D vs Google Sheet

> 비교 대상: 현재 파이프라인(사고 5건) vs Claude v2 A+D(52/60 수렴) vs Google Sheet(과거 대안)
> 기준일: 2026-04-18 / Iteration v2 수렴 직후, Phase 0 착수 전 **의사결정 자료**
> 목적: "지금 어디가 문제인지 → 어느 방식으로 갈지 → 어떻게 고쳐야 하는지"를 한 페이지로

---

## 전체 요약 (한눈에)

| 지표 | 현재 (Lokalise) | Claude v2 A+D | Google Sheet |
|------|---------------|---------------|-------------|
| **개발 공수** | 없음 | **별도 개발 필요** | 별도 개발 필요 |
| **워크플로우 단계** | 17단계 | **6단계** (-65%) | 4단계 (-76%) |
| **5건 사고 차단** | 0/5 | **5/5** (0초 또는 Phase Exit) | 5/5 (구조적) |
| **편법 F1~F5 차단** | 0/5 | **5/5** (0초) | 5/5 (N/A 포함) |
| **연간 PM 시간 절감** | 기준 | **+160~320h** | +72~211h |
| **Lokalise 구독** | 구독 유지 | **구독 유지** (mirror only) | 구독 해지 + 별도 번역 API 필요 |
| **번역팀 UI 변화** | 없음 | **없음** (ko read-only) | Google Sheet 신규 학습 |
| **VNG 충격도** | 없음 (위험 상존) | **Phase 0 쓰기 회수** | Google Sheet 권한 재설계 |
| **롤백 용이성** | N/A | **Phase 0~5 중단 가능** | D-day cut-over (단방향) |

### 한 줄 결론 (추천)

> **본 프로젝트에서는 Claude v2 A+D 채택을 권장합니다.**
> Google Sheet는 Lokalise 구독 해지 압박이 분명하고 번역팀 UI 전환이 합의된 경우에만 대안.
> 현재 방식 유지는 비권장 (월 2건 사고 지속, 누적 손실 연 48~192시간).
>
> ⚠ **v2·Google Sheet 공통 전제**: 현재 `modes.xlsx` 등에 들어있는 한글 자연어를 `translations_ko.xlsx`의 `^key` 참조로 **일괄 마이그레이션하는 일회성 작업**이 Phase 1 착수 전 반드시 선행되어야 함 (자동화 스크립트 필수).

---

## §2. 현재 방식 (As-Is Lokalise, 사고 5건 발생)

```
┌────────────────────────────────────────────────────────┐
│ 기획자                                                  │
│ 1. translations.xlsx에 한글 입력                        │
│    ⚠ modes.xlsx name에도 ko 입력 가능 (사고 02-05)       │
└────────────────────────┬───────────────────────────────┘
                         ↓
              ⏳ PM 배치 처리 대기 (수 시간~1일)
                         ↓
┌────────────────────────────────────────────────────────┐
│ PM — 46분 수동 작업                                     │
│ 2. Fork → 번역키 추출 + 20초 대기                       │
│ 3~4. exports/ 검수 + 7종 카테고리 분류                  │
│ 5. Lokalise 접속 + Upload                              │
│    ⚠ "Differentiate keys by file" 해제 실수 가능         │
│       → 대표키 병합 사고 (02-20)                        │
│ 6. Skipped 키 처리 → 재업로드                          │
│ 7. Tag 수동 입력 — 누락 가능 (사고 03-11)              │
│ 8. Slack 공지                                           │
└────────────────────────┬───────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ 번역팀                                                   │
│ 9. Lokalise 로그인 + 번역 입력 (en/ja/zh/th/id)        │
│    ⚠ ko 필드도 수정 가능 (사고 04-17 rev 누적)         │
│    ⚠ 개인 API 토큰 발급 가능 (편법 F2 상시 열림)       │
└────────────────────────┬───────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ VNG 법인 (베트남)                                        │
│ 10. Lokalise cos-main 직접 접속 → id/vi 편집            │
│     ⚠ ko·en 필드도 편집 가능 (사고 02-20, E5 역류)      │
└────────────────────────┬───────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ PM — Sync 수동                                          │
│ 11~14. Sync 클릭 + 10분 대기 + Fork 확인 + 완료 공지    │
└────────────────────────┬───────────────────────────────┘
                         ↓
               [게임 반영]
                         ↓
        ❓ 오타 발견? → 기획자 로컬 datasheet
           ⚠ .pb만 커밋 가능 (사고 03-07 잔여물)
```

### 사고 발생 포인트 5건

| 날짜 | 사고 | 발생 경로 (현재 구조) |
|------|------|---------------------|
| 2026-02-05 | Modes^1303 이중 소스 | 기획자가 modes.xlsx + translations.xlsx **양쪽에 ko 입력** |
| 2026-02-20 | VNG 대표키 병합 | "Differentiate keys by file" 체크 실수 + VNG가 ko·en도 편집 |
| 2026-03-07 | skill_description 잔여물 | 로컬 datasheet → **.pb만 커밋, excel 누락** |
| 2026-03-11 | 303건 태깅 누락 | PM 수동 태깅 단계 누락 |
| 2026-04-17 | rev 누적 복합 | Lokalise 웹 직수정 + Excel 미갱신 → rev 누적 |

---

## §3. Claude v2 방식 (A 프록시 기본 + D cron 보강)

```
┌────────────────────────────────────────────────────────────┐
│ 기획자 — 할 일 3가지 (로컬 수작업은 이게 전부)               │
│ 1. translations.xlsx에 str_id + ko + tag 입력                │
│    (예: str_id=`Modes.modes^1303.name`, ko=`랭크전`, tag=new) │
│ 2. 데이터 시트의 텍스트 컬럼에 str_id **연결** (값 입력 X)    │
│    (예: modes.xlsx `name` 컬럼 = `Modes.modes^1303.name`)    │
│ 3. **git commit → PR 생성 → 리뷰 → main 머지**               │
│    (이 PR 머지가 CI 자동 실행의 트리거)                       │
│    ※ str_id는 자동 생성 키 — 기획자는 **연결만** 수행         │
│       (한글·자연어는 절대 데이터 시트에 직접 입력 금지)        │
│    🛡 Validator (a): 데이터 시트에 자연어 입력 → CI reject    │
│    🛡 Validator (b): translations.xlsx ko 중복값 → CI reject  │
└────────────────────────────┬───────────────────────────────┘
                             ↓
                  [ PR 머지 = CI 트리거 ]
                             ↓
        ┌────────────────────────────────────┐
        │ CI 자동 (머지 후 + 매 빌드)         │
        │ • Validator 3종 검사                │
        │ • datasheet rev-dedup               │
        │ • pb 자동 생성 (레포에 커밋 안 함)    │
        │ • pre-receive hook: pb push 거부    │
        │ • tag→Lokalise publish 1:1 매핑     │
        └────────────────┬────────────────────┘
                         ↓
              [클라이언트/서버 배포 반영]
                         ↓
        ┌────────────────────────────────────┐
        │ 번역팀                               │
        │ 4. Lokalise 로그인 + 번역 입력       │
        │    (en/ja/zh/th/id 5개 언어만)       │
        │ 🛡 ko 필드는 읽기 전용 (A 프록시 403) │
        │ 🛡 개인 API 토큰 발급 불가 (역할 제한) │
        └────────────────┬────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │ VNG 법인 (cos-vng 전용)              │
        │ 5. cos-vng 프로젝트에서 id/vi 편집   │
        │ 🛡 cos-main 쓰기 권한 0 (Phase 0)    │
        └────────────────┬────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │ CI 자동 (10분 cron)                 │
        │ • Lokalise 표류 발생 시              │
        │   delete_rev + create_translation   │
        │ • 프록시 우회 공격 이중 방어선        │
        └────────────────┬────────────────────┘
                         ↓
              [게임 반영]
                         ↓
        ❓ 오타 발견? → 발견자가 translations_ko.xlsx에서
                       ko 수정 + tag=re
                         ↓
        ┌────────────────────────────────────┐
        │ 6. git commit → PR → 리뷰 → main 머지 │
        │    (1~3번과 동일한 일상 기획 워크플로)│
        │    CI 자동: re 태그 감지 →             │
        │    Lokalise ko 덮어쓰기 + 번역팀 알림  │
        └────────────────────────────────────┘
```

> **왜 `tag` 값이 `new` / `re` / `test` 3개뿐인가?**
> `translations_ko.xlsx`는 **ko 원문만** 담는 파일이고, 번역팀은 프록시 403으로 ko를 수정할 수 없다. 즉 이 파일은 **기획자가 단독으로 관리**하는 원천이므로 "번역팀 번역 완료(done)" 같은 상태를 기록할 이유가 없다 — 번역 완료 여부는 **Lokalise 자체 status (translated / reviewed)** 가 관리한다. 따라서 기획자가 표현해야 할 상태는
>
> - `new` — 신규 등록 (Lokalise upload + 번역팀 요청)
> - `re` — ko가 수정됨 (번역팀 재검토 필요)
> - `test` — **테스트/미완성 원문, 번역팀에 요청하지 않음** (Lokalise upload 안 함, ko만 게임에 표시)
>
> 3가지로 충분하다. `test` 태그는 개발 중 임시 원문·placeholder·hold 상태를 하나로 통합한다. `done` / `hold` / `renew` 같은 추가 값은 도입 비용 대비 실익이 낮으므로 생략.

### 🛡 다이어그램 장치별 차단 목적

각 🛡 마커는 ko 원문의 **단일 쓰기 원천을 `translations_ko.xlsx`로 고정**하기 위한 구조 장치. 편법 경로가 생기지 않도록 **웹 UI + API + 외부 법인** 3축을 모두 봉쇄.

| 🛡 장치 (다이어그램 위치) | 막는 쓰기 경로 | 막는 사고/편법 |
|------------------------|-------------|--------------|
| Validator (a) — 기획자 PR | 데이터 시트(`modes.xlsx` 등)에 한글 자연어 직접 입력 | **02-05** Modes^1303 이중 소스 / **F1** xlsx ko 이중 소스 |
| Validator (b) — 기획자 PR | `translations_ko.xlsx`에 동일 한글 중복 등록 | **02-20** 대표키 병합 재발 방지 |
| **ko 필드 읽기 전용 (A 프록시 403)** — 번역팀 | **웹 UI**로 Lokalise ko 직수정 | **04-17** rev 누적 / **E1** 웹 직수정 편법 |
| **개인 API 토큰 발급 불가** (역할 제한) — 번역팀 | **개인 토큰 + curl**로 Lokalise API 직접 호출 (프록시 우회) | **F2** 토큰 우회 편법 |
| cos-main 쓰기 권한 0 (Phase 0) — VNG | VNG가 `cos-main` 프로젝트에서 ko/en 역류 편집 | **02-20** VNG 중복 / **E5** VNG 역류 |

> **번역팀의 🛡 2개가 쌍으로 필요한 이유**: Lokalise ko를 쓰는 경로는 ① 웹 UI ② API 두 가지.
> 프록시 403만 있으면 **개인 토큰 + curl로 우회 가능(F2)**, 토큰 금지만 있으면 **웹 UI에서 수정 가능(E1)**.
> 두 장치가 **함께 있어야** ko 필드의 모든 쓰기 경로가 0초 차단됨. 파생물(Lokalise ko)은 cron으로 원천에서 자동 재생성되므로 손댈 필요가 없음.

---

### 🛡 차단 구조 (편법 8종 전부)

| 편법 | 차단 방식 | 원복 지연 |
|------|---------|----------|
| E1 Lokalise 웹 ko | **A 프록시 403** + D cron 10분 | 0초 |
| E2 대표키 병합 | CI `differentiate_by_file=true` 하드코딩 | 0초 |
| E3 `.pb` 커밋 | `.gitignore` + 서버 pre-receive reject | 0초 |
| E4 git 커밋 누락 | **CI only pb 생성** | 0초 |
| E5 VNG 역류 | Phase 0 Exit부터 쓰기 권한 0 | 0초 (Phase 0 이후) |
| F1 xlsx 이중 | **Validator (a) CI reject** | 0초 |
| F2 개인 API 토큰 | 토큰 발급 금지 + **IP allowlist** | 0초 |
| F4 pre-receive bypass | GitHub bypass OFF + 서버 hook | 0초 |

---

## §4. Google Sheet 방식 (과거 대안, Lokalise 해지형)

```
┌────────────────────────────────────────────────────────┐
│ 기획자                                                  │
│ 1. excel/*.xlsx에 str_id 참조 입력                       │
│    (ex. name = str_cookie_power)                       │
│    🛡 CI validator: xlsx에 ko 자연어 금지 (F1 차단 동일) │
│ 2. Google Sheet에 str_id + ko + tag=new 추가            │
└────────────────────────┬───────────────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │ CI 자동 (5분 cron)                  │
        │ Google Sheet hash 비교              │
        │ → ko CSV 생성 → cos-client 배포     │
        │ → Unity Editor 즉시 반영            │
        └────────────────┬────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │ 번역팀 (Slack 알림 수신)              │
        │ 3. 워크벤치 툴 접속                   │
        │    tag=new/re 필터 → 번역 입력       │
        │    저장 시 tag=done 자동 변경         │
        └────────────────┬────────────────────┘
                         ↓
        ┌────────────────────────────────────┐
        │ CI 자동 (새벽 4시 cron)              │
        │ 전체 언어 pb 생성 + Portal 업로드    │
        │ Slack 배포 완료 알림                 │
        └────────────────┬────────────────────┘
                         ↓
              [게임 반영]
                         ↓
        ┌────────────────────────────────────┐
        │ VNG 법인 (별도 Sheet or 파일 교환)    │
        │ 4. 전용 Google Sheet / xlsx 교환      │
        │    🛡 메인 Sheet 직접 쓰기 권한 0     │
        └────────────────────────────────────┘
```

### 🛡 차단 구조 (5건 사고 + 편법 재분석)

**5건 사고 × Google Sheet**:

| 사고 | 차단 방식 | 등급 |
|------|---------|------|
| 02-05 Modes^1303 이중 | xlsx는 str_id 참조만 → ko 자연어 컬럼 부재 (validator 필요) | 차단 (validator) |
| 02-20 VNG 대표키 병합 | Lokalise 제거 → "Differentiate keys" 옵션 소멸 | 차단 (구조 부재) |
| 03-07 .pb 잔여물 | `.gitignore` + CI only pb 생성 | 차단 (0초) |
| 03-11 태깅 누락 | Google Sheet `tag` 컬럼 구조 포함 + 번역 시 자동 `done` | 차단 (구조적) |
| 04-17 rev 누적 | Lokalise 제거 → rev 개념 소멸, Sheet 단일 원문 | 차단 (구조 부재) |

**편법 F1~F5 × Google Sheet**:

| 편법 | 차단 방식 | 등급 |
|------|---------|------|
| F1 xlsx ko 이중 소스 | **CI validator 필수** (str_id 참조 검증) — v2와 동일 구현 | 차단 (validator) |
| F2 Lokalise 개인 토큰 | Lokalise 부재 | N/A (구조 소멸) |
| F3 Excel + Lokalise 동시 | Lokalise 부재 | N/A (구조 소멸) |
| F4 pre-receive bypass | `.gitignore` + 서버 hook 필수 (v2와 동일) | 차단 (동일 메커니즘) |
| F5 VNG 잔존 권한 | VNG 전용 Sheet or 파일 교환 → 메인 쓰기 권한 0 | 차단 (권한 분리) |

---

## §5. 3-way 사고 차단 매트릭스

| 사례 | 현재 | v2 A+D | Google Sheet |
|------|------|--------|-------------|
| **02-05** Modes^1303 이중 소스 | ⚠ 통과 | 🛡 차단 (validator) | 🛡 차단 (validator) |
| **02-20** VNG 대표키 병합 | ⚠ 통과 | 🛡 차단 (Phase 0 권한) | 🛡 차단 (Lokalise 부재) |
| **03-07** .pb 잔여물 | ⚠ 통과 | 🛡 차단 (CI only pb) | 🛡 차단 (CI only pb) |
| **03-11** 303건 태깅 누락 | ⚠ 통과 | 🛡 차단 (tag 컬럼) | 🛡 차단 (Sheet 구조) |
| **04-17** rev 누적 | ⚠ 통과 | 🛡 차단 (프록시 403) | 🛡 차단 (Lokalise 부재) |
| **차단률** | **0/5** | **5/5** | **5/5** |

> 주석: Google Sheet 방식의 차단 메커니즘 중 일부(F1/F4)는 v2와 동일한 validator + pre-receive hook이 필요. **Google Sheet 전환이 "자동으로" 편법을 막지 않는다** — 전환 + 동일 CI 인프라 구축 시에만 차단 성립.

---

## §6. 3-way 편법 F1~F5 차단 매트릭스

| 편법 | 현재 | v2 A+D | Google Sheet |
|------|------|--------|-------------|
| **F1** xlsx ko 이중 소스 | ⚠ 통과 | 🛡 차단 (validator) | 🛡 차단 (validator, 동일 구현 필요) |
| **F2** Lokalise 개인 API 토큰 | ⚠ 통과 | 🛡 차단 (토큰 금지 + IP allowlist) | N/A (Lokalise 부재로 구조 소멸) |
| **F3** Excel + Lokalise 동시 수정 | ⚠ 통과 | 🛡 차단 (Lokalise ko read-only) | N/A (Lokalise 부재로 구조 소멸) |
| **F4** pre-receive bypass | ⚠ 통과 | 🛡 차단 (bypass OFF + 서버 hook) | 🛡 차단 (동일 구현 필요) |
| **F5** VNG 잔존 권한 | ⚠ 통과 | 🛡 차단 (Phase 0 회수) | 🛡 차단 (전용 Sheet 분리) |
| **차단률** | **0/5** | **5/5** | **5/5** (N/A 2건 포함) |

> 주석: Google Sheet 방식은 F2/F3가 **구조 자체 소멸**로 N/A. Lokalise 제거로 공격면 축소 효과는 있으나, **새로운 공격면**(Google Sheet 권한 관리, Google OAuth 남용 등)이 열릴 수 있어 별도 검토 필요.

---

## §7. 실무 지표 상세 비교

| 지표 | 현재 (Lokalise) | v2 A+D | Google Sheet |
|------|---------------|--------|-------------|
| 개발 공수 | 없음 | 별도 개발 필요 (프록시 Lambda + validator 3종 + tag 자동화 + cron 복구) | 별도 개발 필요 (마이그레이션 + 워크벤치 툴 + CI cron 2종 + 권한 재설계) |
| 개발 인원 | N/A | 별도 산정 | 별도 산정 |
| Lokalise 구독 | 구독 유지 | 구독 유지 (ko mirror only) | 구독 해지 + 별도 번역 API 필요 |
| 번역팀 UI | Lokalise 현행 | Lokalise 현행 (ko 필드만 read-only) | Google Sheet 워크벤치 신규 |
| 번역팀 학습 비용 | 0 | 0 (UI 동일) | 높음 (도구 전환) |
| 기획팀 워크플로 | translations.xlsx | translations.xlsx + tag 컬럼 (초기 마이그레이션 후 일상 변화는 적음) | xlsx(str_id 참조) + Google Sheet 병용 |
| VNG 충격도 | 없음 (위험 상존) | Phase 0 쓰기 회수 + 2~4주 대리 입력 창구 | Google Sheet 권한 구조 재설계 필요 |
| 롤백 용이성 | N/A | Phase 0~5 단계별 중단 가능 (프록시 off / 권한 복원) | D-day cut-over (단방향, Sheet→xlsx 역마이그 복잡) |
| 장기 실패 모드 | 월 2건 사고 지속 | translations.xlsx 거대화(6mo) / Lokalise API v4(12mo) / 추가 법인(24mo) | Google Sheet API 정책 변경 / 무료 tier 한계 / 데이터 권한 누수 |
| 신규 언어 추가 | 수동 import (공수 큼) | translations_xx.xlsx 추가 (공수 적음) | Sheet 탭 추가 (공수 최소) |
| **기존 자연어 → str_id 마이그레이션** | N/A (현재 유지) | **일회성 필수** — 자동화 스크립트로 `modes/cookies/skill_infos` 등 ko 자연어 컬럼 전부를 `translations_ko.xlsx`의 `^key`로 이관 | **일회성 필수** — 동일 자연어→str_id 이관 + Google Sheet 구조로 재배치 (v2보다 규모 큼) |
| Lokalise 데이터 이관 | N/A | 불필요 | 5개 언어 × 수천 키 전량 이관 |
| 신규 법인 추가 | 프로젝트 분리 필요 | cos-vng 구조 유지 (Phase 4) | Sheet 탭 or 파일 교환 옵션 |

---

## §8. 작업 효율 개선 비교 (Before → After)

**핵심 효율 지표** — 현재 방식 대비 v2 / Google Sheet 선택 시 개선폭

| 효율 지표 | 현재 방식 | v2 A+D 선택 시 | Google Sheet 선택 시 |
|---------|---------|---------------|---------------------|
| **사고 건수 (월)** | 2건 | **0건** (5/5 차단) | **0건** (5/5 차단) |
| **사고 복구 소요 (건당)** | 3~8시간 | 0분 (사전 차단) | 0분 (사전 차단) |
| **PM 번역 사이클 (회)** | 46분 | **0분** (PR 머지 즉시 CI 자동 처리) | **0분** (CI 자동) |
| **연간 PM 시간 절감** | 기준 (0) | **+160~320시간** | **+72~211시간** |
| **번역팀 작업 단계** | 17단계 | 6단계 (**-65%**) | 4단계 (**-76%**) |
| **배포 파이프라인 불안정** | 월 2건 긴급 배포 | 0건 | 0건 |
| **담당자 소환 빈도 (주)** | 3~5회 | **0회** (발견자 직접 수정) | **0회** (직접 편집) |
| **신규 언어 추가 공수** | 수동 import (높음) | 파일 추가 (낮음) | Sheet 탭 추가 (최저) |
| **배치 대기 시간** | 배치 주기 의존 (수 시간~1일) | PR 머지 + CI 소요 (수 분) | 5분 (ko CSV cron) |

**Before → After 요약**:

```
사고 발생률:
  현재 ██████████        월 2건 × 12개월 = 연 24건
  v2 A+D                 연 0건 (5/5 구조 차단)
  Google Sheet           연 0건 (5/5 구조 차단)

PM 번역 사이클 시간:
  현재 ████████████████████████  46분/회 × 주 2~4회 × 52주 = 연 160~320h
  v2 A+D                         0분/회 = 연 0h
  Google Sheet                    0분/회 = 연 0h (Sheet 도입 후)

개발 공수:
  현재           변경 없음
  v2 A+D         별도 개발 필요
  Google Sheet   별도 개발 필요

번역팀 학습 비용:
  현재 ░░                  0 (Lokalise 친숙)
  v2 A+D ░░                0 (UI 동일, ko만 read-only)
  Google Sheet ██████████  높음 (도구 전환 + 워크벤치 학습)
```

**연간 효과 요약**:

| 효과 항목 | v2 A+D 선택 시 | Google Sheet 선택 시 |
|----------|---------------|---------------------|
| PM 시간 절감 | **+160~320시간/년** | **+72~211시간/년** (보수적 산정) |
| 사고 대응 공수 절감 | **+48~192시간/년** (구조적 차단) | **+48~192시간/년** (구조적 차단) |
| 번역팀 재작업 | 대폭 감소 | 대폭 감소 |
| Lokalise 구독 비용 | 구독 유지 (동일) | 구독 해지 + 별도 번역 API 비용 발생 |
| **총 절감 (시간 환산)** | **208~512시간/년** | **120~403시간/년** (구독/API 비용은 별도 산정) |

> v2 A+D의 PM 시간 절감이 더 큰 이유: 현재 방식의 46분 PM 작업(Fork·Upload·태깅·Sync)이 전부 CI 자동으로 넘어가기 때문. 오타 수정도 **일상 PR 경로**(translations_ko.xlsx 수정 + `tag=re` → git push) 하나로 통합되어 "Slack 커맨드 vs 정식 워크플로"의 이중 경로가 사라진다.

---

## §9. 추천 결론 (명확한 선택)

> ## 추천: **Claude v2 A+D 채택**

**선택 근거** (프로젝트 상황 기준):

| 기준 | v2 A+D 우세 | Google Sheet 불리 |
|------|-----------|-----------------|
| Lokalise 구독 유지 필요 | ✅ 구독 유지 (고정 제약 준수) | ❌ 구독 해지 + 별도 번역 API 필요 |
| VNG 외부 법인 존재 | ✅ Phase 0 회수 + Phase 4 cos-vng 분리 | ⚠ Google Sheet 권한 구조 재설계 필요 |
| 번역팀 Lokalise 친숙 | ✅ UI 변화 없음 (ko 필드만 read-only) | ❌ 워크벤치 재교육 (도구 전환) |
| 점진 전환 가능 | ✅ Phase 0~5 단계별 중단·롤백 가능 | ❌ D-day cut-over (단방향) |
| 개발 공수 | **별도 개발 필요** | 별도 개발 필요 (유사하나 범위 조금 더 큼) |
| 기존 자연어 → str_id 마이그레이션 | 일회성 필수 (스크립트) | 일회성 필수 + Google Sheet 구조 이관 (규모 더 큼) |
| 5건 사고 차단율 | **5/5 (100%)** | 5/5 (구조 차단이나 validator 별도 구현 필요) |
| 연간 PM 시간 절감 | **+160~320시간** | +72~211시간 (배치 대기 존재) |

**Google Sheet를 선택해야 하는 조건** (현재 상황에 해당 없음):

- Lokalise 구독 해지 + 별도 번역 API 도입 여력 확보 가능
- 번역팀 Google Sheet 전환 합의 확보 (재교육 수용)
- VNG 법인 Google 계정 접근 확정 (합의 필요)
- D-day 1회 cut-over 리스크 수용 가능 (롤백 불가 감수)
- Lokalise 데이터 이관 스크립트 + 마이그레이션 QA 수용

**현재 방식 유지를 선택해야 하는 조건** (비권장):

- 개발 리소스 전혀 확보 불가
- 월 2건 사고 + 연 208~512시간 손실을 감수할 수 있는 상황
- 3~6개월 내 팀 전면 재편 예정 (매몰비용 회피)

---

## §10. 구현 체크리스트 — 지금 파이프라인에서 뭘 바꿔야 하나

> **추천안 v2 A+D 구현을 위한 구체 변경사항**. Google Sheet 선택 시는 §10-B 참조.

### 10-A. Claude v2 A+D 구현 체크리스트 (권장)

#### 데이터 소스 변경 (기획팀)

> **기획자 할 일 3가지로 정리** (로컬 수작업은 이게 전부):
> 1. `translations.xlsx`에 `str_id + ko + tag` 입력 (원문·번역 관리)
> 2. 데이터 시트(`modes.xlsx` 등)의 텍스트 컬럼에 `str_id` **연결** (한글 직접 입력 금지)
> 3. **git commit + PR 생성 → 리뷰 → main 머지** (이 PR 머지가 CI 자동 실행의 트리거)
>
> `str_id`는 자동 생성 키 — 기획자는 생성된 키를 데이터 시트에 꽂기만 하면 됨.
> 나머지(Validator / pb 빌드 / Lokalise publish / cron 복구)는 전부 CI에서 자동 처리.

---

##### ⚠ 일회성 마이그레이션 (v2 착수 전 **선행 필수**)

**현재 상태**: `modes.xlsx`의 `name`, `cookies.xlsx`의 `name`·`description`, `skill_infos.xlsx` 등 **데이터 시트에 한글 자연어가 직접 입력**되어 있음. v2의 Validator (a)가 이를 "이중 소스"로 감지해 reject하므로, **전량 `str_id` 참조로 일괄 이관**해야 Phase 1 프록시를 켤 수 있음.

**수동 작업은 비현실적** (수천 건 규모) → **자동화 스크립트 필수**.

- [ ] **마이그레이션 스크립트 개발**
  - 입력: ko 자연어 컬럼이 있는 xlsx 전체
  - 처리: 각 셀 자연어 → `str_id` 자동 생성 (명명 규칙) → `translations_ko.xlsx`에 `^key + ko` 등록 (tag 공란 = CI Lokalise upload 대상 아님, 기존 번역 유지) → 원본 셀을 `str_id` 참조로 치환
  - 출력: 변경된 xlsx 세트 + `translations_ko.xlsx` 증분
- [ ] **Dry-run 검증**
  - PR diff로 치환 결과 검토
  - 마이그레이션 전/후 `datasheet` 빌드 결과 pb diff **0건** 확인 (런타임 동일성 보장)
  - 중복 자연어 감지 → 동일 `str_id` 공유 여부 기획 판단
- [ ] **실행 대상 xlsx 목록 확정** (ko 자연어 컬럼 보유 추정):
  - `modes.xlsx`, `cookies.xlsx`, `skill_infos.xlsx`, `dialog_groups.xlsx`, `ui_strings.xlsx` 등
  - `textconv`로 현재 데이터 전수 스캔 → 자연어 존재 컬럼 전수 리스트 확정
- [ ] **단계적 실행**
  - xlsx 파일별 PR 분리 (롤백 단위 확보)
  - PR 머지 시마다 CI 빌드 + pb diff 0건 게이트
- [ ] **마이그레이션 완료 후** Validator (a) **활성화** — 이후 자연어 직접 입력 자동 차단
- [ ] 마이그레이션 중에는 Validator (a) **warn 모드**로 운영 (기존 자연어 reject하지 않음)

##### 마이그레이션 후 일상 운영 체크리스트

- [ ] `str_id` 명명 규칙 확정 (예: `Modes.modes^{id}.name`, `Cookies.cookies^{id}.description`)
- [ ] `str_id` 자동 생성·주입 스크립트 **상시 운영화** — 신규 텍스트 추가 시에도 기획자 수동 입력 부담 최소화
- [ ] `translations.xlsx`(또는 `translations_ko.xlsx`)에 `tag` 컬럼 추가 (값: `new` / `re` / `done` / `hold`)

#### Phase 0 — VNG 권한 회수

- [ ] 번역팀·VNG 계정의 Lokalise **ko 필드 write 권한 제거** (read-only 강등)
- [ ] VNG 계정의 `cos-main` **쓰기 권한 회수** (Phase 0 Exit Criteria)
- [ ] 과도기 `#l10n-vng-requests` Slack 채널 개설, 기획팀 대리 입력 담당자 2인(당번제) 지정
- [ ] `cos-vng` 프로젝트 생성 신청 (Lokalise 리드타임 별도, Phase 4 완성 시점 의존)
- [ ] Lokalise API rate limit / webhook 용량 측정 (7일치 admin 로그)

#### Phase 1 — 프록시 Lambda + IP allowlist

- [ ] AWS Lambda + API Gateway로 Lokalise API 프록시 구축
- [ ] `target_language=ko` PUT/PATCH → **403 리젝 (0초 차단)**
- [ ] Lokalise API IP allowlist 활성화 — 프록시 Lambda EIP만 허용
- [ ] Lokalise 역할 재정의: `translator_nonko` / `reviewer` / `admin_api`
- [ ] `translator_nonko` 이하 역할에서 **개인 API 토큰 발급 권한 제거** (F2 차단)
- [ ] **Fail-close 거동 명시** + 복구 SOP 1페이지 (Lambda 장애 시 쓰기 전면 거부)
- [ ] Slack 알림: ko 쓰기 시도 감지 시 `#l10n-ops`에 차단 로그

#### Phase 2 — CI Validator 3종 + pb 바이너리 봉쇄

- [ ] **Validator (a)**: `translations.xlsx` 외 xlsx(modes/dialog_groups/ui_strings 등)에 ko 자연어 컬럼 금지 → datasheet 변환 거부
- [ ] **Validator (b)**: `translations.xlsx` ko 컬럼 중복값 검사 (unique constraint + warn-then-fail)
- [ ] **Validator (c)**: validator 실패 시 CI 전면 중단, pb artifact 미생성
- [ ] `.gitignore`에 `protobuf/*.pb` 추가
- [ ] CI `build-pb` 워크플로 추가 — `datasheet` 실행 (Linux binary 이미 존재)
- [ ] **서버측 pre-receive hook**: `protobuf/` 경로 diff 있는 push 거부
- [ ] GitHub repo admin bypass **OFF** 설정
- [ ] Phase 2 Exit 테스트:
  - [ ] modes.xlsx name 컬럼에 ko 주입 → CI reject 확인
  - [ ] translations.xlsx 동일 ko 중복 → CI reject 확인
  - [ ] admin push pb 커밋 시도 → reject 확인
  - [ ] 오타 수정 플로우 종단 확인 — translations_ko.xlsx `ko` 수정 + `tag=re` → PR 머지 → CI에서 Lokalise ko 덮어쓰기 + 번역팀 Slack 알림까지 자동 실행
  - [ ] `tag=test` 격리 동작 확인 — `test` row는 pb에는 포함되지만 Lokalise upload 안 됨 / 번역팀 워크벤치에 노출되지 않음
  - [ ] `tag=test → new` 전환 시 Lokalise 신규 upload 정상 작동 확인

> **오타 수정에 별도 Slack 커맨드/자동 PR Lambda를 두지 않음** — 신규 원문 등록과 동일하게 `translations_ko.xlsx`를 수정하고 `tag=re`로 마킹한 뒤 일상 PR 경로를 탄다. 별도 인프라 없이 작업 경로 일관성 + git 히스토리 통합성이 확보됨.

#### Phase 3 — tag 자동화 + cron 백업 (D+3 분리)

- [ ] `translations_ko.xlsx` `tag` 컬럼 스키마 강제 (datasheet validator에 필수 추가) — **허용 값: `new` / `re` / `test` / 공란(=처리 완료 or 마이그레이션 row)**
- [ ] CI 업로드 스크립트: tag → Lokalise API 호출 1:1 매핑
  - `tag=new` (신규 등록) → Lokalise key 신규 생성 + ko upload + **publish** + 번역팀 Slack 알림
  - `tag=re` (ko 수정) → Lokalise ko 덮어쓰기 + **publish** + 번역팀 Slack 알림 (`Changed since last review` 필터에 노출)
  - `tag=test` (테스트/미완성 원문) → **Lokalise upload 안 함** (번역팀 워크벤치 노출 0). ko만 pb에 포함되어 게임에 표시
  - `tag=공란` → CI 처리 대상 아님 (이미 Lokalise에 반영 완료된 row)
- [ ] `tag=test → new` 전환 감지: 기획자가 test → new로 바꾸면 CI가 해당 시점부터 Lokalise upload 시작 (개발 중 placeholder를 정식 원문으로 승격)
- [ ] **번역 완료 상태는 Lokalise 자체 status가 관리** — `translations_ko.xlsx`에 별도 `done` 태그 두지 않음 (번역팀이 ko를 수정할 수 없으므로 기획자 관점에서 `done` 상태가 무의미)
- [ ] CI 처리 후 tag 자동 공란화 옵션 검토 — PR 머지 시점 tag → CI 처리 완료 시 공란 전환 (`test`는 기획자 의도 상태이므로 공란화 제외)
- [ ] CI가 매 빌드마다 git diff 기반으로 추가·수정된 row만 Lokalise와 동기화 (tag는 신호, diff는 실제 판단)

##### Lokalise API 자동화 기술 검증 (2026-04-18 조사)

Lokalise 공식 API / GitHub Actions 문서를 직접 확인한 결과, **v2 A+D가 가정한 자동화는 전부 구현 가능**.

| 자동화 요구 | Lokalise 공식 지원 | 구현 메모 |
|-----------|-----------------|---------|
| xlsx → Lokalise upload | ✅ `/files/upload` (async, 202 queued) | 공식 GitHub Action `lokalise/lokalise-push-action` 재사용 가능 (base language=ko 자동 push 지원) |
| 특정 key에 tag 부여 | ✅ upload 파라미터 `tags` + `tag_inserted_keys` / `tag_updated_keys` / `tag_skipped_keys` | Excel `tag` 컬럼 값을 그대로 API tag로 전달 |
| 대표키 병합 방지 (E2 차단) | ✅ `distinguish_by_file=true` (upload 옵션) | CI 업로드 스크립트에 하드코딩 |
| Publish / Unpublish | ⚠ `published` 필드 없음 → **Custom Translation Status** (`custom_translation_status_ids`)로 대체 | `draft` / `live` 두 status 정의 후 tag 값에 매핑 (`new`·`re` → `live`, `test` → `draft` 또는 upload skip) |
| 외부 수정 감지 (cron 대체 가능) | ✅ Webhook `project.translation.updated` / `project.translations.updated` / `project.keys.modified` | `action` 필드(`api`·`bulk`·`ui`)로 편집 경로 식별 가능 → 10분 cron 대신 실시간 복구 여지 |
| 언어별 이벤트 필터 | ❌ API 레벨 필터 없음 | payload `language.iso` 값을 애플리케이션에서 `ko`만 필터 (간단) |
| Rate limit | 6 req/sec per token + per IP | 마이그레이션 대량 업로드 시 throttle 필요. 일상 운영은 여유 |
| 공식 GitHub Actions | ✅ `lokalise/lokalise-push-action`, `lokalise/lokalise-pull-action` | 브랜치명을 tag로 자동 부여하는 기능 내장 → PR 단위 추적 유리 |

**결론**: v2 A+D의 "CI가 자동으로 Lokalise에 publish 한다" 가정은 **기술 검증 완료**. 공식 GitHub Actions 재사용 + custom translation status 매핑 + webhook 활용으로 구현 공수는 처음 추정보다 축소 여지 있음. 단, `published` 필드 부재로 인한 **custom status 매핑 설계**가 Phase 1 착수 전 선행되어야 함.
- [ ] 10분 cron Lambda: xlsx ko 해시 비교 → 표류 시 `delete_rev` + `create_translation`
- [ ] D-day: 프록시 warn → enforce 전환 + 번역팀 공지
- [ ] D+3: Excel → Lokalise ko cron 첫 실행 + 태깅 CI 첫 동기화
- [ ] D+7: rev 누적 0건 확인, publish/태그 불일치 0건 확인

#### Phase 4 — cos-vng 완성 (리드타임 완료 시점)

- [ ] `cos-vng` 프로젝트 공식 가동 (Phase 0에서 신청한 프로젝트)
- [ ] VNG 권한을 `cos-vng`에만 부여
- [ ] 메인 → VNG 단방향 반영 cron (ko/en 한정)
- [ ] `cos-vng`에 Phase 1~3 프록시/validator/태깅 복제 적용
- [ ] Phase 0의 Slack 대리 입력 창구 폐쇄

#### Phase 5 — 장기 실패 모드 대응 (선택)

- [ ] 6개월: `translations.xlsx` 도메인별 분할 PoC
- [ ] 12개월: Lokalise API v4 호환 레이어 검토
- [ ] 24개월: tenant 모델 도입 검토 (`cos-*` N개 증식 전)

**총 공수**: 별도 개발 필요 (Phase 0~5 순차 진행)

---

### 10-B. Google Sheet 구현 체크리스트 (참고, 비권장)

#### Phase 0 — 사전 준비

- [ ] Google Sheet 구조 설계 (str_id / tag / ko / en / ja / zh-TW / zh-CN / th / id)
- [ ] Google Sheet API 서비스 계정 발급 + 권한 정책
- [ ] 번역팀 Google Sheet 전환 합의 + 교육 자료
- [ ] VNG 법인 Google 계정 접근 합의 (별도 Sheet or 파일 교환 확정)

#### Phase 1 — 병행 개발

- [ ] **일회성 마이그레이션 스크립트**: (1) `modes.xlsx`·`cookies.xlsx` 등 데이터 시트의 한글 자연어 → `str_id` 참조 이관 (v2 10-A와 동일 작업) + (2) `translations.xlsx` + Lokalise → Google Sheet 구조 이관 **2단계 연속**
- [ ] str_id 참조 검증 CI (excel/*.xlsx의 ko 자연어 컬럼 금지, v2 validator와 동일)
- [ ] ko CSV 자동 배포 파이프라인 (5분 cron, GitHub Actions)
- [ ] 전체 언어 pb 자동 배포 파이프라인 (새벽 4시 cron, KST 04:00 = UTC 19:00)
- [ ] 번역팀 워크벤치 툴 (tag=new/re 필터 + 번역 입력 UI)
- [ ] 기획 팀장 긴급 배포 툴 (전체 언어 pb 강제 빌드)
- [ ] Slack 알림 (신규/수정 발생 시, 배포 완료 시)
- [ ] 배포 시점 스냅샷 S3 자동 백업 (`translations_snapshot_vX.X.X_날짜.xlsx`)

#### Phase 2 — 통합 QA

- [ ] 8,546개 항목 이관 검증 (한 건도 누락 없는지 diff)
- [ ] `.gitignore`에 `protobuf/*.pb` 추가
- [ ] 서버 pre-receive hook (v2와 동일 메커니즘)
- [ ] F1/F4 편법 테스트 (v2 Phase 2 Exit 테스트와 동일)

#### Phase 3 — D-day cut-over

- [ ] Lokalise Sync Lambda 비활성화
- [ ] 마이그레이션 스크립트 실행
- [ ] `validate_diff.mjs` + `.gitignore` 수정 커밋
- [ ] `feat/*` 브랜치 → main 머지
- [ ] 기획팀 워크플로우 전환 공지
- [ ] 전체 언어 pb cron 첫 실행 확인
- [ ] D+7: 안정화 확인 후 **Lokalise 구독 종료** (별도 번역 API 도입 선행 필수)

**총 공수**: 별도 개발 필요 (Phase 0~3 순차 진행)

**위험 요인**:
- 번역팀 재교육 부담 (동일 회사지만 도구 전환)
- VNG 법인 조율 리스크 (Google 계정 접근 합의)
- D-day 1회 cut-over (롤백 불가)

---

### 10-C. 현재 방식 유지 (비권장)

- 변경사항 없음
- 월 2건 사고 지속 (연 24건 + 대응 48~192시간 손실)
- 6개월 후 재평가 권장

---

## §11. 후속 단계

### v2 A+D 선택 시 (권장)

1. **Phase 0 착수 준비** (`harness_artifacts/iter-2/handoff-v2.md §2.2` 참조):
   - VNG PM과 과도기 Slack 창구 합의 (공식 착수 1주 전)
   - Slack 대리 입력 담당자 2인 지정 (당번제)
   - VNG 편집 빈도 7일치 Lokalise admin 로그 확보
   - 프록시 Lambda owner 지정 (Primary: 인프라팀, Secondary: 백엔드 dev팀)
   - `cos-vng` 프로젝트 생성 신청 (리드타임 2~4주)
   - 오타 수정 플로우 확정: translations_ko.xlsx `ko` 수정 + `tag=re` → 일상 PR 경로 (별도 Slack 커맨드 없음)
2. **Phase 0 공식 착수** → Phase 0 Exit 통과 후 Phase 1 진입
3. **Phase 1~3 진행** (4~5주)
4. **Phase 4** (cos-vng 완성, 리드타임 완료 시점)
5. **Phase 5 (선택)** — 장기 실패 모드 PoC

### Google Sheet 선택 시

1. `google_sheet_workflow.md` + `l10n_google_sheet_workflow.md` 재검토
2. VNG 법인 + 번역팀 합의 (재교육·권한·접근)
3. Phase 0 사전 준비 (Google Sheet 구조 설계, API 발급)
4. Phase 1~3 병행 개발 + 통합 QA
5. D-day cut-over + D+7 안정화
6. Lokalise 구독 종료

### 현재 방식 유지 시 (비권장)

1. 월간 사고 추적 대시보드 구축
2. 6개월 후 재평가 (사고 건수 + 대응 시간 누적 집계)
3. 누적 손실이 개발 공수를 초과하면 v2 재검토

---

## 관련 문서

| 문서 | 역할 |
|------|------|
| [workflow_comparison_v2.md](./workflow_comparison_v2.md) | 현재 vs v2 A+D 2-way 비교 (상세) |
| [workflow_comparison.md](./workflow_comparison.md) | Lokalise vs Google Sheet 2-way 비교 (구) |
| [redesign_final.md](./redesign_final.md) | **v2 A+D 최종 추천안 상세** (Phase 0~5 Entry/Exit/롤백) |
| [google_sheet_workflow.md](./google_sheet_workflow.md) | Google Sheet 방식 8 컴포넌트 상세 |
| [l10n_google_sheet_workflow.md](./l10n_google_sheet_workflow.md) | Google Sheet 추가 정보 |
| [translation_pipeline.md](./translation_pipeline.md) | 현재 17단계 파이프라인 (as-is) |
| [case_study_2026-04-17_rev_pollution.md](./case_study_2026-04-17_rev_pollution.md) | 5건 사고 원인 분석 |
| [harness_artifacts/iter-2/](./harness_artifacts/iter-2/) | Iteration v2 Critic 52/60 근거 + Phase 0 handoff |

---

## 한 줄 요약

> **현재**: 월 2건 사고, PM 46분/회, 연 208~512시간 손실.
> **v2 A+D** (권장): 별도 개발 후 사고 0건, PM 시간 +160~320h/년 절감, Lokalise 구독 유지, 번역팀 학습 0.
> **Google Sheet**: 별도 개발 후 사고 0건, PM 시간 +72~211h/년 절감, Lokalise 구독 해지 + **별도 번역 API 필요**, 번역팀 재교육 부담.
> **결론**: **v2 A+D가 프로젝트 제약(Lokalise 유지·VNG·번역팀 UI)에 가장 부합** → Phase 0 착수 권장.

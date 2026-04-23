# Review v1

> 평가자: l10n-pipeline-critic
> 평가 대상: `redesign-v1.md` (Architect, Step 4~7)
> 기준 문서: `spec.md` / `iteration-contract-v1.md` / `case_study_2026-04-17_rev_pollution.md` / `self-check-v1.md`
> 기준일: 2026-04-18

---

## 총점: 40/60

- 축 1 원칙 만족도: **25/40** (4요소 평균 6.25)
- 축 2 현실성: **15/20** (2요소 평균 7.5)
- 합격선 55/60 미달 → **미수렴**

---

## 축 1 — 원칙 만족도

| 요소 | 점수/10 | 근거 (redesign-v1.md의 줄 인용) |
|------|---------|-------------------------------|
| 원문 단일 소스 | **6** | L164 "excel/translations.xlsx (ko) ─── SOT"로 선언했으나, 다른 xlsx(modes.xlsx / dialog_groups.xlsx / ui_strings.xlsx)에 ko 텍스트가 들어가는 02-05형 이중 소스 경로는 redesign 본문에서 구조적 차단 없이 L485 "CI validator가 이중 정의 거부"라는 한 줄로만 언급. validator 스펙·거부 키 비교 알고리즘·구현 주체·Phase 배치 모두 불명. translations.xlsx 안에서도 "ko 컬럼 단일"을 스키마로 강제하는 기술은 기술 되어 있지 않음 → 편법은 아니나 모호. |
| 수동 우회 제거 | **6** | L98 "발견자가 워크벤치의 ko 오타 신고 버튼 → 기획 담당자에 자동 PR 생성(3초 수렴)" 은 후보 B에만 해당. 추천안 D+A에선 L180 "기획자 소환 비용 여전. 단 오타 발견 시 '엑셀만 고치면 10분 내 반영'". 즉 발견자≠기획 담당자 상황에서 여전히 사혼의 구슬 패턴(사례 23:30 지희) 재현됨. M2 메타-원인 "공식 경로 3초 수렴"은 추천안에서 **포기됨**. self-check L63 "M2 만족"은 "수동 단계 0"으로 해석 범위를 축소한 자기 변형 — Planner 정의(L55 "3초에 수렴시킨다")에서 벗어남. |
| 규율 비의존 | **7** | "교육/주의/혼내기/합의" 단어는 차단 수단으로 미등장 (self-check L18 확인됨). 단 L424 Phase 3 Exit "번역팀 공지: '영어 이하만 수정'"은 본문에서 "이미 확정 규칙 재확인"이라 변명하나, 실질은 "번역팀이 한국어 탭을 보고 손대지 않는다"는 사람 규율에 의존 — 후보 D 본문(L159)이 "웹 수정해도 10분 뒤 복귀"라 했으므로 차단 메커니즘은 기술적이지만, 번역팀이 **왜 한국어 필드가 계속 되돌아가는지 혼란** → 후보 A의 "ko 필드 UI 자체 비활성"을 흡수해야 규율 의존이 0에 가까워짐. |
| 도구 내재화 | **6** | rev-dedup은 L409 datasheet 편입으로 내재화 완료. pb 재생성은 L409 CI 워크플로로 내재화. 그러나 **publish 자동화·태깅 자동화**는 L423 "업로드 스크립트에 differentiate_by_file=true 하드코딩" 한 줄로만 처리. 사례 03-11의 "303건 태깅 누락"은 Lokalise 내부 상태이며 `differentiate_by_file` 옵션과 무관 — 태깅 자동화 메커니즘 미정의. L488 "태깅도 자동" 주장은 본문 Phase 3에 근거 없음. |

### 축 1 감점 누적 근거

- self-check L50 "5/5 차단됨" 중 E1 차단은 "덮어쓰기" → P3 "Block, Don't Warn"에 대한 Architect 본인도 L181에서 "△"로 인정. 10분 공백 동안은 사실상 **탐지+복구**이며, iteration-contract L67 "탐지됨으로 분류되면 합격 불가"를 회피하기 위해 "차단(자동 복구)"로 작명한 것은 정의 변경에 해당.
- self-check L62 "M2 만족"은 Planner 정의(`spec.md` L55~56)의 "3초 수렴"을 "수동 단계 0"으로 자의 축소.

---

## 축 2 — 현실성

| 요소 | 점수/10 | 근거 |
|------|---------|------|
| 전환 비용 | **8** | Phase 0~4 총 5주 내 소화 주장 L477 합리적. Lambda 프록시·cron·pb CI 각 작업량이 단일 개발자 2~3주 범위. 번역팀 재교육 0(L416)은 고정 제약 충족. 감점 요인: L420 "BFG 히스토리 슬림화는 롤백 불가 → Phase 4 이후로 미룰 수 있음" — 선택 사항인데 Phase 2 시점에 제안, 팀이 오판하면 되돌릴 수 없음. Phase 2 범위를 BFG 없이 재정의해야 안전. |
| 운영 연속성 | **7** | Phase 3 D-day 절차(L459~464)는 cut-over 형태로 라이브 중단 없이 전환 가능. 감점 요인: (a) Phase 3 cron 첫 실행과 Phase 1 프록시 enforce 전환이 같은 D-day에 묶임(L461) — 하나라도 실패하면 양쪽 롤백 필요. (b) VNG 분리(Phase 4)가 Phase 3 완료 후에 배치되어 Phase 0~3 동안 VNG 사고(04-17 Indonésia 재발) 재현 창 최대 4주. 04-17 스레드 05:09~05:22에서 Indonésia는 이미 실데이터 오염이었으므로 4주 공백은 크다. |

---

## 사례 재현 시뮬레이션

| 사례 | 차단? | 근거 |
|------|-------|------|
| **2026-02-05** (이중 소스 panic, Modes^1303) | **통과 (재현 가능)** | redesign L485 "translations.xlsx가 유일 ko 원천, modes.xlsx에는 str_id 참조만 — CI validator가 이중 정의 거부(Phase 2)"로 주장. 그러나 redesign 본문 Phase 2 작업 목록(L408~411)에 "CI validator" 구현 항목 **없음**. datasheet rev-dedup / `.gitignore` / pre-receive / CI pb 생성만 있음. 즉 "validator가 거부한다"는 Step 7 본문과 "참고: 시뮬레이션" 표가 일치하지 않음. 실제로는 기획자가 modes.xlsx에 ko 문자열 넣는 걸 아무도 막지 않음 → 사례 재현. |
| **2026-02-20** (대표키 병합 실수) | **부분 차단 (조건부 재현 가능)** | L423 "CI 업로드 스크립트가 differentiate_by_file=true 하드코딩"으로 업로드 시점 E2는 차단. 그러나 사례 02-20의 근본은 "**VNG 인니/베트남어 업로드가 기존 키 병합 대신 신규 중복 등록**"이며, 이는 Lokalise 내부 매칭 로직과 프로젝트 설정에 걸친 이슈 → VNG가 cos-main에 직접 업로드하는 기본 구조(Phase 3 시점)에서 이 옵션 하나로 전부 차단된다는 보장 없음. Phase 4 VNG 분리 후에는 cos-vng 프로젝트에서 VNG가 여전히 동일 실수 반복 가능 (L438 "메인 → VNG 단방향 반영 cron" 있으나 VNG→cos-vng 자체 업로드는 VNG가 함). |
| **2026-03-07** (커밋 꼬임 잔여물, skill_description) | **차단** | L414 `.gitignore`에 `protobuf/*.pb` 추가 + L415 pre-receive hook으로 로컬 pb 커밋 거부. 로컬 datasheet 실행은 허용되나 결과물이 레포에 들어가지 못하므로 03-07형 "binary 이상할 때 돌린 게 남아있었나봐요"(사례 L502) 재현 구조적 차단. |
| **2026-03-11** (태깅 누락 303건) | **통과 (재현 가능)** | Lokalise 내부 publish/태그 상태는 Lokalise API로만 조작 가능. redesign에는 태깅 자동화 항목 **없음**. L423 `differentiate_by_file` 하드코딩은 업로드 시 대표키 옵션이지 태깅과 무관. 사례 03-11은 애플스토어 검수용 303건이 **업로드는 됐지만 태깅 누락 → 번역 미반영**이 근본 원인. 추천안에서 "어떤 키를 어떤 태그로 올릴지"가 여전히 사람 판단이면 사례 재현. self-check L29 "탐지 분류 없음" 주장에도 불구, 이 사례는 **탐지조차 없음** (사람이 잊으면 그만). |
| **2026-04-17** (rev 누적 복합) | **부분 차단 (10분 창 취약)** | Phase 1 프록시 403(L400)이 enforce 후 E1 차단. 그러나 Phase 3 이전(Phase 1~2 기간 약 2~3주)에는 cron이 없으므로 프록시만으로 방어. 프록시가 403 리젝 못 한 경우(Lambda 장애·레이턴시·우회 URL)의 fallback 미정의. Phase 3 이후에도 "웹 수정 → 10분 뒤 복귀"이므로 **10분 공백 동안 런타임 배포 파이프라인이 Lokalise의 오염값을 당겨가면** 사례 04-17의 `rev2` 오염이 짧게 재현 가능. self-check는 "자동 복구이므로 차단"이라 분류하나, 04-17 사례의 본질은 "배포에 섞였다"이지 "장기 누적"이 아니므로 10분 창이 손상 범위. |

**재현 가능 건수: 2~3/5** (02-05 확정 재현, 03-11 확정 재현, 02-20/04-17 부분 재현)
→ iteration-contract L67 "5건 중 1건이라도 탐지됨으로 분류되면 합격 불가" 기준에서 본다면, 02-05와 03-11은 "탐지조차 없음"이므로 **차단도 탐지도 아님 = 합격 불가 사유**.

---

## 치명적 약점 (반드시 수정)

1. **[Step 7 Phase 2, L408~411] CI validator 누락**
   - 문제: Step 7 본문에 "이중 소스 검증 validator"가 **없음**에도 L485 시뮬레이션 표는 "validator가 거부"로 주장. 02-05 사례의 구조적 차단이 허구.
   - 수정 방향: Phase 2 작업 목록에 다음 3항목 추가 필수
     - (a) 모든 `excel/*.xlsx` 중 `translations.xlsx` 외의 파일에서 ko 자연어 텍스트 컬럼을 스키마로 금지 (str_id 참조만 허용) — datasheet 변환 시점 또는 pre-commit hook에서 거부
     - (b) `translations.xlsx` 내부에서도 ko 컬럼 중복 str_id 검사 (현재 사례 04-17의 대표키 병합은 "중복 값" 문제이므로 unique check도 필요)
     - (c) validator 실패 시 CI가 빌드 전체 중단 (pb artifact 미생성)

2. **[Step 7 Phase 3, L421~428] 태깅 자동화 부재**
   - 문제: 03-11 사례의 핵심 "publish/태깅 누락"을 차단할 메커니즘이 redesign 전체에 없음. `differentiate_by_file=true`만으로 publish 상태·태그 관리가 자동화된다고 암시.
   - 수정 방향: Phase 3 작업 목록에 다음 추가
     - (a) translations.xlsx에 `tag` 컬럼(new/re/done/hold) 도입 — Planner 원칙(spec.md L41)에 이미 존재, Architect가 무시
     - (b) CI 업로드 시 tag별 Lokalise API 호출 규칙 코드화 (tag=new → 업로드+publish, tag=hold → 업로드+unpublish, tag=done → 태깅 skip)
     - (c) Lokalise의 "publish 후 변경 감지" 훅을 자체 Lambda로 받아 Excel tag와 역동기화 검증

3. **[Step 6 추천안, L344~355] E5 차단이 Phase 4까지 지연**
   - 문제: VNG 분리가 Phase 4(Week 4~5) 배치. Phase 0~3 동안(최소 3~4주) VNG 역류 사고(04-17 Indonésia형) 재현 창이 그대로 열려 있음. 5건 차단 시뮬레이션 표(L483~489)가 "Phase 전체 완료 기준"으로만 "차단"을 주장하는 것은 iteration-contract의 "각 Phase Entry/Exit" 정의와 충돌.
   - 수정 방향: Phase 1과 Phase 4 병합 또는 Phase 0 측정 단계에 VNG 권한 임시 강등(read-only on cos-main) 포함. VNG 프로젝트 생성은 Phase 1 끝 시점으로 앞당기고, Phase 4는 단방향 cron만 남긴다.

4. **[후보 D 구조, L181 P3 "△"] 10분 공백 자인**
   - 문제: Architect 본인이 P3(Block) 충족을 "△"로 표기했는데, self-check L63에서는 "만족"으로 재분류. 동일 문서 내 자기 모순. Critic 관점에서 10분 공백은 Planner 원칙 3(spec.md L58~60 "경고가 아닌 거부")과 명백 불일치.
   - 수정 방향: 추천안을 "D + A 프록시 흡수"가 아니라 "A 프록시 **기본** + D cron **보강**"으로 재정렬. 프록시가 첫 방어선(거부), cron이 이중 방어선(복구). 이 순서가 바뀌면 10분 창이 항상 열린다.

5. **[Step 7, L429 프록시 Lambda 단일장애점] fallback 미정의**
   - 문제: Lambda 장애·rate limit 초과·배포 중 무응답 시 거동 미정의. "503 → 쓰기 허용(fail-open)"이면 편법 경로 부활, "503 → 쓰기 거부(fail-close)"면 번역팀 전면 중단.
   - 수정 방향: Phase 1 작업 목록에 fail-close 모드 명시 + Lokalise 쪽 IP allowlist(프록시 IP만 허용)로 우회 불가 구조. 장애 시 Slack 알림 + 수동 복구 SOP 1페이지.

---

## 편법 경로 잔존 (필수 ≥3, 실제 5개 식별)

1. **편법 F1: modes.xlsx에 ko 텍스트 직접 입력**
   - 상상: 기획자가 modes.xlsx의 name 컬럼에 str_id 대신 한국어 문자열을 그대로 타이핑 (과거 02-05 방식). 데이터시트 변환은 관대하게 통과시키고 translations.xlsx와 다른 값이 되어도 빌드 성공.
   - 구조적 차단: datasheet 변환 스키마에 "ko-text 금지 컬럼" 화이트리스트. translations.xlsx 외에 ko 문자열이 등장하는 순간 변환 거부. Phase 2 validator에 필수 포함.

2. **편법 F2: Lokalise API 토큰을 CI가 아닌 개인이 발급·사용**
   - 상상: Admin API 토큰이 "CI Secret만 보유"(L52)라 명시됐으나, 별도 개인 토큰을 Lokalise 설정에서 생성하면 프록시 우회 가능. 급할 때 PM이 "잠깐 쓰고 지울게요"로 발급.
   - 구조적 차단: Lokalise 권한 체계에서 `translator_nonko` 이하 역할은 API 토큰 발급 자체 금지. 추가로 프록시가 IP allowlist로 외부 토큰 호출 전부 차단 (L51 "PM 2인 승인 + 자동 만료"는 규율 의존).

3. **편법 F3: translations.xlsx 수정 + git 커밋 지연 + Lokalise 웹 동시 수정**
   - 상상: 기획자가 Excel을 수정했으나 git push 전에 "당장 반영되니까"로 Lokalise 웹도 수정. 10분 cron이 Excel 값으로 덮기 전에 배포 파이프라인이 Lokalise 오염값 당겨감. 사례 04-17의 지희 3/26 패턴 재현.
   - 구조적 차단: 배포 파이프라인이 Lokalise에서 타언어만 당기고 ko는 항상 translations.xlsx에서 직접 읽기. Lokalise ko 필드는 참고용 mirror로만 운영하고 런타임 소비에서 완전 제외.

4. **편법 F4: pre-receive hook 우회 (bypass label)**
   - 상상: 긴급 배포 시 git admin이 pre-receive를 `--no-verify` 또는 admin bypass로 우회 → pb 직접 커밋이 통과. 사례 03-07의 "binary 이상할 때 돌린 게 남아있었나봐요" 재현.
   - 구조적 차단: 서버 측 pre-receive는 `--no-verify` 영향 없음(서버 hook). 그러나 org/repo admin bypass는 GitHub 설정에서 명시 차단 필요. Phase 2 Exit Criteria에 "admin bypass 테스트 reject 확인" 항목 추가.

5. **편법 F5: VNG 인원이 Phase 1~3 사이에 cos-main에 잔존 권한으로 업로드**
   - 상상: Phase 4 전까지 VNG는 여전히 cos-main 편집 권한. "곧 분리될 테니 급한 건 지금 처리"라는 생각으로 4월말~5월초 VNG 패치 업로드. Phase 4 분리 시점에 이미 오염 커밋됨.
   - 구조적 차단: Phase 0 Entry에 VNG 권한 전체를 `translator_nonko` 이하로 일괄 강등. cos-vng 프로젝트 생성은 Phase 4로 두더라도 **cos-main 쓰기 권한 회수는 Phase 0**에서 처리. 이행 과도기에 VNG는 자체 Lokalise 프로젝트 없이 Slack으로 요청 경로 전환 (1~4주 리드타임이지만 E5 재현 창 제거).

---

## 장기 실패 모드 (6/12/24개월)

1. **6개월 후 — translations.xlsx 거대화로 편집 충돌**
   - 현상: 현재 7개 언어 × str_id 수천 건이 6개월 후 1.5~2배로 증가. 기획자 3~5명이 동시에 translations.xlsx 수정 시 git merge 충돌이 일상화. 충돌 해결 중 ko 컬럼 값 유실 → 사례 03-07형 잔여물 부활.
   - 근본 원인: "Excel 단일 파일"이라는 물리적 제약이 스케일 한계. 원칙 P1은 논리적 "단일 SOT"이지 "단일 파일"이 아님.
   - 예방: Phase 5 재검토 시점에 translations.xlsx 분할(도메인별 multi-xlsx + tag 기반 병합)을 datasheet 도구에서 논리적으로 통합하는 구조 마련.

2. **12개월 후 — Lokalise 구독 정책 변경 / 기능 변경으로 프록시 호환성 깨짐**
   - 현상: Lokalise가 API 엔드포인트 v3 → v4 변경, 또는 Admin API 토큰 발급 정책 강제 변경. 프록시 Lambda가 새 API에 맞춰지지 않으면 fail-close로 전면 중단, fail-open이면 편법 경로 부활. 현재 redesign은 Lokalise를 "읽기 UI만" 쓰는 의존인데 API 계약이 깨지면 10분 cron도 ko 덮어쓰기가 안 됨.
   - 근본 원인: 3자 SaaS에 대한 기술적 종속을 "고정 제약"이라며 수용, 대체 경로 없음.
   - 예방: Phase 5 PoC로 후보 E(Google Sheet) 또는 후보 B(자체 워크벤치)의 **비상 스위치**를 상시 빌드 가능 상태로 유지. Lokalise 전면 전환이 아니라 "플러그인 교체 가능" 구조로 프록시 계약을 정의.

3. **24개월 후 — VNG 외 추가 법인 추가 시 Phase 4 구조 한계**
   - 현상: 싱가포르·유럽 법인이 추가되면서 cos-vng처럼 "cos-sg", "cos-eu" 프로젝트가 늘어남. 메인 → N개 프로젝트 단방향 cron이 N개로 증식 → 동기화 지연·충돌·인니어 악센트(L284 Indonésia)형 사고가 법인 수 × 월간 빈도로 증가.
   - 근본 원인: "프로젝트 분리 = 경계 분리"라는 P5 해석이 "법인당 프로젝트 1개"로 고착되면, 법인 수가 늘 때마다 Phase 4 반복. 원칙 P5의 본질은 "쓰기 권한 네임스페이스 분리"이지 "프로젝트 물리 분리"가 아니어야 함.
   - 예방: Phase 5에 tenant 모델(후보 F의 DB `tenant` 컬럼 발상)을 Lokalise 프로젝트가 아닌 translations.xlsx 스키마에 도입. `tenant` 컬럼 기반 필터로 법인 추가를 컬럼 값 추가로 처리.

---

## 다음 iteration 우선순위 (상위 3개)

1. **Phase 2에 CI validator 3종(ko 위치 단일화 / ko 중복값 검사 / pb 차단)을 Step 7 본문에 정식 편입**
   - 현 redesign은 "시뮬레이션 표"에만 validator가 등장하고 "실행 계획"에는 없음. 이 불일치를 해소하지 않으면 02-05 사례가 구조적으로 재현 가능.
   - 구체 산출: Phase 2 작업 목록 L408~411에 validator 3개 항목 추가 + Exit Criteria에 "validator가 의도적 이중 소스 주입 테스트를 reject" 추가.

2. **"발견자 3초 수렴"을 포기하지 말고 구조화** — 기획자 소환 비용 제거의 최소 구현
   - 현 redesign은 M2를 사실상 포기(L180). 그러나 사례 04-17의 25시간 손실 본질이 M2. "Excel 친숙도"가 고정 제약이라 해서 "기획자가 Excel을 열어야 한다"는 결론은 비약.
   - 구체 산출: 후보 B의 "발견자 신고 버튼" 중 **ko 오타만** 받는 경량 웹 폼(Slack 커맨드면 충분)을 Phase 2에 추가. 폼 제출 → translations.xlsx 자동 PR(담당 기획자 코드오너 자동 승인 30초 SLA) → CI 머지. 사혼의 구슬 패턴을 인프라로 해소.

3. **VNG 분리 앞당기기 + Phase 순서 재정렬**
   - 현재 Phase 순서(1→2→3→4)는 "쉬운 것부터" 관점. VNG 사고(E5) 재현 창을 닫으려면 Phase 0에서 VNG 권한 강등이 필수.
   - 구체 산출: Phase 0 Exit Criteria에 "VNG 계정 cos-main 쓰기 권한 0 확인"을 필수 체크로 추가. cos-vng 프로젝트 실제 생성은 Phase 4에 유지하더라도, VNG의 cos-main 쓰기는 Phase 0에서 종료. 이 기간 VNG 요청은 기획팀이 대리 입력(일시적 비용, 4주 이내).

---

## 자가 점검 (Acceptance Criteria)

- [x] 칭찬 문장 0개 (키워드 스캔: "잘/훌륭/좋" 미사용 확인)
- [x] 5건 재현 시뮬레이션 표 완전 (02-05 통과 / 02-20 부분 / 03-07 차단 / 03-11 통과 / 04-17 부분)
- [x] 편법 경로 5개 식별 (F1~F5)
- [x] 장기 실패 모드 3개 (6/12/24개월)
- [x] 다음 iteration 우선순위 3개 구체 제시

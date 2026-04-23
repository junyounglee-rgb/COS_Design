# 기획팀 git 실용 가이드
## Cookie Run: Oven Smash — cos-data 저장소

> 작성 기준: 2026-04-04 / 실측 데이터 기반 (release_helsinki3 브랜치)

---

## 왜 이 문서가 필요한가

| 지표 | 실측값 | 의미 |
|------|--------|------|
| 3개월간 Revert 커밋 | **56건** (주 4.7건) | 매주 약 5번 "실수 → 되돌리기" 반복 |
| Revert-Revert 체인 발생 | 소준영, 강준구, 이경우 사례 확인 | Revert가 또 다른 Revert를 낳는 상황 |
| lokalise 자동 sync 커밋 | 3개월간 **92건** | 번역 자동화와 수동 작업 충돌 빈번 |
| 번역 관련 Revert | **11건** | 전체 Revert의 20% |
| 브랜치 직접 push | **98.5%** | 개인 브랜치 없이 바로 release_* 에 push |

이 문서에서 다루는 것들은 **툴 변경 없이, 개발팀 도움 없이** 지금 당장 적용 가능한 것들입니다.

---

## 섹션 1. 커밋 메시지 개선

### 왜 버전 태그가 필요한가

cos-data는 현재 `main`, `release_helsinki3`, `release_helsinki_vng` 등 여러 브랜치가 동시에 운영됩니다. 커밋 메시지만 보고 "이 작업이 어느 버전을 위한 건지"를 알 수 없으면:

- **cherry-pick 시 판단 불가**: H3에만 들어가야 할 데이터가 어떤 커밋인지 알 수 없음
- **Revert 시 범위 판단 불가**: 이 Revert가 H3에만 적용되어야 하는지, VNG에도 해야 하는지 불명확
- **신규 팀원 히스토리 파악 불가**: 3개월 치 커밋 로그를 봐도 "어느 버전 작업인지" 컨텍스트가 없음

```
현재 로그 (버전 정보 없음):
  [추태영]까망베르 밸런스 4차     ← H3 작업? main 작업? VNG도?
  [김율희] 코인사용량 퀘스트 반영 ← 어느 브랜치 기준?

개선 후:
  [H3] 까망베르 밸런스 최종 [Wrike:4421xxx]  ← H3 전용임이 명확
  [ALL] 코인사용량 퀘스트 반영 [Wrike:4428xxx] ← 전 버전 공통임이 명확
```

### 왜 Wrike 번호가 필요한가

데이터 작업은 반드시 Wrike 태스크와 연결되어 있습니다. 번호가 없으면:

- **Revert 후 재작업 시**: "왜 이 데이터를 이렇게 바꿨는지" 기획 의도를 다시 찾아야 함
- **QA 이슈 발생 시**: "이 데이터 변경이 언제 어떤 이유로 들어갔는지" 추적에 수십 분 소요
- **인수인계 시**: 담당자가 바뀌어도 커밋 → Wrike → 기획서 연결이 바로 됨

```
Revert 발생 시 실제 상황 비교:

[이름 prefix만 있을 때]
  "까망베르 밸런스 4차" → 왜 4차까지 갔는지, 최종 의도가 뭔지 알 수 없음
  → 담당자에게 직접 물어봐야 함 (담당자 부재 시 불가)

[버전 + Wrike 있을 때]
  "[H3] 까망베르 밸런스 최종 [Wrike:4421xxx]"
  → Wrike 4421xxx 열면 기획 배경, 승인 이력, 관련 논의 즉시 확인 가능
```

### git 히스토리 = 최고의 패치노트

커밋 메시지 컨벤션이 정착되면 **git 히스토리가 곧 패치노트**가 됩니다.

```bash
# H3 버전에 들어간 변경사항 목록 — 명령어 한 줄
git log --oneline --grep="\[H3\]"

# 출력 예시:
# a1b2c3d [H3] 까망베르 밸런스 최종 [Wrike:4421xxx]
# e4f5g6h [H3] 코인사용량 퀘스트 반영 [Wrike:4428xxx]
# i7j8k9l [H3] 모드 스케쥴 코인러시 추가 [Wrike:4430xxx]
```

이 목록이 그대로 H3 업데이트 패치노트의 뼈대가 됩니다.

| 작업 | 현재 (컨벤션 없음) | 컨벤션 정착 후 |
|---|---|---|
| 패치노트 초안 작성 | 팀원에게 "이번에 뭐 바꿨어요?" 물어보며 수집 | `git log --grep="[H3]"` 한 줄로 목록 추출 |
| 변경 배경 확인 | 담당자 직접 문의 또는 히스토리 추적 | 커밋의 Wrike 번호 → 기획서 즉시 연결 |
| 패치노트 자동화 | 불가 | CI가 배포 시 git log 파싱 → Slack/문서 자동 게시 가능 |

**Wrike 번호가 중요한 이유**: 패치노트는 "무엇이 바뀌었는가"를 보여주지만, 플레이어 문의·QA 이슈·인수인계 시에는 "왜 바뀌었는가"가 필요합니다. Wrike 번호가 그 연결고리입니다.

```
git log → "[H3] 까망베르 밸런스 최종 [Wrike:4421xxx]"
                                              ↓
                              Wrike 4421xxx → 기획 의도 + 밸런스 논의 + 승인 이력
```

> **더 나아가**: 버전태그 + Wrike 컨벤션이 안정되면, CI 배포 완료 시 해당 버전 커밋 목록을 Slack에 자동 게시하거나 Notion 패치노트 페이지에 자동으로 기록하는 것도 어렵지 않습니다.

### 왜 [이름] prefix를 빼야 하는가

git은 작성자를 **자동으로 기록**합니다. `[이름]` prefix는 이 정보의 불필요한 중복이며, 메시지 앞부분을 차지해 정작 중요한 버전 태그와 작업 내용을 읽기 어렵게 만듭니다.

```
git log 실제 기록:
Author: 추태영 <taeyoung@devsisters.com>   ← git이 자동 기록
Date:   Mon Mar 31 ...
    [추태영]까망베르 밸런스 4차             ← 이름 중복 + 버전·Wrike 없음
```

### 개선 규칙

```
형식: [버전태그] 작업내용 [Wrike:번호]

버전태그:
  [H3]   = release_helsinki3
  [H2]   = release_helsinki2
  [MAIN] = main
  [IST]  = istanbul (다음 버전)
  [ALL]  = 모든 버전 공통
  [VNG]  = VNG 버전
  [HF]   = Hotfix (긴급 수정)
  [CI]   = CI 자동 생성 커밋 (사람이 쓰지 않음)
```

### Before / After 예시

| Before (현재) | After (개선) |
|---------------|--------------|
| `[추태영]까망베르 밸런스 4차` | `[H3] 까망베르 밸런스 최종 [Wrike:4421xxx]` |
| `[김율희] 코인사용량 퀘스트 반영` | `[H3] 코인사용량 퀘스트 반영 [Wrike:4428xxx]` |
| `[최희준]모드 스케쥴 데이터 수정` | `[H3] 모드 스케쥴 코인러시 추가 [Wrike:4430xxx]` |
| `[이준영][H3] 옵션 스트링 추가[Wrike:4428009503]` | `[H3] 옵션 스트링 추가 [Wrike:4428009503]` ← 이미 좋은 예시 |
| `번역 적용` | `[H3] translations 번역 최신화 2026-04-04` |

### WIP(작업 중) 커밋 vs 완성 커밋 구분

```
# 작업 중이라 커밋하고 싶을 때 (되도록 피하기)
[WIP][H3] 까망베르 스킬 작업 중 (미완성)

# 완성된 단위로만 커밋하는 것이 원칙
[H3] 까망베르 스킬 최종 [Wrike:4421xxx]
```

**[WIP] 커밋은 push 전에 반드시 정리** (아래 `--amend` 참고)

---

## 섹션 2. 브랜치 전략 — 게임 데이터의 현실

### 개인 브랜치가 코드와 다르게 동작하는 이유

```
코드 브랜치:
  A브랜치: foo.cs 일부 수정
  B브랜치: foo.cs 다른 부분 수정
  → merge 시 git이 라인 단위로 합침 ✅

게임 데이터 현실:
  A브랜치: cookies.xlsx 수정
  B브랜치: cookies.xlsx 다른 쿠키 수정
  → merge 시 "어느 파일 전체를 쓸 것인가?" 양자택일 ❌
     라인 단위 merge 없음, 체리픽 없음
```

**개인 브랜치가 주는 것:**
- CI 실패가 나만의 문제 (팀 전체 blocking 방지) ✅
- 완성 전 데이터가 라이브에 나가지 않음 ✅

**개인 브랜치가 못 주는 것:**
- 같은 파일을 두 사람이 동시에 수정 후 합치기 ❌
- 특정 쿠키 데이터만 체리픽 ❌
- 진정한 병렬 협업 ❌

**결론**: 같은 파일 작업 시 구두 협의("나 오늘 cookies.xlsx 작업해")가 실질적 해결책. 브랜치는 SVN lock의 git 버전일 뿐.

> ⚠️ **feature 브랜치 완료 시 주의**: branch→main 수동 머지 필요. xlsx/pb는 자동 머지 불가이므로 관련 파일 전체를 통째로 덮어쓰는 방식으로 처리.

---

### 현재 권장 방식 (과도기)

G5 파이프라인 전환 전까지는 아래 규칙으로 운영:

```
원칙: 같은 파일은 한 사람씩 순차 작업
      작업 시작 전 팀 채널에 공유 ("cookies.xlsx 작업 시작")
      완료 후 push → 다음 사람 작업
```

```cmd
:: 작업 전 반드시 최신화
git -C "D:/COS_Project/cos-data" pull origin main

:: 수정 후 커밋
git -C "D:/COS_Project/cos-data" add excel/cookies.xlsx
git -C "D:/COS_Project/cos-data" commit -m "[H3] 까망베르 밸런스 최종 [Wrike:4421xxx]"
git -C "D:/COS_Project/cos-data" push origin main
```

---

### 장기 방향: 기획자는 main에서만 작업 (G5 완료 후)

> 이 섹션이 이 문서의 핵심입니다.
> 현재 "브랜치마다 따로 작업 → 수동 동기화"의 근본 문제를 해결하는 구조 변경입니다.

---

#### 지금 무엇이 문제인가

기획자가 데이터를 수정하려면 지금은 이렇게 해야 합니다:

```
1. release_helsinki3으로 브랜치 전환
2. cookies.xlsx 수정
3. datasheet.exe 실행 (전체 pb 재생성, 수 분 소요)
4. commit + push

5. release_helsinki2로 브랜치 전환
6. 같은 내용을 또 수정
7. datasheet.exe 또 실행
8. commit + push

9. release_helsinki_vng도 동일하게 반복...
```

**같은 수정을 브랜치 수만큼 반복해야 합니다.**
브랜치를 깜빡하면 버전 간 데이터가 어긋나고, ui_string_propagate 같은 전파 도구가 필요해진 것도 이 때문입니다.

---

#### G5 이후 기획자의 하루

```
1. main 브랜치 하나에서 cookies.xlsx 수정
2. $filter 컬럼에 이 데이터가 어느 버전부터 적용되는지 표시
3. commit + push
   → 끝.

[CI가 자동으로]
  cookies.xlsx → cookies.csv (텍스트 변환)
  cookies.csv --build HELSINKI_3 → helsinki3.pb → H3 Portal 배포
  cookies.csv --build ISTANBUL_1 → istanbul1.pb → IST1 Portal 배포
  cookies.csv --build VNG        → vng.pb        → VNG S3 배포
```

브랜치 전환 없음. datasheet.exe 로컬 실행 없음. 전파 도구 불필요.

---

#### $filter 컬럼 동작 원리

`keywords.xlsx`의 `build` 시트에 버전별 우선순위가 이미 정의되어 있습니다:

```
LAUNCH_0   = 1          ← 베이스 (모든 버전 공통)
HELSINKI_3 = 1030       ← H3 이상에 적용
ISTANBUL_1 = 2010       ← ISTANBUL_1 이상에 적용
VNG_ONLY   = 9999999999 ← VNG 전용
```

**규칙: 숫자가 높은 $filter가 낮은 $filter를 덮어씁니다.**

예시 — 까망베르 쿠키 HP:

```
| id   | hp  | $filter        | 설명 |
|------|-----|----------------|------|
| 1000 | 100 | $$LAUNCH_0     | 베이스: 모든 버전에서 HP=100 |
| 1000 | 120 | $$HELSINKI_3   | H3 이상에서는 HP=120으로 override |
| 1000 | 150 | $$ISTANBUL_1   | IST1 이상에서는 HP=150으로 override |
```

- H2 빌드: `--build HELSINKI_2` → HP=100 (LAUNCH_0만 적용)
- H3 빌드: `--build HELSINKI_3` → HP=120 (HELSINKI_3이 덮어씀)
- IST1 빌드: `--build ISTANBUL_1` → HP=150 (ISTANBUL_1이 덮어씀)

기획자는 **한 파일 안에 버전별 수치를 모두 관리**합니다. 브랜치를 나눌 필요가 없습니다.

---

#### 왜 CSV를 거치는가

Excel(xlsx)은 binary 포맷이라 git에서 diff/merge가 불가합니다.
CSV는 텍스트이므로 git이 라인 단위로 변경 내역을 추적합니다.

```
현재 (xlsx → pb 직접):
  git diff cookies.xlsx → "Binary files differ" (내용 확인 불가)
  두 브랜치 merge → 충돌 시 수동 선택

G5 이후 (xlsx → csv → pb):
  git diff cookies.csv →
    - id=1000, hp: 100 → 120   ← 무엇이 얼마나 바뀌었는지 한눈에
    + id=1001, hp: 200          ← 새로 추가된 행

  git blame cookies.csv → 누가 언제 이 수치를 바꿨는지 라인 단위로 추적
```

또한 Excel 수식(`=SUM`, `=VLOOKUP`)은 CSV 변환 시 **계산된 값으로 자동 치환**되어, xlmerge가 실패했던 수식 깨짐 문제가 완전히 사라집니다.

---

#### 사라지는 고통들

| 현재 고통 | G5 이후 |
|---|---|
| 브랜치별 반복 작업 (H3, H2, VNG 각각) | main 하나에서만 작업 |
| datasheet.exe 로컬 실행 | CI가 자동 실행 |
| ui_string_propagate 전파 도구 | CI가 $filter 기준으로 자동 처리 |
| `validate_diff.mjs` 전체 팀 push 차단 | pb를 git에 저장하지 않으므로 검증 불필요 |
| git 용량 4.6GB (pb 바이너리 누적) | CSV 텍스트만 저장 → 용량 대폭 감소 |
| "이 수치가 어느 버전에서 바뀌었나" 추적 불가 | `git blame cookies.csv`로 라인 단위 추적 |
| xlmerge 수식 깨짐 | CSV 변환 시 수식 → 값으로 자동 처리 |

---

#### 전제 조건 (개발팀 작업)

기획팀 혼자 할 수 없는 부분이 있습니다:

| 작업 | 담당 | 난이도 |
|---|---|---|
| `datasheet` CSV 입력 지원 추가 | cos-data-manager 팀 | 중간 |
| `datasheet --build {TARGET}` 옵션 추가 | cos-data-manager 팀 | 중간 |
| CI: Excel → CSV 자동 변환 step | CI 관리자 | 낮음 |
| CI: 빌드 타겟별 pb 생성 + Portal 배포 병렬화 | CI 관리자 | 중간 |
| 131개 Excel의 $filter 컬럼 정비 | **기획팀** | 낮음 |

> **기획팀이 지금 당장 할 수 있는 것**: 새 데이터 추가 시 `$filter` 컬럼을 명시적으로 채우는 습관 들이기.
> 이 데이터가 G5 전환 시 그대로 사용됩니다.

---

## 섹션 3. 번역 데이터 — 현재 고충

> 해결 방안 및 새 파이프라인 설계: **`l10n_pipeline_redesign.md`** 참조.

### 담당자 현황

- **번역 파이프라인 전담: 1명 (PM)**
- PM의 본래 업무(기획, 일정 관리, 커뮤니케이션)와 완전히 별개의 성격
- 별도 전문성 없이 수행 중인 **반복 수작업**, 게임 출시/업데이트 주기마다 반복

### 담당자가 매번 수행하는 작업 (1회 기준)

```
1. Fork 실행 → cos-data 최신화
2. Fork → Repository → "번역키 추출 (cos-common)" 버튼 클릭
3. 20초 대기 → exports/ 폴더에 타임스탬프 파일 생성 확인
4. 추출 파일을 7개 카테고리로 수동 분류
   (dialog / cookie / quests / ui / item / skill / etc)
5. lokalise.com 접속 → 프로젝트 선택
6. 카테고리별 파일을 각각 업로드 (설정값 매번 수동 입력)
   - Key → Key 매핑 설정
   - Differentiate keys by file 체크 해제 (안 하면 데이터 오염)
   - Replace modified values 선택
   - Detected language 확인
7. 업로드 완료 알림 확인
8. Sync 페이지 접속 → Email / Branch / Mode 입력
9. "Just Do It" 클릭 → 10분 대기
10. 완료 팝업 확인 → Fork에 자동 푸시됨 확인
```

**1회 소요 시간: 약 30~60분 (오류 발생 시 더 길어짐)**

- 스트링 수정이 발생할 때마다 전 과정 반복
- 런칭/업데이트 시즌: 주 수회 이상 반복
- 긴급 수정(핫픽스): 퇴근 후/주말에도 대응 필요

### 구조적 고충

| 고충 | 내용 |
|---|---|
| **본업 방해** | PM 업무 중 갑자기 번역 요청이 들어오면 하던 일 중단 |
| **단일 장애점** | 담당자 부재(휴가, 병가) 시 번역 파이프라인 전체 중단 |
| **실수 위험** | 설정값 수동 입력 → `Differentiate keys by file` 실수 시 전체 데이터 오염 |
| **충돌 위험** | Sync Lambda push 타이밍이 다른 작업자 작업과 겹치면 git 충돌 → Revert 발생 |
| **확인 부담** | 10분 대기 후 결과 확인을 직접 해야 함 (알림 없음) |
| **의미 없는 전문성** | 번역 내용을 이해하지 못해도 수행 가능한 단순 반복 작업 |

### git 충돌 패턴 (3개월 실측)

```
jihee.ko   Sync lokalise translations at 2026-03-31T14:19:13  ← Sync Lambda 자동 push
이경우     [이경우] translations.xlsx main꺼 가져오기          ← 수동 작업과 타이밍 충돌
강준구     Revert "translations 최신화 (2026-03-22, 02:04)"
강준구     Revert "translations 최신화 (2026-03-22, 02:04)"    ← 동일 Revert 2회
이동성     Revert "[이동성] 번역 데이터 재 업로드"
```

→ 3개월간 번역 관련 Revert **11건** (주 1회꼴)

---

## 섹션 4. 작업 시작 전 체크리스트

매 작업 시작 전 2분 투자:

```
[ ] 1. 최신 상태 pull 했는가?
        git -C "D:/COS_Project/cos-data" pull origin release_helsinki3

[ ] 2. 현재 어떤 브랜치인지 확인했는가?
        git -C "D:/COS_Project/cos-data" branch

[ ] 3. 규모 있는 피쳐 작업인가? (1주 이상, 길드·신규 쿠키 등)
        → YES: git -C "D:/COS_Project/cos-data" checkout -b feat/작업명
        → NO:  main에서 직접 작업 (일상 밸런스·퀘스트 수정은 브랜치 실익 없음)

[ ] 4. Wrike 번호 확인했는가? (커밋 메시지에 포함)

[ ] 5. datasheet.exe 실행했는가? (pb 파일 동기화)
```

### 빠른 상태 확인 명령어

```cmd
:: 현재 상태 한눈에 보기
git -C "D:/COS_Project/cos-data" status

:: 최근 커밋 5개 확인
git -C "D:/COS_Project/cos-data" log --oneline -5

:: 내가 수정한 파일 목록
git -C "D:/COS_Project/cos-data" diff --name-only
```

---

## 섹션 5. $filter 컬럼 — 버전별 데이터 관리 (G5 준비 단계)

> 현재는 datasheet `--build` 옵션 추가가 필요하므로 **준비 단계**입니다.
> `$filter` 컬럼 자체는 이미 xlsx에 존재 — 지금 바로 활용 가능합니다.

### 개념

`$filter` 컬럼은 이미 모든 xlsx에 존재하며, `keywords.xlsx`의 build 시트 값을 참조합니다.

```
현재 방식:
  release_helsinki3/excel/cookies.xlsx  ← 브랜치마다 별도 파일
  release_istanbul1/excel/cookies.xlsx

$filter 컬럼 방식 (G5 목표):
  main/excel/cookies.xlsx 한 파일 안에서:
  | id   | hp  | $filter        |
  | 1000 | 100 | $$LAUNCH_0     |  ← 베이스 (모든 버전 공통)
  | 1000 | 120 | $$HELSINKI_3   |  ← H3에서 override (높은 값이 낮은 값 덮어씀)
  | 1001 | 200 | $$ISTANBUL_1   |  ← IST1 이상에만 존재
```

### keywords.xlsx build 시트 우선순위 체계

| 값 | 적용 범위 |
|---|---|
| `$$LAUNCH_0` (=1) | 베이스 — 모든 버전 공통 |
| `$$HELSINKI_3` (=1030) | H3 이상에서 override |
| `$$ISTANBUL_1` (=2010) | IST1 이상에서 override |
| `$$VNG_ONLY` (=9999999999) | VNG 버전만 |

**높은 값이 낮은 값을 덮어씁니다.** 이미 이 체계가 설계되어 있음.

### 지금 당장 할 수 있는 것

새 데이터 추가 시 `$filter` 컬럼을 명시적으로 입력:
- 모든 버전 공통 → `$$LAUNCH_0`
- H3 이상 전용 → `$$HELSINKI_3`
- VNG 전용 → `$$VNG_ONLY`

CI 자동화(`--build` 옵션)는 cos-data-manager 팀 개발 완료 후 적용 (G5).

---

## 섹션 6. 개발팀 진행 중 항목

아래 항목들은 현재 개발팀과 함께 진행 중이거나 요청된 작업입니다.

| 항목 | 상태 | 비고 |
|---|---|---|
| **datasheet --build 옵션** | 개발 예정 | G5 핵심 — `datasheet.exe --build HELSINKI_3`으로 버전별 pb 생성 |
| **lokalise sync 야간 배치 전환** | 요청 완료 | 업무 시간 자동 sync → 새벽으로 변경, 충돌 방지 |
| **CI 실패 시 Slack 개인 DM 알림** | 요청 중 | 채널 알림 → 본인 직접 알림 |

### 브랜치 일괄 pull 자동화 툴 (개발 중)

여러 브랜치를 순서대로 `pull` 받는 작업이 번거롭고 시간이 오래 걸리는 문제를 해결하기 위해 자동화 툴을 개발 중입니다.

```
ui_string_propagate 툴 (D:\claude_make\ui_string_propagate\)
  ├── 선택한 브랜치 모두 pull 받기  ← 개발 중
  ├── ui_strings.xlsx 브랜치 전파
  ├── datasheet.exe 자동 실행 (xlsx → pb)
  └── 커밋 + push 자동화
```

현재는 브랜치 전파(xlsx 복사 → datasheet → commit → push)까지 지원.
"선택한 브랜치 모두 pull 받기" 기능 추가 작업 중.

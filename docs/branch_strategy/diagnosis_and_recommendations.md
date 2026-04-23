# COS 프로젝트 Git 운영 현황 진단 및 개선 권고

> 작성일: 2026-04-04
> 분석 대상: cos-data, cos-client, cos-common 저장소
> 목적: 현재 git 운영 문제점 실측 기반 진단 + 개선 권고

---

## 1. 현황 진단

### 1-1. 저장소 구조

| 항목 | 실측값 |
|---|---|
| cos-data `.git` 크기 | **4.6 GB** |
| binary 파일 비율 | **47.3%** (xlsx·pb·이미지) |
| 운영 브랜치 | `main` + `release_helsinki2` + `release_helsinki3` + `release_helsinki_vng` |
| release 브랜치가 main보다 뒤처진 커밋 수 | **391 커밋** (3개 브랜치 동일) |

**해석**: binary 파일이 절반 가까이를 차지해 git의 핵심 기능인 머지/diff가 사실상 작동하지 않는 구조.

---

### 1-2. 커밋·PR 패턴

| 항목 | 실측값 | 의미 |
|---|---|---|
| 직접 push 비율 | **98.5%** | PR 문화 없음 |
| PR 머지 수 (6개월) | **29건** | 전체 커밋의 1.5% |
| Revert 커밋 수 | **69건** | "공유 브랜치 실험 후 되돌리기" 패턴 |
| 상위 5명 커밋 집중도 | **57.2%** | 소수 인원 주도 |
| 커밋 prefix 사용률 | **`[이름]` 형태 다수** | SVN 사고방식의 흔적 |

**해석**: PR이 1.5%뿐이라는 것은 코드 리뷰 없이 모든 변경이 공유 브랜치에 직행하고 있음을 의미. Revert 69건은 feature 브랜치 격리 없이 main/release에서 직접 실험하기 때문에 발생.

---

### 1-3. 번역(lokalise) sync 작업 충돌

| 항목 | 실측값 |
|---|---|
| 3개월간 lokalise sync push 수 | **92건** |
| 번역 관련 Revert 수 | **11건** |
| 충돌 원인 | PM의 lokalise Sync 수동 실행 타이밍 ↔ 기획팀 데이터 작업 겹침 |

**해석**: 92건은 자동 push가 아니라 PM이 Sync Lambda를 수동으로 실행할 때마다 발생하는 push. 이 Sync 작업이 진행되는 약 10분간 cos-data에 push가 들어오면 충돌이 발생하며, 기획팀은 이 타이밍을 알 수 없어 Revert가 반복 발생. **Sync 실행 중에는 기획팀이 데이터를 올리지 못하는 사실상의 작업 중단 상태**가 된다.

---

### 1-4. CI 구조 (2026-04-04 분석)

| 파일 | 역할 | 트리거 |
|---|---|---|
| `upload.yaml` | xlsx↔pb 싱크 검증 + Portal/S3 업로드 | 모든 push |
| `validate-translations.yaml` | 번역 충돌 검증 + Slack 알림 | `excel/**`, `translations/**` 변경 시 |
| `etl-delta-lake.yml` | pb → Delta Lake 변환 | release 브랜치 upload 완료 후 |
| `sync-mapdatas.yaml` | MapData → S3 | release 브랜치 `mapdatas/**` 변경 시 |

**핵심 제약 — `validate_diff.mjs` 동작**:
```
./datasheet pb 실행 → 전체 pb 재생성 → git diff로 변경 확인
→ 변경된 pb가 1개라도 있으면 에러 → 전체 팀 push 차단
```

- xlsx만 커밋하고 pb를 안 올리면 → CI 실패 → **전체 팀 push 차단**
- CI runner: 전체 Ubuntu (`blacksmith-4vcpu-ubuntu-2404`)
- `./datasheet`: Linux 바이너리 래퍼 스크립트 (CI에서 정상 실행됨)
- CI는 pb를 생성하지만 **git commit/push는 하지 않음**

---

### 1-5. ui_string_propagate 도구 현황

기획팀이 UI 문자열 xlsx를 여러 release 브랜치에 전파하는 자체 도구.

**현재 방식**:
```
각 target 브랜치마다 반복:
  git checkout {branch}
  → git pull (선행 필수, 뒤처지면 rejected)
  → xlsx 복사
  → datasheet.exe 실행 (전체 pb 재생성)
  → git commit + push
```

**문제점**:

| 문제 | 원인 |
|---|---|
| pull 선행 강제 | 로컬 브랜치가 remote보다 뒤처지면 push rejected |
| datasheet.exe N회 반복 | monolithic 구조 — 브랜치 수만큼 실행 |
| sibling repos 전환 필요 | cos-common, cos-client도 같이 브랜치 전환해야 함 |
| main의 pb를 그냥 복사 불가 | CI validate_diff.mjs가 xlsx↔pb 싱크 재검증 |

---

## 2. 왜 git을 SVN처럼 쓰는가

### 구조적 원인 — 어쩔 수 없이

| 원인 | 내용 | 대안 가능 여부 |
|---|---|---|
| **binary 47.3%** | xlsx·pb는 merge 불가 → branch 격리가 의미 없음 | P6로 장기 해결 가능 |
| **datasheet monolithic** | 모든 xlsx → 모든 pb 한꺼번에 → cherry-pick 불가 | P6로 장기 해결 가능 |
| **CI push 단위 동작** | PR 없이 직접 push해도 검증됨 → PR이 불필요하게 느껴짐 | Branch Protection 설정으로 단기 해결 가능 |
| **release_* = 즉시 라이브** | push = 배포 → PR 리뷰 단계가 비효율로 느껴짐 | 배포 파이프라인 분리로 장기 해결 가능 |

### 문화적 원인 — SVN 사고방식 유지

| 패턴 | 의미 |
|---|---|
| `[이름] 작업내용` 커밋 prefix | "내 작업 영역" 명시 = SVN의 lock 개념 그대로 |
| 공유 브랜치에서 실험 후 Revert 69건 | feature 브랜치로 격리하는 습관 없음 |
| 직접 push 98.5% | PR 경험 없이 온보딩된 팀원이 "이게 정상"으로 학습 |

### 기술적 원인 — 시도했다가 포기 또는 미인지

| 항목 | 상황 |
|---|---|
| **xlmerge** | `.gitattributes` 설정까지 했으나 Excel 수식(`=SUM`, `=VLOOKUP`) 깨짐 → 팀이 포기 |
| **`--amend` / `rebase -i`** | 미활용 → "N차 수정" 커밋 반복 |
| **lokalise 야간 배치** | 낮 시간 자동 sync 유지 → 수동 작업과 반복 충돌 |

---

## 3. 개선 권고 — 번역(스트링) 파이프라인

번역 파이프라인은 규모가 크고 구조적 변화가 필요하여 별도 문서로 분리.

| 항목 | 내용 |
|---|---|
| **진단** | 1-3 lokalise sync 충돌 (Revert 11건, 작업 중단 문제) |
| **단기 대응** | Sync 실행 전 Slack 공지 ("완료까지 cos-data push 보류") |
| **근본 해결** | Google Sheet 기반 통합 번역 파이프라인으로 전환 |
| **상세 내용** | → **`l10n_pipeline_redesign.md`** 참고 |

**번역 파이프라인 전환 시 게임 데이터에 미치는 영향**:
- 번역 pb가 git에서 제거되면 `validate_diff.mjs` 번역 항목 제외 처리 필요
- 번역 관련 `validate-translations.yaml` CI 역할 재검토 필요

---

## 4. 개선 권고 — 게임 데이터 파이프라인

번역 외 모든 기획 데이터(쿠키·스킬·밸런스 등 131개 excel)에 적용되는 개선사항.

---

### G1 — CI가 pb 생성 후 Portal 직접 업로드 (git에서 pb 제거)

**우선순위**: 높음 | **난이도**: 중 | **효과**: 높음

**문제**: 모든 기획 데이터가 번역과 동일한 구조적 문제를 가짐
- xlsx 수정 시 반드시 로컬에서 datasheet.exe 실행 후 pb까지 커밋해야 함
- pb 누락 시 validate_diff.mjs → **전체 팀 push 차단**
- pb 바이너리가 매 커밋마다 누적 → `.git` 4.6GB의 주요 원인

**왜 pb auto-commit(임시방편)이 아닌가**:

| 항목 | pb auto-commit | git pb 제거 (근본) |
|---|---|---|
| `contents: read` 권한 | ❌ `write`로 변경 필요 | ✅ 유지 가능 |
| 무한 루프 리스크 | ❌ `[ci-sync]` 필터로 우회 필요 | ✅ 없음 |
| git 용량 | ❌ 계속 누적 | ✅ 대폭 감소 |
| validate_diff.mjs | ❌ 역할 유지 (의미 없어짐) | ✅ 제거 가능 |

**권고 방향**:
```
현재:
  기획자: xlsx + pb 커밋 → CI validate_diff.mjs → Portal 업로드

개선:
  기획자: xlsx만 커밋
      ↓
  CI: xlsx → pb 생성 → Portal 직접 업로드 (pb는 git에 저장 안 함)
      validate_diff.mjs 역할 자체가 사라짐
```

**효과**:
- 기획자는 xlsx만 커밋 → datasheet.exe 로컬 실행 불필요
- `validate_diff.mjs` 제거 → 전체 팀 push 차단 문제 해소
- git 용량 대폭 감소 (pb 바이너리 누적 중단)
- G2(도구 개선)의 전제 조건

**담당**: CI 관리자(개발팀) + cos-data-manager 팀

---

### G2 — ui_string_propagate 도구 개선

**우선순위**: 중 | **난이도**: 중 | **효과**: 중
**전제 조건**: G1 완료 후 진행

**권고 방향**: xlsx만 GitHub API로 전파 → CI가 pb 자동 생성

| 항목 | 현재 | 개선 후 |
|---|---|---|
| xlsx 전파 방식 | git checkout → pull → copy → commit → push | GitHub API 직접 커밋 |
| pb 생성 | 로컬 datasheet.exe (브랜치 N회) | CI 자동 생성 |
| pull 선행 필요 | 필수 | 불필요 |
| sibling repos 전환 | 필수 | 불필요 |
| 병렬 처리 | 불가 | 가능 |

**새 워크플로우**:
```
[기획팀] xlsx 수정 → main push
[도구 "전파" 클릭] xlsx만 GitHub API로 각 브랜치 직접 커밋
[CI 자동] xlsx 변경 감지 → pb 생성 → Portal 업로드
```

**담당**: 도구 개발 담당

---

### G3 — 커밋 메시지 컨벤션 공식화

**우선순위**: 중 | **난이도**: 낮 | **효과**: 중

**현황**: `[이름][H3] 내용[Wrike:번호]` 형태가 비공식 표준으로 자리잡음

**권고 컨벤션**:
```
[버전태그] 작업 내용 요약 [Wrike:번호]

예시:
[H3] 쿠키 스킬 밸런스 조정 [Wrike:1234]
[HF] 번역 누락 키 추가 [Wrike:5678]
[CI] auto-generate pb from xlsx
```

> `[작업자이름]` prefix 제거 — git이 Author를 자동 기록하므로 불필요한 중복.

**버전 태그 정의**:

| 태그 | 의미 |
|---|---|
| `[H2]` | Helsinki2 버전 |
| `[H3]` | Helsinki3 버전 |
| `[IST]` | Istanbul 버전 |
| `[MAIN]` | main 브랜치 작업 |
| `[VNG]` | VNG 버전 |
| `[ALL]` | 전체 버전 공통 |
| `[HF]` | Hotfix |
| `[CI]` | CI 자동 생성 (사람이 쓰지 않음) |

**담당**: 리드 기획자 (CONTRIBUTING.md 작성 + 팀 공지)

---

### G4 — git worktree로 브랜치 병렬 유지

**우선순위**: 낮 | **난이도**: 낮 | **효과**: 중

**권고**: 각 release 브랜치를 git worktree로 별도 디렉토리에 상시 유지
```bash
git worktree add ../cos-data-h2 release_helsinki2
git worktree add ../cos-data-h3 release_helsinki3
git worktree add ../cos-data-vng release_helsinki_vng
```

**효과**: checkout/pull 없이 여러 브랜치를 동시에 열어두고 작업 가능

**단점**: 디스크 추가 사용 (~수 GB)

**담당**: 개발팀 인프라 담당

---

### G5 — Excel → CSV → pb 파이프라인 전환 + 기획자 main 단일 작업

**우선순위**: 중 | **난이도**: 중 | **효과**: 매우 높음

**현황**: binary 47.3% → git diff/merge 불가, xlmerge 수식 문제로 포기 상태

---

#### 핵심 아이디어: $filter + CSV 중간 포맷

keywords.xlsx의 `build` 시트에 이미 버전별 우선순위 체계가 존재:

```
LAUNCH_0   = 1        ← 베이스 (모든 버전 공통)
HELSINKI_3 = 1030     ← H3 이상에 적용
ISTANBUL_1 = 2010     ← ISTANBUL_1 이상에 적용
VNG_ONLY   = 9999999999
NONE       = 10000000000  ← 항상 포함
```

각 xlsx의 `$filter` 컬럼이 이미 이 값을 참조하고 있음:

```
| id   | hp  | $filter        |
| 1000 | 100 | $$LAUNCH_0     |  ← 베이스
| 1000 | 120 | $$HELSINKI_3   |  ← H3에서 override (높은 값이 낮은 값 덮어씀)
| 1001 | 200 | $$ISTANBUL_1   |  ← ISTANBUL_1 이상에만 존재
```

**높은 $filter 값이 낮은 값을 덮어쓰는 override 규칙이 이미 설계돼 있음.**

---

#### 목표 파이프라인

```
현재:
  release_h3/excel/cookies.xlsx   ← 브랜치별 따로 관리
  release_h2/excel/cookies.xlsx
      ↓ 브랜치별 datasheet 실행

목표:
  main/excel/cookies.xlsx (전체 버전 + $filter 컬럼)
      ↓ CI: Excel → CSV 자동 변환
  main/csv/cookies.csv  ← git에 커밋 (text, diffable)
      ↓ CI: datasheet --input csv --build HELSINKI_3
      ├── helsinki3.pb  → H3 환경 배포
      ├── istanbul1.pb  → IST1 환경 배포
      └── vng.pb        → VNG 환경 배포
```

**기획자는 main에서만 작업. 브랜치 전환 없음.**

---

#### Excel 수식 문제 해소

xlmerge가 실패했던 원인(Excel 수식 `=SUM`, `=VLOOKUP`)은 CSV 변환 시 **계산된 값으로 자동 치환**되어 사라짐 → 문제 자체가 없어짐.

---

#### 해결되는 문제

| 현재 문제 | 전환 후 |
|---|---|
| pb 바이너리 git 누적 (`.git` 4.6GB) | CSV 텍스트만 git 저장 → 용량 대폭 감소 |
| git diff/merge 불가 | CSV는 라인 단위 diff/merge 완전히 작동 |
| xlmerge 수식 깨짐 | 수식 → 값으로 변환 후 CSV 저장, 문제 없음 |
| 브랜치별 xlsx 따로 관리 | main 단일 파일 + $filter로 버전 구분 |
| validate_diff.mjs 전체 팀 push 차단 | git에 pb 없음 → 검증 자체 불필요 |
| 기획자가 브랜치 전환하며 작업 | main에서만 작업, 브랜치 개념 불필요 |
| ui_string_propagate 브랜치 전파 | CI가 $filter 기준 자동 빌드 → 전파 도구 불필요 |

---

#### 필요한 작업

| 작업 | 난이도 | 담당 |
|---|---|---|
| datasheet CSV 입력 지원 추가 | 중간 | cos-data-manager 팀 |
| datasheet `--build {TARGET}` 옵션 추가 | 중간 | cos-data-manager 팀 |
| CI: Excel → CSV 자동 변환 step 추가 | 낮음 | CI 관리자 |
| CI: 빌드 타겟별 pb 생성 + Portal 배포 병렬화 | 중간 | CI 관리자 |
| 131개 Excel의 $filter 컬럼 정비 | 낮음 | 기획팀 |

**담당**: cos-data-manager 팀 (datasheet 수정) + CI 관리자

---

## 5. 실행 로드맵

### 번역 파이프라인 트랙 (대규모, 별도 진행)

상세 내용은 `l10n_pipeline_redesign.md` 참고.

| 단계 | 내용 | 기간 |
|---|---|---|
| **즉시** | lokalise Sync 전 Slack 공지 | 1일 |
| **1~1.5개월** | Google Sheet 기반 L10N 파이프라인 전환 (병행 개발 → cut-over) | 5~6주 |

---

### 게임 데이터 파이프라인 트랙

| 단계 | 항목 | 예상 기간 | 담당 |
|---|---|---|---|
| **즉시 (1주 내)** | G3 커밋 컨벤션 공식화 | 3일 | 리드 기획자 |
| **즉시 (1주 내)** | G4 git worktree 도입 | 1~2일 | 인프라 담당 |
| **단기 (1~2개월)** | G1 CI pb 생성 → Portal 직접 업로드 (git pb 제거) | 2~3주 | CI 관리자 + cos-data-manager |
| **단기 (G1 완료 후)** | G2 ui_string_propagate 도구 개선 | 2~3주 | 도구 개발 담당 |
| **중기 (3~6개월)** | G5 Excel → CSV → pb 전환 + 기획자 main 단일 작업 | 2~3개월 | cos-data-manager 팀 + CI 관리자 |
| **장기 (G5 이후)** | 버전별(release_*) 브랜치 → 피쳐별 브랜치 전략 전환 | G5 완료 후 논의 | 팀 전체 |

> **장기 과제 배경:** 현재 release_* 브랜치는 버전(helsinki, istanbul 등) 단위로 분기. G5 완료 후 기획 데이터가 main 단일 작업 + $filter 구조로 전환되면, 브랜치를 버전이 아닌 피쳐(길드, 신규 쿠키 등) 단위로 운영하는 것이 자연스러워짐. 단, 이는 cos-data뿐 아니라 cos-client·cos-battle-server 등 전체 저장소에 영향을 미치는 팀 전체 과제이므로 G5 완료 이후 별도 논의 필요.

---

## 5. 참고 문서

| 파일 | 내용 |
|---|---|
| `branch_improvement_plan.md` | 기획 데이터 / 코드 관점 개선 방안 상세 (P1~P6) |
| `svn_pattern_analysis.md` | SVN식 git 사용 원인 실측 분석 (커밋 통계, 커밋 패턴 상세) |
| `planning_team_guide.md` | 기획팀 즉시 적용 실용 가이드 (툴 변경 없이 가능한 것들) |

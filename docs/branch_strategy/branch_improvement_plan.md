# cos-data 브랜치 전략 개선 방향

**작성일**: 2026-04-04
**대상 저장소**: cos-data (Cookie Run: Oven Smash 게임 데이터)
**분석 기준 브랜치**: release_helsinki3 (현재 체크아웃)

---

## 현황 분석

### 브랜치 구조

| 브랜치 | 역할 | main 대비 divergence |
|--------|------|----------------------|
| `main` | 최신 개발 기준선 | — |
| `release_helsinki2` | 라이브 ver1 | main 기준 391 커밋 뒤짐 |
| `release_helsinki3` | 라이브 ver2 (현재) | main 기준 391 커밋 뒤짐 |
| `release_helsinki_vng` | VNG 지역 서버 | main 기준 391 커밋 뒤짐 |

> release_helsinki2 / release_helsinki3 divergence 수치가 동일한 것은 두 브랜치가 main으로부터 같은 시점에 분기되었음을 의미함. 이후 각 브랜치에서 독립적으로 커밋이 누적됨.

### 원격 브랜치 현황

- 활성 feature 브랜치 다수 존재 (origin/blackpudding-skill, origin/add-coin-battle-mode2 등)
- 이전 릴리즈 브랜치 잔존 (release-essen, release-fargo, release-geneva, release_dubai, release_helsinki 등)
- 테스트용 브랜치 다수 (test, test-helsinki, test-main 등)

### 기존 CI/CD 구조 (GitHub Actions)

| 워크플로우 | 트리거 | 역할 |
|-----------|--------|------|
| `upload.yaml` | push (전 브랜치) | xlsx↔pb 싱크 검증 → Portal/S3 업로드 |
| `validate-translations.yaml` | push (excel/, translations/ 변경) | 번역키 충돌 감지 |
| `etl-delta-lake.yml` | upload 워크플로우 완료 후 (release_* 브랜치) | Delta Lake ETL |
| `sync-mapdatas.yaml` | (별도) | 맵 데이터 동기화 |
| `integrate-wrike.yml` | (별도) | Wrike 연동 |

### 실측 커밋 패턴 (최근 3개월)

- **총 커밋**: 약 4,221건
- **Revert 커밋**: 56건 (전체의 약 1.3%)
- **작업자 수**: 약 50명 (중복 ID 포함 실질 약 35명)
- **가장 많이 변경된 파일**:
  1. `excel/modes.xlsx` (64회)
  2. `excel/status_effect_values.xlsx` (29회)
  3. `excel/skill_collision_infos.xlsx` (28회)
  4. `excel/product.xlsx` (24회)
  5. `excel/ui_strings.xlsx` (23회)

### 커밋 메시지 현황

- 비표준: `[이름] 작업내용` 형태가 대부분
- 일부 Wrike 연동 커밋: `[이름][H3] 내용 [Wrike:XXXXXXXX]`
- 버전 태그 혼재: `[H3]`, `Helsinki3`, `v03` 혼용

### 핵심 문제

| # | 문제 | 발생 빈도 | 영향 |
|---|------|-----------|------|
| 1 | xlsx↔pb 비동기화로 CI 차단 | 재발 중 | 전체 팀 push 불가 |
| 2 | ui_strings.xlsx 등 공통 데이터 다중 브랜치 수동 전파 | 매일 | 작업 중복, 누락 위험 |
| 3 | 어느 브랜치에 어떤 데이터가 반영됐는지 추적 불가 | 지속 | 릴리즈 리스크 |
| 4 | Revert 남발 (3개월간 56건) | 빈번 | 히스토리 오염 |
| 5 | 커밋 메시지 비표준화 | 항상 | 자동화 어려움 |
| 6 | 브랜치별 독립 xlsx 편집 → merge 불가 상태 | 구조적 | 파이프라인 근본 한계 |

---

## 섹션 1: 기획 데이터 관점 분석

> 관점: 데이터 기획자/운영자가 매일 하는 작업 기준
> 정렬 기준: 작업 난이도 낮음 + 긴급도 높음 순

---

### P1. 커밋 메시지 표준화

| 항목 | 내용 |
|------|------|
| **문제** | 현재 `[이름] 내용` 형태로 작성 중. Wrike 연동이 일부에만 적용되어 히스토리 검색 불가. 브랜치 태그(`[H3]`, `Helsinki3`)도 혼재. |
| **해결방안** | 아래 컨벤션 팀 내 공지 및 PR 템플릿에 예시 삽입 |
| **난이도** | 낮음 (툴 변경 없음, 교육만 필요) |
| **긴급도** | 높음 (다른 모든 자동화의 전제 조건) |
| **기대효과** | Wrike 자동 연동 확대, `git log --grep` 으로 버전별 히스토리 필터링 가능 |

**권장 커밋 메시지 형식**

```
<type>(<scope>): <제목>

Version: v03
Wrike: #XXXXXXXX
```

**type 정의**

| type | 사용 시점 |
|------|-----------|
| `feat` | 신규 데이터 테이블/컬럼 추가 |
| `fix` | 수치 오류 수정 |
| `hotfix` | 라이브 긴급 수정 |
| `data` | 일반 밸런스/운영 데이터 작업 |
| `refactor` | 구조 변경 (기능 변화 없음) |
| `docs` | 번역/텍스트 작업 |
| `chore` | CI 설정, 도구 업데이트 |

**scope 예시**: `monster`, `item`, `char`, `balance`, `ui`, `ci`, `map`, `mode`

---

### P2. CI 차단 사태 재발 방지 (로컬 사전 검증)

| 항목 | 내용 |
|------|------|
| **문제** | `validate_diff.mjs`가 xlsx→pb 재빌드 후 git diff로 비동기화 감지. 로컬에서 pb 재빌드 없이 push하면 CI 차단 발생. 최근 3개월 Revert 56건 중 다수가 이 패턴. |
| **해결방안** | git pre-push hook 로컬 배포로 push 전 자동 검증 |
| **난이도** | 낮음 (스크립트 배포만 필요) |
| **긴급도** | 높음 (이미 전체 팀 차단 사례 발생) |
| **기대효과** | CI 차단 사태 80% 이상 감소 예상 |

**pre-push hook 스크립트** (`D:/COS_Project/cos-data/.git/hooks/pre-push` 또는 팀 공유용 `scripts/pre-push.sh`)

```bash
#!/bin/bash
echo "[pre-push] xlsx↔pb 싱크 검증 중..."
./datasheet -validate=false -strict pb 2>/dev/null
DIFF=$(git ls-files -m 'protobuf/*.pb' | wc -l)
if [ "$DIFF" -gt 0 ]; then
  echo "[오류] pb 파일이 xlsx와 동기화되지 않았습니다."
  echo "  → ./datasheet 실행 후 변경된 pb를 커밋하세요."
  git ls-files -m 'protobuf/*.pb'
  exit 1
fi
echo "[OK] 싱크 정상"
```

> Windows 환경에서는 `manager.exe` 대신 `datasheet.exe` 경로 확인 필요.

---

### P3. 브랜치별 전파 부담 완화 (단기: 수동 절차 문서화)

| 항목 | 내용 |
|------|------|
| **문제** | ui_strings.xlsx, errors.xlsx 등 공통 데이터 변경 시 release_helsinki2, release_helsinki3, release_helsinki_vng 각각에 수동 복사/push 필요. 누락 시 버전별 UI 텍스트 불일치 발생. |
| **해결방안** | 단기: 전파 대상 파일 목록 + 절차 체크리스트 문서화. 중기: 아래 섹션 2 target 컬럼 파이프라인으로 전환. |
| **난이도** | 낮음 (단기 문서화) / 높음 (중기 파이프라인) |
| **긴급도** | 높음 (매일 발생하는 작업 부담) |
| **기대효과** | 단기: 누락 방지. 중기: 전파 작업 자동화로 수동 작업 제거. |

**즉시 적용 가능한 전파 대상 파일 목록 (실측 기반)**

```
공통 전파 필요 파일 (모든 release_* 브랜치):
  - excel/ui_strings.xlsx
  - excel/errors.xlsx
  - excel/translations_ko.xlsx / translations_ja.xlsx 등

버전별 독립 파일 (전파 불필요):
  - excel/modes.xlsx         ← 버전별 스케줄 다름
  - excel/product.xlsx       ← 버전별 상품 다름
  - excel/maps.xlsx 계열    ← 버전별 맵 구성 다름
```

---

### P4. 버전 추적 가시성 확보 (target 컬럼 도입 파일럿)

| 항목 | 내용 |
|------|------|
| **문제** | 어떤 데이터가 어느 라이브 버전에 적용되는지 xlsx 내에서 확인 불가. 기획자가 브랜치 전환 후 직접 확인해야 함. |
| **해결방안** | ui_strings.xlsx에 `target` 컬럼 파일럿 추가 (값: `all` / `v02` / `v03` / `v05+`) |
| **난이도** | 중간 (datasheet.exe 변경 없이 컬럼만 추가하여 시각적 구분 먼저 적용 가능) |
| **긴급도** | 중간 |
| **기대효과** | 기획자가 xlsx 안에서 버전별 데이터 범위 파악 가능. 이후 datasheet --branch 옵션 연계 기반 마련. |

**target 컬럼 값 정의**

| 값 | 의미 |
|----|------|
| `all` | 모든 라이브 버전에 공통 적용 |
| `v02` | release_helsinki2 전용 |
| `v03` | release_helsinki3 전용 |
| `vng` | release_helsinki_vng 전용 |
| `v05+` | 미래 버전 선반영 (main 전용) |

---

### P5. 핫픽스 다중 브랜치 동시 수정 부담

| 항목 | 내용 |
|------|------|
| **문제** | 긴급 수정 시 release_helsinki2, release_helsinki3에 동일 작업 반복. binary 파일이므로 cherry-pick 불가. 파일 복사 후 pb 재빌드 → 각 브랜치 push 필요. |
| **해결방안** | 단기: `scripts/hotfix_propagate.sh` 스크립트 작성으로 절차 자동화. 장기: target 컬럼 파이프라인으로 브랜치별 전파 제거. |
| **난이도** | 중간 |
| **긴급도** | 중간 (발생 시 고통 큼, 빈도는 낮음) |
| **기대효과** | 핫픽스 소요 시간 50% 단축 예상. 실수 방지. |

**핫픽스 전파 스크립트 (개념)**

```bash
# scripts/hotfix_propagate.sh <파일명> <대상브랜치1> <대상브랜치2>
# 예: ./scripts/hotfix_propagate.sh excel/ui_strings.xlsx release_helsinki2 release_helsinki3
FILE=$1; shift; BRANCHES=("$@")
for B in "${BRANCHES[@]}"; do
  git worktree add .worktrees/$B $B
  cp $FILE .worktrees/$B/$FILE
  (cd .worktrees/$B && ./datasheet -validate=false -strict pb && git add excel/ protobuf/ && git commit -m "hotfix: $FILE 전파 from $(git branch --show-current)")
  git worktree remove .worktrees/$B
done
```

---

### P6. 데이터 변경 히스토리 불명확 (버전 추적)

| 항목 | 내용 |
|------|------|
| **문제** | 같은 파일명이 여러 브랜치에 독립 존재. 특정 데이터가 라이브에 언제 반영됐는지 추적하려면 브랜치별 git log를 각각 확인해야 함. |
| **해결방안** | 커밋 메시지에 `Version:` 태그 필수화 (P1과 연계). GitHub Actions에서 `Version:` 태그 파싱하여 Job Summary에 표시. |
| **난이도** | 낮음~중간 |
| **긴급도** | 중간 |
| **기대효과** | 릴리즈 노트 자동 생성 기반 마련. QA 시 버전별 변경사항 즉시 조회 가능. |

---

## 섹션 2: 프로젝트 전체 코드 관점 — Git 전략 파이프라인

> 관점: 개발자/DevOps 기준
> 제약 조건: **pb 파일 형태 변경 불가 (회사 내규)**

---

### 2-1. 단기 전략 (0~2개월)

#### A. CI 격리 정책 강화 — release_* 브랜치 자동 pb 재빌드

**현재 상태**

```
push → upload.yaml → validate_diff.mjs → pb 재빌드 → git diff 감지 → 불일치 시 전체 차단
```

**변경 상태**

```
push → upload.yaml
  ├─ main/feature/*: 기존 validate (차단 유지)
  └─ release_*: pb 자동 재빌드 후 커밋 생성 → 차단 없이 진행
```

**구현 방안**

`upload.yaml`에 release_* 브랜치 전용 분기 추가:

```yaml
- name: Auto-rebuild pb for release branches
  if: startsWith(github.ref, 'refs/heads/release_')
  working-directory: cos-data
  run: |
    ./datasheet -validate=false -strict pb
    DIFF=$(git ls-files -m 'protobuf/*.pb' | wc -l)
    if [ "$DIFF" -gt 0 ]; then
      git config user.email "ci@devsisters.com"
      git config user.name "COS CI Bot"
      git add protobuf/*.pb
      git commit -m "chore(ci): pb 자동 재빌드 [skip ci]"
      git push
    fi
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data |
| **영향 팀** | 전체 (CI 차단 감소 체감) |
| **구현 난이도** | 낮음 |
| **효과** | 높음 (CI 차단 사태 즉시 방어) |
| **위험도** | 낮음 (기존 검증 로직 유지, release_* 에만 적용) |

---

#### B. git worktree 상시 유지로 전파 안정화

**현재 상태**

- 브랜치 전파 시 `git checkout` → 작업 → `git checkout` 반복
- 전환 중 작업 손실 위험, Windows에서 pb 파일 잠금 이슈 발생 가능

**변경 상태**

```
D:/COS_Project/cos-data/              ← main 작업 디렉토리
D:/COS_Project/cos-data-h2/          ← release_helsinki2 worktree (상시)
D:/COS_Project/cos-data-h3/          ← release_helsinki3 worktree (상시)
D:/COS_Project/cos-data-vng/         ← release_helsinki_vng worktree (상시)
```

**설정 명령**

```bash
cd D:/COS_Project/cos-data
git worktree add ../cos-data-h2 release_helsinki2
git worktree add ../cos-data-h3 release_helsinki3
git worktree add ../cos-data-vng origin/release_helsinki_vng
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data |
| **영향 팀** | 기획팀 (전파 작업자) |
| **구현 난이도** | 낮음 |
| **효과** | 중간 (전파 작업 안정성 향상) |
| **위험도** | 낮음 |

---

#### C. Branch Protection Rules 설정

**현재 상태**

- release_* 브랜치에 대한 force-push 방지 규칙 불명확
- 직접 push 허용 여부 불분명

**권장 설정 (GitHub 브랜치 보호 규칙)**

```
대상: release_helsinki*, main

규칙:
  - Require pull request before merging: OFF (데이터 저장소 특성상 직접 push 필수)
  - Require status checks to pass: ON
    - upload.yaml (validate pb sync)
    - validate-translations.yaml
  - Do not allow bypassing: ON (관리자도 동일 규칙)
  - Restrict force pushes: ON
  - Restrict deletions: ON
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data |
| **영향 팀** | 전체 |
| **구현 난이도** | 낮음 (GitHub UI 설정) |
| **효과** | 중간 (브랜치 오염 방지) |
| **위험도** | 낮음 |

---

### 2-2. 중기 전략 (2~6개월)

#### D. datasheet.exe `--branch` 옵션 개발 요청

**현재 상태**

```
datasheet.exe → 모든 xlsx → 모든 pb (monolithic)
```

**변경 상태**

```
datasheet.exe --branch v03 → target=v03 또는 target=all 행만 필터링 → pb 생성
datasheet.exe --branch v02 → target=v02 또는 target=all 행만 필터링 → pb 생성
```

**cos-data-manager 팀 요청 사항**

```
기능: xlsx 내 'target' 컬럼 기반 행 필터링
입력: --branch <브랜치명> or --version <버전태그>
출력: 기존 pb 포맷 유지 (형태 변경 불가 제약 준수)
파일럿 대상: ui_strings.xlsx (가장 전파 부담 높은 파일)
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data-manager (datasheet 소스), cos-data |
| **영향 팀** | 기획팀, 클라이언트팀, 서버팀 |
| **구현 난이도** | 높음 (외부 팀 협의 + 개발 필요) |
| **효과** | 매우 높음 (브랜치 전파 문제 근본 해결) |
| **위험도** | 중간 (파이프라인 전체 영향, 충분한 테스트 필요) |

---

#### E. target 컬럼 기반 단계적 전환 (ui_strings.xlsx 파일럿)

**현재 상태**

```
excel/ui_strings.xlsx (main)
    ↓ 수동 복사
excel/ui_strings.xlsx (release_helsinki2)
excel/ui_strings.xlsx (release_helsinki3)
```

**변경 상태 (파일럿)**

```
excel/ui_strings.xlsx (main 단일 관리)
    ├─ target=all   → 모든 버전 공통
    ├─ target=v02   → release_helsinki2 전용
    └─ target=v03   → release_helsinki3 전용

datasheet --branch v02 → output/v02/ui_strings.pb
datasheet --branch v03 → output/v03/ui_strings.pb
```

**단계별 전환 계획**

```
Step 1: ui_strings.xlsx에 target 컬럼 추가 (기획팀 작업, 1주)
Step 2: datasheet --branch 옵션 개발 완료 후 로컬 테스트 (개발팀, 2주)
Step 3: CI에 --branch 옵션 연동, output/ 폴더 구조 검증 (1주)
Step 4: 클라이언트/서버가 output/v02/, output/v03/ 경로 참조 변경 (2주)
Step 5: 정상 운영 확인 후 modes.xlsx, product.xlsx 등 확대 적용
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data, cos-client, cos-battle-server, cos-town-server |
| **영향 팀** | 기획팀, 클라이언트팀, 서버팀 전체 |
| **구현 난이도** | 높음 |
| **효과** | 매우 높음 |
| **위험도** | 높음 (전체 파이프라인 변경, 단계적 롤아웃 필수) |

---

#### F. output/ 폴더 구조 도입

**변경 상태 (폴더 구조)**

```
cos-data/
  excel/           ← xlsx 원본 (main에서만 편집)
  protobuf/        ← 기존 pb (하위 호환용, 유지)
  output/
    all/           ← target=all 공통 pb
    v02/           ← release_helsinki2 전용 pb
    v03/           ← release_helsinki3 전용 pb
    vng/           ← VNG 전용 pb
  csv/             ← diff 확인용 (서비스 미사용)
    all/
    v02/
    v03/
```

> pb 파일 포맷 자체는 변경 없음. 폴더 분리만 추가.
> 기존 `protobuf/*.pb` 경로는 하위 호환을 위해 유지 (점진적 deprecation).

**CI/CD 파이프라인 재설계**

```
[push to main]
  excel/*.xlsx 변경 감지
    → datasheet --branch all → output/all/*.pb
    → datasheet --branch v02 → output/v02/*.pb
    → datasheet --branch v03 → output/v03/*.pb
    → datasheet --branch vng → output/vng/*.pb
    → csv 생성 (diff 확인용)
    → Portal/S3 업로드

[push to release_*]
  excel/*.xlsx 편집 원칙적 금지
  pb 변경 시 자동 재빌드 (2-1.A 정책)
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data, cos-client, cos-battle-server, cos-town-server |
| **영향 팀** | 전체 |
| **구현 난이도** | 높음 |
| **효과** | 높음 |
| **위험도** | 높음 (경로 변경으로 클라이언트/서버 동시 업데이트 필요) |

---

### 2-3. 장기 전략 (6개월~)

#### G. xlsx는 main 단일 관리 — release_* 브랜치 xlsx 편집 금지

**현재 상태**

```
각 release_* 브랜치에서 xlsx 직접 편집 가능
→ 브랜치별 xlsx divergence 누적
→ merge 불가 상태 고착화
```

**변경 상태**

```
main: xlsx 편집 (유일한 편집 위치)
release_*: pb 파일만 존재 (xlsx 없음 또는 read-only)
```

**단계별 전환**

```
Phase 1: 신규 release 브랜치부터 xlsx 편집 금지 정책 적용
Phase 2: 기존 release_helsinki* 브랜치는 운영 종료 시 자연 소멸
Phase 3: CI에 release_* 브랜치 xlsx 변경 감지 시 경고 추가
```

**CODEOWNERS 설정 (xlsx 편집 제한)**

```
# .github/CODEOWNERS
excel/*.xlsx  @devsisters/data-pipeline-team
```

> release_* 브랜치에서 xlsx 변경 PR 시 data-pipeline-team 승인 필수화로 실수 방지.

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data |
| **영향 팀** | 기획팀 (워크플로우 변화 가장 큼) |
| **구현 난이도** | 중간 (정책 + CI 설정) |
| **효과** | 매우 높음 (브랜치별 divergence 문제 근본 해결) |
| **위험도** | 중간 (기획 워크플로우 변화에 대한 팀 적응 필요) |

---

#### H. 전파 도구 단계적 축소

**현재 상태**

- 수동 전파 (파일 복사 + push)
- 일부 스크립트 존재 추정

**변경 상태 (단계별)**

```
Step 1: hotfix_propagate.sh 스크립트 표준화 (단기)
Step 2: target 컬럼 파이프라인 도입 후 공통 파일 전파 자동화 (중기)
Step 3: release_* 브랜치 xlsx 편집 금지 후 전파 도구 필요 없어짐 (장기)
```

| 구분 | 내용 |
|------|------|
| **구현 난이도** | 낮음 (단계적 자연 감소) |
| **효과** | 높음 |
| **위험도** | 낮음 |

---

#### I. pb 파일 git 관리 → GitHub Actions Artifact 검토 (장기)

> 제약 사항: pb 파일 형태 변경 불가이나 git 저장 위치는 내규에 포함되지 않을 경우 검토 가능.

**현재 상태**

```
pb 파일을 git으로 관리 → 저장소 크기 증가 (binary diff 불가)
→ clone/fetch 속도 저하 우려 (장기)
```

**변경 상태 (검토안)**

```
excel/*.xlsx → GitHub Actions 빌드 → pb → S3/Portal 직접 업로드
git에는 xlsx만 저장

단, pb를 git에서 제거하려면:
  - 클라이언트/서버의 pb 취득 방식 변경 필요
  - 현재 portal 업로드 체계와 중복되므로 실현 가능성 있음
```

| 구분 | 내용 |
|------|------|
| **영향 저장소** | cos-data, cos-client, cos-battle-server, cos-town-server |
| **영향 팀** | 전체 |
| **구현 난이도** | 매우 높음 (저장소 구조 근본 변경) |
| **효과** | 높음 (저장소 크기 감소, binary 충돌 완전 제거) |
| **위험도** | 매우 높음 (사전 충분한 파일럿 필수) |

---

## 우선순위 로드맵

### 단계별 실행 계획

```
0~1개월 (즉시 실행 가능)
  [P1] 커밋 메시지 컨벤션 팀 공지 + PR 템플릿 추가
  [P2] pre-push hook 스크립트 배포 (전팀)
  [B ] Branch Protection Rules 설정 (GitHub UI)
  [B ] worktree 상시 유지 환경 구성 (전파 담당자)

1~2개월
  [P3] 전파 대상 파일 목록 문서화 + hotfix_propagate.sh 작성
  [A ] upload.yaml에 release_* 자동 pb 재빌드 분기 추가
  [P4] ui_strings.xlsx target 컬럼 파일럿 (기획팀 내부)

2~4개월
  [D ] cos-data-manager 팀에 datasheet --branch 옵션 개발 요청 + 요구사항 정의
  [E ] ui_strings.xlsx 파일럿 기반 target 컬럼 전환 테스트
  [F ] output/ 폴더 구조 설계 확정

4~6개월
  [F ] output/ 폴더 구조 도입 + CI 파이프라인 재설계
  [E ] 주요 xlsx 파일 target 컬럼 전환 확대 (modes, product 등)

6~12개월
  [G ] 신규 release 브랜치부터 xlsx main 단일 관리 정책 적용
  [H ] 전파 도구 단계적 축소
  [I ] pb 파일 git 분리 가능성 검토 (팀 협의)
```

### 요약 테이블

| 단계 | 작업 | 난이도 | 효과 | 위험도 | 담당 |
|------|------|--------|------|--------|------|
| 즉시 | 커밋 메시지 컨벤션 | 낮음 | 중간 | 없음 | 기획팀 전체 |
| 즉시 | pre-push hook 배포 | 낮음 | 높음 | 낮음 | DevOps |
| 즉시 | Branch Protection | 낮음 | 중간 | 낮음 | DevOps |
| 1개월 | release_* 자동 pb 재빌드 | 낮음 | 높음 | 낮음 | DevOps |
| 1개월 | worktree 환경 구성 | 낮음 | 중간 | 낮음 | 전파 담당자 |
| 2개월 | target 컬럼 파일럿 | 중간 | 높음 | 중간 | 기획팀 + DevOps |
| 4개월 | datasheet --branch 옵션 | 높음 | 매우높음 | 중간 | cos-data-manager 팀 |
| 6개월 | output/ 폴더 + CI 재설계 | 높음 | 높음 | 높음 | 전체 팀 협의 |
| 12개월+ | xlsx main 단일 관리 | 중간 | 매우높음 | 중간 | 전체 |
| 12개월+ | pb git 분리 검토 | 매우높음 | 높음 | 매우높음 | 아키텍처 검토 |

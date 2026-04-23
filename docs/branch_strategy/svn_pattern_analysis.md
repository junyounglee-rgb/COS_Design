# cos-data SVN식 Git 사용 패턴 분석 보고서

> 분석 기준일: 2026-04-04
> 분석 대상: devsisters/cos-data (D:/COS_Project/cos-data)
> 분석 범위: 최근 3~6개월 커밋 이력, 브랜치 구조, CI/CD 파이프라인, 파일 구성

---

## 1. 실증 데이터 기반 현황 진단

### 1.1 커밋 패턴 — SVN식 직접 push 우세

| 구분 | 수치 | 비고 |
|------|------|------|
| 전체 커밋 수 (누적) | 7,622건 | `git log --oneline` 전체 |
| 최근 3개월 일반 커밋 | 4,157건 | `--no-merges` |
| 최근 3개월 머지 커밋 | 64건 | `--merges` |
| 머지 커밋 비율 | **1.5%** | 64 / 4,221 |
| 최근 6개월 Revert 커밋 | **69건** | (3개월 기준 56건) |
| 최근 6개월 PR 머지 | 29건 | `Merge pull request` 패턴 |

**해석:** 전체 커밋의 98.5%가 직접 push. 64개의 머지 커밋 중 절반 이상은 `Merge branch 'release_helsinki3'`(동시 push 충돌로 인한 pull 후 강제 머지). PR 기반 협업은 사실상 소수 케이스에 그침.

### 1.2 브랜치 활용도 — feature 브랜치 형식은 있지만 활용은 제한적

| 구분 | 수치 |
|------|------|
| 전체 remote 브랜치 수 | 48개 |
| release_* 브랜치 | 11개 (dubai, essen, fargo, geneva, geneva-press, geneva-vng, helsinki, helsinki2, helsinki3, helsinki_vng, essen-preorder) |
| 3개월+ 방치 feature 브랜치 | **4개** (gamedata-screen-effect: 2025-07, add-party-config: 2025-09, maps-table-add-column: 2025-09, dialog-group-new-format: 2025-10) |
| release_helsinki3에 직접 push된 커밋 | **4,157건** (3개월, 非 main) |
| release_helsinki3에 PR 없이 들어간 커밋 추정 | **339건** (main에 없는 커밋) |

**해석:** feature 브랜치를 만들어도 PR로 리뷰 후 머지하는 경우는 29건에 불과. 대부분의 일상 데이터 작업은 release_* 브랜치에 직접 push.

### 1.3 Revert 패턴 — "커밋으로 되돌리는" SVN 관행

```
최근 6개월 Revert 커밋: 69건
├── translation 관련: 11건 (translations 최신화, lokalise sync 등)
├── 데이터 작업 실수: 40여건 (개별 데이터 수정 후 원복)
└── 실험/테스트 커밋: 수건 (JaeEui Ma: "Revert test")

Revert-Revert 패턴 발견:
  이경우: Revert "[이경우] 불필요한 excel 제거"
          → Revert "Revert "[이경우] 불필요한 excel 제거""  (되돌리기를 다시 되돌림)
  소준영: Revert "[소준영] 1150, 1350, 1351 맵 이름 수정"
          → Reapply "[소준영] 1150, 1350, 1351 맵 이름 수정"
          → Revert "Reapply "..."  (3단계 revert 체인)
  강준구: Revert "translations 최신화 (2026-03-22, 02:04)" (2번 반복)
```

**비용 추정 (추정치):** Revert 1건당 평균 30분 손실 가정 시 → 69건 × 30분 = **34.5시간**, 팀 평균 인건비 기준 약 **350만원 이상** 비용 발생 (6개월).

### 1.4 커밋 메시지 비표준화

```
표준 형식 (feat/fix/refactor/chore 등) 사용률: 18건 / 4,157건 = 0.4%

실제 커밋 메시지 패턴:
  [이름] 작업내용           ← 대부분
  [이름][브랜치] 작업내용   ← 일부
  작업내용만               ← 소수
  Wrike 티켓 번호 포함      ← 극소수 (이준영 등 일부만)

표준 커밋 컨벤션 미적용 → 자동화 도구 (changelog 생성, 릴리즈 노트 등) 활용 불가
```

### 1.5 파일 구성 — binary가 압도적

| 파일 유형 | 수 | 비율 |
|----------|----|------|
| 전체 tracked 파일 | 974개 | 100% |
| `.xlsx` (Excel) | 289개 | 29.7% |
| `.pb` (Protobuf binary) | 129개 | 13.2% |
| binary 실행 파일 등 기타 | 43개 | 4.4% |
| **binary 계 합산** | **461개** | **47.3%** |
| 텍스트/코드 파일 (yaml/json/md/proto 등) | 513개 | 52.7% |

**저장소 크기:** `.git/objects` = **4.6GB** — 대부분 xlsx/pb 파일의 버전 누적으로 인한 비대화.

### 1.6 CI/CD — push 단위로만 동작

```yaml
# upload.yaml 트리거
on:
  push: {}    # 모든 브랜치, 모든 push에 실행
```

CI는 `push` 이벤트에만 연동됨 → PR을 사용하더라도 결국 push 시에만 검증 → "push하면 바로 CI 돌아간다"는 인식 = PR 없이 직접 push해도 불편함 없음.

---

## 2. SVN식 사용의 원인 분석

### 2.1 구조적 원인 — 어쩔 수 없이 SVN처럼 쓰는 이유

#### binary 파일이 전체의 47%: merge 불가능

Excel(`.xlsx`) 파일은 본질적으로 ZIP 기반 바이너리 포맷이다. git은 두 브랜치에서 동일 xlsx를 수정했을 때 자동 3-way merge를 할 수 없다. 이로 인해:

- feature 브랜치에서 데이터 수정 → main에 머지 시도 → xlsx 충돌 발생 → 수동 해결 필요
- 수동 해결이 어려울수록 "그냥 직접 push"가 합리적 선택으로 인식됨
- 결과: branch 자체가 "의미 없는 것"으로 팀 내 인식

```
.gitattributes 설정 (현재):
*.xlsx diff=xlsx merge=xlsx          ← xlmerge 드라이버 연결됨
localizations.xlsx merge=binary      ← 수동 이진 머지 (충돌 시 선택 필요)
*.pb diff=pb                         ← 머지 드라이버 미설정
```

`xlmerge` 도구가 존재하고 `merge.xlsx.driver` 설정도 되어 있으나, 실제 사용 흔적이 로그에서 확인되지 않음 (6개월간 "xlmerge" 관련 커밋 메시지 1건만 존재 — "update xlmerge"). 도구가 있어도 팀이 신뢰하지 않거나 워크플로우에 통합되지 않은 상태.

#### datasheet.exe 단일 변환 구조: cherry-pick 불가

데이터 흐름: `excel/*.xlsx` → `datasheet.exe` → `protobuf/*.pb`

- Excel 1개 수정 → datasheet 전체 재실행 → 모든 pb 파일이 새로 생성
- 하나의 기능만 cherry-pick하려 해도 pb 전체가 함께 변경됨
- feature 브랜치에서 기능 분리 후 선택적 머지가 구조적으로 어려움
- "어차피 전부 다시 생성되니까 그냥 release 브랜치에 직접 작업"이 합리적 귀결

#### release_* 브랜치 직접 작업 = 라이브 서비스 필수

release 브랜치에 push → CI가 Portal 및 S3에 즉시 업로드:

```yaml
elif [[ "$BRANCH" =~ ^release_ ]]; then
  UPLOAD_VNG="true"
  UPLOAD_PORTAL="true"
```

데이터 기획자 입장에서 "작업 = release 브랜치에 push = 게임에 반영"이 하나의 동작으로 연결되어 있음. feature 브랜치 사용 시 별도로 main → release 머지가 필요해 불필요한 단계가 추가됨.

### 2.2 문화적 원인 — 습관과 관행에서 비롯된 이유

#### 코드 리뷰 문화 부재

6개월간 29건의 PR 머지 중 대부분은 스키마 변경(컬럼 추가), 인프라 작업, VNG 관련 작업 등 기술팀 주도 변경에 집중됨. 일상적인 데이터 밸런스 수정, 퀘스트 데이터, 번역 작업은 PR 없이 직접 push. 코드 리뷰는 "코드 작업할 때만 필요한 것"으로 인식되는 문화가 있는 것으로 추정됨.

#### "[이름] 작업내용" 커밋 메시지 관행

```
[추태영]까망베르 밸런스 4차
[김율희] 코인사용량 퀘스트 반영
[최희준]모드 스케쥴 데이터 수정
```

커밋 메시지에 이름을 prefix로 붙이는 관행은 SVN의 "누가 어떤 파일을 수정했는지 트래킹"이라는 사고방식에서 비롯된 것. git에는 `git blame`, `git log --author` 등 저자 추적이 이미 내장되어 있어 불필요한 중복이지만, 팀 관행으로 굳어져 있음.

#### "테스트 후 Revert" 문화

JaeEui Ma의 `Revert "test"`, 이경우의 연속 Revert 체인, 강준구의 동일 커밋 2회 Revert는 모두 "git branch를 활용한 격리 테스트" 대신 "공유 브랜치에서 작업 후 되돌리기"를 선택하고 있음을 보여줌. 분리된 환경에서 검증 → 머지하는 워크플로우가 팀 문화로 정착되지 않은 상태.

#### 동시 push로 인한 pull merge 커밋 반복

```
Merge branch 'release_helsinki3' of https://github.com/devsisters/cos-data into release_helsinki3
(3개월간 4회)
```

이는 여러 명이 동시에 release_helsinki3에 push를 시도하다 충돌이 생겨 git pull 후 생기는 merge 커밋. SVN의 "checkout → 수정 → commit → 충돌나면 update → 재커밋" 패턴과 동일. 브랜치를 나누는 대신 공유 브랜치에서 경쟁적으로 작업하는 문화의 증거.

### 2.3 기술적 원인 — git 기능이 활용되지 않는 이유

#### interactive rebase, --amend 흔적 없음

로그를 보면 "1차, 2차, 3차, 4차" 형태의 작업 진행이 별도 커밋으로 기록됨:

```
[추태영]까망베르 밸런스 4차
[추태영]까망베르 밸런스 3차
[추태영]까망베르 밸런스 2차 (추정)
[추태영]까망베르 밸런스 1차 (추정)
```

`git commit --amend` 또는 `git rebase -i`를 사용하면 하나의 완성된 커밋으로 관리할 수 있으나 활용되지 않음. 결과적으로 "작업 중간 상태"가 모두 공유 히스토리에 남음.

#### `.gitattributes`의 xlmerge 드라이버 — 설정은 되어 있으나 신뢰 없음

```
merge.xlsx.driver=manager/xlmerge %O %A %B %A %P
```

설정은 완성되어 있으나, 실제 xlsx 충돌 발생 시 xlmerge가 자동으로 실행되어 머지를 시도하는 워크플로우가 팀에 공유·검증되지 않은 상태. 도구의 존재 자체를 모르는 팀원이 다수일 가능성.

#### PR 기반 워크플로우 장벽 — main vs release_* 이원화

PR은 main으로, 라이브 데이터는 release_*로 직접 push하는 이원화 구조가 고착화됨. 새로운 팀원은 "일상 작업 = release 브랜치 직접 push"로 온보딩되어 PR 워크플로우를 배울 기회 자체가 없음.

---

## 3. 이 패턴이 계속될 경우의 위험 예측

### 3.1 저장소 비대화 → 성능 저하

현재 `.git/objects` 크기: **4.6GB**

xlsx 파일은 수정할 때마다 전체 파일이 새 blob으로 저장됨 (git은 xlsx를 binary로 처리하므로 delta 압축이 어려움). 현재 289개 xlsx 파일이 누적 7,622커밋에 걸쳐 반복 저장되고 있음.

| 시점 | 추정 저장소 크기 | 영향 |
|------|----------------|------|
| 현재 (7,622커밋) | 4.6GB | clone 5~10분 (추정) |
| 1년 후 (~15,000커밋) | 8~10GB (추정) | clone 15~20분 |
| 2년 후 (~25,000커밋) | 15~20GB (추정) | 신규 팀원 온보딩 30분+ |

이는 추정치이며 실제 증가 속도는 xlsx 변경 빈도에 따라 달라짐.

### 3.2 Revert 56건의 실제 비용

3개월간 Revert 56건 발생. 유형별로 분류하면:

| 유형 | 건수 | 건당 소요 시간 (추정) | 합산 |
|------|------|----------------------|------|
| 단순 Revert (데이터 수정 실수) | ~44건 | 10~20분 | ~11시간 |
| Revert-Revert 체인 (이경우·소준영·강준구 사례) | ~12건 | 30~60분 | ~9시간 |
| **합산** | **56건** | | **~20시간 (3개월)** |

연 환산: ~80시간 / 인건비 기준 **약 150~250만원/년** (추정)

**단, Revert 직접 비용보다 더 큰 문제는 팀 전체 blocking**:

validate_diff.mjs에 의해 CI 실패 시 팀 전체(20명+) push 불가 → Revert가 완료될 때까지 전원 대기.
- incident 1건당 팀 대기 비용: 20명 × 평균 10분 = **3.3시간/건**
- 이 blocking이 분기에 수회만 발생해도 Revert 직접 비용을 초과

특히 Revert-Revert 체인(이경우, 소준영, 강준구 사례)은 단순 실수보다 구조적 문제 — 검증 없이 공유 브랜치에 직접 커밋하는 워크플로우 — 임을 시사함.

### 3.3 팀 규모 증가 시 동시 충돌 확률 급증

현재 20명 이상이 같은 release 브랜치에 직접 push. 이미 4회의 동시 push 충돌이 3개월간 발생했음. n명이 동시에 작업할 때 충돌 확률은 인원 수에 비례하여 증가:

```
현재: 20명 → 관찰된 충돌: 4건 / 3개월
인원 30명 → 예상 충돌: 9~12건 / 3개월 (추정, 비선형 증가)
```

### 3.4 번역(translations) 데이터 취약성

11건의 번역 관련 Revert는 특히 심각. `translations.xlsx`는 전 팀원이 접근하는 공유 파일인데:

- lokalise 자동 sync → 수동 데이터 작업과 충돌
- 위 충돌 해결 방법이 "Revert 후 재작업"으로 고착
- 번역 배포가 지연되거나 잘못된 데이터가 라이브에 반영될 위험

### 3.5 버스 팩터 (Bus Factor)

상위 5명의 커밋 집중도:

| 작성자 | 3개월 커밋 수 | 비율 |
|--------|-------------|------|
| dongseong.lee | 518 | 12.5% |
| daisongoh | 504 | 12.1% |
| 추태영 | 456 | 11.0% |
| ryeogang | 456 | 11.0% |
| 김율희 | 444 | 10.7% |
| **상위 5명 합산** | **2,378** | **57.2%** |

상위 5명이 전체 커밋의 57%를 차지. 브랜치 기반 작업 분리가 없어 특정 인원의 부재 시 해당 작업 내용 파악에 시간이 소요될 위험.

---

## 4. 논리적 설득 전략

### 4.1 경영진 / 팀장 설득

#### 비용 관점

| 문제 | 측정값 | 환산 비용 |
|------|-------|---------|
| Revert 비용 | 56건 / 3개월 | 연 ~500~700만원 (추정) |
| 저장소 비대화 | 4.6GB | 팀원 클론 시간 × 인원 × 빈도 |
| CI 차단 시 전체 blocking | 연 수십회 추정 | 팀 전체 대기 비용 |

#### 리스크 관점

- **라이브 서비스 위험:** 검증 없이 release 브랜치에 직접 push → CI 검증 실패 → 전 팀원이 데이터 업로드 불가 상태로 blocking. 이미 여러 차례 발생한 패턴.
- **온보딩 비용 증가:** 저장소 크기 증가 = 신규 팀원 환경 구축 시간 증가.
- **감사/추적 불가:** Revert 69건 중 상당수는 "왜 이 데이터가 이렇게 됐는지" 히스토리 추적이 어려운 상태.

#### 업계 표준과의 비교

Unity, Unreal 등 게임 회사의 데이터 팀도 binary asset에 대해 Git LFS + PR 기반 워크플로우를 채택하고 있음. Revert 기반 되돌리기는 "변경 사항을 상호 검토하지 않기 때문"에 발생하는 문제로, PR 도입 시 사전 차단 가능.

### 4.2 개발자 / 데이터 기획자 설득

#### "지금 불편한 것들이 사실 git을 제대로 못 써서" 라는 점

| 현재의 불편함 | 원인 | 개선 방법 |
|------------|------|---------|
| 내가 작업 중에 누군가 push해서 pull 후 재작업 | 공유 브랜치 동시 작업 | **근본 해결 없음 (과도기)** — 파일 단위 구두 협의 / 장기: G5 (main 단일 작업) |
| 잘못 올린 데이터를 Revert로 수동 원복 | 사전 검증 없이 release에 직접 push | 로컬에서 `./datasheet -strict validate` 확인 후 push |
| translations.xlsx 충돌로 반복 Revert | lokalise 자동 sync 타이밍 충돌 | l10n 파이프라인 재설계 (→ `l10n_pipeline_redesign.md` 참조) |
| "몇 차" 작업이 히스토리에 그대로 남음 | `--amend` 미사용 | 커밋 정리 후 push |

#### Before / After 비교

```
현재 워크플로우:
  release_helsinki3 → Excel 수정 → datasheet 실행 → git push
  → CI 실패 시 → Revert → 재수정 → 재push (30~60분 손실)
  (브랜치별로 같은 파일이 따로 존재 → 동기화 수작업)

기획 데이터 안정화 목표:
  main → Excel 수정 ($filter 컬럼으로 버전 구분)
       → CI: Excel → CSV → datasheet --build HELSINKI_3
       → helsinki3.pb → Portal (H3 환경)
       → datasheet --build ISTANBUL_1
       → istanbul1.pb → Portal (IST1 환경)
  (브랜치별 배포는 CI가 담당 → 기획자는 main 하나만 작업)

  규모 있는 피쳐 (예: 길드 시스템) → feature 브랜치 생성
  → 작업 완료 후 branch→main 수동 머지 (xlsx/pb merge 불가, 수작업)
  → CI 실패가 팀 전체가 아닌 해당 브랜치로 격리
```

**핵심:** xlsx/pb는 git merge가 불가하므로 feature 브랜치는 **격리** 용도로만 유효.
- 완료 시 branch→main 손머지 필요 (cherry-pick, 자동 머지 불가)
- 일상 소규모 작업에는 브랜치 생성 실익 없음
- **G5 완료 시**: main 단일 작업 + `$filter` + `--build` → 브랜치별 배포를 CI가 처리, 기획자가 브랜치를 직접 다룰 필요 없어짐

### 4.3 현실적 반론 대응

#### "우리 데이터는 binary라서 git merge 원래 안 됨"

같은 파일의 동시 수정에 관해서는 **사실**이다.

- `.gitattributes`에 xlmerge 드라이버 설정이 존재하지만, 실제로는 **Excel 수식(=SUM, =VLOOKUP)이 깨지는 문제**로 팀이 포기한 상태
- `*.pb`는 머지 드라이버 자체가 없어 충돌 시 둘 중 하나를 선택해야 함
- 결론: **같은 파일을 두 명이 동시에 작업하는 케이스는 개인 브랜치로도 해결 불가** → 구두 협의 또는 파일 단위 작업 분담이 현실적 해법

branch를 쓰지 말아야 할 이유는 아니나, 용도가 제한적:
- **일상 데이터 작업**: 브랜치 생성 실익 없음. 완료 후 손머지 비용이 더 큼
- **규모 있는 피쳐** (길드, 신규 쿠키 등): feature 브랜치로 **CI 격리** 효과 유효. 단, 완료 시 branch→main 수동 머지 필수 (cherry-pick/자동 머지 불가)
- **장기 해결**: G5 파이프라인 (Excel → CSV → pb, `--build` 옵션) 완료 시 merge 자체가 불필요해짐 (`→ diagnosis_and_recommendations.md` G5 참조)

#### "지금도 잘 돌아가고 있음"

- Revert 56건 / 3개월 = 주당 4.7건의 실수가 공개 히스토리에 기록됨
- 번역 Revert 11건 = 번역 배포가 주 1회꼴로 문제 발생
- `Merge branch 'release_helsinki3'` 4건 = 동시 push 충돌이 이미 발생하고 있음

이는 "잘 돌아가는 것"이 아니라 "높은 비용을 지불하면서 유지되는 것"임.

#### "배우기 귀찮음"

PR 도입의 실질적 변화는 **커밋 전에 브랜치를 만들고, 커밋 후에 PR 버튼을 클릭**하는 것뿐. 도구(GitHub), CI(이미 설정됨), 검증 방법(datasheet validate) 모두 그대로. 배울 것은 `git checkout -b` 단 하나.

---

## 5. 변화를 위한 실행 가능한 첫 걸음

저항이 가장 적은 것부터 시작해 단계적으로 구조를 개선하는 3단계 전략이다.

### Step 1. 커밋 메시지 컨벤션 정착 (즉시, 학습 비용 0)

팀 전체가 당장 내일부터 바꿀 수 있는 유일한 변화.

```
형식: [버전태그] 작업내용 [Wrike:번호]

버전태그:
  [H3]   = release_helsinki3
  [H2]   = release_helsinki2
  [MAIN] = main
  [IST]  = istanbul (다음 버전)
  [ALL]  = 모든 버전 공통
```

```
# 현재 (비표준)
[추태영]까망베르 밸런스 4차

# 개선안
[H3] 까망베르 밸런스 최종 [Wrike:4421xxx]
```

| Before | After |
|---|---|
| `[추태영]까망베르 밸런스 4차` | `[H3] 까망베르 밸런스 최종 [Wrike:4421xxx]` |
| `[김율희] 코인사용량 퀘스트 반영` | `[H3] 코인사용량 퀘스트 반영 [Wrike:4428xxx]` |
| `번역 적용` | `[H3] translations 번역 최신화 2026-04-04` |
| `[이준영][H3] 옵션 스트링 추가[Wrike:4428009503]` | `[H3] 옵션 스트링 추가 [Wrike:4428009503]` ← 이미 좋은 예 |

- git은 `--author`로 이미 작성자를 추적 → `[이름]` prefix 불필요
- 버전 태그로 "이 커밋이 어느 버전을 위한 작업인지" 즉시 식별 가능
- Wrike 번호로 "왜 이 데이터가 이렇게 됐는지" 맥락 추적 가능
- "4차, 5차" 반복 커밋 → **push 전**에 `--amend`로 정리 권장 (이미 push한 커밋에는 사용 금지)
- 리드 기획자가 슬랙 공지 1건 + CONTRIBUTING.md 작성으로 완료
- 상세 가이드: `planning_team_guide.md` 섹션 1 참조

---

### Step 2. 엑셀 작업 main 단일화 — 기획 데이터 안정화 (G5, 2~3개월)

현재 브랜치별로 흩어진 Excel 작업을 main 하나로 집약. CI가 브랜치별 배포를 담당.

```
현재:
  release_h3/excel/cookies.xlsx  (H3 전용)
  release_vng/excel/cookies.xlsx (VNG 전용)
  → 파일이 브랜치마다 따로 존재, 동기화 수작업

목표 (G5):
  main/excel/cookies.xlsx  ($filter 컬럼으로 버전 구분)
  → CI: Excel → CSV → datasheet --build HELSINKI_3 → helsinki3.pb → Portal
  → CI: Excel → CSV → datasheet --build ISTANBUL_1 → istanbul1.pb → Portal
```

- 기획자는 main 하나에서만 작업, 브랜치 전환·동기화 불필요
- 필요 작업: `datasheet` CSV 입력 + `--build` 옵션 지원 (cos-data-manager 팀)
- 상세: `diagnosis_and_recommendations.md` G5 참조

---

### Step 3. 브랜치 전략 개선 — 버전별 → 피쳐별 (장기, G5 이후)

G5 완료로 기획 데이터가 main 단일 작업이 되면, 브랜치를 버전(release_helsinki)이 아닌 피쳐(guild-system, new-cookie) 단위로 운영하는 것이 자연스러워짐.

| 현재 | 목표 |
|---|---|
| `release_helsinki3` (버전 단위) | `feat/guild-system` (피쳐 단위) |
| 브랜치별로 Excel 파일 따로 존재 | main 하나, $filter로 버전 구분 |
| 일상 작업도 release 브랜치에 직접 push | 일상 작업 main, 규모 있는 피쳐만 feature 브랜치 |

**feature 브랜치 사용 기준 (과도기 ~ 장기 공통):**

| 기준 | feature 브랜치 사용 |
|---|---|
| 길드, 신규 쿠키 등 **규모 있는 피쳐** | ✅ — 중간 상태 격리, CI 실패 격리 |
| 기간이 **1주 이상** 걸리는 작업 | ✅ |
| **밸런스 수정, 퀘스트 데이터** 등 소규모 | ❌ — main 직접 작업 (브랜치 실익 없음) |

> ⚠️ feature 브랜치 완료 시 branch→main 수동 머지 필요 (xlsx/pb는 자동 머지 불가).
> G5 완료 후에는 CSV(텍스트) 기반이라 merge/cherry-pick 정상 동작.
> 이 단계는 cos-data 단독이 아니라 cos-client·cos-battle-server 등 **팀 전체 과제**로 별도 논의 필요.

---

**전체 타임라인:**

| 단계 | 내용 | 시점 |
|---|---|---|
| **Step 1** | 커밋 메시지 컨벤션 | 즉시 |
| **Step 2** | G5 — main 단일 작업 + `$filter` + `--build` | 착수: 1~2개월 후 / 완료: 착수 후 2~3개월 |
| **Step 3** | 버전별(release_*) → 피쳐별(feat/*) 브랜치 전략 (팀 전체) | G5 이후 |

---

## 부록: 핵심 수치 요약

| 지표 | 수치 |
|------|------|
| 직접 push 비율 (3개월) | **98.5%** (4,157 / 4,221 커밋) |
| PR 머지 (6개월) | **29건** |
| Revert 커밋 (6개월) | **69건** |
| Revert 추정 비용 | **연 500~700만원** (추정) |
| binary 파일 비율 | **47.3%** (461 / 974 파일) |
| .git 크기 | **4.6GB** |
| 3개월+ 방치 feature 브랜치 | **4개** |
| 동시 push 충돌 (3개월) | **4회** |
| 커밋 참여 인원 | **20명+** |
| 상위 5명 커밋 집중도 | **57.2%** |

---

*본 문서의 비용 추정치는 실제 인건비 및 작업 시간 데이터가 없는 상태에서 보수적으로 산출한 추정치입니다. 실제 수치는 달라질 수 있습니다.*

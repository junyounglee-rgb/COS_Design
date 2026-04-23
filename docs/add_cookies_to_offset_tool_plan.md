# 툴 제작 계획: add_cookies_to_offset.py
> 개발자 에이전트 + QA 에이전트 검토 반영 (2026-04-16)

## 개요
OutGameCookieOffsetForUIData.asset 에 신규 쿠키를 일괄 추가하는 Python CLI 툴.
반복 작업 자동화 · 패널 제외 · 미리보기 · 기본값 설정 지원.

## 파일 위치
- **툴:** `D:\claude_make\tools\add_cookies_to_offset.py`
- **대상:** `D:\COS_Project\cos-client\Assets\GameAssets\Remote\CH_Common\OutGameCookieOffsetForUIData\OutGameCookieOffsetForUIData.asset`
- **백업:** `D:\claude_make\docs\<파일명>_backup_YYYYMMDD_HHMMSS.asset`

---

## CLI 인터페이스

```bash
python add_cookies_to_offset.py [옵션]

필수:
  --cookies CH_A,CH_B,CH_C       추가할 쿠키 리소스 키 (쉼표 구분)

선택:
  --file PATH                    asset 파일 경로 (기본값: 위 대상 경로)
  --exclude-panels P1,P2         제외할 패널명 (쉼표 구분, 이름 기반 매핑)

기본값:
  --scale-offset  1.0            scaleOffset      (기본: 1)
  --position-x    0.0            positionOffset.x (기본: 0)
  --position-y    0.0            positionOffset.y (기본: 0)
  --position-z    0.0            positionOffset.z (기본: 0)
  --rotation-x    0.0            rotationOffset.x (기본: 0)
  --rotation-y    0.0            rotationOffset.y (기본: 0)
  --rotation-z    0.0            rotationOffset.z (기본: 0)
  --accessory     0.0            accessoryOffset  (기본: 0)

실행 제어:
  --preview                      미리보기만 출력 (파일 수정 없음)
  --no-backup                    백업 생략
  --yes                          확인 프롬프트 스킵 (무인 실행)
```

### 사용 예시

```bash
# 기본 실행
python add_cookies_to_offset.py --cookies CH_Licorice,CH_GoatCheese

# SmashPass 패널 제외
python add_cookies_to_offset.py --cookies CH_Licorice \
  --exclude-panels SmashPassPanel,SmashPassPremiumBenefitsPanel

# position Y + scale 적용
python add_cookies_to_offset.py --cookies CH_Licorice --position-y 0.05 --scale-offset 1.1

# 미리보기 (파일 수정 없음)
python add_cookies_to_offset.py --cookies CH_Licorice --preview

# 무인 실행 (CI 등)
python add_cookies_to_offset.py --cookies CH_Licorice --yes --no-backup
```

---

## 모듈 구조

> ⚠️ 개발자 에이전트 검토 반영: `parse_asset()`은 단순 라인이 아닌 **패널 구조체** 반환

```python
# 패널 구조체
Panel = {
    "name": str,        # 패널명 (외부 _keyData 순서 기반)
    "keys": [str],      # 쿠키 리소스 키 목록
    "values": [dict],   # OffsetEntry 목록
    "start_line": int,  # 파일 내 시작 라인 (디버그용)
}
```

```
add_cookies_to_offset.py
│
├── parse_asset(file_path) → List[Panel]
│     외부 _keyData → 패널명 수집
│     내부 섹션 순회 → Panel 구조체 생성
│     반환: 이름 기반 매핑 가능한 Panel 리스트
│
├── validate_pre(panels, cookies, exclude_panels)
│     - 중복 검사: 제외 패널 제외하고, 일부 패널에만 존재하는 partial 상태도 감지
│     - 키=밸류 불일치: 패널명 명시하여 리포트
│     - exclude_panels 중 존재하지 않는 패널명 → 경고 출력 (FAIL 아님)
│     - 쿠키 ID 빈 문자열 / 공백 → FAIL
│
├── preview(panels, cookies, values, exclude_panels)
│     [미리보기] 헤더
│     [제외 패널] 목록
│     [삽입 대상 패널 N개] 테이블: 패널명 / 현재 수 / 삽입 후 수
│     [삽입 값] 쿠키별 모든 offset 값 테이블
│
├── backup(file_path) → backup_path
│     저장: D:\claude_make\docs\<파일명>_backup_YYYYMMDD_HHMMSS.asset
│     동일 타임스탬프 충돌 시 _1, _2 suffix 추가
│
├── insert(file_path, cookies, values, panel_names, exclude_panels)
│     외부 _keyData에서 패널명 리스트 수집 (이름 기반 추적)
│     라인 순회:
│       "      _valueData:" → 현재 패널이 제외 대상 아니면 쿠키 키 삽입
│       "    - _keyData:"   → 이전 패널이 제외 대상 아니면 OffsetEntry 삽입
│     마지막 패널 처리 (제외 여부 확인)
│
├── validate_post(panels_before, panels_after, cookies, exclude_panels)
│     - 모든 대상 패널: 키=밸류 일치
│     - 모든 대상 패널: 신규 쿠키 존재
│     - 제외 패널: 키/밸류 수 변화 없음
│     - 총 삽입 수 = 대상 패널 수 × 추가 쿠키 수 (단순 카운트)
│     - 결과 테이블 출력
│
└── main()
      argparse → 전체 흐름 제어
```

---

## 실행 흐름

```
[1] 인자 파싱 및 기본값 설정
[2] 파일 파싱 → Panel 구조체 리스트
      파일 없음 / 인코딩 오류 → 즉시 FAIL + 메시지
[3] 사전 검증
      FAIL → 리포트 출력 후 exit(1)
[4] 미리보기 출력 (--preview 여부와 무관하게 항상 출력)
[5] --preview 이면 여기서 exit(0)
[6] 확인 프롬프트 (--yes 없으면)
      "위 내용으로 진행합니까? [y/N]: "
      N 입력 → exit(0)
[7] 백업 생성 (--no-backup 아니면)
[8] 삽입 실행
[9] 사후 검증 + 결과 리포트 출력
      FAIL → exit(1)
      PASS → exit(0)
```

---

## 미리보기 출력 예시

```
[미리보기] 추가 예정 쿠키: CH_Licorice, CH_GoatCheese (2개)
           기본값: scale=1  posX=0  posY=0.05  posZ=0
                   rotX=0   rotY=0  rotZ=0     acc=0

[제외 패널] SmashPassPanel, SmashPassPremiumBenefitsPanel (2개)

[삽입 대상 패널 14개]
  패널명                         현재   삽입 후
  CookieListPanel                24     26
  CookieDetailPanel              24     26
  ...
  GameResultPanel                27     29

[삽입 값]
  쿠키            posX  posY  posZ  rotX  rotY  rotZ  scale  acc
  CH_Licorice     0     0.05  0     0     0     0     1.0    0
  CH_GoatCheese   0     0.05  0     0     0     0     1.0    0

계속 진행합니까? [y/N]:
```

---

## 개발 + 테스트 단계

### Phase 1: 파싱 + 사전 검증

**개발**
- `parse_asset()` — Panel 구조체 반환, 이름 기반 매핑
- `validate_pre()` — 중복·partial 중복·키=밸류·쿠키ID 유효성

**테스트 (QA)**

| TC | 입력 | 기대 결과 |
|----|------|----------|
| 정상 파싱 | 현재 파일 | 16패널, 14개×24쿠키, 2개×1쿠키 |
| 중복 쿠키 | 이미 존재하는 쿠키 | FAIL + 패널명 명시 |
| partial 중복 | 일부 패널에만 존재 | FAIL + 해당 패널 목록 |
| 키≠밸류 | 조작된 파일 | FAIL + 패널명 명시 |
| 빈 쿠키 ID | --cookies "" | FAIL |
| 파일 없음 | 잘못된 경로 | FAIL + 경로 출력 |

---

### Phase 2: 미리보기

**개발**
- `preview()` — 제외 패널/대상 패널/값 테이블 출력
- `--preview` 플래그 처리

**테스트 (QA)**

| TC | 입력 | 기대 결과 |
|----|------|----------|
| --preview 실행 | 정상 입력 | 파일 byte 변화 없음 |
| 제외 패널 표시 | --exclude-panels SmashPassPanel | 미리보기에 [제외 패널] 표시 |
| 삽입 후 수 정확성 | 24쿠키 패널 + 2개 추가 | 미리보기에 26 표시 |
| 존재하지 않는 제외 패널 | --exclude-panels NoSuchPanel | 경고 출력 + 계속 |

---

### Phase 3: 삽입 + 백업

**개발**
- `backup()` — 타임스탬프 파일명, 충돌 시 suffix
- `insert()` — 이름 기반 패널 추적, 제외 패널 건너뜀

**테스트 (QA)**

| TC | 입력 | 기대 결과 |
|----|------|----------|
| 백업 생성 | 기본 실행 | .asset 백업 파일 생성 |
| 백업 무결성 | 백업 후 md5 비교 | 원본과 byte 동일 |
| 전체 삽입 | --cookies CH_X | 16패널 모두 키+밸류 +1 |
| 제외 삽입 | --exclude-panels P1,P2 | P1,P2 패널 변화 없음 |
| position-y 적용 | --position-y 0.05 | 삽입된 항목 posY=0.05 |
| 백업 타임스탬프 중복 | 1초 내 2회 실행 | suffix _1 추가된 파일 생성 |

---

### Phase 4: 사후 검증 + 통합 E2E

**개발**
- `validate_post()` — 키=밸류, 신규 쿠키 존재, 제외 패널 불변, 총 삽입 수
- `main()` 전체 흐름 통합
- 확인 프롬프트 + `--yes` 처리

**테스트 (QA)**

| TC | 시나리오 | 기대 결과 |
|----|---------|----------|
| E2E 기본 | 전체 흐름 실행 | PASS 리포트 |
| --yes 무인 실행 | --yes 포함 | 프롬프트 없이 완료 |
| N 입력 | 프롬프트에서 N | 파일 미수정, exit(0) |
| 복합 시나리오 | SmashPassPanel 제외 + --yes + position-y 0.05 | 제외 패널 불변, 나머지 정상 삽입 |
| 롤백 검증 | 삽입 후 백업으로 복원 → md5 비교 → 재삽입 | 원본 복원 확인 + 재삽입 PASS |
| 사후 검증 FAIL | 삽입 후 파일 조작 | FAIL + 리포트 |

---

## 에러 처리 정의

| 상황 | 동작 |
|------|------|
| 파일 없음 / 권한 오류 | FAIL + 경로 출력 |
| 인코딩 오류 | FAIL + "UTF-8로 읽을 수 없음" |
| 쿠키 ID 빈 문자열 | FAIL + "유효하지 않은 쿠키 ID" |
| 중복 쿠키 (전체) | FAIL + 패널 목록 |
| 중복 쿠키 (partial) | FAIL + 존재 패널 / 부재 패널 구분 출력 |
| 키≠밸류 불일치 | FAIL + 패널명 + 키 수 / 밸류 수 |
| 존재하지 않는 제외 패널 | WARNING (FAIL 아님) + 계속 진행 |
| 백업 파일 충돌 | suffix _1, _2 자동 추가 |

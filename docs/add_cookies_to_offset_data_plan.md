# OutGameCookieOffsetForUIData 쿠키 일괄 추가 작업 계획

## 대상 파일
`D:\COS_Project\cos-client\Assets\GameAssets\Remote\CH_Common\OutGameCookieOffsetForUIData\OutGameCookieOffsetForUIData.asset`

## 파일 구조

```
    _valueData:                    ← 외부 _valueData (4칸)
    - _keyData:                    ← 패널 내부 시작 (4칸 + dash)
      - CH_FruitPunch              ← 쿠키 키 (6칸)
      ...
      _valueData:                  ← 내부 _valueData (6칸)
      - _positionOffset: ...       ← OffsetEntry (6칸)
        _rotationOffset: ...       ← (8칸)
        _scaleOffset: X
        _accessoryOffset: X
    - _keyData:                    ← 다음 패널
```

## 실행 순서

### STEP 1: 사전 검증

**체크 1 - 중복 키 검사**
- 추가할 쿠키가 각 패널 _keyData에 이미 있는지 확인
- 발견 시 → 중단

**체크 2 - 키=밸류 일치 검사**
- 각 패널의 _keyData 수 == _valueData 항목 수 확인
- 불일치 시 → 중단

### STEP 2: 삽입 (라인별 처리)

```
inInnerSection = false

각 라인 순회:
  "      _valueData:" (6칸) 발견
    → 쿠키 키 N개 삽입 후 해당 라인 출력

  "    - _keyData:" (4칸+dash) 발견
    → inInnerSection=true 이면: OffsetEntry N개 먼저 삽입
    → inInnerSection = true, 해당 라인 출력

파일 끝: OffsetEntry N개 추가
```

**삽입 쿠키 키:**
```yaml
      - CH_Licorice
      - CH_GoatCheese
      - CH_Prosciutto
```

**삽입 OffsetEntry (scaleOffset=1, 나머지 0):**
```yaml
      - _positionOffset: {x: 0, y: 0, z: 0}
        _rotationOffset: {x: 0, y: 0, z: 0}
        _scaleOffset: 1
        _accessoryOffset: 0
```
→ 추가 쿠키 수만큼 반복

### STEP 3: 사후 검증

- 줄 수 확인: 기존 + (패널 수 × 쿠키 수 × 15줄)
- 16개 패널 모두 새 쿠키 키 존재 확인
- 키 = 밸류 수 일치 확인

---

## 향후 툴 인터페이스 (예정)

```
add-cookies-to-offset-data.py
  --file   OutGameCookieOffsetForUIData.asset
  --cookies CH_Licorice,CH_GoatCheese,CH_Prosciutto
  --scaleOffset 1
  --positionY 0
```

**툴 기능:**
- 사전 검증 자동화 (중복, 키=밸류)
- 삽입
- 사후 검증 리포트
- 백업 파일 자동 생성 (`.asset.bak`)

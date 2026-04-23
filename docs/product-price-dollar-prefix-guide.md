# 상품 가격 `$` prefix 표시 가이드

## 목적
Excel `product.xlsx`의 `general_products` 시트 → `product_base.price_type.payment.product_price`에 입력된 USD 숫자(예: `9.99`)를 **Editor / Dev 빌드에서 `$9.99` 형식으로 표시**.

- 실기기(Google Play / App Store)는 SDK가 로케일별 포맷(`₩9,900`, `$9.99`, `₫230,000`)을 반환하므로 **변경 영향 없음**
- Editor / DevPlay Develop 빌드처럼 SDK가 빈 문자열을 반환하는 **fallback 경로에서만** `$` prefix 적용

---

## 수정 대상

### 파일
`Assets/Scripts/UserState/UserState.Shop.cs`

### 함수
`GetStoreProductPriceString(long productId)`

### 정확한 diff (2줄)

| 라인 | 변경 전 | 변경 후 |
|------|---------|---------|
| 853 | `return UIStrings.Format.Raw.Text(paymentCase.ProductPrice);` | `return UIStrings.Format.Raw.Text($"${paymentCase.ProductPrice}");` |
| 857 | `return UIStrings.Format.Raw.Text(paymentCase.ProductPrice);` | `return UIStrings.Format.Raw.Text($"${paymentCase.ProductPrice}");` |

### 전체 함수 (변경 후)

```csharp
public TString GetStoreProductPriceString(long productId)
{
    if (GameData.Instance.TryGetProductInfoData(productId, out var productInfoData) == false)
        return TString.Empty;

    var productBase = productInfoData.GetProductBase();
    if (productBase == null || productBase.PriceType is not GameData.ProductBase.PriceTypeOneOf.PaymentCase paymentCase)
        return TString.Empty;

    if (SDKManager.HasSingleton == false)
        return UIStrings.Format.Raw.Text($"${paymentCase.ProductPrice}");   // ← 변경

    var productPriceString = SDKManager.Instance.GetProductPriceString(productId);
    if (productPriceString.IsNullOrEmpty())
        return UIStrings.Format.Raw.Text($"${paymentCase.ProductPrice}");   // ← 변경

    return UIStrings.Text(productPriceString);   // SDK 포맷 경로 — 변경 없음
}
```

> `UIStrings.Text(productPriceString);` 라인은 **절대 건드리지 말 것**. 실기기에서 이미 `₩9,900` 같이 포맷된 문자열이 들어오므로 `$`를 붙이면 `$₩9,900` 이중 prefix가 됩니다.

---

## 동작 결과

| 환경 | SDK 반환값 | 변경 전 | 변경 후 |
|------|-----------|---------|---------|
| 실기기 (Google Play KR) | `₩9,900` | `₩9,900` | `₩9,900` (동일) |
| 실기기 (App Store US) | `$9.99` | `$9.99` | `$9.99` (동일) |
| Unity Editor | `""` | `9.99` | **`$9.99` ✅** |
| DevPlay Develop 빌드 | `""` | `9.99` | **`$9.99` ✅** |

---

## 검증 절차

### 1. Unity 컴파일 검증
1. Unity Editor에서 `Ctrl+R` (Refresh) 또는 MCP `Unity_Refresh` 실행
2. `Console`에서 컴파일 에러 0건 확인

### 2. 런타임 확인
1. Unity Editor에서 Play Mode 진입
2. 상점 화면 진입 → 일반 상점 상품 슬롯(`UI_StorePackageSlotProduct`) price 텍스트가 `$9.99` 형식인지 확인
3. 상품 상세 팝업(`UI_StoreGoodsPopup`, `UI_StoreGoodsPopup_S`)도 동일 형식 확인

---

## 다른 PC에 적용하는 방법

### 방법 A: 직접 수정 (가장 간단)
1. `Assets/Scripts/UserState/UserState.Shop.cs` 열기
2. 853, 857 라인을 위 diff대로 수정
3. Unity Refresh로 컴파일 확인

### 방법 B: Git stash 공유
```bash
# 원본 PC에서 stash 저장
cd D:\COS_Project\cos-client
git stash push -m "local: price dollar prefix" Assets/Scripts/UserState/UserState.Shop.cs
git stash show -p stash@{0} > price-dollar-prefix.patch

# 다른 PC에서 patch 적용
git apply price-dollar-prefix.patch
```

### 방법 C: 로컬 전용 유지 (권장)
이 변경은 **커밋하지 않는 로컬 전용 수정**이므로, 브랜치 전환 시 손실 방지를 위해:

```bash
# 작업 시작 전 stash로 보관
git stash push -m "local: price dollar prefix" Assets/Scripts/UserState/UserState.Shop.cs

# 브랜치 전환 후 복원
git stash pop
```

---

## 브랜치 전환 시 주의사항

- 이 변경은 **커밋하지 않은 로컬 수정**입니다.
- `git checkout` / `git pull` 시 **충돌 또는 덮어쓰기** 가능성이 있습니다.
- 브랜치 전환 전에는 항상 `git stash push ...` 로 보관하거나, 별도 patch 파일로 백업하세요.

---

## 변경하지 않은 파일 (참고)

다음 파일들은 **절대 수정하지 않음**:

| 파일 | 이유 |
|------|------|
| `cos-data/excel/product.xlsx` | `product_price`는 서버 가격 검증용 숫자(USD). 문자열에 `$` 섞으면 검증 파이프라인 파손 |
| `cos-battle-server/cos-common/gamedata/product.proto` | 스키마 불변. `product.proto:196-197` 주석 참고 |
| `UI_StoreCurruncy.cs` | TString을 그대로 `_priceText.SetText`에 전달 — 자동으로 `$9.99` 표시됨 |
| `UI_StorePackageSlotProduct.cs`, `UI_StoreGoodsPopup*.cs` | `GetStoreProductPriceString` 결과를 투명하게 전달하므로 수정 불필요 |

---

## FAQ

**Q. `product_price`가 비어있는 상품은?**
A. 현재도 `""` (빈 문자열)로 표시됩니다. 변경 후에는 `$` 단독 표시. 필요 시 `string.IsNullOrEmpty()` 체크 추가 가능.

**Q. 향후 KRW/JPY 등 다른 통화 지원이 필요해지면?**
A. 현재는 USD 고정이라 OK. 확장 시 `UIStrings.Format.UsdPrice` 전용 format을 `UIStrings.AdditionalData.cs`에 추가하는 2단계 리팩토링 권장.

**Q. 인게임 재화(젤리 등)로 구매하는 상품도 `$`가 붙나?**
A. 아니요. `price_type`이 `PriceItem`인 상품은 `UI_StorePackageSlotProduct.cs:138-139`에서 별도 경로로 처리되므로 영향 없음.

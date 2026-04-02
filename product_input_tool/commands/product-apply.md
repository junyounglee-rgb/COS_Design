상품 입력 템플릿 → product.xlsx 적용.

**사용법:** `/product-apply [mode]`

- `mode` 생략 시 `all` (전체 타입)
- `mode`: `all` | `일반` | `조건부` | `출석` | `월정액` | `패스` | `스텝`

---

1. 실행:
   ```
   python make_outgame/product/apply-product-input.py <mode>
   ```
   - `mode` 미입력 시 `all` 사용
   - 템플릿 경로 기본값: `make_outgame/product/product-input-template.xlsx`

2. 동작:
   - 제작완료=TRUE 행 스킵
   - 상품ID 비어있으면 product_infos 최대 key+1 자동 할당
   - product_infos + 타입별 시트에 행 삽입
   - 적용 완료 행 → 템플릿 제작완료=TRUE 기입
   - product.xlsx + template.xlsx 모두 저장

3. 출력:
   - 추가된 상품 key + 상품명 목록
   - 총 추가 건수

4. 적용 후:
   - `datasheet.exe` 실행하여 protobuf 변환 필요
   - 변환 후 커밋 및 푸시

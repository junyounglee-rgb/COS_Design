상품 입력 템플릿 생성 (keywords/items 동적 최신화).

**사용법:** `/product-gen`

---

1. worktree 경로 확인:
   - 현재 작업 중인 worktree 기준 `make_outgame/product/gen-product-template.py` 경로 찾기
   - `REPO_ROOT` = 해당 스크립트 기준 3단계 상위 (cos-data 루트)

2. 실행:
   ```
   python make_outgame/product/gen-product-template.py
   ```

3. 출력:
   - 로드된 키워드 수, 아이템 수, 서브카테고리 수, 뱃지/태그 수
   - 저장 경로: `make_outgame/product/product-input-template.xlsx`
   - 총 탭 수 (참조 탭 5개 + 입력 탭 6개 = 11개)

4. 완료 후 안내:
   - 생성된 템플릿 파일 경로 출력
   - 기획자는 해당 파일을 열어 입력 탭에 상품 정보 입력 후 `/product-apply` 실행

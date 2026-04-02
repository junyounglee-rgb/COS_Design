# spec001 — product_input_tool 스펙

## 개요

| 항목 | 내용 |
|------|------|
| 프로젝트 | Cookie Run: Oven Smash (COS) — cos-data 저장소 |
| 목적 | 기획자가 Excel 템플릿에 상품 데이터 입력 → product.xlsx에 자동 삽입 |
| 작성일 | 2026-04-02 |
| 작성자 | 이준영 (기획), Claude Code (구현) |

## 대상 상품 타입

| 탭명 | product_type | 대상 시트 |
|------|-------------|----------|
| 출석패키지 | PRODUCT_TYPE_ATTENDANCE_PRODUCT | product_infos + attendance_product + attendance_product_rewards |
| 일반상품 | PRODUCT_TYPE_GENERAL_PRODUCT | product_infos + general_store_products_shop |
| 조건부상품 | PRODUCT_TYPE_CONDITIONAL_PRODUCT | product_infos + conditional_products |
| 월정액 | PRODUCT_TYPE_DAILY_REWARD_PRODUCT | product_infos + daily_reward_product |
| 프리미엄패스 | PRODUCT_TYPE_PREMIUM_PASS_PRODUCT | product_infos + premium_pass_product |
| 스텝상품 | PRODUCT_TYPE_STEP_PRODUCT | product_infos + step_products |

## 파일 구성

```
make_outgame/product/
├── gen-product-template.py       # 템플릿 생성 스크립트
├── apply-product-input.py        # 템플릿 → product.xlsx 삽입 스크립트
└── product-input-template.xlsx   # 생성된 입력 템플릿 (gen 실행 출력물)

~/.claude/commands/
├── product-gen.md                # /product-gen 슬래시 커맨드
└── product-apply.md              # /product-apply 슬래시 커맨드
```

## gen-product-template.py

- keywords.xlsx, items.xlsx, product.xlsx에서 참조 데이터 동적 로드
- 11탭 Excel 템플릿 생성

### 참조 탭 (5개)

| 탭명 | 소스 | 내용 |
|------|------|------|
| 📖 안내 | 하드코딩 | 사용법 가이드 |
| 📖 키워드 | keywords.xlsx/timestamp | 판매기간 키워드 + KST 변환 / keywords.xlsx/build → $filter 빌드 목록 (E열) |
| 📖 아이템 | items.xlsx/items | 아이템 key, 이름, 카테고리 |
| 📖 서브카테고리 | product.xlsx/product_sub_categories | 서브카테고리 목록 |
| 📖 뱃지태그 | product.xlsx/badge_infos, tag_infos, popup_deco_info | 뱃지/태그/팝업 목록 |

### 입력 탭 공통 기능

- 드롭다운: slot_type, description_type, price_type, store_type, refresh_type, 판매기간 키워드, $filter 빌드
- XLOOKUP: 판매시작/종료 → KST 자동 표시 / 아이템ID → 아이템명 자동 표시
- 색상 구분: 필수(연분홍), 선택(연파랑), 자동입력(회색/연황색)
- 제작완료: apply 후 TRUE 자동 기입, 재실행 시 스킵

### 주요 상수

```python
REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # cos-data 루트
MAX_DATA_ROW = 203      # 최대 입력 행 (row4~203)
ATTENDANCE_DAYS = 30    # 출석패키지 일수
ATT_ITEMS_PER_DAY = 3   # 일차별 아이템 수
STEP_COUNT = 3          # 스텝상품 최대 스텝 수
STEP_ITEMS = 4          # 스텝당 최대 아이템 수
```

### BASE_HEADERS 구조 (C1~C36)

| 열 | 헤더 | 대상 시트 필드 |
|----|------|--------------|
| C1 | 상품ID (비우면 자동) | product_infos.^key |
| C2 | $filter | product_infos.$filter |
| C3 | 서브카테고리ID | product_infos.ref_sub_category_id |
| C4 | 슬롯크기 | product_infos.slot_type |
| C5 | 슬롯 썸네일 | product_infos.slot_thumb_img |
| C6 | 정렬순서 | product_infos.order |
| C7 | 팝업 리소스키 | product_infos.product_popup_resource_key |
| C8 | 팝업 썸네일 | product_infos.popup_thumb_img |
| C9 | 뱃지ID | product_infos.badge_info_id |
| C10 | 태그ID | product_infos.tag_info_id |
| C11 | 슬롯 FX ID | product_infos.slot_fx_info_id |
| C12 | 팝업 FX ID | product_infos.popup_fx_info_id |
| C13 | 검수모드 노출 | product_infos.show_review |
| C14 | 구성품 노출 | product_infos.show_goods |
| C15 | 설명타입 | product_infos.description_type |
| C16 | 상품명 | product_base.product_name |
| C17 | 부제 | product_base.product_sub_name |
| C18 | 설명 | product_base.description |
| C19 | 팝업 설명 | product_infos.product_popup_description |
| C20 | 판매시작 키워드 | product_base.start_timestamp |
| C21 | [판매시작 KST] | XLOOKUP 자동 |
| C22 | 판매종료 키워드 | product_base.end_timestamp |
| C23 | [판매종료 KST] | XLOOKUP 자동 |
| C24 | 구매횟수제한 | product_base.purchase_count_limit |
| C25 | 활성화 | product_base.available |
| C26 | 매진시노출 | product_base.is_show_when_sold_out |
| C27 | 결제방식 | price_type.%key |
| C28~C33 | p1~p6 | price_type.%param1~6 |
| C34 | 리프레시 방식 | refresh_config.%key |
| C35 | 리프레시 주기 | refresh_config.%param1 |
| C36 | 리프레시 기준 | refresh_config.%param2 |

> BASE_NO_REFRESH_HEADERS = C1~C33 (출석/월정액/패스 탭 사용)

### 타입별 추가 열

| 타입 | 추가 열 범위 | 제작완료 열 |
|------|------------|-----------|
| 일반상품 | C37~C51 (아이템 5개 × 3열: id+[name]+qty) | C52 |
| 조건부상품 | C37~C51 (아이템 5개) + C52 valid_time + C53 trigger_cooltime + C54 ref_unlock_condition_id | C55 |
| 출석패키지 | C34 reward_until_days + C35 mail_template_id + C36~C215 (30일 × 3아이템 × 2열) | C216 |
| 월정액 | C34 period_days + C35 repurchase + C36 mail + C37 mail_bonus + C38~C46 즉시지급 + C47 daily_key + C48~C49 daily_params + C50~C52 bonus_item | C53 |
| 프리미엄패스 | C34 product_id + C35~C43 즉시지급 | C44 |
| 스텝상품 | C37~C78 (3스텝 × 14열) | C79 |

## apply-product-input.py

```bash
python make_outgame/product/apply-product-input.py <mode> [template.xlsx]
# mode: all | 일반 | 조건부 | 출석 | 월정액 | 패스 | 스텝
```

### 동작 순서

1. 템플릿 해당 탭에서 row4+ 읽기
2. 제작완료=TRUE인 행 스킵
3. 상품ID 비어있으면 product_infos 최대 key+1 자동 할당
4. product_infos 행 삽입 (product_type 자동 설정)
5. 타입별 시트에 행 삽입
6. 적용 완료 행 → 제작완료=TRUE 기입
7. product.xlsx + template.xlsx 저장

### 기본값

```python
DEFAULT_AVAILABLE = 1
DEFAULT_SHOW_GOODS = 0
DEFAULT_PURCHASE_LIMIT = -1
DEFAULT_SHOW_SOLD_OUT = 0
DEFAULT_ITEM_FOCUS = "[]{}"
DEFAULT_SHOW_REVIEW = 0
```

## 슬래시 커맨드

| 커맨드 | 파일 | 역할 |
|--------|------|------|
| /product-gen | ~/.claude/commands/product-gen.md | 템플릿 최신화 생성 |
| /product-apply [mode] | ~/.claude/commands/product-apply.md | 템플릿 → product.xlsx 적용 |

## 의존성

```
python >= 3.9
openpyxl >= 3.1
```

## 실행 환경

- OS: Windows (manager.exe 사용)
- REPO_ROOT 자동 감지 (스크립트 위치 기준 3단계 상위)
- 모든 참조 데이터: excel/ 폴더에서 동적 로드 → 클론 위치 무관

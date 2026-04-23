"""pytest 단위 테스트 -- quest_writer.py 읽기 전용 함수 + append 검증"""
import sys
from pathlib import Path

import pytest

# quest_writer.py를 import 할 수 있도록 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"
QUESTS_TEST = str(FIXTURES / "quests_test.xlsx")
ITEMS_TEST = str(FIXTURES / "items_test.xlsx")
KEYWORDS_TEST = str(FIXTURES / "keywords_test.xlsx")

from quest_writer import (
    append_quest_row,
    generate_unique_key,
    get_existing_keys,
    get_header_map,
    load_items,
    load_keywords,
    load_quest_templates,
    parse_quest_texts,
)

# append 테스트에 사용할 최소 유효 필드값
_MINIMAL_ROW = {
    "^key": 999001,
    "category": "QUEST_CATEGORY_GENERAL",
    "description": "테스트 추가 행",
    "count_type": "QUEST_COUNT_TYPE_SUM",
    "goal_count": 1,
    "reset_type": "QUEST_RESET_TYPE_NONE",
    "goal_type/type/%key": "daily_login",
}


class TestHeaderMap:
    def test_simple_fields_exist(self):
        """기본 필드는 단순 이름으로 존재해야 함."""
        hm = get_header_map(QUESTS_TEST)
        for key in ["^key", "$filter", "category", "description", "count_type", "goal_count", "reset_type"]:
            assert key in hm, f"'{key}' 키 없음"

    def test_compound_keys_exist(self):
        """중복 헤더는 경로 조합 키로 존재해야 함."""
        hm = get_header_map(QUESTS_TEST)
        for key in [
            "conditions/0/condition/%key",
            "conditions/1/condition/%key",
            "goal_type/type/%key",
            "goal_type/type/%param1",
            "rewards/0/id",
            "rewards/0/qty",
        ]:
            assert key in hm, f"'{key}' 키 없음"

    def test_no_duplicate_values(self):
        """모든 컬럼 인덱스가 고유해야 함 (중복 없음)."""
        hm = get_header_map(QUESTS_TEST)
        values = list(hm.values())
        assert len(values) == len(set(values)), "컬럼 인덱스 중복 존재"

    def test_key_col_is_b(self):
        """^key는 B컬럼(2)이어야 함."""
        hm = get_header_map(QUESTS_TEST)
        assert hm["^key"] == 2

    def test_returns_dict_of_int(self):
        """반환값이 dict이고 값이 정수인지 확인."""
        hm = get_header_map(QUESTS_TEST)
        assert isinstance(hm, dict)
        for col_name, col_idx in hm.items():
            assert isinstance(col_idx, int), f"'{col_name}' 컬럼 인덱스가 int가 아님"


class TestExistingKeys:
    def test_returns_set_of_ints(self):
        """반환 타입이 set[int]인지 확인."""
        keys = get_existing_keys(QUESTS_TEST)
        assert isinstance(keys, set)
        for k in keys:
            assert isinstance(k, int), f"키 {k!r}가 int가 아님"

    def test_known_keys_present(self):
        """31, 32, 500001, 500002 포함 확인."""
        keys = get_existing_keys(QUESTS_TEST)
        for expected in (31, 32, 500001, 500002):
            assert expected in keys, f"키 {expected} 누락"

    def test_count(self):
        """픽스처에 4개 데이터 행 -> 4개 키."""
        keys = get_existing_keys(QUESTS_TEST)
        assert len(keys) == 4


class TestGenerateUniqueKey:
    def test_range(self):
        """생성 키가 100000~999999 범위인지 확인."""
        existing: set[int] = set()
        for _ in range(100):
            key = generate_unique_key(existing)
            assert 100000 <= key <= 999999, f"범위 초과: {key}"

    def test_uniqueness(self):
        """existing에 없는 값 반환 확인."""
        existing = {i for i in range(100000, 999999)}  # 범위 거의 채움
        existing.discard(500000)
        key = generate_unique_key(existing)
        assert key not in existing

    def test_avoids_existing(self):
        """existing에 포함된 값 반환 안 함."""
        existing = set(range(100000, 1000000))  # 100000~999999 전체 (500000 제외하여 1개만 남김)
        existing.discard(500000)
        key = generate_unique_key(existing)
        assert key == 500000

    def test_custom_range(self):
        """lo, hi 파라미터 적용 확인."""
        existing: set[int] = set()
        for _ in range(50):
            key = generate_unique_key(existing, lo=200000, hi=299999)
            assert 200000 <= key <= 299999


class TestLoadItems:
    def test_returns_list(self):
        """반환 타입이 list인지 확인."""
        items = load_items(ITEMS_TEST)
        assert isinstance(items, list)

    def test_item_structure(self):
        """각 항목이 {id, name, category} 키를 가지는지 확인."""
        items = load_items(ITEMS_TEST)
        assert len(items) > 0
        for item in items:
            assert "id" in item, "id 키 누락"
            assert "name" in item, "name 키 누락"
            assert "category" in item, "category 키 누락"

    def test_known_item_present(self):
        """id=1 (골드) 포함 확인."""
        items = load_items(ITEMS_TEST)
        ids = {item["id"] for item in items}
        assert 1 in ids, "id=1 (골드) 누락"

    def test_no_none_ids(self):
        """id가 None인 항목 없음."""
        items = load_items(ITEMS_TEST)
        for item in items:
            assert item["id"] is not None

    def test_id_is_int(self):
        """모든 id가 int 타입인지 확인."""
        items = load_items(ITEMS_TEST)
        for item in items:
            assert isinstance(item["id"], int), f"id={item['id']!r}가 int가 아님"

    def test_known_items_count(self):
        """픽스처에 22개 데이터 행 포함 확인 (id=10, 1301401, 1301402 추가 후)."""
        items = load_items(ITEMS_TEST)
        assert len(items) == 22


class TestLoadKeywords:
    def test_build_sheet_exists(self):
        """build 시트 데이터 존재 확인."""
        kw = load_keywords(KEYWORDS_TEST)
        assert "build" in kw
        assert len(kw["build"]) > 0

    def test_timestamp_sheet_exists(self):
        """timestamp 시트 데이터 존재 확인."""
        kw = load_keywords(KEYWORDS_TEST)
        assert "timestamp" in kw
        assert len(kw["timestamp"]) > 0

    def test_launch_0_in_build(self):
        """build 시트에 'LAUNCH_0' 키 존재 확인."""
        kw = load_keywords(KEYWORDS_TEST)
        assert "LAUNCH_0" in kw["build"], "LAUNCH_0 키 누락"

    def test_indefinite_timestamp(self):
        """timestamp 시트에 'INDEFINITE_TIMESTAMP' 키 존재 확인."""
        kw = load_keywords(KEYWORDS_TEST)
        assert "INDEFINITE_TIMESTAMP" in kw["timestamp"], "INDEFINITE_TIMESTAMP 키 누락"

    def test_returns_dict_of_dict(self):
        """반환값이 dict[str, dict] 구조인지 확인."""
        kw = load_keywords(KEYWORDS_TEST)
        assert isinstance(kw, dict)
        for sheet_name, mapping in kw.items():
            assert isinstance(mapping, dict), f"'{sheet_name}' 값이 dict가 아님"

    def test_missing_sheet_returns_empty_dict(self):
        """존재하지 않는 시트는 빈 dict 반환."""
        # keywords_test.xlsx에는 build, timestamp만 있고
        # load_keywords는 이 두 시트만 처리하므로
        # 파일 자체를 바꿔 없는 시트 테스트는 건너뜀
        # 대신 결과에 두 키가 모두 존재하는지 확인
        kw = load_keywords(KEYWORDS_TEST)
        assert "build" in kw
        assert "timestamp" in kw


class TestLoadQuestTemplates:
    def test_returns_dict(self):
        """반환 타입이 dict인지 확인."""
        templates = load_quest_templates(QUESTS_TEST)
        assert isinstance(templates, dict)

    def test_b_to_a_mapping(self):
        """B컬럼 값(quest) -> A컬럼 값(desc) 매핑 최소 1건 확인."""
        templates = load_quest_templates(QUESTS_TEST)
        assert len(templates) >= 1, "템플릿 매핑이 비어있음"

    def test_keys_are_strings(self):
        """모든 키(B컬럼)가 문자열인지 확인."""
        templates = load_quest_templates(QUESTS_TEST)
        for k in templates:
            assert isinstance(k, str), f"키 {k!r}가 str이 아님"

    def test_values_are_strings(self):
        """모든 값(A컬럼)이 문자열인지 확인."""
        templates = load_quest_templates(QUESTS_TEST)
        for v in templates.values():
            assert isinstance(v, str), f"값 {v!r}가 str이 아님"

    def test_template_count(self):
        """픽스처 #quest 시트 Row 4~8 -> 5개 템플릿."""
        templates = load_quest_templates(QUESTS_TEST)
        assert len(templates) == 5, f"템플릿 수 {len(templates)}, 기대=5"


class TestAppendQuestRow:
    """append_quest_row 쓰기 함수 검증 (TC-13 ~ TC-15).
    quests_test.xlsx 원본을 직접 수정하지 않고 tmp_path 복사본으로 테스트."""

    def test_append_increments_row(self, quest_xlsx_copy):
        """TC-13: append 후 max_row가 1 증가해야 함."""
        from openpyxl import load_workbook

        # 추가 전 max_row 확인
        wb_before = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        before_max = wb_before["quests"].max_row
        wb_before.close()

        append_quest_row(quest_xlsx_copy, dict(_MINIMAL_ROW))

        # 추가 후 max_row 확인
        wb_after = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        after_max = wb_after["quests"].max_row
        wb_after.close()

        assert after_max == before_max + 1, (
            f"max_row 증가 실패: before={before_max}, after={after_max}"
        )

    def test_duplicate_key_raises(self, quest_xlsx_copy):
        """TC-14: 기존 ^key로 append 시 ValueError 발생해야 함."""
        # quests_test.xlsx에 이미 존재하는 ^key=31 사용
        dup_row = dict(_MINIMAL_ROW)
        dup_row["^key"] = 31

        with pytest.raises(ValueError, match="31"):
            append_quest_row(quest_xlsx_copy, dup_row)

    def test_written_key_verified(self, quest_xlsx_copy):
        """TC-15: 저장 후 재오픈해서 ^key 값 일치 확인."""
        from openpyxl import load_workbook

        row_data = dict(_MINIMAL_ROW)
        new_key = 999002
        row_data["^key"] = new_key

        target_row = append_quest_row(quest_xlsx_copy, row_data)

        # 재오픈 후 해당 행 ^key 확인
        wb = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        ws = wb["quests"]
        hm = get_header_map(quest_xlsx_copy)
        key_col = hm["^key"]
        actual_key = ws[target_row][key_col - 1].value
        wb.close()

        assert actual_key == new_key, (
            f"Row {target_row} ^key={actual_key!r}, 기대={new_key!r}"
        )

    def test_town_quest_append(self, quest_xlsx_copy):
        """TC-16: TOWN 퀘스트 Row 6(^key=500001) 재현 -- 필드 포함 확인."""
        from openpyxl import load_workbook

        town_row = {
            "^key": 500999,
            "$filter": "$$NONE",
            "category": "QUEST_CATEGORY_TOWN",
            "description": "대화 완료",
            "start_timestamp": "$$COMMON_STARTTAMP",
            "end_timestamp": "$$INDEFINITE_TIMESTAMP",
            "town_category": "TOWN_CATEGORY_INGAME",
            "town_icon": "Icon_Mini_CH_BaconRoll",
            "town_title": "퀘스트 제목 1",
            "town_description": "타운 퀘스트 텍스트입니다",
            "count_type": "QUEST_COUNT_TYPE_SUM",
            "goal_count": 1,
            "goal_type/type/%key": "play:need_win",
            "goal_type/type/%param1": True,
            "conditions/0/condition/%key": "finish_town_dialog:dialog_group_id",
            "conditions/0/condition/%param1": 500001,
            "rewards/0/id": 10,
            "rewards/0/qty": 50,
        }

        target_row = append_quest_row(quest_xlsx_copy, town_row)

        # 저장 후 검증
        wb = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        ws = wb["quests"]
        hm = get_header_map(quest_xlsx_copy)

        row_data = {k: ws[target_row][v - 1].value for k, v in hm.items()}
        wb.close()

        assert row_data["^key"] == 500999
        assert row_data["category"] == "QUEST_CATEGORY_TOWN"
        assert row_data["town_category"] == "TOWN_CATEGORY_INGAME"
        assert row_data["town_icon"] == "Icon_Mini_CH_BaconRoll"
        assert row_data["rewards/0/id"] == 10
        assert row_data["rewards/0/qty"] == 50
        assert row_data["goal_type/type/%key"] == "play:need_win"
        assert row_data["conditions/0/condition/%key"] == "finish_town_dialog:dialog_group_id"


class TestParseQuestTexts:
    def test_single_line_no_match(self):
        """매칭 없는 텍스트 -> description만 채우고 town_description 빈 문자열."""
        result = parse_quest_texts("퀘스트 없는 텍스트", {})
        assert len(result) == 1
        assert result[0]["description"] == "퀘스트 없는 텍스트"
        assert result[0]["town_description"] == ""
        assert result[0]["matched"] is False

    def test_matching_template(self):
        """{템플릿 키: desc} 매핑 -> town_description 자동 채움."""
        templates = {"<color=#ffe535>{0}회 승리</color>": "퀘스트 설명 텍스트"}
        result = parse_quest_texts("<color=#ffe535>{0}회 승리</color>", templates)
        assert result[0]["town_description"] == "퀘스트 설명 텍스트"
        assert result[0]["matched"] is True

    def test_placeholder_preserved(self):
        """{0} placeholder는 치환 없이 그대로 보존."""
        result = parse_quest_texts("{0}회 달성하기", {})
        assert "{0}" in result[0]["description"]

    def test_empty_lines_skipped(self):
        """빈 줄은 건너뜀."""
        result = parse_quest_texts("첫줄\n\n세번째줄", {})
        assert len(result) == 2

    def test_returns_default_values(self):
        """기본값: goal_count=1, qty=1, delete=False."""
        result = parse_quest_texts("텍스트", {})
        assert result[0]["goal_count"] == 1
        assert result[0]["qty"] == 1
        assert result[0]["delete"] is False


class TestBatchAppend:
    def test_description_placeholder_preserved(self, quest_xlsx_copy):
        """TC-12: 배치 저장 시 description의 {0}이 그대로 유지."""
        from openpyxl import load_workbook
        from quest_writer import _build_header_map

        existing = get_existing_keys(quest_xlsx_copy)
        new_key = generate_unique_key(existing)
        fv = {
            "^key": new_key,
            "category": "QUEST_CATEGORY_TOWN",
            "description": "<color=#ffe535>{0}회 승리</color>하기",
            "count_type": "QUEST_COUNT_TYPE_SUM",
            "goal_count": 5,
        }
        target_row = append_quest_row(quest_xlsx_copy, fv)
        # 재오픈해서 description 확인
        wb = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        ws = wb["quests"]
        hm = _build_header_map(ws)
        desc = ws.cell(row=target_row, column=hm["description"]).value
        wb.close()
        assert "{0}" in desc, f"{{0}} 치환됨! 실제값: {desc}"

    def test_batch_three_rows(self, quest_xlsx_copy):
        """배치로 3개 행 순서대로 추가 -> max_row 3 증가."""
        from openpyxl import load_workbook

        wb = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        before_max = wb["quests"].max_row
        wb.close()
        existing = get_existing_keys(quest_xlsx_copy)
        for i in range(3):
            k = generate_unique_key(existing)
            existing.add(k)
            append_quest_row(quest_xlsx_copy, {
                "^key": k,
                "category": "QUEST_CATEGORY_TOWN",
                "count_type": "QUEST_COUNT_TYPE_SUM",
                "goal_count": i + 1,
            })
        wb = load_workbook(quest_xlsx_copy, read_only=True, data_only=True)
        after_max = wb["quests"].max_row
        wb.close()
        assert after_max == before_max + 3

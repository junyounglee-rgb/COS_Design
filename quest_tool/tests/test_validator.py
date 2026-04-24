"""pytest 단위 테스트 — quest_validator.py

R.2.4 스펙 매트릭스 기반 20+건. ValidationRefs 빈 상태 / FK 참조 포함 상태 /
TPL_C 불변식 / strict_count_type 모드를 모두 커버한다.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"
QUESTS_TEST = str(FIXTURES / "quests_test.xlsx")
ITEMS_TEST = str(FIXTURES / "items_test.xlsx")
KEYWORDS_TEST = str(FIXTURES / "keywords_test.xlsx")
DIALOG_GROUPS_TEST = str(FIXTURES / "dialog_groups_test.xlsx")

from quest_validator import (  # noqa: E402
    ValidationError,
    ValidationRefs,
    build_refs_from_paths,
    validate_daily_set,
    validate_quest_row,
)


def _minimal_row(**overrides):
    base = {
        "^key": 700001,
        "$filter": "",
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_NONE",
        "count_type": "QUEST_COUNT_TYPE_SUM",
        "goal_count": 1,
        "goal_type/type/%key": "daily_login",
    }
    base.update(overrides)
    return base


def _parent_row(**overrides):
    base = {
        "^key": 700001,
        "$filter": "$$LAUNCH_0",
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_DAILY",
        "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        "goal_count": 3,
        "goal_type/type/%key": "reward_quest:ref_quest_ids",
    }
    base.update(overrides)
    return base


def _child_row(key: int, **overrides):
    base = {
        "^key": key,
        "$filter": "$$LAUNCH_0",
        "category": "QUEST_CATEGORY_GENERAL",
        "reset_type": "QUEST_RESET_TYPE_DAILY",
        "count_type": "QUEST_COUNT_TYPE_SUM",
        "goal_count": 1,
        "goal_type/type/%key": "daily_login",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ValidationRefs 빈 상태
# ---------------------------------------------------------------------------


class TestValidationRefsEmpty:
    def test_empty_refs_skips_fk(self):
        """빈 refs 는 FK 검증 skip, 형식 오류만 반환."""
        row = _minimal_row(**{"rewards/0/id": 999999})
        refs = ValidationRefs()
        errors = validate_quest_row(row, refs)
        # items.xlsx 참조 없음 → FK 오류 없음
        assert errors == []

    def test_empty_refs_skips_filter_fk(self):
        row = _minimal_row(**{"$filter": "$$FAKE_FILTER_XYZ"})
        refs = ValidationRefs()
        errors = validate_quest_row(row, refs)
        assert errors == []

    def test_empty_refs_still_checks_format(self):
        """빈 refs 에서도 ^key 형식은 검증."""
        row = _minimal_row(**{"^key": "abc"})
        refs = ValidationRefs()
        errors = validate_quest_row(row, refs)
        assert any("^key" in e for e in errors)


# ---------------------------------------------------------------------------
# ValidateQuestRow — 개별 규칙
# ---------------------------------------------------------------------------


class TestValidateQuestRowFormat:
    def test_valid_minimal_row(self):
        errors = validate_quest_row(_minimal_row(), ValidationRefs())
        assert errors == []

    def test_key_non_integer_rejected(self):
        row = _minimal_row(**{"^key": "abc"})
        errors = validate_quest_row(row, ValidationRefs())
        assert any("^key" in e and "정수" in e for e in errors)

    def test_key_zero_rejected(self):
        row = _minimal_row(**{"^key": 0})
        errors = validate_quest_row(row, ValidationRefs())
        assert any("^key" in e and "범위" in e for e in errors)

    def test_key_too_large_rejected(self):
        row = _minimal_row(**{"^key": 10**8})
        errors = validate_quest_row(row, ValidationRefs())
        assert any("^key" in e and "범위" in e for e in errors)

    def test_key_bool_rejected(self):
        """bool True 는 ^key 로 거부 (int 1 취급 방지)."""
        row = _minimal_row(**{"^key": True})
        errors = validate_quest_row(row, ValidationRefs())
        assert any("^key" in e and "정수" in e for e in errors)

    def test_weekly_reset_rejected(self):
        row = _minimal_row(reset_type="QUEST_RESET_TYPE_WEEKLY")
        errors = validate_quest_row(row, ValidationRefs())
        assert any("reset_type" in e and "WEEKLY" in e for e in errors)

    def test_none_reset_allowed(self):
        row = _minimal_row(reset_type="QUEST_RESET_TYPE_NONE")
        errors = validate_quest_row(row, ValidationRefs())
        assert errors == []

    def test_daily_reset_allowed(self):
        row = _minimal_row(reset_type="QUEST_RESET_TYPE_DAILY")
        errors = validate_quest_row(row, ValidationRefs())
        assert errors == []

    def test_unknown_count_type_rejected(self):
        row = _minimal_row(count_type="QUEST_COUNT_TYPE_FAKE")
        errors = validate_quest_row(row, ValidationRefs())
        assert any("count_type" in e for e in errors)


class TestValidateQuestRowFK:
    @pytest.fixture
    def refs(self):
        return build_refs_from_paths(
            items_path=ITEMS_TEST,
            keywords_path=KEYWORDS_TEST,
            dialog_groups_path=DIALOG_GROUPS_TEST,
            quests_path=QUESTS_TEST,
        )

    def test_reward_id_valid(self, refs):
        row = _minimal_row(**{"rewards/0/id": 1})
        errors = validate_quest_row(row, refs)
        # items.xlsx 에 id=1 존재
        assert errors == []

    def test_reward_id_invalid(self, refs):
        row = _minimal_row(**{"rewards/0/id": 999999})
        errors = validate_quest_row(row, refs)
        assert any("rewards/0/id" in e for e in errors)

    def test_filter_valid(self, refs):
        row = _minimal_row(**{"$filter": "$$LAUNCH_0"})
        errors = validate_quest_row(row, refs)
        assert errors == []

    def test_filter_invalid(self, refs):
        row = _minimal_row(**{"$filter": "$$FAKE_BUILD_XYZ"})
        errors = validate_quest_row(row, refs)
        assert any("$filter" in e for e in errors)

    def test_timestamp_valid(self, refs):
        row = _minimal_row(**{"start_timestamp": "$$INDEFINITE_TIMESTAMP"})
        errors = validate_quest_row(row, refs)
        assert errors == []

    def test_timestamp_invalid(self, refs):
        row = _minimal_row(**{"start_timestamp": "$$FAKE_TS_XYZ"})
        errors = validate_quest_row(row, refs)
        assert any("start_timestamp" in e for e in errors)

    def test_literal_timestamp_skipped(self, refs):
        """숫자 timestamp (`$$` 없음) 는 FK 검증 skip."""
        row = _minimal_row(**{"start_timestamp": "1700000000"})
        errors = validate_quest_row(row, refs)
        assert errors == []


class TestValidateConditions:
    def test_days_between_from_gt_to_rejected(self):
        row = _minimal_row(**{
            "conditions/0/condition/%key": "days_between:from,to",
            "conditions/0/condition/%param1": 7,
            "conditions/0/condition/%param2": 3,
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert any("days_between" in e and "위반" in e for e in errors)

    def test_days_between_valid(self):
        row = _minimal_row(**{
            "conditions/0/condition/%key": "days_between:from,to",
            "conditions/0/condition/%param1": 1,
            "conditions/0/condition/%param2": 7,
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert errors == []

    def test_days_between_negative(self):
        row = _minimal_row(**{
            "conditions/0/condition/%key": "days_between:from,to",
            "conditions/0/condition/%param1": -1,
            "conditions/0/condition/%param2": 3,
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert any("days_between" in e for e in errors)

    def test_play_need_win_invalid(self):
        row = _minimal_row(**{
            "conditions/0/condition/%key": "play:need_win",
            "conditions/0/condition/%param1": "MAYBE",
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert any("play:need_win" in e and "TRUE" in e for e in errors)

    def test_play_mode_category_invalid(self):
        row = _minimal_row(**{
            "conditions/0/condition/%key": "play_mode_category:ref_display_category_id",
            "conditions/0/condition/%param1": "999",
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert any("play_mode_category" in e for e in errors)

    def test_play_mode_category_300_allowed(self):
        row = _minimal_row(**{
            "conditions/0/condition/%key": "play_mode_category:ref_display_category_id",
            "conditions/0/condition/%param1": "300",
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert errors == []

    def test_finish_town_dialog_fk(self):
        refs = build_refs_from_paths(dialog_groups_path=DIALOG_GROUPS_TEST)
        row = _minimal_row(**{
            "conditions/0/condition/%key": "finish_town_dialog:dialog_group_id",
            "conditions/0/condition/%param1": 99999999,  # 없는 dialog group
        })
        errors = validate_quest_row(row, refs)
        assert any("dialog_group_id" in e for e in errors)


class TestValidateGoalType:
    def test_reward_quest_format_invalid(self):
        row = _minimal_row(**{
            "goal_type/type/%key": "reward_quest:ref_quest_ids",
            "goal_type/type/%param1": "not a list",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        })
        errors = validate_quest_row(row, ValidationRefs())
        assert any("reward_quest" in e and "형식" in e for e in errors)

    def test_reward_quest_format_valid(self):
        row = _minimal_row(**{
            "goal_type/type/%key": "reward_quest:ref_quest_ids",
            "goal_type/type/%param1": "[]{100,200,300}",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        })
        # existing_quest_keys None → FK 검증 skip → 형식만 통과
        errors = validate_quest_row(row, ValidationRefs())
        assert errors == []

    def test_reward_quest_missing_fk(self):
        """reward_quest:ref_quest_ids 의 id 가 quests.xlsx 에 없으면 오류."""
        refs = ValidationRefs(existing_quest_keys={31, 32})
        row = _minimal_row(**{
            "goal_type/type/%key": "reward_quest:ref_quest_ids",
            "goal_type/type/%param1": "[]{999999}",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        })
        errors = validate_quest_row(row, refs)
        assert any("999999" in e for e in errors)

    def test_strict_count_type_violation(self):
        """strict 모드: daily_login + HIGHEST → 오류."""
        row = _minimal_row(**{
            "goal_type/type/%key": "daily_login",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        })
        errors = validate_quest_row(row, ValidationRefs(), strict_count_type=True)
        assert any("daily_login" in e and "SUM" in e for e in errors)

    def test_strict_count_type_ok(self):
        row = _minimal_row(**{
            "goal_type/type/%key": "daily_login",
            "count_type": "QUEST_COUNT_TYPE_SUM",
        })
        errors = validate_quest_row(row, ValidationRefs(), strict_count_type=True)
        assert errors == []

    def test_reward_battle_road_sum_required(self):
        """reward_battle_road + HIGHEST → strict 모드 오류 (2026-04-24 정정)."""
        row = _minimal_row(**{
            "goal_type/type/%key": "reward_battle_road",
            "count_type": "QUEST_COUNT_TYPE_HIGHEST",
        })
        errors = validate_quest_row(row, ValidationRefs(), strict_count_type=True)
        assert any("reward_battle_road" in e and "SUM" in e for e in errors)


# ---------------------------------------------------------------------------
# ValidateDailySet — TPL_C 불변식
# ---------------------------------------------------------------------------


class TestValidateDailySet:
    def test_empty_children_rejected(self):
        parent = _parent_row()
        errors = validate_daily_set(parent, [], ValidationRefs())
        assert any("children" in e for e in errors)

    def test_valid_set(self):
        parent = _parent_row(goal_count=2, **{
            "goal_type/type/%param1": "[]{700002,700003}",
        })
        children = [
            _child_row(700002),
            _child_row(700003),
        ]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert errors == [], f"예상 통과 but: {errors}"

    def test_parent_sum_rejected(self):
        """S8: parent.count_type == SUM 은 TPL_C 불변식 위반."""
        parent = _parent_row(**{"count_type": "QUEST_COUNT_TYPE_SUM"})
        children = [_child_row(700002), _child_row(700003), _child_row(700004)]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert any("HIGHEST" in e for e in errors)

    def test_parent_goal_type_mismatch(self):
        """S9: parent.goal_type == daily_login 은 reward_quest 가 아니므로 위반."""
        parent = _parent_row(**{"goal_type/type/%key": "daily_login"})
        children = [_child_row(700002), _child_row(700003), _child_row(700004)]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert any("reward_quest:ref_quest_ids" in e for e in errors)

    def test_goal_count_mismatch(self):
        """S11: parent.goal_count != len(children) 위반."""
        parent = _parent_row(goal_count=1)
        children = [_child_row(700002), _child_row(700003), _child_row(700004)]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert any("goal_count" in e for e in errors)

    def test_child_filter_mismatch(self):
        parent = _parent_row(goal_count=1, **{"$filter": "$$LAUNCH_0"})
        children = [_child_row(700002, **{"$filter": "$$HELSINKI_3"})]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert any("$filter" in e for e in errors)

    def test_child_reset_type_mismatch(self):
        parent = _parent_row(goal_count=1, reset_type="QUEST_RESET_TYPE_DAILY")
        children = [_child_row(700002, reset_type="QUEST_RESET_TYPE_NONE")]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert any("reset_type" in e for e in errors)

    def test_repro_s4_daily_login_highest(self):
        """S4: parent 이 아닌 일반 행의 daily_login+HIGHEST 도 strict 에서 차단."""
        parent = _parent_row(goal_count=1)
        children = [
            _child_row(700002, **{
                "goal_type/type/%key": "daily_login",
                "count_type": "QUEST_COUNT_TYPE_HIGHEST",
            })
        ]
        errors = validate_daily_set(parent, children, ValidationRefs())
        assert any("daily_login" in e and "SUM" in e for e in errors)


# ---------------------------------------------------------------------------
# build_refs_from_paths
# ---------------------------------------------------------------------------


class TestBuildRefsFromPaths:
    def test_all_paths_populate(self):
        refs = build_refs_from_paths(
            items_path=ITEMS_TEST,
            keywords_path=KEYWORDS_TEST,
            dialog_groups_path=DIALOG_GROUPS_TEST,
            quests_path=QUESTS_TEST,
        )
        assert refs.item_ids is not None
        assert refs.build_keys is not None
        assert refs.timestamp_keys is not None
        assert refs.dialog_group_ids is not None
        assert refs.existing_quest_keys is not None

        # 알려진 값 포함
        assert 1 in refs.item_ids
        assert "LAUNCH_0" in refs.build_keys
        assert "INDEFINITE_TIMESTAMP" in refs.timestamp_keys
        assert len(refs.dialog_group_ids) >= 1
        assert 31 in refs.existing_quest_keys

    def test_none_paths_skip_loads(self):
        refs = build_refs_from_paths()
        assert refs.item_ids is None
        assert refs.build_keys is None
        assert refs.timestamp_keys is None
        assert refs.dialog_group_ids is None
        assert refs.existing_quest_keys is None

    def test_partial_refs(self):
        """일부 경로만 주면 해당 항목만 채워지고 나머지는 None."""
        refs = build_refs_from_paths(items_path=ITEMS_TEST)
        assert refs.item_ids is not None
        assert refs.build_keys is None


# ---------------------------------------------------------------------------
# ValidationError 공개성
# ---------------------------------------------------------------------------


class TestValidationError:
    def test_is_exception(self):
        assert issubclass(ValidationError, Exception)

    def test_raisable(self):
        with pytest.raises(ValidationError):
            raise ValidationError("테스트 오류")

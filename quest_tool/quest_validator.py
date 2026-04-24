"""
quest_validator.py — quests.xlsx 비즈니스 규칙 검증 모듈.

Streamlit 비의존. `validate_quest_row()` / `validate_daily_set()` 두 공개 API 를
거쳐 FK, GoalType↔CountType 매핑, Condition 파라미터 형식, parent-child 불변식 등을
검사한다. `ValidationRefs` 의 필드가 None 이면 해당 항목 검증은 skip 된다.

R.2 (2026-04-24 Round 2) 재설계 스펙 기반. write-path 7가지 위반 시나리오 차단.
"""
from __future__ import annotations

import re
from typing import Any, NamedTuple


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    """비즈니스 규칙 위반. 메시지는 사용자 노출 가능."""


# ---------------------------------------------------------------------------
# Public refs container
# ---------------------------------------------------------------------------


class ValidationRefs(NamedTuple):
    """검증에 필요한 참조 데이터. None 값은 해당 검증 skip.

    - item_ids: items.xlsx ^key 집합
    - build_keys: keywords.xlsx `build` 시트 id 집합 (prefix 없음, 예: "LAUNCH_0")
    - timestamp_keys: keywords.xlsx `timestamp` 시트 id 집합
    - dialog_group_ids: dialog_groups.xlsx `dialog_groups.dialogs` 시트 ^id 집합
    - existing_quest_keys: quests.xlsx ^key 전체 집합 (parent-child 간 reward_quest 검증용)
    """
    item_ids: set[int] | None = None
    build_keys: set[str] | None = None
    timestamp_keys: set[str] | None = None
    dialog_group_ids: set[int] | None = None
    existing_quest_keys: set[int] | None = None


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

# 허용 reset_type (2026-04-24 확정 — WEEKLY 제외)
_ALLOWED_RESET_TYPES: frozenset[str] = frozenset({
    "",
    "QUEST_RESET_TYPE_NONE",
    "QUEST_RESET_TYPE_DAILY",
    "QUEST_RESET_TYPE_REPEAT",
})

# 허용 count_type
_ALLOWED_COUNT_TYPES: frozenset[str] = frozenset({
    "",
    "QUEST_COUNT_TYPE_SUM",
    "QUEST_COUNT_TYPE_HIGHEST",
    "QUEST_COUNT_TYPE_LOWEST",
    "QUEST_COUNT_TYPE_STREAK",
})

# GoalType ↔ CountType 필수 매핑 (실 데이터 top 15 기반, 2026-04-24)
# 값: "SUM" / "HIGHEST" — count_type 값의 suffix 만 비교.
_REQUIRED_COUNT_TYPE_BY_GOAL: dict[str, str] = {
    "daily_login": "SUM",
    "play:need_win": "SUM",
    "play_report:key": "SUM",
    "open_battle_box:box_type": "SUM",
    "pull_gacha:gacha_type": "SUM",
    "get_ovencrown": "SUM",
    "get_smash_pass_exp": "SUM",
    "send_friend_request": "SUM",
    "play_mvp": "SUM",
    "level_up_cookie:ref_cookie_id": "SUM",
    "get_item:ref_item_id": "SUM",
    "use_item:ref_item_id": "SUM",
    "reward_battle_road": "SUM",  # 2026-04-24 정정 (기존 HIGHEST 표기 오류)
    "play": "SUM",  # 실 데이터 top
    "town_use_landmark:ref_landmark_id": "SUM",
    "town_finish_dialog:ref_dialog_group_id": "SUM",
    "have_cookie:ref_cookie_id": "HIGHEST",
    "have_item:ref_item_id": "HIGHEST",
    "achieve_cookie_level_all": "HIGHEST",
    "achieve_cookie_level_count:level": "HIGHEST",
    "achieve_smash_level": "HIGHEST",
    "have_highest_normal_ovencrown": "HIGHEST",
    "reward_quest:ref_quest_ids": "HIGHEST",
    "reward_town_quest": "HIGHEST",
    "reward_town_quest:ref_dialog_group_id": "HIGHEST",
}

# play_mode_category 허용 값
_ALLOWED_MODE_CATEGORY: frozenset[str] = frozenset({"100", "200", "300"})

# ^key 허용 범위
_KEY_MIN = 1
_KEY_MAX = 999999

# reward_quest:ref_quest_ids 포맷 검증용
_REWARD_QUEST_PATTERN = re.compile(r"^\[\]\{(\d+(?:,\d+)*)\}$")


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _try_int(value: Any) -> int | None:
    """int 로 변환 시도. 실패 시 None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None  # bool 은 거부 (True==1 방지)
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _str_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _count_type_suffix(count_type: str) -> str:
    """'QUEST_COUNT_TYPE_HIGHEST' → 'HIGHEST'."""
    if count_type.startswith("QUEST_COUNT_TYPE_"):
        return count_type[len("QUEST_COUNT_TYPE_"):]
    return count_type


def _check_fk_prefix(
    value: str,
    allowed: set[str] | None,
    errors: list[str],
    label: str,
) -> None:
    """`$$XXX` 형태의 값이 allowed 에 존재하는지 확인."""
    if allowed is None:
        return  # FK 검증 skip
    if not value.startswith("$$"):
        return  # prefix 없으면 리터럴로 판단 (검증 skip)
    key = value[2:]
    if key not in allowed:
        errors.append(f"{label}: `{value}` 가 허용 목록에 없음")


def _validate_conditions(
    row: dict[str, Any],
    refs: ValidationRefs,
    errors: list[str],
) -> None:
    """conditions/N/condition/%key 와 %param1/2 형식 검증."""
    for i in range(3):  # 최대 3개
        key_field = f"conditions/{i}/condition/%key"
        p1_field = f"conditions/{i}/condition/%param1"
        p2_field = f"conditions/{i}/condition/%param2"

        key_val = _str_or_empty(row.get(key_field))
        if not key_val:
            continue

        p1_raw = row.get(p1_field)
        p1_str = _str_or_empty(p1_raw)

        if key_val == "days_between:from,to":
            from_val = _try_int(p1_raw)
            to_val = _try_int(row.get(p2_field))
            if from_val is None or to_val is None:
                errors.append(
                    f"conditions/{i} days_between: from/to 둘 다 정수여야 함 "
                    f"(from={p1_raw!r}, to={row.get(p2_field)!r})"
                )
            elif from_val < 0 or to_val < 0:
                errors.append(
                    f"conditions/{i} days_between: from/to 0 이상이어야 함 "
                    f"(from={from_val}, to={to_val})"
                )
            elif from_val > to_val:
                errors.append(
                    f"conditions/{i} days_between: from({from_val}) ≤ to({to_val}) 위반"
                )

        elif key_val == "play:need_win":
            if p1_str not in ("TRUE", "FALSE"):
                errors.append(
                    f"conditions/{i} play:need_win: %param1 이 TRUE/FALSE 여야 함 ({p1_str!r})"
                )

        elif key_val == "play_with_party:player_count":
            n = _try_int(p1_raw)
            if n is None or n <= 0:
                errors.append(
                    f"conditions/{i} play_with_party: player_count 양수 정수여야 함 ({p1_raw!r})"
                )

        elif key_val == "play_mode_category:ref_display_category_id":
            if p1_str not in _ALLOWED_MODE_CATEGORY:
                errors.append(
                    f"conditions/{i} play_mode_category: %param1 ∈ {{100,200,300}} 여야 함 ({p1_str!r})"
                )

        elif key_val == "finish_town_dialog:dialog_group_id":
            gid = _try_int(p1_raw)
            if gid is None:
                errors.append(
                    f"conditions/{i} finish_town_dialog: dialog_group_id 정수여야 함 ({p1_raw!r})"
                )
            elif refs.dialog_group_ids is not None and gid not in refs.dialog_group_ids:
                errors.append(
                    f"conditions/{i} finish_town_dialog: dialog_group_id={gid} 가 dialog_groups.xlsx 에 없음"
                )


def _validate_goal_type(
    row: dict[str, Any],
    refs: ValidationRefs,
    errors: list[str],
    strict_count_type: bool,
) -> None:
    """goal_type/type/%key + %param1 검증."""
    goal_key = _str_or_empty(row.get("goal_type/type/%key"))
    if not goal_key:
        return

    p1_raw = row.get("goal_type/type/%param1")

    # reward_quest:ref_quest_ids → []{id,id,...} 포맷 + FK
    if goal_key == "reward_quest:ref_quest_ids":
        p1_str = _str_or_empty(p1_raw).strip()
        if not p1_str:
            errors.append("goal_type reward_quest:ref_quest_ids — %param1 비어있음")
            return
        m = _REWARD_QUEST_PATTERN.match(p1_str)
        if not m:
            errors.append(
                f"goal_type reward_quest:ref_quest_ids — %param1 `[]{{id1,id2,...}}` 형식 위반 ({p1_str!r})"
            )
        elif refs.existing_quest_keys is not None:
            ids = [int(x) for x in m.group(1).split(",")]
            missing = [i for i in ids if i not in refs.existing_quest_keys]
            if missing:
                errors.append(
                    f"goal_type reward_quest:ref_quest_ids — 존재하지 않는 quest ^key: {missing}"
                )

    # GoalType ↔ CountType 매핑 강제 (strict 모드)
    if strict_count_type:
        required_suffix = _REQUIRED_COUNT_TYPE_BY_GOAL.get(goal_key)
        if required_suffix is not None:
            ct = _str_or_empty(row.get("count_type"))
            actual_suffix = _count_type_suffix(ct)
            if actual_suffix != required_suffix:
                errors.append(
                    f"GoalType+CountType 매핑 위반: {goal_key} 은 "
                    f"{required_suffix} 필요 (현재 {actual_suffix!r})"
                )


def _validate_rewards(
    row: dict[str, Any],
    refs: ValidationRefs,
    errors: list[str],
) -> None:
    """rewards/0/id → items.xlsx ^key 존재."""
    reward_id_raw = row.get("rewards/0/id")
    if reward_id_raw is None or reward_id_raw == "":
        return
    rid = _try_int(reward_id_raw)
    if rid is None:
        errors.append(f"rewards/0/id — 정수여야 함 ({reward_id_raw!r})")
        return
    if refs.item_ids is not None and rid not in refs.item_ids:
        errors.append(f"rewards/0/id={rid} 가 items.xlsx 에 없음")


# ---------------------------------------------------------------------------
# 공개 API — 단일 행
# ---------------------------------------------------------------------------


def validate_quest_row(
    row: dict[str, Any],
    refs: ValidationRefs,
    *,
    strict_count_type: bool = False,
) -> list[str]:
    """단일 퀘스트 행 검증. 문제 메시지 리스트 반환 (빈 리스트 = 통과).

    Args:
        row: 필드명(^key, category, ...) → 값 매핑
        refs: FK 검증에 사용할 참조. None 필드는 해당 검증 skip
        strict_count_type: True 면 _REQUIRED_COUNT_TYPE_BY_GOAL 위반 시 오류 추가
    """
    errors: list[str] = []

    # 1. ^key 형식
    key_raw = row.get("^key")
    key_val = _try_int(key_raw)
    if key_val is None:
        errors.append(f"^key — 정수여야 함 ({key_raw!r})")
    elif not (_KEY_MIN <= key_val <= _KEY_MAX):
        errors.append(f"^key — {_KEY_MIN}~{_KEY_MAX} 범위 위반 ({key_val})")

    # 2. reset_type 허용 값
    rt = _str_or_empty(row.get("reset_type"))
    if rt not in _ALLOWED_RESET_TYPES:
        errors.append(
            f"reset_type — 허용 목록 외 값 ({rt!r}). "
            f"허용: NONE/DAILY/REPEAT (WEEKLY 제외)"
        )

    # 3. count_type 허용 값
    ct = _str_or_empty(row.get("count_type"))
    if ct not in _ALLOWED_COUNT_TYPES:
        errors.append(f"count_type — 허용 목록 외 값 ({ct!r})")

    # 4. $filter FK
    filter_val = _str_or_empty(row.get("$filter"))
    if filter_val:
        _check_fk_prefix(filter_val, refs.build_keys, errors, "$filter")

    # 5. start/end timestamp FK
    for ts_field in ("start_timestamp", "end_timestamp"):
        ts_val = _str_or_empty(row.get(ts_field))
        if ts_val:
            _check_fk_prefix(ts_val, refs.timestamp_keys, errors, ts_field)

    # 6. conditions
    _validate_conditions(row, refs, errors)

    # 7. goal_type
    _validate_goal_type(row, refs, errors, strict_count_type=strict_count_type)

    # 8. rewards
    _validate_rewards(row, refs, errors)

    return errors


# ---------------------------------------------------------------------------
# 공개 API — TPL_C 데일리 세트
# ---------------------------------------------------------------------------


def validate_daily_set(
    parent: dict[str, Any],
    children: list[dict[str, Any]],
    refs: ValidationRefs,
) -> list[str]:
    """parent + children 일괄 검증. 문제 메시지 리스트 반환.

    검증 항목:
      - parent.count_type == QUEST_COUNT_TYPE_HIGHEST
      - parent.goal_type/type/%key == reward_quest:ref_quest_ids
      - parent.goal_count == len(children)
      - parent/child 동일 $filter, reset_type (DAILY 권장)
      - 각 행에 대해 validate_quest_row 수행 (strict_count_type=True)

    validate_quest_row 에는 strict_count_type=True 를 넘겨 매핑 위반도 잡는다.
    parent.reward_quest FK 검증 시, children 의 ^key 들을 existing_quest_keys 에
    추가한 확장 refs 를 사용한다 (child 들은 아직 파일에 없지만 같은 트랜잭션으로 저장됨).
    """
    errors: list[str] = []

    # child ^key 들을 existing_quest_keys 에 주입한 확장 refs
    # (parent.reward_quest:ref_quest_ids FK 검증용)
    extended_refs = refs
    if refs.existing_quest_keys is not None:
        extra_keys: set[int] = set()
        for c in children:
            k = _try_int(c.get("^key"))
            if k is not None:
                extra_keys.add(k)
        extended_refs = refs._replace(
            existing_quest_keys=refs.existing_quest_keys | extra_keys,
        )

    # parent/child 개별 행 검증 (strict)
    p_errors = validate_quest_row(parent, extended_refs, strict_count_type=True)
    for e in p_errors:
        errors.append(f"[parent] {e}")
    for i, child in enumerate(children):
        c_errors = validate_quest_row(child, refs, strict_count_type=True)
        for e in c_errors:
            errors.append(f"[child#{i}] {e}")

    if not children:
        errors.append("children 비어있음 — 데일리 세트는 1건 이상 child 필요")
        return errors

    # parent 불변식
    p_count_type = _str_or_empty(parent.get("count_type"))
    if _count_type_suffix(p_count_type) != "HIGHEST":
        errors.append(
            f"[parent] count_type == QUEST_COUNT_TYPE_HIGHEST 여야 함 (현재 {p_count_type!r})"
        )

    p_goal_key = _str_or_empty(parent.get("goal_type/type/%key"))
    if p_goal_key != "reward_quest:ref_quest_ids":
        errors.append(
            f"[parent] goal_type/type/%key == reward_quest:ref_quest_ids 여야 함 "
            f"(현재 {p_goal_key!r})"
        )

    p_goal_count = _try_int(parent.get("goal_count"))
    if p_goal_count is None:
        errors.append(f"[parent] goal_count 정수 필수 (현재 {parent.get('goal_count')!r})")
    elif p_goal_count != len(children):
        errors.append(
            f"[parent] goal_count({p_goal_count}) != len(children)({len(children)})"
        )

    # parent/child 동일 $filter, reset_type
    p_filter = _str_or_empty(parent.get("$filter"))
    p_reset = _str_or_empty(parent.get("reset_type"))

    for i, child in enumerate(children):
        c_filter = _str_or_empty(child.get("$filter"))
        c_reset = _str_or_empty(child.get("reset_type"))
        if c_filter != p_filter:
            errors.append(
                f"[child#{i}] $filter 가 parent 와 다름 "
                f"(parent={p_filter!r}, child={c_filter!r})"
            )
        if c_reset != p_reset:
            errors.append(
                f"[child#{i}] reset_type 이 parent 와 다름 "
                f"(parent={p_reset!r}, child={c_reset!r})"
            )

    return errors


# ---------------------------------------------------------------------------
# 헬퍼 — refs 구성
# ---------------------------------------------------------------------------


def build_refs_from_paths(
    items_path: str | None = None,
    keywords_path: str | None = None,
    dialog_groups_path: str | None = None,
    quests_path: str | None = None,
) -> ValidationRefs:
    """경로들로부터 ValidationRefs 구성. quest_writer 로더 재사용.

    None 경로는 해당 참조를 None 상태로 유지 (검증 skip).
    """
    # quest_writer 는 상호 순환 import 없음 (quest_validator 를 import 안 함)
    from quest_writer import (
        get_existing_keys,
        load_dialog_groups,
        load_items,
        load_keywords,
    )

    item_ids: set[int] | None = None
    build_keys: set[str] | None = None
    timestamp_keys: set[str] | None = None
    dialog_group_ids: set[int] | None = None
    existing_quest_keys: set[int] | None = None

    if items_path:
        item_ids = {item["id"] for item in load_items(items_path)}
    if keywords_path:
        kw = load_keywords(keywords_path)
        build_keys = set(kw.get("build", {}).keys())
        timestamp_keys = set(kw.get("timestamp", {}).keys())
    if dialog_groups_path:
        dialog_group_ids = {g["id"] for g in load_dialog_groups(dialog_groups_path)}
    if quests_path:
        existing_quest_keys = get_existing_keys(quests_path)

    return ValidationRefs(
        item_ids=item_ids,
        build_keys=build_keys,
        timestamp_keys=timestamp_keys,
        dialog_group_ids=dialog_group_ids,
        existing_quest_keys=existing_quest_keys,
    )

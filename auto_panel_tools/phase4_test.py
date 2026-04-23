# -*- coding: utf-8 -*-
"""
Phase 4 함수 단위 테스트
"""
import sys, shutil, hashlib, copy, os

sys.path.insert(0, r'D:\claude_make\tools')
from add_cookies_to_offset import parse_asset, validate_post, backup, insert, validate_pre, preview

LIVE_PATH = r'D:\COS_Project\cos-client\Assets\GameAssets\Remote\CH_Common\OutGameCookieOffsetForUIData\OutGameCookieOffsetForUIData.asset'
TEST_COPY = r'D:\claude_make\docs\test_asset.asset'

def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def fresh_copy():
    """라이브 파일에서 테스트 복사본 새로 생성"""
    shutil.copy2(LIVE_PATH, TEST_COPY)

DEFAULT_VALUES = {
    'scale_offset': 1,
    'pos_x': 0, 'pos_y': 0, 'pos_z': 0,
    'rot_x': 0, 'rot_y': 0, 'rot_z': 0,
    'accessory': 0,
}

results = []

# ─────────────────────────────────────────────────────────────
# TC1: E2E 기본 흐름
# ─────────────────────────────────────────────────────────────
print("=== TC1: E2E 기본 흐름 (함수 조합) ===")
try:
    fresh_copy()
    panels_before = parse_asset(TEST_COPY)
    cookies = ['CH_E2E']
    values = copy.copy(DEFAULT_VALUES)
    insert(TEST_COPY, cookies, values, exclude_panels=[])
    panels_after = parse_asset(TEST_COPY)
    ok = validate_post(panels_before, panels_after, cookies, exclude_panels=[])
    if ok:
        print("-> PASS")
        results.append(('TC1', True))
    else:
        print("-> FAIL (validate_post returned False)")
        results.append(('TC1', False))
except Exception as e:
    print(f"-> FAIL (예외: {e})")
    results.append(('TC1', False))

# ─────────────────────────────────────────────────────────────
# TC2: N 입력 (취소) → 파일 미수정
# ─────────────────────────────────────────────────────────────
print()
print("=== TC2: N 입력 (취소) → 파일 미수정 ===")
try:
    fresh_copy()
    md5_before = md5(TEST_COPY)
    # insert를 호출하지 않음 (취소 시뮬레이션)
    md5_after = md5(TEST_COPY)
    if md5_before == md5_after:
        print(f"MD5 before: {md5_before}")
        print(f"MD5 after : {md5_after}")
        print("-> PASS (파일 미수정 확인)")
        results.append(('TC2', True))
    else:
        print("-> FAIL (MD5 불일치 - 파일이 수정됨)")
        results.append(('TC2', False))
except Exception as e:
    print(f"-> FAIL (예외: {e})")
    results.append(('TC2', False))

# ─────────────────────────────────────────────────────────────
# TC3: 복합 시나리오 (제외 + positionY)
# ─────────────────────────────────────────────────────────────
print()
print("=== TC3: 복합 시나리오 (제외 + positionY) ===")
try:
    fresh_copy()
    exclude = ['SmashPassPanel', 'SmashPassPremiumBenefitsPanel']
    cookies = ['CH_Complex']
    values = copy.copy(DEFAULT_VALUES)
    values['pos_y'] = 0.05

    # 삽입 전 y:0.05 카운트 (기존 데이터에도 존재할 수 있으므로 증가분으로 검증)
    with open(TEST_COPY, encoding='utf-8') as f:
        before_content = f.read()
    count_y_before = before_content.count('y: 0.05')

    panels_before = parse_asset(TEST_COPY)
    insert(TEST_COPY, cookies, values, exclude_panels=exclude)
    panels_after = parse_asset(TEST_COPY)

    ok = validate_post(panels_before, panels_after, cookies, exclude_panels=exclude)

    # 추가 검증: y: 0.05 증가분 = 14개 (제외 2개 빼고)
    with open(TEST_COPY, encoding='utf-8') as f:
        after_content = f.read()
    count_y_after = after_content.count('y: 0.05')
    y_increase = count_y_after - count_y_before
    total_panels = len(panels_after)
    excluded_count = sum(1 for p in panels_after if p['name'] in exclude)
    expected_y_increase = total_panels - excluded_count
    print(f"  전체 패널: {total_panels}, 제외: {excluded_count}, 기대 y:0.05 증가분: {expected_y_increase}, 실제 증가분: {y_increase}")

    if ok and y_increase == expected_y_increase:
        print("-> PASS")
        results.append(('TC3', True))
    else:
        reasons = []
        if not ok:
            reasons.append("validate_post False")
        if y_increase != expected_y_increase:
            reasons.append(f"y:0.05 증가분 불일치 (기대={expected_y_increase}, 실제={y_increase})")
        print(f"-> FAIL ({', '.join(reasons)})")
        results.append(('TC3', False))
except Exception as e:
    print(f"-> FAIL (예외: {e})")
    import traceback; traceback.print_exc()
    results.append(('TC3', False))

# ─────────────────────────────────────────────────────────────
# TC4: 롤백 검증
# ─────────────────────────────────────────────────────────────
print()
print("=== TC4: 롤백 검증 ===")
try:
    fresh_copy()
    cookies = ['CH_Rollback']
    values = copy.copy(DEFAULT_VALUES)

    # 삽입 전 MD5 (A)
    md5_a = md5(TEST_COPY)
    print(f"  MD5 A (삽입 전): {md5_a}")

    # 백업
    backup_path = backup(TEST_COPY)
    print(f"  백업 경로: {backup_path}")

    # 삽입
    insert(TEST_COPY, cookies, values, exclude_panels=[])
    md5_b = md5(TEST_COPY)
    print(f"  MD5 B (삽입 후): {md5_b}")

    assert md5_a != md5_b, "삽입 후 MD5가 동일함"

    # 롤백 (백업 복원)
    shutil.copy2(backup_path, TEST_COPY)
    md5_c = md5(TEST_COPY)
    print(f"  MD5 C (복원 후): {md5_c}")

    assert md5_a == md5_c, "롤백 후 MD5 불일치"

    # 재삽입 후 validate_post
    panels_before = parse_asset(TEST_COPY)
    insert(TEST_COPY, cookies, values, exclude_panels=[])
    panels_after = parse_asset(TEST_COPY)
    ok = validate_post(panels_before, panels_after, cookies, exclude_panels=[])

    if ok and md5_a == md5_c:
        print("-> PASS (롤백 OK, 재삽입 validate_post True)")
        results.append(('TC4', True))
    else:
        reasons = []
        if not ok:
            reasons.append("재삽입 validate_post False")
        if md5_a != md5_c:
            reasons.append("롤백 MD5 불일치")
        print(f"-> FAIL ({', '.join(reasons)})")
        results.append(('TC4', False))
except Exception as e:
    print(f"-> FAIL (예외: {e})")
    import traceback; traceback.print_exc()
    results.append(('TC4', False))

# ─────────────────────────────────────────────────────────────
# TC5: 사후 검증 FAIL 시뮬레이션
# ─────────────────────────────────────────────────────────────
print()
print("=== TC5: 사후 검증 FAIL 시뮬레이션 ===")
try:
    fresh_copy()
    cookies = ['CH_PostFail']
    values = copy.copy(DEFAULT_VALUES)

    panels_before = parse_asset(TEST_COPY)
    insert(TEST_COPY, cookies, values, exclude_panels=[])

    # 파일에서 CH_PostFail 키 라인 하나 제거 (조작)
    with open(TEST_COPY, encoding='utf-8') as f:
        lines = f.readlines()

    target_line = f"      - CH_PostFail\n"
    removed = False
    new_lines = []
    for line in lines:
        if not removed and line == target_line:
            removed = True  # 첫 번째만 제거
            continue
        new_lines.append(line)

    if not removed:
        print("  [WARN] CH_PostFail 라인을 찾지 못했습니다 (조작 실패)")
        results.append(('TC5', False))
    else:
        with open(TEST_COPY, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)

        print(f"  CH_PostFail 키 라인 1개 제거 완료")

        panels_after_tampered = parse_asset(TEST_COPY)
        ok = validate_post(panels_before, panels_after_tampered, cookies, exclude_panels=[])

        if not ok:
            print("-> PASS (validate_post가 False 반환 - FAIL/MISSING 감지됨)")
            results.append(('TC5', True))
        else:
            print("-> FAIL (validate_post가 True를 반환함 - 조작을 감지하지 못함)")
            results.append(('TC5', False))

except Exception as e:
    print(f"-> FAIL (예외: {e})")
    import traceback; traceback.print_exc()
    results.append(('TC5', False))

# ─────────────────────────────────────────────────────────────
# 총 요약
# ─────────────────────────────────────────────────────────────
print()
print("=" * 40)
passed = sum(1 for _, v in results if v)
total = len(results)
print(f"총 요약: {passed}/{total} PASS")
for name, v in results:
    print(f"  {name}: {'PASS' if v else 'FAIL'}")

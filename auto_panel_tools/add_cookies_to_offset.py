# -*- coding: utf-8 -*-
"""
OutGameCookieOffsetForUIData.asset 에 신규 쿠키를 일괄 추가하는 툴.
"""
import os
import sys
import shutil
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.txt")
BACKUP_DIR = os.path.join(SCRIPT_DIR, "backups")


def load_config():
    """config.txt 에서 asset 경로를 읽어 반환. 없으면 None."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding='utf-8') as f:
            path = f.read().strip()
        if path:
            return path
    return None

# ──────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────

def fmt(v):
    """float → YAML 표기 (불필요한 .0 제거)"""
    if float(v) == int(float(v)):
        return str(int(float(v)))
    return f"{float(v):g}"


def ask(prompt, default=None):
    """기본값 표시 포함 입력."""
    if default is not None:
        val = input(f"  {prompt:<14} [{default}] : ").strip()
        return val if val else str(default)
    return input(f"  {prompt}: ").strip()


def ask_float(prompt, default):
    while True:
        raw = ask(prompt, default)
        try:
            return float(raw)
        except ValueError:
            print("    숫자를 입력하세요.")


def fail(msg):
    """에러 출력 후 pause → 종료."""
    print(f"\n[ERROR] {msg}")
    input("\nEnter를 누르면 창이 닫힙니다.")
    sys.exit(1)


# ──────────────────────────────────────────────
# parse_asset
# ──────────────────────────────────────────────

def parse_asset(file_path):
    """
    asset 파일 파싱 → List[Panel]
    Panel = {"name": str, "keys": [str], "values": [int(count)]}
    """
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()

    # 외부 _keyData → 패널명 수집
    panel_names = []
    in_outer_key = False
    for line in lines:
        s = line.rstrip('\n')
        if s == '    _keyData:':
            in_outer_key = True
            continue
        if in_outer_key:
            if s.startswith('    - ') and not s.startswith('    - _'):
                panel_names.append(s.strip()[2:])
            else:
                break

    # 내부 섹션 파싱
    panels = []
    current_keys = []
    current_values = []
    in_inner_key = False
    in_inner_value = False
    started = False

    for line in lines:
        s = line.rstrip('\n')
        if s == '    - _keyData:':
            if started:
                idx = len(panels)
                name = panel_names[idx] if idx < len(panel_names) else f'패널{idx}'
                panels.append({'name': name, 'keys': list(current_keys), 'values': list(current_values)})
            started = True
            current_keys = []
            current_values = []
            in_inner_key = True
            in_inner_value = False
            continue
        if in_inner_key:
            if s == '      _valueData:':
                in_inner_key = False
                in_inner_value = True
                continue
            if s.startswith('      - CH_'):
                current_keys.append(s.strip()[2:])
        elif in_inner_value:
            if s.startswith('      - _positionOffset:'):
                current_values.append(1)

    if started:
        idx = len(panels)
        name = panel_names[idx] if idx < len(panel_names) else f'패널{idx}'
        panels.append({'name': name, 'keys': list(current_keys), 'values': list(current_values)})

    return panels


# ──────────────────────────────────────────────
# validate_pre
# ──────────────────────────────────────────────

def validate_pre(panels, cookies, exclude_panels):
    """
    사전 검증. (errors, warnings) 반환.
    errors 비어있으면 PASS.
    """
    errors = []
    warnings = []

    # 쿠키 ID 유효성
    for c in cookies:
        if not c.strip():
            errors.append("유효하지 않은 쿠키 ID: 빈 문자열 포함")

    # 존재하지 않는 제외 패널 → WARNING
    panel_name_set = {p['name'] for p in panels}
    for ep in exclude_panels:
        if ep not in panel_name_set:
            warnings.append(f"존재하지 않는 패널 '{ep}' - 무시됩니다")

    # 키=밸류 불일치 (전체 패널)
    for p in panels:
        if len(p['keys']) != len(p['values']):
            errors.append(
                f"키/밸류 불일치 [{p['name']}]: 키={len(p['keys'])} / 밸류={len(p['values'])}"
            )

    # 중복 쿠키 검사 (대상 패널 기준)
    target = [p for p in panels if p['name'] not in exclude_panels]
    for cookie in cookies:
        has = [p['name'] for p in target if cookie in p['keys']]
        if len(has) == len(target):
            errors.append(f"중복 쿠키 [{cookie}]: 모든 대상 패널에 이미 존재")
        elif has:
            no = [p['name'] for p in target if cookie not in p['keys']]
            errors.append(f"partial 중복 [{cookie}]:")
            errors.append(f"  존재: {', '.join(has)}")
            errors.append(f"  부재: {', '.join(no)}")

    return errors, warnings


# ──────────────────────────────────────────────
# preview
# ──────────────────────────────────────────────

def preview(panels, cookies, values, exclude_panels):
    target = [p for p in panels if p['name'] not in exclude_panels]
    excluded = [p['name'] for p in panels if p['name'] in exclude_panels]

    print()
    print(f"[미리보기] 추가 예정 쿠키: {', '.join(cookies)} ({len(cookies)}개)")
    print(f"           기본값: scale={fmt(values['scale_offset'])}  "
          f"posX={fmt(values['pos_x'])}  posY={fmt(values['pos_y'])}  posZ={fmt(values['pos_z'])}")
    print(f"                   rotX={fmt(values['rot_x'])}   "
          f"rotY={fmt(values['rot_y'])}  rotZ={fmt(values['rot_z'])}     "
          f"acc={fmt(values['accessory'])}")

    if excluded:
        print()
        print(f"[제외 패널] {', '.join(excluded)} ({len(excluded)}개)")

    print()
    print(f"[삽입 대상 패널 {len(target)}개]")
    print(f"  {'패널명':<42} {'현재':>5}  {'삽입 후':>6}")
    print(f"  {'-'*57}")
    for p in target:
        cur = len(p['keys'])
        print(f"  {p['name']:<42} {cur:>5}  {cur + len(cookies):>6}")

    print()
    print("[삽입 값]")
    print(f"  {'쿠키':<22} {'posX':>6} {'posY':>6} {'posZ':>6} "
          f"{'rotX':>6} {'rotY':>6} {'rotZ':>6} {'scale':>6} {'acc':>6}")
    print(f"  {'-'*74}")
    for c in cookies:
        print(f"  {c:<22} "
              f"{fmt(values['pos_x']):>6} {fmt(values['pos_y']):>6} {fmt(values['pos_z']):>6} "
              f"{fmt(values['rot_x']):>6} {fmt(values['rot_y']):>6} {fmt(values['rot_z']):>6} "
              f"{fmt(values['scale_offset']):>6} {fmt(values['accessory']):>6}")


# ──────────────────────────────────────────────
# backup
# ──────────────────────────────────────────────

def backup(file_path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    base = os.path.basename(file_path)
    name, ext = os.path.splitext(base)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f"{name}_backup_{ts}{ext}")

    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(BACKUP_DIR, f"{name}_backup_{ts}_{counter}{ext}")
        counter += 1

    shutil.copy2(file_path, dest)
    return dest


# ──────────────────────────────────────────────
# insert
# ──────────────────────────────────────────────

def insert(file_path, cookies, values, exclude_panels):
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()

    # 패널명 순서 수집
    panel_names = []
    in_outer_key = False
    for line in lines:
        s = line.rstrip('\n')
        if s == '    _keyData:':
            in_outer_key = True
            continue
        if in_outer_key:
            if s.startswith('    - ') and not s.startswith('    - _'):
                panel_names.append(s.strip()[2:])
            else:
                break

    cookie_key_lines = [f"      - {c}\n" for c in cookies]

    entry_block = []
    for _ in cookies:
        px, py, pz = fmt(values['pos_x']), fmt(values['pos_y']), fmt(values['pos_z'])
        rx, ry, rz = fmt(values['rot_x']), fmt(values['rot_y']), fmt(values['rot_z'])
        sc = fmt(values['scale_offset'])
        ac = fmt(values['accessory'])
        entry_block += [
            f"      - _positionOffset: {{x: {px}, y: {py}, z: {pz}}}\n",
            f"        _rotationOffset: {{x: {rx}, y: {ry}, z: {rz}}}\n",
            f"        _scaleOffset: {sc}\n",
            f"        _accessoryOffset: {ac}\n",
        ]

    out = []
    in_inner = False
    panel_idx = -1
    cur_panel_name = None

    for line in lines:
        s = line.rstrip('\n')

        # 내부 _valueData: (6칸) → 쿠키 키 삽입
        if s == '      _valueData:':
            if cur_panel_name not in exclude_panels:
                out.extend(cookie_key_lines)
            out.append(line)
            continue

        # 패널 내부 시작 → 이전 패널 OffsetEntry 삽입
        if s == '    - _keyData:':
            if in_inner and cur_panel_name not in exclude_panels:
                out.extend(entry_block)
            in_inner = True
            panel_idx += 1
            cur_panel_name = panel_names[panel_idx] if panel_idx < len(panel_names) else None
            out.append(line)
            continue

        out.append(line)

    # 마지막 패널
    if in_inner and cur_panel_name not in exclude_panels:
        out.extend(entry_block)

    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(out)


# ──────────────────────────────────────────────
# validate_post
# ──────────────────────────────────────────────

def validate_post(panels_before, panels_after, cookies, exclude_panels):
    before_map = {p['name']: p for p in panels_before}
    all_ok = True

    print()
    print("[사후 검증]")
    print(f"  {'패널명':<42} {'이전':>4} {'키':>4} {'밸류':>4} {'상태':>8} {'신규쿠키':>8}")
    print(f"  {'-'*78}")

    for p_after in panels_after:
        name = p_after['name']
        p_before = before_map.get(name)
        before_k = len(p_before['keys']) if p_before else '?'
        after_k = len(p_after['keys'])
        after_v = len(p_after['values'])
        kv_ok = after_k == after_v

        if name in exclude_panels:
            # 제외 패널: 변화 없어야 함
            unchanged = (p_before and after_k == len(p_before['keys']))
            status = "제외 OK" if unchanged else "제외 ERR"
            new_c = "-"
            if not unchanged:
                all_ok = False
        else:
            has_new = all(c in p_after['keys'] for c in cookies)
            status = "OK" if (kv_ok and has_new) else "FAIL"
            new_c = "OK" if has_new else "MISSING"
            if not (kv_ok and has_new):
                all_ok = False

        print(f"  {name:<42} {before_k:>4} {after_k:>4} {after_v:>4} {status:>8} {new_c:>8}")

    print()
    if all_ok:
        print("-> PASS: 모든 패널 검증 통과")
    else:
        print("-> FAIL: 문제가 발견되었습니다. 위 리포트를 확인하세요.")

    return all_ok


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--asset', default=None)
    args = parser.parse_args()

    asset_path = args.asset or load_config()
    if not asset_path:
        fail(f"asset 경로 설정이 없습니다.\ninstall.bat 을 먼저 실행해 경로를 등록하세요.\n경로: {CONFIG_FILE}")

    print()

    # 파일 파싱
    try:
        panels = parse_asset(asset_path)
    except FileNotFoundError:
        fail(f"파일을 찾을 수 없습니다.\n경로: {asset_path}")
    except UnicodeDecodeError:
        fail(f"파일 인코딩 오류 (UTF-8로 읽을 수 없음).\n경로: {asset_path}")
    except Exception as e:
        fail(f"파일 읽기 오류: {e}")

    # ── 대화형 입력 ──────────────────────────
    print("추가할 쿠키를 입력하세요 (쉼표 구분):")
    cookies_raw = input("> ").strip()
    cookies = [c.strip() for c in cookies_raw.split(',') if c.strip()]
    if not cookies:
        fail("유효하지 않은 쿠키 ID: 빈 입력")

    print()
    print("제외할 패널 (없으면 Enter):")
    exc_raw = input("> ").strip()
    exclude_panels = [p.strip() for p in exc_raw.split(',') if p.strip()] if exc_raw else []

    print()
    print("기본값 입력 (Enter = 기본값 유지):")
    values = {
        'scale_offset': ask_float("scaleOffset", 1),
        'pos_x':        ask_float("positionX",   0),
        'pos_y':        ask_float("positionY",   0),
        'pos_z':        ask_float("positionZ",   0),
        'rot_x':        ask_float("rotationX",   0),
        'rot_y':        ask_float("rotationY",   0),
        'rot_z':        ask_float("rotationZ",   0),
        'accessory':    ask_float("accessory",   0),
    }

    # ── 사전 검증 ────────────────────────────
    errors, warnings = validate_pre(panels, cookies, exclude_panels)

    if warnings:
        print()
        for w in warnings:
            print(f"  [WARNING] {w}")

    if errors:
        print()
        for e in errors:
            print(f"  [ERROR] {e}")
        input("\nEnter를 누르면 창이 닫힙니다.")
        sys.exit(1)

    # ── 미리보기 ─────────────────────────────
    preview(panels, cookies, values, exclude_panels)

    # ── 확인 프롬프트 ────────────────────────
    print()
    ans = input("계속 진행합니까? [y/N]: ").strip().lower()
    if ans != 'y':
        print("\n취소되었습니다.")
        sys.exit(0)

    # ── 백업 ─────────────────────────────────
    backup_path = backup(asset_path)
    print(f"\n[백업] {os.path.basename(backup_path)}")

    # ── 삽입 ─────────────────────────────────
    panels_before = parse_asset(asset_path)
    insert(asset_path, cookies, values, exclude_panels)
    panels_after = parse_asset(asset_path)

    # ── 사후 검증 ────────────────────────────
    ok = validate_post(panels_before, panels_after, cookies, exclude_panels)

    if not ok:
        input("\nEnter를 누르면 창이 닫힙니다.")
        sys.exit(1)

    total_inserted = sum(
        1 for p in panels_after
        if p['name'] not in exclude_panels
        for c in cookies
        if c in p['keys']
    ) // len(cookies) if cookies else 0

    print(f"\n완료. {total_inserted}개 패널에 {len(cookies)}개 쿠키 추가됨.")


if __name__ == '__main__':
    main()

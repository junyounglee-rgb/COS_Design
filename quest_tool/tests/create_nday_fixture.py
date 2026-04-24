"""nday_mission_events_test.xlsx 픽스처 생성 스크립트.

Usage: python tests/create_nday_fixture.py
"""
from pathlib import Path
from openpyxl import Workbook

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "nday_mission_events_test.xlsx"


def create_fixture():
    wb = Workbook()

    # --- events 시트 ---
    ws_ev = wb.active
    ws_ev.title = "events"

    # Row 1: 설명
    ws_ev["A1"] = "이벤트 설명"
    # Row 2: 경로 (path row)
    ws_ev["A2"] = "events/^0/"
    ws_ev["B2"] = "events/^0/"
    ws_ev["C2"] = "events/^0/"
    ws_ev["D2"] = "events/^0/"
    ws_ev["E2"] = "events/^0/"
    # Row 3: 헤더
    ws_ev["A3"] = "^key"
    ws_ev["B3"] = "description"
    ws_ev["C3"] = "start_timestamp"
    ws_ev["D3"] = "end_timestamp"
    ws_ev["E3"] = "mission_active_days"
    # Row 4: data ^key=101
    ws_ev["A4"] = 101
    ws_ev["B4"] = "HELSINKI_3_1일차"
    ws_ev["C4"] = "$$HELSINKI_3_NDAY1"
    ws_ev["D4"] = "$$HELSINKI_3_NDAY1_END"
    ws_ev["E4"] = 0
    # Row 5: data ^key=201
    ws_ev["A5"] = 201
    ws_ev["B5"] = "ISTANBUL_1_1일차"
    ws_ev["C5"] = "$$ISTANBUL_1_NDAY1"
    ws_ev["D5"] = "$$ISTANBUL_1_NDAY1_END"
    ws_ev["E5"] = 0

    # --- events.day 시트 ---
    ws_day = wb.create_sheet("events.day")

    # Row 1: 설명
    ws_day["A1"] = "이벤트 일차 설명"
    # Row 2: 경로 (path row)
    ws_day["A2"] = "events/^0/"
    ws_day["B2"] = "events/^0/day/+/"
    ws_day["C2"] = "events/^0/day/+/"
    ws_day["D2"] = "events/^0/day/+/"
    ws_day["E2"] = "events/^0/day/+/"
    # Row 3: 헤더
    ws_day["A3"] = "^key"
    ws_day["B3"] = "day"
    ws_day["C3"] = "description"
    ws_day["D3"] = "quest_ids"
    ws_day["E3"] = "finish_quest_id"
    # Row 4: data ^key=101
    ws_day["A4"] = 101
    ws_day["B4"] = 1
    ws_day["C4"] = "1일차 데일리 미션"
    ws_day["D4"] = "[]{71101,71102,71103,71104,71105}"
    ws_day["E4"] = 71101
    # Row 5: data ^key=201
    ws_day["A5"] = 201
    ws_day["B5"] = 1
    ws_day["C5"] = "1일차 데일리 미션"
    ws_day["D5"] = "[]{72101,72102,72103,72104,72105}"
    ws_day["E5"] = 72101

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(FIXTURE_PATH)
    print(f"Saved: {FIXTURE_PATH}")


if __name__ == "__main__":
    create_fixture()

@echo off
title Quest Tool (D7.5 Reproduce)

cd /d "%~dp0.."

echo.
echo  =========================================
echo   Quest Tool - D7.5 REPRODUCE MODE (port 8508)
echo   baseline: tests/fixtures/daily_mission_baseline.json
echo   target xlsx: tests/fixtures/quests_test_reproduce.xlsx
echo  =========================================
echo.

REM -- Step 1: Find uv --
set "UV_EXE="

where uv >nul 2>&1
if %errorlevel% equ 0 set "UV_EXE=uv"

if not defined UV_EXE (
    if exist "%USERPROFILE%\.local\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_EXE (
    if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
)
if not defined UV_EXE (
    if exist "%USERPROFILE%\.cargo\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
)

if not defined UV_EXE (
    echo  [ERROR] uv not found. Please run tests/run_test.bat first.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] .venv not found. Please run tests/run_test.bat first.
    pause
    exit /b 1
)

echo  [OK] env ready
echo.
echo  =========================================
echo   D7.5 REPRODUCE MODE
echo   1) Capture baseline first:
echo        python scripts\capture_daily_mission_baseline.py
echo   2) Enter baseline values in UI (parent 40001 set, then 40011 set)
echo   3) Close this window when done, then run:
echo        pytest tests/test_reproduce_real_data.py -v
echo  =========================================
echo.

timeout /t 2 /nobreak >nul
start "" http://localhost:8508
.venv\Scripts\streamlit.exe run app.py --server.headless true --server.port 8508 -- --config tests/quest_tool_test_reproduce.yaml

echo.
echo  Program stopped.
pause

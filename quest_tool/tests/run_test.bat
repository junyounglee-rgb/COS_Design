@echo off
title Quest Tool (Test)

cd /d "%~dp0.."

echo.
echo  =========================================
echo   Quest Tool - TEST MODE (port 8507)
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
    echo  [1/3] Installing package manager... (first time only)
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1

    if exist "%USERPROFILE%\.local\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
    if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
    if exist "%USERPROFILE%\.cargo\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"

    if not defined UV_EXE (
        echo.
        echo  [ERROR] Installation failed.
        pause
        exit /b 1
    )
    echo  [1/3] Done!
) else (
    echo  [1/3] OK
)

REM -- Step 2: Setup Python environment --
if not exist ".venv\Scripts\python.exe" (
    echo  [2/3] Setting up Python environment... (first time only)
    "%UV_EXE%" python install 3.12 >nul 2>&1
    "%UV_EXE%" venv .venv --python 3.12
    if %errorlevel% neq 0 (
        echo.
        echo  [ERROR] Failed to create Python environment.
        pause
        exit /b 1
    )
    echo  [2/3] Done!
) else (
    echo  [2/3] OK
)

REM -- Step 3: Install packages --
if not exist ".venv\Lib\site-packages\streamlit" (
    echo  [3/3] Installing packages... (first time only, 1-3 min)
    "%UV_EXE%" pip install -r requirements.txt --quiet 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo  [ERROR] Package installation failed.
        pause
        exit /b 1
    )
    echo  [3/3] Done!
) else (
    echo  [3/3] OK
)

REM -- Launch --
echo.
echo  =========================================
echo   TEST MODE - fixtures data only
echo   Close this window to stop.
echo  =========================================
echo.

timeout /t 2 /nobreak >nul
start "" http://localhost:8507
.venv\Scripts\streamlit.exe run app.py --server.headless true --server.port 8507 -- --config tests/quest_tool_test.yaml

echo.
echo  Program stopped.
pause
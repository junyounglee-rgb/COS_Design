@echo off
title Excel Search Tool

cd /d "%~dp0"

echo.
echo  =========================================
echo   Excel Search Tool - Starting...
echo  =========================================
echo.

REM -- Step 1: Find uv --
set "UV_EXE="

where uv >nul 2>&1
if %errorlevel% equ 0 set "UV_EXE=uv"

if not defined UV_EXE (
    if exist "%USERPROFILE%\.local\bin\uv.exe"      set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_EXE (
    if exist "%LOCALAPPDATA%\Programs\uv\uv.exe"    set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
)
if not defined UV_EXE (
    if exist "%USERPROFILE%\.cargo\bin\uv.exe"      set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
)

if not defined UV_EXE (
    echo  [1/3] Installing package manager... (first time only)
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1

    if exist "%USERPROFILE%\.local\bin\uv.exe"      set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
    if exist "%LOCALAPPDATA%\Programs\uv\uv.exe"    set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
    if exist "%USERPROFILE%\.cargo\bin\uv.exe"      set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"

    if not defined UV_EXE (
        echo.
        echo  [ERROR] Installation failed.
        echo          Please check your internet connection and try again.
        echo.
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
    "%UV_EXE%" venv .venv --quiet 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo  [ERROR] Failed to create Python environment.
        echo.
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
        echo          Please check your internet connection and try again.
        echo.
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
echo   Ready! Opening browser...
echo   Close this window to stop the program.
echo  =========================================
echo.

timeout /t 2 /nobreak >nul
start "" http://localhost:8501
.venv\Scripts\streamlit.exe run app.py --server.headless true --server.port 8501

echo.
echo  Program stopped.
pause

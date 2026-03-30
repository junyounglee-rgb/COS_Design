@echo off
chcp 65001 >nul 2>&1
title Excel 검색 도구

cd /d "%~dp0"

echo.
echo  =========================================
echo       Excel 검색 도구 시작 중...
echo  =========================================
echo.

REM ── 1단계: uv 위치 확인 ──────────────────────
set "UV_EXE="

where uv >nul 2>&1
if %errorlevel% equ 0 set "UV_EXE=uv"

if not defined UV_EXE (
    if exist "%USERPROFILE%\.local\bin\uv.exe"          set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_EXE (
    if exist "%LOCALAPPDATA%\Programs\uv\uv.exe"        set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
)
if not defined UV_EXE (
    if exist "%USERPROFILE%\.cargo\bin\uv.exe"          set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
)

REM uv 없으면 자동 설치
if not defined UV_EXE (
    echo  [1/3] 필수 구성 요소를 설치합니다... ^(최초 1회^)
    echo        인터넷 연결이 필요합니다. 잠시 기다려주세요.
    echo.
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1

    REM 설치 후 재탐색
    if exist "%USERPROFILE%\.local\bin\uv.exe"          set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
    if exist "%LOCALAPPDATA%\Programs\uv\uv.exe"        set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
    if exist "%USERPROFILE%\.cargo\bin\uv.exe"          set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"

    if not defined UV_EXE (
        echo.
        echo  [오류] 설치에 실패했습니다.
        echo         인터넷 연결 상태를 확인하고 다시 실행해주세요.
        echo.
        pause
        exit /b 1
    )
    echo  [1/3] 완료!
) else (
    echo  [1/3] 구성 요소 확인 완료
)

REM ── 2단계: Python 가상환경 확인 ──────────────
if not exist ".venv\Scripts\python.exe" (
    echo  [2/3] Python 환경을 구성합니다... ^(최초 1회^)
    "%UV_EXE%" venv .venv --quiet 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo  [오류] Python 환경 구성에 실패했습니다.
        echo         관리자에게 문의해주세요.
        echo.
        pause
        exit /b 1
    )
    echo  [2/3] 완료!
) else (
    echo  [2/3] Python 환경 확인 완료
)

REM ── 3단계: 패키지 설치 확인 ──────────────────
if not exist ".venv\Lib\site-packages\streamlit" (
    echo  [3/3] 필요한 프로그램을 설치합니다... ^(최초 1회^)
    echo        잠시 기다려주세요. ^(1~3분 소요^)
    "%UV_EXE%" pip install -r requirements.txt --quiet 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo  [오류] 프로그램 설치에 실패했습니다.
        echo         인터넷 연결 상태를 확인하고 다시 실행해주세요.
        echo.
        pause
        exit /b 1
    )
    echo  [3/3] 완료!
) else (
    echo  [3/3] 프로그램 확인 완료
)

REM ── 실행 ─────────────────────────────────────
echo.
echo  =========================================
echo   준비 완료! 브라우저가 자동으로 열립니다.
echo   이 창을 닫으면 프로그램이 종료됩니다.
echo  =========================================
echo.

timeout /t 2 /nobreak >nul
start "" http://localhost:8501
.venv\Scripts\streamlit.exe run app.py --server.headless true --server.port 8501

echo.
echo  프로그램이 종료되었습니다.
pause

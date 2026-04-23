@echo off
title Excel Diff Preview
chcp 65001 >nul 2>&1

cd /d "%~dp0"

echo.
echo  =========================================
echo   Excel Diff Preview - Starting...
echo  =========================================
echo.

REM -- Check Python executable --
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    echo  [ERROR] Python environment not found.
    echo          Please run install.bat first.
    echo.
    pause
    exit /b 1
)

echo  Environment: OK
echo.
echo  =========================================
echo   Opening browser...
echo   Close this window to stop the app.
echo  =========================================
echo.

timeout /t 2 /nobreak >nul
start "" http://localhost:8507
"%PYTHON_EXE%" -m streamlit run app.py --server.address localhost --server.headless true --server.port 8507

echo.
echo  Application stopped.
pause

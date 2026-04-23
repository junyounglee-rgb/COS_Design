@echo off
title Auto Pull

cd /d "%~dp0"

echo.
echo  =========================================
echo   Auto Pull - Starting...
echo  =========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] Environment not set up.
    echo          Please run install.bat first.
    echo.
    pause
    exit /b 1
)

echo  Environment OK.
echo.
echo  =========================================
echo   Ready! Opening browser...
echo   Close this window to stop the program.
echo  =========================================
echo.

timeout /t 4 /nobreak >nul
start "" http://localhost:8504
.venv\Scripts\python.exe -m streamlit run app_autopull.py --server.address localhost --server.headless true --server.port 8504

echo.
echo  Program stopped.
pause

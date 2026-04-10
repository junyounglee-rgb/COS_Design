@echo off
title Cherry Pick Propagator
cd /d "%~dp0"
echo.
echo  =========================================
echo   Cherry Pick Propagator - Starting...
echo  =========================================
echo.
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "..\autopull\.venv\Scripts\python.exe" set "PYTHON_EXE=..\autopull\.venv\Scripts\python.exe"
if not defined PYTHON_EXE (echo  [ERROR] Environment not set up. Run install.bat first. & pause & exit /b 1)
echo  Environment OK.
echo.
echo  =========================================
echo   Ready! Opening browser...
echo   Close this window to stop the program.
echo  =========================================
echo.
timeout /t 4 /nobreak >nul
start "" http://localhost:8506
"%PYTHON_EXE%" -m streamlit run app_cherry_pick.py --server.address localhost --server.headless true --server.port 8506
echo.
echo  Program stopped.
pause

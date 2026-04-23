@echo off
title Excel Diff Preview - Install
chcp 65001 >nul 2>&1

cd /d "%~dp0"

echo.
echo  =========================================
echo   Excel Diff Preview - Install
echo  =========================================
echo.

REM -- Step 1: Find uv --
set "UV_EXE="

where uv >nul 2>&1
if %errorlevel% equ 0 set "UV_EXE=uv"

if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV_EXE if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
if not defined UV_EXE if exist "%USERPROFILE%\.cargo\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"

if defined UV_EXE goto :uv_ok

echo  [1/3] Installing uv package manager...
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1

if exist "%USERPROFILE%\.local\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
if exist "%USERPROFILE%\.cargo\bin\uv.exe"   set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"

if not defined UV_EXE (
    echo.
    echo  [ERROR] Failed to install uv.
    echo          Please install manually: https://docs.astral.sh/uv/
    echo.
    pause
    exit /b 1
)
echo  [1/3] Done!
goto :step2

:uv_ok
echo  [1/3] uv found. OK

:step2
REM -- Step 2: Create Python environment --
if exist ".venv\Scripts\python.exe" (
    echo  [2/3] Python environment already exists. OK
    goto :step3
)

echo  [2/3] Creating Python 3.12 environment...
"%UV_EXE%" python install 3.12 >nul 2>&1
"%UV_EXE%" venv .venv --python 3.12
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to create Python environment.
    echo          Install Python 3.12: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo  [2/3] Done!

:step3
REM -- Step 3: Install packages --
if exist ".venv\Lib\site-packages\streamlit" if exist ".venv\Lib\site-packages\openpyxl" (
    echo  [3/3] Packages already installed. OK
    goto :done
)

echo  [3/3] Installing packages...
"%UV_EXE%" pip install -r requirements.txt --python .venv --quiet 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install packages.
    echo.
    pause
    exit /b 1
)
echo  [3/3] Done!

:done
echo.
echo  =========================================
echo   Install complete! Run run.bat to start.
echo  =========================================
echo.
pause

@echo off
chcp 65001 > nul

set SCRIPT_DIR=%~dp0
set CONFIG_FILE=%SCRIPT_DIR%config.txt

echo ============================================
echo  OutGameCookieOffsetForUIData - Add Cookies
echo ============================================
echo.

:: Check config.txt
if not exist "%CONFIG_FILE%" (
    echo [ERROR] config.txt not found.
    echo.
    echo Please run install.bat first.
    echo.
    echo Press Enter to close.
    pause > nul
    exit /b 1
)

:: Read asset path from config.txt
set /p ASSET_FILE=< "%CONFIG_FILE%"

:: Check asset file exists
if not exist "%ASSET_FILE%" (
    echo [ERROR] Asset file not found.
    echo.
    echo Path: %ASSET_FILE%
    echo.
    echo Re-run install.bat to update the path.
    echo.
    echo Press Enter to close.
    pause > nul
    exit /b 1
)

echo [OK] Asset file found.
echo.

:: Run Python script
set PYTHONIOENCODING=utf-8
python "%SCRIPT_DIR%add_cookies_to_offset.py"

echo.
echo Press Enter to close.
pause > nul

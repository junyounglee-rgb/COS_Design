@echo off
chcp 65001 > nul

echo ============================================
echo  add_cookies_to_offset - Setup
echo ============================================
echo.

:: Python check
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is not installed.
    echo.
    echo Download: https://www.python.org/downloads/
    echo.
    echo Press Enter to close.
    pause > nul
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [OK] %PYTHON_VER%
echo.

:: Check existing config
set CONFIG_FILE=%~dp0config.txt

if exist "%CONFIG_FILE%" (
    echo [Current config]
    type "%CONFIG_FILE%"
    echo.
    echo.
    set /p OVERWRITE=Overwrite? [y/N]:
    if /i not "%OVERWRITE%"=="y" goto :done
    echo.
)

:input_path
echo Enter the full path to OutGameCookieOffsetForUIData.asset
echo ex) D:\COS_Project\cos-client\Assets\...\OutGameCookieOffsetForUIData.asset
echo.
set /p ASSET_PATH=^>

if "%ASSET_PATH%"=="" (
    echo [ERROR] Path cannot be empty.
    echo.
    goto :input_path
)

if not exist "%ASSET_PATH%" (
    echo.
    echo [WARNING] File not found. Check the path.
    echo           You can save and fix it later by re-running install.bat
    echo.
)

echo %ASSET_PATH%> "%CONFIG_FILE%"
echo.
echo [OK] Saved to: %CONFIG_FILE%

:done
echo.
echo Setup complete. Run add_cookies_to_offset.bat to start.
echo.
pause

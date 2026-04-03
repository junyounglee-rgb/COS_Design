@echo off
cd /d "%~dp0"
echo Installing packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [FAIL] pip install failed.
    echo Please install Python first: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo.
echo [OK] Install complete. Run run_propagate.bat to start.
echo.
pause

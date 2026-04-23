@echo off
chcp 65001 > nul
echo.
echo =====================================================
echo   Excel 데이터 구조 분석 툴 - 설치 시작
echo =====================================================
echo.

cd /d "%~dp0"

:: Python 설치 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo.
    echo 아래 순서로 진행해주세요:
    echo   1. https://www.python.org/downloads/ 에서 Python 설치
    echo   2. 설치 시 "Add Python to PATH" 체크박스 반드시 선택
    echo   3. 설치 완료 후 이 파일(install.bat)을 다시 실행
    echo.
    pause
    exit /b 1
)

echo [1/3] Python 확인 완료
python --version

echo.
echo [2/3] 가상환경 생성 중...
python -m venv .venv
if errorlevel 1 (
    echo [오류] 가상환경 생성에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [3/3] 필요한 패키지 설치 중... (수 분 소요될 수 있습니다)
.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   설치 완료! run.bat 을 실행하면 프로그램이 시작됩니다.
echo =====================================================
echo.
pause

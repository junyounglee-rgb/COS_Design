@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: 설치 확인
if not exist ".venv\Scripts\streamlit.exe" (
    echo [오류] 먼저 install.bat 을 실행해서 설치를 완료해주세요.
    echo.
    pause
    exit /b 1
)

echo 프로그램을 시작합니다...
echo 잠시 후 브라우저가 자동으로 열립니다.
echo.
echo 종료하려면 이 창을 닫으세요.
echo.
.venv\Scripts\streamlit.exe run app_text.py --server.port 8502

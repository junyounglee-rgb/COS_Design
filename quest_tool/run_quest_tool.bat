@echo off
cd /d "%~dp0"
start "" cmd /c "streamlit run app.py -- --config quest_tool.yaml --server.port 8502"
timeout /t 2 >nul
start http://localhost:8502

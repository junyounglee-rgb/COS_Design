@echo off
cd /d "%~dp0.."
start "" cmd /c "streamlit run app.py -- --config tests/quest_tool_test.yaml --server.port 8503"
timeout /t 2 >nul
start http://localhost:8503

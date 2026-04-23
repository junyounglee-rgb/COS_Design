@echo off
cd /d "%~dp0"
python -m streamlit run app_propagate.py --server.port 8500
pause

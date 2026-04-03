@echo off
cd /d "%~dp0"
python -m streamlit run app_propagate.py
pause

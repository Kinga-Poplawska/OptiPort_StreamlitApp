@echo off
echo Starting OptiPort Visualization Interface...
echo.
cd /d "%~dp0"
streamlit run main.py
pause


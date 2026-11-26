@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo [스마트팜 대시보드] 필요한 패키지를 확인하고 앱을 실행합니다...
pip install -q streamlit pandas numpy matplotlib
streamlit run app.py
pause

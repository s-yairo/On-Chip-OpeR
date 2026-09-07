@echo off
cd /d %~dp0
python -m pip install -r requirements.txt
if exist optional_requirements\experiment_condition_advisor.txt (
  python -m pip install -r optional_requirements\experiment_condition_advisor.txt
)
python -m streamlit run app.py
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python tests\test_gerenteneuron.py
) else (
  python tests\test_gerenteneuron.py
)
pause

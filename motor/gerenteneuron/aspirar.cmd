@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python ..\..\bin\mb-aspirador.py --dir . --ext py,js,css,md %*
) else (
  python ..\..\bin\mb-aspirador.py --dir . --ext py,js,css,md %*
)
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
python ..\bin\mb-aspirador.py --dir . --ext py,js,css,md %*
pause

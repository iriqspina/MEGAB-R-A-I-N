@echo off
setlocal
cd /d "%~dp0.."
rem Relatorios locais abrem somente na central nativa. As fontes ficam intactas.
"apps\ia-quota-widget\.venv\Scripts\python.exe" "bin\mb-abrir-entrega.py" --project "%CD%"
if errorlevel 1 pause

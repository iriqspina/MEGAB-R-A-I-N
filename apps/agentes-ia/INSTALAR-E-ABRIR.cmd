@echo off
rem ===========================================================================
rem INSTALAR-E-ABRIR.cmd — Widget "Agentes IA" (painel vivo de processos)
rem O que faz: sobe o server do board se preciso e abre o widget translúcido
rem (família do Cotas IA). Fechar o widget ENCERRA o server do board.
rem Parar a força: powershell -File "<MEGABRAIN_ROOT>\bin\mb-board.ps1" -Parar
rem Requisito: venv do Cotas IA (PySide6 + QtWebEngine) em apps\ia-quota-widget\.venv
rem ===========================================================================
setlocal
cscript //nologo "%~dp0launch.vbs"
endlocal

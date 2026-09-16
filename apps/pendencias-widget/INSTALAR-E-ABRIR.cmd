@echo off
rem ===========================================================================
rem INSTALAR-E-ABRIR.cmd — Widget "Pendências" (radar de projetos MEGABRAIN)
rem Requisito: venv do Cotas IA (PySide6) em apps\ia-quota-widget\.venv
rem Se não existir, cria um venv próprio com PySide6 (primeira instalação).
rem ===========================================================================
setlocal
chcp 65001 >nul
set "AQUI=%~dp0"
set "VENV_IRMAO=%AQUI%..\ia-quota-widget\.venv"
set "PYW=%VENV_IRMAO%\Scripts\pythonw.exe"

if not exist "%PYW%" (
  echo venv do Cotas IA nao encontrado - criando ambiente proprio do widget...
  set "PYCMD="
  where py >nul 2>&1 && set "PYCMD=py -3"
  where python >nul 2>&1 && set "PYCMD=python"
  if "%PYCMD%"=="" (
    echo Python nao encontrado. Instale em https://www.python.org/downloads/
    echo marcando "Add python.exe to PATH" e rode este arquivo de novo.
    pause & exit /b 1
  )
  if not exist "%AQUI%.venv\Scripts\python.exe" %PYCMD% -m venv "%AQUI%.venv"
  "%AQUI%.venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check PySide6
  if errorlevel 1 ( echo FALHOU ao instalar PySide6. Verifique a internet. & pause & exit /b 1 )
  set "PYW=%AQUI%.venv\Scripts\pythonw.exe"
)

rem Atalho na Área de Trabalho (idempotente)
powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut(\"$d\Pendencias.lnk\"); $s.TargetPath='%PYW%'; $s.Arguments='\"%AQUI%widget.py\"'; $s.WorkingDirectory='%AQUI%'; $s.Description='Widget Pendencias - radar dos projetos'; $s.Save()" >nul 2>&1

start "" "%PYW%" "%AQUI%widget.py"
echo Pronto! O widget Pendencias esta na tela.
echo - Clique no triangulo ▴ pra expandir; Esc ou ▾ recolhe.
echo - Duplo clique no titulo alterna pill/card; duplo clique num item abre a pasta.
echo - Pausar/retomar projeto e add/remover pendencia: comando /pendencias em qualquer IA.
pause

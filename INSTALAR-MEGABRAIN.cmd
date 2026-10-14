@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-central.ps1"
if errorlevel 1 (
  echo A instalacao encontrou uma falha. Leia a mensagem acima.
  pause
  exit /b 1
)

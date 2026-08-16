@echo off
setlocal
rem Abre o Kimi Code com interface visual no navegador.

set "KIMI=%USERPROFILE%\.kimi-code\bin\kimi.exe"

if not exist "%KIMI%" (
  echo.
  echo  Kimi Code nao encontrado em:
  echo    %KIMI%
  echo.
  echo  Se instalou em outro lugar, arraste o kimi.exe para esta janela
  echo  e pressione Enter. Deixe vazio para cancelar.
  echo.
  set /p "KIMI=Caminho do kimi.exe: "
)

if not exist "%KIMI%" (
  echo  Cancelado - nenhum kimi.exe valido.
  pause
  exit /b 1
)

cd /d "%USERPROFILE%"
"%KIMI%" web

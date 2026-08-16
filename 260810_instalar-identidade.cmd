@echo off
setlocal
chcp 65001 >nul
rem Instala/copia o arquivo de identidade pessoal nos 4 destinos (Claude/Gemini/Kimi/Kimi Code).
rem Edite SO a fonte. Nunca edite as copias.

set "FONTE=%~dp0260810_memoria-pessoal.md"
set "SCRIPT=%~dp0bin\mb-sync-memoria.py"

set "PY=python"
where python >nul 2>nul || (
  echo.
  echo  Python nao esta no PATH deste computador.
  set /p "PY=Cole o caminho do python.exe (ou deixe vazio para cancelar): "
)
if "%PY%"=="" (echo  Cancelado. & pause & exit /b 1)

if not exist "%FONTE%" (
  echo.
  echo  Arquivo de identidade nao encontrado:
  echo    %FONTE%
  echo  Crie-o na raiz do megabrain antes de instalar.
  pause
  exit /b 1
)

"%PY%" "%SCRIPT%" --source "%FONTE%" --target claude --modo conteudo --dir "%USERPROFILE%\.claude"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target gemini --modo conteudo --dir "%USERPROFILE%\.gemini"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target kimi   --modo conteudo --dir "%USERPROFILE%\.kimi"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target kimi   --modo conteudo --dir "%USERPROFILE%\.kimi-code"

echo.
echo Pronto. Feche e reabra Claude Code / Kimi para recarregar.
pause

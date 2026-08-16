@echo off
setlocal
chcp 65001 >nul
rem Sincroniza a identidade nos 4 destinos de uma vez.
rem Edite SO a fonte. Nunca edite as copias.

set "MB=%~dp0"
set "FONTE=%MB%260810_memoria-pessoal.md"
set "SCRIPT=%MB%bin\mb-sync-memoria.py"

rem Python: usa o do PATH. Se nao houver, pergunta uma vez.
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
  echo  Crie-o na raiz do megabrain antes de sincronizar.
  pause
  exit /b 1
)

echo.
echo == Sincronizando identidade a partir de:
echo    %FONTE%
echo.

"%PY%" "%SCRIPT%" --source "%FONTE%" --target claude --modo conteudo --dir "%USERPROFILE%\.claude"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target gemini --modo conteudo --dir "%USERPROFILE%\.gemini"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target kimi   --modo conteudo --dir "%USERPROFILE%\.kimi"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target kimi   --modo conteudo --dir "%USERPROFILE%\.kimi-code"

echo.
echo == Conferencia
for %%F in ("%USERPROFILE%\.claude\CLAUDE.md" "%USERPROFILE%\.gemini\GEMINI.md" "%USERPROFILE%\.kimi\AGENTS.md" "%USERPROFILE%\.kimi-code\AGENTS.md") do (
  if exist %%F ( echo    OK    %%~zF bytes  %%~F ) else ( echo    FALTA %%~F )
)
echo.
echo Pronto. Feche e reabra Claude Code / Kimi para recarregar.
pause

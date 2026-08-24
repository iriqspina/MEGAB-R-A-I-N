@echo off
setlocal
chcp 65001 >nul
rem Instala/copia o arquivo de identidade pessoal nos 6 destinos (Claude/Gemini/Kimi/Kimi Code/Codex/output style do Claude).
rem Edite SO a fonte. Nunca edite as copias.

set "FONTE=%~dp0..\memoria\identidade\260810_memoria-pessoal.md"
set "SCRIPT=%~dp0..\bin\mb-sync-memoria.py"

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
"%PY%" "%SCRIPT%" --source "%FONTE%" --target codex      --modo conteudo --dir "%USERPROFILE%\.codex"
"%PY%" "%SCRIPT%" --source "%FONTE%" --target claude-style --modo conteudo --dir "%USERPROFILE%\.claude"

echo.
echo == Conferencia
for %%F in ("%USERPROFILE%\.claude\CLAUDE.md" "%USERPROFILE%\.gemini\GEMINI.md" "%USERPROFILE%\.kimi\AGENTS.md" "%USERPROFILE%\.kimi-code\AGENTS.md" "%USERPROFILE%\.codex\AGENTS.md" "%USERPROFILE%\.claude\output-styles\megabrain.md") do (
  if exist %%F ( echo    OK    %%~zF bytes  %%~F ) else ( echo    FALTA %%~F )
)
echo.
echo Pronto. Feche e reabra Claude Code / Kimi / Codex para recarregar.
pause

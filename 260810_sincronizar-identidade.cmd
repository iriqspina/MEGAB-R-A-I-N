@echo off
setlocal
rem 260810 - sincroniza a identidade nos 4 destinos de uma vez.
rem Edite SO a fonte abaixo. Nunca edite as copias.

set "PY=<USER_HOME>\AppData\Local\Programs\Python\Python314\python.exe"
set "MB=<MEGABRAIN_ROOT>\_github-repo-local"
set "FONTE=<MEGABRAIN_ROOT>\260810_memoria-pessoal.md"

echo.
echo == Sincronizando identidade a partir de:
echo    %FONTE%
echo.

"%PY%" "%MB%\bin\mb-sync-memoria.py" --source "%FONTE%" --target claude --modo conteudo --dir "%USERPROFILE%\.claude"
"%PY%" "%MB%\bin\mb-sync-memoria.py" --source "%FONTE%" --target gemini --modo conteudo --dir "%USERPROFILE%\.gemini"
"%PY%" "%MB%\bin\mb-sync-memoria.py" --source "%FONTE%" --target kimi   --modo conteudo --dir "%USERPROFILE%\.kimi"
"%PY%" "%MB%\bin\mb-sync-memoria.py" --source "%FONTE%" --target kimi   --modo conteudo --dir "%USERPROFILE%\.kimi-code"

echo.
echo == Conferencia
for %%F in ("%USERPROFILE%\.claude\CLAUDE.md" "%USERPROFILE%\.gemini\GEMINI.md" "%USERPROFILE%\.kimi\AGENTS.md" "%USERPROFILE%\.kimi-code\AGENTS.md") do (
  if exist %%F ( echo    OK    %%~zF bytes  %%~F ) else ( echo    FALTA %%~F )
)
echo.
echo Pronto. Feche e reabra Claude Code / Kimi para recarregar.
pause

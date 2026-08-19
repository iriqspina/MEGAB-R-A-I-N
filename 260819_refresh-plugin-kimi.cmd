@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
rem ============================================================
rem  MEGABRAIN v6 — refresh do plugin Kimi em 1 clique (260819)
rem  Copia a FONTE (plugin-megabrain/ + skill megabrain da central)
rem  por cima do plugin instalado no Kimi Code CLI, com backup e
rem  verificacao de hash do hook. A fonte manda; a copia nao se edita.
rem ============================================================

set "FONTE=<MEGABRAIN_ROOT>"
set "PLUGIN=<USER_HOME>\.kimi-code\plugins\managed\megabrain"
set "SKILL_DEST=%PLUGIN%\skills\megabrain"
set "DESKTOP=<USER_HOME>\AppData\Roaming\kimi-desktop\daimon-share\daimon\skills\megabrain"

echo.
echo  ================================================================
echo   REFRESH DO PLUGIN KIMI — fonte: plugin-megabrain/ da central
echo  ================================================================
echo.
type "%FONTE%\VERSAO.txt" | findstr /n "^" | findstr "^1:"
echo.

if not exist "%PLUGIN%\kimi.plugin.json" (
  echo  ERRO: plugin instalado nao encontrado em %PLUGIN%
  echo  Instale o plugin no Kimi Code CLI antes de dar refresh.
  pause
  exit /b 1
)

rem --- 1. backup do instalado (timestamp) -------------------------
for /f "tokens=1-3 delims=/ " %%a in ("%DATE%") do set "DT=%%c%%b%%a"
set "HR=%TIME::=%"
set "BACKUP=%FONTE%\.mb-backup\plugin-kimi-%DT%-%HR:~0,4%"
echo  [1/4] backup do plugin instalado:
echo        %BACKUP%
robocopy "%PLUGIN%" "%BACKUP%" /E /R:1 /W:1 >nul
if errorlevel 8 (echo        FALHOU & pause & exit /b 1) else (echo        OK)

rem --- 2. plugin (manifesto, SYSTEM.md, hooks, commands, seed) ----
echo  [2/4] copiando plugin-megabrain/ da central:
robocopy "%FONTE%\plugin-megabrain" "%PLUGIN%" /E /XF LEIAME.txt /R:1 /W:1 >nul
if errorlevel 8 (echo        FALHOU & pause & exit /b 1) else (echo        OK)
robocopy "%FONTE%\bin" "%PLUGIN%\bin" mb-sync.py mb-sync-memoria.py /R:1 /W:1 >nul

rem --- 3. skill /megabrain (SKILL.md, MEGABRAIN.md, referencias) --
echo  [3/4] copiando a skill /megabrain da central:
robocopy "%FONTE%\skills\megabrain" "%SKILL_DEST%" SKILL.md /R:1 /W:1 >nul
robocopy "%FONTE%" "%SKILL_DEST%" MEGABRAIN.md /R:1 /W:1 >nul
robocopy "%FONTE%\referencias" "%SKILL_DEST%\referencias" 26*_*.md /R:1 /W:1 >nul
if errorlevel 8 (echo        FALHOU & pause & exit /b 1) else (echo        OK)
if exist "%DESKTOP%\.." (
  robocopy "%FONTE%\skills\megabrain" "%DESKTOP%" SKILL.md /R:1 /W:1 >nul
  robocopy "%FONTE%" "%DESKTOP%" MEGABRAIN.md /R:1 /W:1 >nul
  robocopy "%FONTE%\referencias" "%DESKTOP%\referencias" 26*_*.md /R:1 /W:1 >nul
  echo        OK (kimi-desktop tambem)
)

rem --- 4. verificacao: o hook instalado E o da fonte? -------------
echo  [4/4] verificando o hook (fc /b fonte x instalado):
fc /b "%FONTE%\plugin-megabrain\hooks\260810_licoes-kimi.mjs" "%PLUGIN%\hooks\260810_licoes-kimi.mjs" >nul
if errorlevel 1 (
  echo        FALHOU — o hook instalado NAO bate com a fonte!
  pause
  exit /b 1
)
echo        OK — hook identico a fonte.

echo.
echo  Pronto. Na PROXIMA sessao do Kimi o hook novo ja vale
echo  (observabilidade em .mb-log/ + contexto unificado via mb-contexto.py).
echo  Backup do estado anterior em: %BACKUP%
echo.
pause

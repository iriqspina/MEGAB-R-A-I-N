@echo off
setlocal
chcp 65001 >nul
set "FONTE=<MEGABRAIN_ROOT>"
set "ARQ=260810_MEGABRAIN.md VERSAO.txt licoes-megabrain.md LEIAME.txt"

echo.
echo  ================================================================
echo   MEGABRAIN v3 - projeto novo (ja nasce no nivel 1 da pipeline)
echo  ================================================================
echo.
set /p "NOME=Nome do projeto (vira a pasta <PROJETOS_ROOT>\NOME): "
if "%NOME%"=="" (echo. & echo  Nome vazio - cancelado. & pause & exit /b 1)
set "DEST=<PROJETOS_ROOT>\%NOME%"
if exist "%DEST%" (echo. & echo  Ja existe: %DEST% & pause & exit /b 1)

mkdir "%DEST%\.scratch"
mkdir "%DEST%\MEGABRAIN\skills\megabrain"
mkdir "%DEST%\MEGABRAIN\referencias"
mkdir "%DEST%\MEGABRAIN\bin"
robocopy "%FONTE%" "%DEST%\MEGABRAIN" %ARQ% /R:1 /W:1 >nul
robocopy "%FONTE%\skills\megabrain" "%DEST%\MEGABRAIN\skills\megabrain" SKILL.md /R:1 /W:1 >nul
robocopy "%FONTE%\referencias" "%DEST%\MEGABRAIN\referencias" 260810_*.md /R:1 /W:1 >nul
robocopy "%FONTE%\bin" "%DEST%\MEGABRAIN\bin" mb-sync.py mb-sync-memoria.py /R:1 /W:1 >nul

rem arquivos de estado multi-agente (Gate 0/6) - so precisam existir se
rem mais de um agente/sessao vai tocar o projeto; ficam vazios ate la
(
  echo # ESTADO
  echo.
  echo ^(retrato de 5 linhas - reescrito a cada sessao, nunca acumula historico^)
) > "%DEST%\ESTADO.md"
(
  echo # HANDOFF
  echo.
  echo ^<!-- mb-sync:lock:start --^>
  echo TRAVADO_POR: livre
  echo ^<!-- mb-sync:lock:end --^>
) > "%DEST%\HANDOFF.md"
(
  echo # DECISOES
  echo.
  echo ^(append-only - toda decisao com a alternativa descartada^)
) > "%DEST%\DECISOES.md"
(
  echo # LICOES
  echo.
  echo ^(append-only - GATILHO/LICAO/ATALHO especifico deste projeto^)
) > "%DEST%\LICOES.md"

(
  echo # %NOME% - contexto
  echo.
  echo Glossario do dominio e decisoes do projeto.
  echo.
  echo Forma de trabalho: MEGABRAIN\skills\megabrain\SKILL.md ^(gates de
  echo entrega + multi-agente^) e MEGABRAIN\260810_MEGABRAIN.md ^(fases
  echo macro + regras de ouro^).
  echo Tracker de features: .scratch\^<feature^>\spec.md
) > "%DEST%\CONTEXT.md"

echo.
echo  Pronto: %DEST%
echo   - MEGABRAIN\        a pipeline v3 completa ^(cópia sincronizada^)
echo   - CONTEXT.md        o glossario ^(comece a alimentar^)
echo   - .scratch\         specs e tickets
echo   - ESTADO/HANDOFF/DECISOES/LICOES.md   so preenche se mais de um
echo     agente for trabalhar aqui - se for so voce e um agente, ignora
echo.
echo  Proximo passo: abra uma sessao na pasta e grelhe a primeira ideia.
echo.
pause

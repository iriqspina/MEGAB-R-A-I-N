@echo off
setlocal
chcp 65001 >nul
rem ============================================================
rem  MEGABRAIN - compreender padroes (260824, spec 7)
rem  Cruza pendencias x cerebro x docs x estado x visuais x
rem  telemetria e aponta o tema que ja se repete e ainda nao
rem  virou modelo. Grava 00_painel\AAMMDD_padroes.md e
rem  .mb-log\padroes.json, e abre o relatorio no fim.
rem  Sem parenteses dentro de bloco if: licao 260824 - eles
rem  fechavam o bloco antes da hora e matavam o batch no meio.
rem ============================================================
cd /d "%~dp0.."

where python >nul 2>&1
if errorlevel 1 goto :sempython

echo.
echo   Procurando padrao que ja se repete...
echo.
python bin\mb-compreensor.py
if errorlevel 1 goto :erro

rem  abre o mais recente: o nome carrega a data do dia da rodada
for /f "delims=" %%A in ('dir /b /o-d "00_painel\*_padroes.md" 2^>nul') do goto :abrir
goto :fim

:abrir
for /f "delims=" %%A in ('dir /b /o-d "00_painel\*_padroes.md"') do (
  start "" "00_painel\%%A"
  goto :fim
)

:sempython
echo.
echo   AVISO: python nao encontrado no PATH. Nada foi gerado.
goto :fim

:erro
echo.
echo   Falhou. Rode na mao pra ver o erro:
echo     python bin\mb-compreensor.py

:fim
echo.
pause

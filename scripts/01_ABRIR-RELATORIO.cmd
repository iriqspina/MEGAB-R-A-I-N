@echo off
setlocal
chcp 65001 >nul
rem ============================================================
rem  MEGABRAIN - abrir o relatorio (260825)
rem  ESTE E O BOTAO. Se voce nao sabe onde esta, clique aqui.
rem  Regenera 00_painel\RELATORIO.html e abre no navegador.
rem
rem  Por que regenera antes de abrir: o relatorio e "vivo" mas o
rem  HTML e um arquivo. Em 24/08 os .md mudaram 2 minutos DEPOIS
rem  da ultima geracao e ninguem regenerou - o painel recarregava
rem  a cada 15s um conteudo vencido. O Gate 5 manda regenerar;
rem  este .cmd faz o Gate 5 acontecer sozinho.
rem
rem  Nome comeca com 00_ de proposito: ordena primeiro na pasta.
rem  Sem parenteses dentro de bloco if: licao 260824.
rem ============================================================
cd /d "%~dp0.."

where python >nul 2>&1
if errorlevel 1 goto :sempython

echo.
echo   Regenerando o relatorio...
echo.
python bin\mb-relatorio-vivo.py
if errorlevel 1 goto :erro

if not exist "00_painel\RELATORIO.html" goto :semarquivo
start "" "00_painel\RELATORIO.html"
echo.
echo   Aberto. Ele recarrega sozinho enquanto estiver na tela.
goto :fim

:semarquivo
echo.
echo   O script rodou mas 00_painel\RELATORIO.html nao existe.
goto :fim

:sempython
echo.
echo   AVISO: python nao encontrado no PATH. Nada foi gerado.
echo   Abrindo a ultima versao gerada, se houver...
if exist "00_painel\RELATORIO.html" start "" "00_painel\RELATORIO.html"
goto :fim

:erro
echo.
echo   Falhou ao gerar. Rode na mao pra ver o erro:
echo     python bin\mb-relatorio-vivo.py
echo.
echo   Abrindo a ultima versao gerada, se houver...
if exist "00_painel\RELATORIO.html" start "" "00_painel\RELATORIO.html"

:fim
echo.
pause

@echo off
rem ===========================================================================
rem 00_abrir-sessao.cmd - abertura de sessao MEGABRAIN (v7.15, 260914)
rem Ressincroniza a central com o projeto e confere o git: busca e so avanca
rem (fetch e pull --ff-only). Nunca faz commit nem push. Mostra o retrato.
rem
rem Uso: duplo clique abre a propria central. Para um projeto, arraste a pasta
rem dele em cima deste arquivo, ou rode: 00_abrir-sessao.cmd "CAMINHO"
rem
rem EXCECAO AO REGISTRO (bin\mb_registro.py): a regra e botao novo entrar no
rem fim, com o proximo numero livre. Este leva o 00 por pedido explicito do
rem dono (<USUARIO>, 260914) para ser o primeiro da lista. O 00 nao se reusa
rem e nao se renumera.
rem ===========================================================================
setlocal
chcp 65001 >nul
set "RAIZ=%~dp0.."
set "PROJETO=%~1"
if "%PROJETO%"=="" set "PROJETO=%CD%"
rem Duplo clique: a pasta atual e 01_acoes, entao o projeto e a central.
if /i "%CD%\"=="%~dp0" set "PROJETO=%RAIZ%"

echo.
python -X utf8 "%RAIZ%\bin\mb-abertura-sessao.py" --projeto "%PROJETO%"
echo.
pause

@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
rem Cria um projeto novo ja no nivel 1 da pipeline megabrain.
rem 260824: dentro do bloco if, %PROJETOS% expandia na leitura (vazio) e o
rem script cancelava sozinho na primeira rodada; agora usa !PROJETOS!.

set "FONTE=%~dp0..\"
set "ARQ=MEGABRAIN.md VERSAO.txt licoes-megabrain.md"
set "CFG=%~dp0..\.mb-projetos.cmd"
if exist "%CFG%" call "%CFG%"

echo.
echo   MEGABRAIN - projeto novo (ja nasce no nivel 1 da pipeline)
echo.

if "%PROJETOS%"=="" (
  echo  Onde ficam seus projetos? Ex.: C:\projetos
  set /p "PROJETOS=Pasta raiz dos projetos: "
  if "!PROJETOS!"=="" (echo. & echo  Cancelado. & pause & exit /b 1)
  > "%CFG%" echo set "PROJETOS=!PROJETOS!"
  echo  Guardado em %CFG% - nao pergunto de novo.
  echo.
)
if not exist "%PROJETOS%" mkdir "%PROJETOS%"

set /p "NOME=Nome do projeto (vira a pasta %PROJETOS%\NOME): "
if "%NOME%"=="" (echo  Cancelado. & pause & exit /b 1)

set "DEST=%PROJETOS%\%NOME%"
if exist "%DEST%" (
  echo  A pasta %DEST% ja existe. Cancelado.
  pause
  exit /b 1
)

mkdir "%DEST%\MEGABRAIN" 2>nul
for %%A in (%ARQ%) do (
  if exist "%FONTE%memoria\nucleo\%%A" copy "%FONTE%memoria\nucleo\%%A" "%DEST%\MEGABRAIN\%%A" >nul
)
robocopy "%FONTE%bin" "%DEST%\MEGABRAIN\bin" /E /NFL /NDL /NJH /NJS >nul
robocopy "%FONTE%motor\dna" "%DEST%\MEGABRAIN\dna" /E /NFL /NDL /NJH /NJS >nul
robocopy "%FONTE%motor\referencias" "%DEST%\MEGABRAIN\referencias" /E /NFL /NDL /NJH /NJS >nul
robocopy "%FONTE%motor\skills\megabrain" "%DEST%\MEGABRAIN\skills\megabrain" /E /NFL /NDL /NJH /NJS >nul
if exist "%FONTE%OFFLINE.md" copy "%FONTE%OFFLINE.md" "%DEST%\MEGABRAIN\OFFLINE.md" >nul
if exist "%FONTE%motor\modelos" robocopy "%FONTE%motor\modelos" "%DEST%\MEGABRAIN" LEIAME-megabrain-do-projeto.txt /R:1 /W:1 >nul

echo.
echo  Projeto criado em %DEST%
echo  Leia MEGABRAIN\LEIAME-megabrain-do-projeto.txt (skill do protocolo em
echo  MEGABRAIN\skills\megabrain\SKILL.md, camada de projeto em
echo  MEGABRAIN\MEGABRAIN.md).
echo.
pause

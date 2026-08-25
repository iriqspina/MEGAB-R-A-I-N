@echo off
setlocal
chcp 65001 >nul
rem Regenera o pacote publico e publica no clone local do repositorio GitHub.

set "FONTE=%~dp0..\_github\export"
set "CLONE=%~dp0..\_github\repo-local"

set "PY=python"
where python >nul 2>nul || (
  echo.
  echo  Python nao esta no PATH deste computador.
  set /p "PY=Cole o caminho do python.exe (ou deixe vazio para cancelar): "
)
if "%PY%"=="" (echo  Cancelado. & pause & exit /b 1)

echo.
echo == Gerando pacote publico (mb-generate-template.py)...
"%PY%" "%~dp0..\bin\mb-generate-template.py"
if errorlevel 1 (
  echo  ERRO ao gerar o pacote publico. Abortando.
  pause
  exit /b 1
)

if not exist "%CLONE%\.git" (
  echo.
  echo  Clone local do repositorio nao encontrado em:
  echo    %CLONE%
  echo  Rode "git clone" manualmente antes de usar este script.
  pause
  exit /b 1
)

echo.
echo == Sincronizando %FONTE% -^> %CLONE%
robocopy "%FONTE%" "%CLONE%" /MIR /XD .git /NFL /NDL /NJH /NJS >nul

cd /d "%CLONE%"
git add -A

rem 260825b (decisao 260825am): o assunto do commit sai de bin/mb-titulo-versao.py.
rem O corte antigo era `tokens=1 delims=.` e parava no PRIMEIRO ponto - que na
rem linha do VERSAO.txt e o ponto da versao, nao o ponto final: o commit publico
rem 011d1af saiu "megabrain: 2026-08-25 - v7.". Batch nao distingue os dois; o
rem script corta no ponto final de verdade, cabe em 72 caracteres e sanitiza
rem aspas e metacaractere - com teste em motor/tests/test_mb_titulo_versao.py.
rem O texto completo continua no VERSAO.txt, que e a fonte.
rem A saida vai para arquivo em vez de backtick: dentro de `for /f ... in (...)`
rem o cmd.exe reprocessa as aspas e %PY% entre aspas devolve captura VAZIA
rem (medido nas 3 variantes em 260825) - o commit cairia no texto de reserva
rem sem avisar. Lendo de arquivo, caminho de python com espaco continua valendo.
set "MBTITARQ=%TEMP%\mb-titulo-versao.txt"
set "MBTIT="
"%PY%" "%~dp0..\bin\mb-titulo-versao.py" --arquivo "%CLONE%\memoria\nucleo\VERSAO.txt" > "%MBTITARQ%"
for /f "usebackq delims=" %%T in ("%MBTITARQ%") do set "MBTIT=%%T"
del "%MBTITARQ%" >nul 2>nul
if "%MBTIT%"=="" set "MBTIT=megabrain v7"
git commit -m "%MBTIT%"
if errorlevel 1 (
  echo.
  echo  Nada para commitar ou commit falhou. Verifique "git status".
  pause
  exit /b 1
)

echo.
echo Commit criado. Push continua manual: "git push" quando decidir publicar.
pause

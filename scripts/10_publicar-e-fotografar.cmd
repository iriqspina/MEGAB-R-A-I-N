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

for /f "usebackq delims=" %%V in ("%CLONE%\memoria\nucleo\VERSAO.txt") do (set "MBVER=%%V" & goto :temversao)
:temversao
rem 260822: aspas na primeira linha do VERSAO.txt quebravam o -m (commit falhava em silencio)
set "MBVER=%MBVER:"='%"
if "%MBVER%"=="" set "MBVER=megabrain v7"
if "%MBVER%"=="='" set "MBVER=megabrain v7"
rem 260825: a linha do VERSAO.txt tem ~1500 caracteres e virava o assunto do
rem commit inteiro - `git log --oneline` ficava ilegivel justo quando voce
rem esta procurando alguma coisa no historico. Corta no primeiro ponto final,
rem que na convencao da casa fecha o titulo da versao. O texto completo
rem continua no VERSAO.txt, que e a fonte.
for /f "tokens=1 delims=." %%T in ("%MBVER%") do set "MBTIT=%%T"
if "%MBTIT%"=="" set "MBTIT=%MBVER%"
git commit -m "megabrain: %MBTIT%."
if errorlevel 1 (
  echo.
  echo  Nada para commitar ou commit falhou. Verifique "git status".
  pause
  exit /b 1
)

echo.
echo Commit criado. Push continua manual: "git push" quando decidir publicar.
pause

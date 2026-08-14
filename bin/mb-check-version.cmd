@echo off
REM mb-check-version.cmd — checa e sincroniza o megabrain de um projeto
REM Uso: mb-check-version.cmd "<PROJETOS_ROOT>/<Projeto>" [--dry-run] [--force]

if "%~1"=="" (
    echo Uso: %~nx0 "caminho\do\projeto" [--dry-run] [--force]
    exit /b 1
)

set PROJETO=%~1
shift

set ARGS=
:loop
if "%~1"=="" goto run
if /i "%~1"=="--dry-run" set ARGS=%ARGS% --dry-run
if /i "%~1"=="--force" set ARGS=%ARGS% --force
shift
goto loop

:run
python "<MEGABRAIN_ROOT>\bin\mb-check-version.py" --projeto "%PROJETO%" %ARGS%
exit /b %ERRORLEVEL%

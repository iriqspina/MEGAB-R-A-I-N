@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%bootstrap\MegaBrain.exe" (
    echo Lancador ausente. Execute scripts\launcher-build.ps1 nesta pasta.
    exit /b 1
)
start "" "%ROOT%bootstrap\MegaBrain.exe" %*

@echo off
setlocal
chcp 65001 >nul
rem ============================================================
rem  Cotas IA - instalacao de 1 clique (260914)
rem  Faz TUDO: ambiente Python, dependencias, atalho na area de
rem  trabalho, abrir junto com o Windows e ja abre o widget.
rem  Rodar de novo e seguro: so atualiza, nunca duplica nada.
rem ============================================================
set "AQUI=%~dp0"
set "VENV=%AQUI%.venv"

set "PYCMD="
where py >nul 2>&1 && set "PYCMD=py -3"
where python >nul 2>&1 && set "PYCMD=python"
if "%PYCMD%"=="" (
  echo.
  echo  Python nao encontrado. Instale em https://www.python.org/downloads/
  echo  marquando "Add python.exe to PATH" e rode este arquivo de novo.
  pause
  exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
  echo.
  echo  == 1/4 Criando ambiente Python privado do widget...
  %PYCMD% -m venv "%VENV%"
  if errorlevel 1 (
    echo     FALHOU ao criar o ambiente. Rode de novo ou chame alguem pra ver.
    pause
    exit /b 1
  )
) else (
  echo.
  echo  == 1/4 Ambiente ja existe, reaproveitando.
)

echo  == 2/4 Instalando dependencias ^(so na primeira vez; demora um pouco^)...
"%VENV%\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r "%AQUI%requirements.txt"
if errorlevel 1 (
  echo     FALHOU ao instalar dependencias. Verifique a internet e rode de novo.
  pause
  exit /b 1
)

echo  == 3/4 Criando atalhos ^(area de trabalho + abrir com o Windows^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%AQUI%scripts\criar-atalho.ps1" -InstallDir "%AQUI%"
if errorlevel 1 (
  echo     AVISO: atalho da area de trabalho falhou. O widget abre mesmo assim.
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%AQUI%scripts\atalho-inicializacao.ps1" -InstallDir "%AQUI%" 2>nul
)

echo  == 4/4 Abrindo o Cotas IA...
cscript //nologo "%AQUI%launch.vbs"

echo.
echo  Pronto! O widget Cotas IA ja esta na tela.
echo  - Segure e arraste o nome de uma IA ate a coluna de bolinhas
echo    a esquerda pra tira-la da vista; arraste a bolinha de volta
echo    pra devolve-la na posicao que quiser.
echo  - Para nao abrir junto com o Windows: Win+R, digite
echo    shell:startup e apague o atalho "Cotas IA".
echo.
echo  Pode fechar esta janela.
pause

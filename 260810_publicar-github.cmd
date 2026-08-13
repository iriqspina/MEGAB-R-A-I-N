@echo off
setlocal
chcp 65001 >nul
set "FONTE=%~dp0260810_github-export"
set "CLONE=%~dp0_github-repo-local"
set "REPO=https://github.com/iriqspina/MEGAB-R-A-I-N.git"

echo.
echo  ================================================================
echo   MEGABRAIN - publicar pacote sanitizado no GitHub
echo  ================================================================
echo.
echo  Isto vai:
echo   1. Clonar (ou atualizar) %REPO%
echo   2. REMOVER .megabrain\memoria-global.md do repo (dado pessoal)
echo   3. Copiar o conteudo de 260810_github-export\ por cima
echo   4. Mostrar o que vai ser commitado e PARAR antes de enviar
echo.
echo  O commit antigo com dado pessoal continua no HISTORICO do git
echo  (nao apagado por padrao). Se quiser limpar o historico tambem,
echo  isso e um passo separado (reescreve hash de commit) - nao roda
echo  aqui sem voce pedir explicitamente.
echo.
pause

if not exist "%CLONE%" (
  echo Clonando pela primeira vez...
  git clone "%REPO%" "%CLONE%"
) else (
  echo Atualizando clone existente...
  pushd "%CLONE%"
  git pull
  popd
)

if not exist "%CLONE%\.git" (
  echo FALHOU: nao consegui clonar/atualizar. Confira se voce esta logado
  echo no git deste computador ^(git credential manager^) e tente de novo.
  pause
  exit /b 1
)

pushd "%CLONE%"

if exist ".megabrain\memoria-global.md" (
  echo Removendo arquivo pessoal do repo...
  git rm -r --cached .megabrain >nul 2>&1
  rmdir /s /q .megabrain 2>nul
)

echo Copiando pacote sanitizado...
robocopy "%FONTE%" "%CLONE%" /MIR /XD .git /R:1 /W:1 >nul

git add -A

echo.
echo  ----------------------------------------------------------------
echo   Isto sera commitado (confira antes de continuar):
echo  ----------------------------------------------------------------
git status
echo.
echo  Proximo passo ENVIA pro GitHub PUBLICO. Confira a lista acima -
echo  nao deve aparecer nenhum arquivo com nome pessoal ou memoria-global.
echo.
pause

git commit -m "megabrain v3.1: pacote sanitizado (gates, multi-agente, sync de identidade sem dado pessoal); remove memoria-global.md do HEAD"
git push origin main

echo.
echo  Pronto. Confira em %REPO%
echo.
popd
pause

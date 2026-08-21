@echo off
setlocal
rem ============================================================
rem  MEGABRAIN - push em 1 clique (260821, revisado 260822)
rem  Sessoes Cowork/cloud nao conseguem fazer push (proxy 403 no
rem  bridge). Elas commitam no repo-local; este botao empurra.
rem  Tudo que aparece aqui tambem vai pro log em .mb-log\push.log
rem  (arquivo so ASCII e CRLF: acento + chcp quebra o cmd.exe).
rem ============================================================
set "RAIZ=%~dp0"
set "CLONE=%RAIZ%_github-repo-local"
set "LOG=%RAIZ%.mb-log\push.log"
if not exist "%RAIZ%.mb-log" mkdir "%RAIZ%.mb-log"
echo ==== %DATE% %TIME% ==== >> "%LOG%"

if not exist "%CLONE%\.git" (
  echo  Clone nao encontrado em %CLONE%
  echo  clone nao encontrado >> "%LOG%"
  pause
  exit /b 1
)
cd /d "%CLONE%"

echo.
echo  Commits locais ainda nao publicados:
git log --oneline origin/main..HEAD
git log --oneline origin/main..HEAD >> "%LOG%" 2>&1
echo.
echo  Empurrando para origin/main ...
git push origin main >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
type "%LOG%" | findstr /v "^====" | more
if not "%RC%"=="0" (
  echo.
  echo  PUSH FALHOU (codigo %RC%). A mensagem do git esta acima e em:
  echo    %LOG%
  echo  Causas comuns: credencial do GitHub, rede, ou remoto mais novo
  echo  (nesse caso: git pull --rebase e rode de novo).
  echo  Plano B: pedir pro Kimi rodar "git push origin main" nesta pasta.
  pause
  exit /b %RC%
)

echo.
echo  OK. origin/main agora =
git rev-parse --short origin/main
git rev-parse --short origin/main >> "%LOG%"
echo.
echo  Atualizando o relatorio vivo (bloco de versao)...
python "%RAIZ%bin\mb-relatorio-vivo.py" --nota "push feito via 260821_push-github.cmd"
echo.
echo  Pronto. Pode fechar.
pause

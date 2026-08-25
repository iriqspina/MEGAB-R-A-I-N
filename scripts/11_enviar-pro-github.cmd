@echo off
setlocal
rem ============================================================
rem  MEGABRAIN - push em 1 clique (260821, revisado 260824)
rem  Sessoes Cowork/cloud nao conseguem fazer push (proxy 403 no
rem  bridge). Elas commitam no repo-local; este botao empurra.
rem  Tudo que aparece aqui tambem vai pro log em .mb-log\push.log
rem  (arquivo so ASCII e CRLF: acento + chcp quebra o cmd.exe).
rem  260824b: corrigido bug que matava o script no meio do caminho.
rem  Parenteses sem escape dentro de bloco if fechavam o bloco antes
rem  da hora (". foi inesperado neste momento") e o batch abortava:
rem  rev-parse e o relatorio vivo nunca rodavam, sem nenhum aviso.
rem  Mensagens agora sem parenteses dentro de blocos; etapa do
rem  relatorio com checagem de errorlevel e saida gravada no log.
rem ============================================================
set "RAIZ=%~dp0..\"
set "CLONE=%RAIZ%_github\repo-local"
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
if not "%RC%"=="0" (
  echo.
  echo  PUSH FALHOU - codigo %RC%. A mensagem do git esta no final de:
  echo    %LOG%
  echo  Causas comuns: credencial do GitHub, rede, ou remoto mais novo
  echo  - nesse caso: git pull --rebase e rode de novo.
  echo  Plano B: pedir pro Kimi rodar "git push origin main" nesta pasta.
  pause
  exit /b %RC%
)

echo.
echo  OK. origin/main agora =
git rev-parse --short origin/main
git rev-parse --short origin/main >> "%LOG%"

echo.
echo  Atualizando o relatorio vivo - bloco de versao ...
where python >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  echo  AVISO: python nao encontrado no PATH. Push OK, relatorio NAO atualizado.
  echo  relatorio FALHOU: python ausente no PATH >> "%LOG%"
  pause
  exit /b 9009
)
python "%RAIZ%bin\mb-relatorio-vivo.py" --nota "push feito via 11_enviar-pro-github.cmd" >> "%LOG%" 2>&1
set "RC2=%ERRORLEVEL%"
if not "%RC2%"=="0" (
  echo  AVISO: relatorio NAO atualizou - codigo %RC2%. Push OK. Detalhe no final de:
  echo    %LOG%
  echo  relatorio FALHOU codigo %RC2% >> "%LOG%"
  pause
  exit /b %RC2%
)
echo  relatorio OK >> "%LOG%"

echo.
echo  Pronto. Pode fechar.
pause

@echo off
setlocal
chcp 65001 >nul
set "FONTE=%~dp0260810_memoria-pessoal.md"
set "SCRIPT=%~dp0bin\mb-sync-memoria.py"

echo.
echo  ================================================================
echo   MEGABRAIN - instalar identidade global (Claude, Kimi, Gemini)
echo  ================================================================
echo.
echo  Isto escreve seu perfil (nome, formato de resposta, preferencias)
echo  dentro de:
echo    %%USERPROFILE%%\.claude\CLAUDE.md
echo    %%USERPROFILE%%\.kimi\AGENTS.md
echo    %%USERPROFILE%%\.gemini\GEMINI.md
echo  entre marcadores proprios - nao apaga o que ja existir nesses
echo  arquivos, so acrescenta/atualiza o bloco do MEGABRAIN. Roda de
echo  novo sempre que voce editar 260810_memoria-pessoal.md.
echo.
pause

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado no PATH. Instale python ou rode o comando
  echo abaixo manualmente trocando "python" pelo caminho do seu python.exe.
  pause
  exit /b 1
)

python "%SCRIPT%" --source "%FONTE%" --target all --modo conteudo --dir "%USERPROFILE%"

echo.
echo  Pronto. Confira os 3 arquivos acima se quiser ver o resultado.
echo.
pause

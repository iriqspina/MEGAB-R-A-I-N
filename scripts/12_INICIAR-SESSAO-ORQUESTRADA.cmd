@echo off
setlocal
chcp 65001 >nul
set "RAIZ=%~dp0.."

echo.
echo   MEGABRAIN — iniciar sessao orquestrada
echo   Confere skills e deixa a instrucao pronta para colar na IA.
echo   Nao chama modelos, nao inicia loop e nao consome cota.
echo.
python -X utf8 "%RAIZ%\bin\mb-inicio-sessao.py"
echo.
pause

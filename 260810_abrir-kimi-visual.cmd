@echo off
rem 260810 - abre o Kimi Code com interface visual no navegador.
rem Mesmo motor do CMD: seus arquivos, o plugin megabrain, tudo igual.
rem Deixe esta janela preta aberta enquanto usar. Fechar aqui encerra o Kimi.
title Kimi Code - servidor (nao feche)
cd /d <USER_HOME>
"<USER_HOME>\.kimi-code\bin\kimi.exe" web
pause

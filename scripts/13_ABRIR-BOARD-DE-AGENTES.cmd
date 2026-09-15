@echo off
rem ===========================================================================
rem 13_ABRIR-BOARD-DE-AGENTES.cmd - quadro vivo de agentes (Agent Flow)
rem Uso opcional (a pedido do dono, 260915, no padrao do ia-quota-widget).
rem
rem O que faz: abre o board dos agentes em janela propria (Chrome/Edge app).
rem Roda quando voce abre o icone; PARA sozinho quando voce fecha a janela.
rem Na primeira vez pode demorar ate ~45s (baixa o pacote via npx).
rem
rem Parar a forca (sem fechar janela): powershell -File
rem   "<MEGABRAIN_ROOT>\bin\mb-board.ps1" -Parar
rem
rem Observacao: e um app de terceiros (patoles/agent-flow, Apache-2.0) rodando
rem LOCAL, via npx, em http://localhost:3001. Nada sai da maquina.
rem ===========================================================================
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<MEGABRAIN_ROOT>\bin\mb-board.ps1"
endlocal

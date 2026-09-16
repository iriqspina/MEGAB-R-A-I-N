@echo off
rem ===========================================================================
rem 13_ABRIR-BOARD-DE-AGENTES.cmd - Agentes IA na area de trabalho (260916)
rem
rem O que faz: abre o WIDGET VAZADO "Agentes IA" - so os cartoes dos processos
rem flutuando na area de trabalho, sem fundo, sem moldura. Cliques fora dos
rem cartoes passam pro desktop normalmente. Hover no canto superior esquerdo
rem (ou clique ali) revela os controles: modo Mapa, nevoa, reexibir, fechar.
rem Fechar o widget encerra o server do board.
rem
rem Board completo no navegador (moldura normal de janela):
rem   powershell -File "<MEGABRAIN_ROOT>\bin\mb-board.ps1"
rem
rem Parar a forca (sem fechar widget): powershell -File
rem   "<MEGABRAIN_ROOT>\bin\mb-board.ps1" -Parar
rem
rem Requisito: venv do Cotas IA (PySide6 + QtWebEngine) em apps\ia-quota-widget\.venv
rem ===========================================================================
setlocal
cscript //nologo "<MEGABRAIN_ROOT>\apps\agentes-ia\launch.vbs"
endlocal

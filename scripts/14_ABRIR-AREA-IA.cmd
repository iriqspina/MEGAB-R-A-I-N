@echo off
rem ===========================================================================
rem 14_ABRIR-AREA-IA.cmd - area de trabalho paralela do agente "I.A." (260916)
rem
rem O que faz: sobe o Chrome DEDICADO DO AGENTE (perfil isolado, ponte propria
rem na porta 9223, abre MINIMIZADO - nao rouba seu foco, nao toca no seu Chrome).
rem Depois da primeira vez: logins do agente (ex.: Google/Keep) moram nesse
rem perfil - voce digita a senha UMA VEZ nessa janela quando quiser autorizar.
rem
rem Primeira vez: crie o desktop virtual "I.A." com Win+Ctrl+D e arraste a
rem janela do Chrome-I.A. pra la (ou deixe ela minimizada, tanto faz).
rem
rem Parar tudo: powershell -File "...\bin\abrir-area-ia.ps1" -Parar
rem ===========================================================================
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<MEGABRAIN_ROOT>\bin\abrir-area-ia.ps1"
pause
endlocal

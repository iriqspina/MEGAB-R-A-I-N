# Lançador nativo

O instalador compila `MegaBrainLauncher.cs` com o compilador .NET Framework 4
do próprio Windows. Não transporta executável ou ambiente Python de outra pessoa.

O lançador usa `apps/ia-quota-widget/.venv/Scripts/pythonw.exe`, abre
`central_desktop.py` e tenta focar a janela da mesma instalação já aberta.
O atalho fica em `00_PARA-VOCE/MegaBrain Central.lnk`.

Para reconstruir, use `scripts/launcher-build.ps1` nesta pasta do aplicativo.
`MegaBrain.exe --verify` confere arquivos/atalho e grava evidência local;
esse resultado é distinto de verificar renderização e interações no app.

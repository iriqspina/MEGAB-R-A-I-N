@echo off
rem 15_ABRIR-CLAUDE-COM-MOD - abre o Claude Code no terminal, na central, com o megabrain-mod ligado.
rem O mod mora em motor\mods\megabrain-mod. Ajustes: motor\mods\megabrain-mod\AJUSTES.ts
rem Nao apaga nem altera nada: so abre o Claude com o mod carregado.
cd /d "%~dp0.."
claude --plugin-dir "%~dp0..\motor\mods\megabrain-mod"

@echo off
rem Codex CLI na conta gpt2 (e-mail do cadastro na memoria da sessao — Plus gratis 1 mes, ate ~26/out/2026)
rem NAO mexe na sessao da conta principal (~/.codex continua <USUARIO>).
set "CODEX_HOME=%USERPROFILE%\.codex-gpt2"
cd /d "<MEGABRAIN_ROOT>"
codex

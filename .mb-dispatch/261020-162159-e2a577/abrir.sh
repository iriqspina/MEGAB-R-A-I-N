#!/usr/bin/env bash
# Despacho MEGABRAIN · 20/10/2026 16:21 · 261018_PONTE-ORQUESTRADORES.html
clear
echo "════════════════════════════════════════════════════"
echo " RESPOSTAS DO <USUARIO> · Codex"
echo " projeto: <MEGABRAIN_ROOT>"
echo "════════════════════════════════════════════════════"
cat '<MEGABRAIN_ROOT>/.mb-dispatch/261020-162159-e2a577/prompt.txt'
echo
echo " arquivo completo: <MEGABRAIN_ROOT>/.mb-dispatch/261020-162159-e2a577/respostas.json"
true
echo "════════════════════════════════════════════════════"
run(){ local n="$1"; shift; local c; for c in "$n" "$n.cmd" "$n.exe"; do if command -v "$c" >/dev/null 2>&1; then "$c" "$@"; return; fi; done; echo ""; echo "⚠ '$n' não encontrado neste terminal. As respostas continuam em <MEGABRAIN_ROOT>/.mb-dispatch/261020-162159-e2a577/prompt.txt"; }
PROMPT="$(cat '<MEGABRAIN_ROOT>/.mb-dispatch/261020-162159-e2a577/prompt.txt')"
run codex -m gpt-6.1-sol -c 'model_reasoning_effort="xhigh"' "$PROMPT"
echo
read -p "Enter para fechar…" ignored

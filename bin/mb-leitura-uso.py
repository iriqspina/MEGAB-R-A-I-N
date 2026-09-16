#!/usr/bin/env python
"""mb-leitura-uso — leitura de situação de créditos/uso para /amadurecer.

Lê <CENTRAL>/dados/orcamento_ia.json (medição viva do widget Cotas IA e do
motor de orquestração) e imprime: por conta/janela o uso %, horas até renovar,
veredito, a conta recomendada pra trabalho pesado e alerta de janela
descrepante (uma espremida >=70% enquanto outra tem folga >=30 pontos).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CENTRAL = Path(__file__).resolve().parent.parent
FONTE = CENTRAL / "dados" / "orcamento_ia.json"

APERTADO = 70
ESGOTADO = 95
DISCREPANCIA = 30

# janelas de worker leve não elegíveis como rota principal pra trabalho pesado
SO_WORKER = {"codex_bengalfox"}


def _janelas(no, caminho="", out=None):
    out = out if out is not None else []
    if isinstance(no, dict):
        if "used_percent" in no and isinstance(no.get("used_percent"), (int, float)):
            out.append((caminho, float(no["used_percent"]), no.get("hours_to_reset")))
        else:
            for k, v in no.items():
                _janelas(v, f"{caminho}.{k}" if caminho else k, out)
    return out


def main() -> int:
    if not FONTE.exists():
        print(f"sem medição: {FONTE} não existe — abra o widget Cotas IA ou rode um scan de cota")
        return 1
    dados = json.loads(FONTE.read_text(encoding="utf-8"))
    linhas = []
    for provedor in ("claude", "codex", "codex_gpt2", "zai", "spark"):
        janelas = _janelas(dados.get(provedor, {}), provedor)
        for caminho, uso, reset in janelas:
            base = caminho.split(".")[0]
            if any(w in caminho for w in SO_WORKER):
                veredito = "só worker leve" if uso < APERTADO else "apertado (worker)"
            elif uso >= ESGOTADO:
                veredito = "ESGOTADO"
            elif uso >= APERTADO:
                veredito = "apertado"
            else:
                veredito = "folga"
            linhas.append((uso, caminho, reset, veredito, base))

    print(f"leitura de uso · fonte {FONTE.name}")
    for uso, caminho, reset, veredito, _ in sorted(linhas):
        h = f"renova em {reset}h" if reset is not None else ""
        print(f"  {uso:5.1f}%  {veredito:<16} {caminho}  {h}")

    principais = [l for l in linhas if not any(w in l[1] for w in SO_WORKER)]
    if principais:
        melhor = min(principais, key=lambda l: l[0])
        print(f"\nrota recomendada pro pesado: {melhor[4]} ({melhor[0]:.0f}% usados)")
        pior = max(principais, key=lambda l: l[0])
        if pior[0] - melhor[0] >= DISCREPANCIA and pior[0] >= APERTADO:
            print(
                f"JANELA DESCREPANTE: {pior[1]} em {pior[0]:.0f}% enquanto {melhor[1]} "
                f"em {melhor[0]:.0f}% — rotear o trabalho pra {melhor[4]} antes de tocar a apertada."
            )
    else:
        print("\nnenhuma janela medida nas contas principais")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERRO lendo {FONTE}: {e}", file=sys.stderr)
        sys.exit(1)

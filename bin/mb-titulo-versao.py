#!/usr/bin/env python3
"""
mb-titulo-versao.py — assunto do commit a partir da 1ª linha do VERSAO.txt.
v1 (260825)

Por que existe: a ação 10 cortava o título com `for /f "tokens=1 delims=."`,
que para no PRIMEIRO ponto — e o primeiro ponto da linha é o da versão. O
commit público de 260825 saiu "megabrain: 2026-08-25 · v7." (decisão
260825am). Batch não distingue ponto de versão de ponto final; regex sim, e
aqui a regra fica testada em vez de embutida numa linha de .cmd.

Regras, nesta ordem:
  1. corta no primeiro ponto FINAL — ponto seguido de espaço ou de fim de
     linha. "v7.5" e "4,6" passam ilesos; "…por numero. MEMORIA:" corta.
  2. cabe em --limite (default 72, convenção de assunto de commit) contando o
     prefixo; o corte respeita fronteira de palavra e marca com "...".
  3. sanitiza o que quebra `git commit -m "..."` dentro do cmd.exe: aspa dupla
     vira apóstrofo, metacaractere de batch (% & | < > ^) vira espaço.

Uso:
    python bin/mb-titulo-versao.py                      # usa o VERSAO.txt da central
    python bin/mb-titulo-versao.py --arquivo <path> --prefixo "megabrain: "
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

PREFIXO = "megabrain: "
LIMITE = 72
RESERVA = "megabrain v7"          # linha ilegível/vazia não aborta a publicação
PONTO_FINAL = re.compile(r"\.(?=\s|$)")
QUEBRA_BATCH = re.compile(r"[%&|<>^]")
RETICENCIAS = "..."


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def sanitizar(texto: str) -> str:
    texto = texto.replace('"', "'")
    texto = QUEBRA_BATCH.sub(" ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def encurtar(texto: str, espaco: int) -> str:
    """Texto dentro de `espaco`, cortado em fronteira de palavra."""
    if espaco <= 0:
        return ""
    if len(texto) <= espaco:
        return texto
    util = espaco - len(RETICENCIAS)
    if util <= 0:
        return texto[:espaco]
    corte = texto[:util]
    if " " in corte:
        corte = corte[:corte.rindex(" ")]
    return corte.rstrip(" ,;:—-·") + RETICENCIAS


def titulo(linha: str, prefixo: str = PREFIXO, limite: int = LIMITE) -> str:
    """Assunto completo (com prefixo) para o -m do commit."""
    limpo = sanitizar(linha or "")
    if not limpo:
        limpo = RESERVA
    m = PONTO_FINAL.search(limpo)
    if m:
        limpo = limpo[:m.start()]
    limpo = limpo.strip()
    return prefixo + encurtar(limpo, limite - len(prefixo))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--arquivo", default=None, help="VERSAO.txt (default: o da central)")
    p.add_argument("--prefixo", default=PREFIXO)
    p.add_argument("--limite", type=int, default=LIMITE)
    args = p.parse_args()

    arq = Path(args.arquivo) if args.arquivo else u.achar(central(), "VERSAO.txt")
    linha = u.read_first_non_empty_line(arq) or ""
    print(titulo(linha, args.prefixo, args.limite))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # A publicação não pode morrer por causa do assunto do commit.
        print(PREFIXO + RESERVA)
        sys.exit(0)

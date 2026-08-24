#!/usr/bin/env python3
"""mb-testar.py — roda a suíte inteira, esteja ela onde estiver (v7.1, 260824).

Depois da etapa 2 da reorg a suíte mudou de `tests/` pra `motor/tests/`. Em vez
de todo mundo (docs, checklists, sua memória) decorar o caminho novo, o comando
vira um só:

    python bin/mb-testar.py

Acha a pasta de testes (plana ou dentro de motor/), monta o discover com o
top-level certo e devolve exit 0/1. Sem pytest, sem dependência externa.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


def raiz() -> Path:
    return Path(__file__).resolve().parent.parent


def pasta_testes(base: Path) -> Path | None:
    for cand in (base / "tests", base / "motor" / "tests"):
        if cand.is_dir() and any(cand.glob("test_*.py")):
            return cand
    return None


def main() -> int:
    base = raiz()
    testes = pasta_testes(base)
    if testes is None:
        print("ERRO: não achei pasta de testes (tests/ nem motor/tests/) em", base)
        return 1
    # top-level = pai da pasta de testes: mantém `tests` como pacote importável
    topo = testes.parent
    sys.path.insert(0, str(base / "bin"))
    sys.path.insert(0, str(topo))
    print(f"suíte: {testes.relative_to(base)}  (top-level: {topo.name or '.'})")
    carregador = unittest.TestLoader()
    suite = carregador.discover(str(testes), top_level_dir=str(topo))
    resultado = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

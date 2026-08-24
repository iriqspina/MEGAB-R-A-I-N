#!/usr/bin/env python3
"""ATALHO DE COMPATIBILIDADE — o orquestrador virou modo do GerenteNeuron.

Fusão decidida em 260819 (DECISOES.md): modelos hardcoded saíram daqui e os
defaults passaram a vir de gerenteneuron/pricing.json (com carimbo de
validade). O código vive em `gerenteneuron/orquestrador.py`; este arquivo só
delega pra não quebrar comandos documentados.
"""

import subprocess
import sys
from pathlib import Path

import mb_utils as u  # noqa: E402
DESTINO = u.pasta(Path(__file__).resolve().parent.parent, "gerenteneuron") / "orquestrador.py"

if __name__ == "__main__":
    if not DESTINO.exists():
        print(f"ERRO: {DESTINO} não encontrado — a fusão de 260819 moveu o "
              "orquestrador pra lá.", file=sys.stderr)
        sys.exit(1)
    print("(aviso: use `python gerenteneuron/orquestrador.py` — este caminho é só um atalho)",
          file=sys.stderr)
    sys.exit(subprocess.call([sys.executable, str(DESTINO), *sys.argv[1:]]))

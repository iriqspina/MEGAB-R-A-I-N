# -*- coding: utf-8 -*-
"""mb-interacoes.py — põe (ou atualiza) as Ferramentas do cursor em relatórios HTML.

Elemento obrigatório dos relatórios MEGABRAIN desde 261010 (pedido do <USUARIO>).
Idempotente: o bloco fica entre <!-- mb-interacoes:inicio --> e <!-- mb-interacoes:fim -->.

    python MEGABRAIN/bin/mb-interacoes.py 00_PARA-VOCE/INICIO.html
    python MEGABRAIN/bin/mb-interacoes.py --seco "00_PARA-VOCE/**/*.html"

Relatório que pede decisão: use também o modelo
modelos/interacoes/261010_decisoes-respondiveis/ (caixas por pergunta + Finalizar).
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_pop_tema  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="insere/atualiza as Ferramentas do cursor em HTML")
    ap.add_argument("caminhos", nargs="+", help="arquivos .html ou padrões glob")
    ap.add_argument("--seco", action="store_true", help="só mostra o que faria")
    a = ap.parse_args(argv)
    if not mb_pop_tema.html_interacoes():
        print("componente não encontrado (modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js)")
        return 1
    arquivos = []
    for c in a.caminhos:
        achados = glob.glob(c, recursive=True)
        arquivos += achados if achados else [c]
    contagem = {}
    for f in arquivos:
        p = Path(f)
        if not p.is_file() or p.suffix.lower() not in (".html", ".htm"):
            continue
        texto = p.read_text(encoding="utf-8", errors="strict")
        novo, estado = mb_pop_tema.aplicar_interacoes(texto)
        contagem[estado] = contagem.get(estado, 0) + 1
        if novo != texto and not a.seco:
            p.write_text(novo, encoding="utf-8")
        print(f"{estado:<10} {p}")
    print("resumo:", ", ".join(f"{k} {v}" for k, v in sorted(contagem.items())) or "nenhum HTML")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mb-pele-pop.py — injeta a pele POP v1.2 (<style id="mb-pop-skin">) em relatórios HTML legados.

Fonte da pele: motor/modelos/relatorios/260914_pop/260915_pele-pop-legado.css.
Idempotente: se o bloco já existe, é substituído; senão entra antes do primeiro </head>.
Só pele — o conteúdo do HTML não é tocado.

--tema claro: além da pele, grava data-tema="claro" no <html> do alvo (alteração
registrada separadamente do bloco de pele — a integridade byte a byte vale
fora dessas duas operações). Sem a flag, nada de tema: a pele segue escura.
--tema escuro: remove um data-tema="claro" eventual (default da pele).

Uso: python bin/mb-pele-pop.py [--tema claro|escuro] ARQUIVO.html [ARQUIVO2.html ...]
"""
import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "motor" / "modelos" / "relatorios" / "260914_pop" / "260915_pele-pop-legado.css"
BLOCO = re.compile(r'<style id="mb-pop-skin">.*?</style>\n?', re.S)
HTML_TAG = re.compile(r'<html\b[^>]*>')


def aplicar(html: str, css: str) -> str:
    html = BLOCO.sub("", html)
    i = html.find("</head>")
    if i < 0:
        raise ValueError("sem </head>")
    return html[:i] + f'<style id="mb-pop-skin">\n{css.strip()}\n</style>\n' + html[i:]


def aplicar_tema(html: str, tema: str) -> str:
    """Grava/remove data-tema="claro" no <html>. Retorno: (novo, mudou_atributo)."""
    m = HTML_TAG.search(html)
    if not m:
        raise ValueError("sem <html>")
    tag = m.group(0)
    limpo = re.sub(r'\s+data-tema="[^"]*"', "", tag)
    if tema == "claro":
        novo_tag = limpo[:-1] + ' data-tema="claro">'
    else:
        novo_tag = limpo
    return html[:m.start()] + novo_tag + html[m.end():]


def main() -> int:
    args = sys.argv[1:]
    tema = None
    if "--tema" in args:
        i = args.index("--tema")
        try:
            tema = args.pop(i + 1)
        except IndexError:
            print("ERRO: --tema precisa de claro|escuro")
            return 2
        args.pop(i)
        if tema not in ("claro", "escuro"):
            print(f"ERRO: --tema inválido: {tema} (use claro|escuro)")
            return 2
    if not args:
        print(__doc__)
        return 2
    css = CSS.read_text(encoding="utf-8")
    for arg in args:
        p = Path(arg)
        with open(p, encoding="utf-8", newline="") as f:  # newline="": preserva CRLF/LF do arquivo
            antes = f.read()
        depois = aplicar(antes, css)
        nota_tema = ""
        if tema is not None:
            depois2 = aplicar_tema(depois, tema)
            if depois2 != depois:
                nota_tema = f" · data-tema {'gravado' if tema == 'claro' else 'removido'}"
            depois = depois2
        if depois != antes:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(depois)
        print(f"ok  {p}  ({len(antes)} -> {len(depois)} bytes){nota_tema}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

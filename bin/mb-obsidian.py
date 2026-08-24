#!/usr/bin/env python3
"""mb-obsidian.py — aponta o Obsidian pro cérebro do megabrain (v7.1, 260824).

DECISÃO 260824: você instala o Obsidian; o megabrain aponta o vault pra
`memoria/cerebro`. O Obsidian passa a ser a JANELA do cérebro — links entre
páginas, grafo, busca — sem virar dono de nada: quem escreve ali continua
sendo o `/ingerir`, e o formato continua sendo markdown puro.

Por que só `memoria/cerebro` e não a `memoria` inteira: cérebro é conhecimento
de conteúdo (o que você sabe). `estado/`, `nucleo/` e `pendencias/` são
operação do protocolo — quem lê é a IA, e abrir tudo junto vira ruído no grafo.

O que este script faz:
  --preparar (padrão)  cria memoria/cerebro/.obsidian/ com uma config inicial
                       (tema escuro, links relativos, anexos em raw/) SEM
                       sobrescrever nada que já exista, e escreve o leia-me.
  --abrir              abre o vault no Obsidian (obsidian://open?path=...).
                       Na PRIMEIRA vez o Obsidian pode pedir "Open folder as
                       vault" — o caminho fica na área de transferência.

A pasta `.obsidian/` é config LOCAL: já está no .gitignore e nunca sobe.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_utils as u  # noqa: E402

u.utf8_console()

CONFIG = {
    "app.json": {
        "attachmentFolderPath": "raw",
        "newLinkFormat": "relative",
        "useMarkdownLinks": False,
        "alwaysUpdateLinks": True,
        "showUnsupportedFiles": True,
        "readableLineLength": True,
        "strictLineBreaks": False,
        "promptDelete": True,
    },
    "appearance.json": {
        "theme": "obsidian",
        "baseFontSize": 15,
        "showViewHeader": True,
    },
    "core-plugins.json": {
        "file-explorer": True, "global-search": True, "switcher": True,
        "graph": True, "backlink": True, "outgoing-link": True,
        "tag-pane": True, "page-preview": True, "templates": True,
        "note-composer": True, "command-palette": True, "editor-status": True,
        "bookmarks": True, "outline": True, "word-count": True,
        "file-recovery": True, "random-note": False, "daily-notes": False,
        "canvas": True, "properties": True,
    },
    "hotkeys.json": {},
}

LEIAME = """# Cérebro no Obsidian — como usar (260824)

O Obsidian é só uma JANELA pra esta pasta. Ele não muda nada de lugar e não
inventa formato: os arquivos continuam markdown puro, e continuam sendo
escritos pelo `/ingerir`.

## Abrir

Dois cliques em `01_acoes\\260824_abrir-cerebro-obsidian.cmd`.
Na primeira vez o Obsidian pergunta qual pasta é o vault: escolha
**Open folder as vault** e aponte pra esta pasta (o caminho já está na sua
área de transferência).

## O que você ganha

- **Links entre páginas**: escreva `[[nome-do-arquivo]]` e vira link.
- **Grafo**: o mapa de como os assuntos se ligam (ícone de grafo na lateral).
- **Busca de verdade** em tudo que a IA já destilou.
- **Backlinks**: em qualquer página, quem aponta pra ela.

## O que NÃO fazer

- Não renomeie `raw/`, `wiki/` e `pessoas/` — o `/ingerir` e o índice contam
  com esses nomes.
- Não apague a página que o índice cita: quem arquiva é
  `bin\\mb-manutencao-cerebro.py --arquivar`, que move pra `90_arquivo\\` em
  vez de apagar.
- Não instale plugin que reescreve arquivo sozinho (formatadores automáticos):
  eles brigam com o que a IA escreve.

## Onde fica a configuração

`.obsidian/` aqui dentro. É local, está no `.gitignore` e nunca sobe pro
GitHub — inclusive porque guarda o layout da SUA tela.
"""


def vault(central: Path) -> Path:
    return u.pasta(central, "cerebro")


def preparar(central: Path) -> int:
    v = vault(central)
    if not v.is_dir():
        print(f"ERRO: não achei o cérebro em {v}")
        return 1
    cfg = v / ".obsidian"
    cfg.mkdir(exist_ok=True)
    criados, mantidos = [], []
    for nome, conteudo in CONFIG.items():
        alvo = cfg / nome
        if alvo.exists():
            mantidos.append(nome)
            continue
        u.atomic_write_text(alvo, json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n")
        criados.append(nome)
    leiame = v / "260824_obsidian-leiame.md"
    if not leiame.exists():
        u.atomic_write_text(leiame, LEIAME)
        criados.append(leiame.name)
    print(f"vault do Obsidian: {v}")
    if criados:
        print("  criado(s): " + ", ".join(criados))
    if mantidos:
        print("  já existia(m), não toquei: " + ", ".join(mantidos))
    print("  no Obsidian: Open folder as vault → escolha a pasta acima")
    return 0


def abrir(central: Path) -> int:
    v = vault(central)
    if not v.is_dir():
        print(f"ERRO: não achei o cérebro em {v}")
        return 1
    preparar(central)
    caminho = str(v.resolve())
    try:  # deixa o caminho pronto pra colar, caso o Obsidian peça a pasta
        subprocess.run("clip", input=caminho, text=True, shell=True, check=False)
    except OSError:
        pass
    uri = "obsidian://open?path=" + quote(caminho, safe="")
    print(f"abrindo: {uri}")
    try:
        import os
        os.startfile(uri)  # type: ignore[attr-defined]  # Windows
    except (AttributeError, OSError):
        import webbrowser
        if not webbrowser.open(uri):
            print("Não consegui abrir o Obsidian. Abra ele e use "
                  f"'Open folder as vault' apontando pra:\n  {caminho}")
            return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--abrir", action="store_true")
    ap.add_argument("--preparar", action="store_true")
    args = ap.parse_args()
    central = Path(args.dir).resolve() if args.dir else Path(__file__).resolve().parent.parent
    return abrir(central) if args.abrir else preparar(central)


if __name__ == "__main__":
    raise SystemExit(main())

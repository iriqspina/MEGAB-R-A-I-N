#!/usr/bin/env python3
"""mb-mapa-refs.py — mapa de referências a pastas (v7.1, 260824).

PRA QUE SERVE: antes de mover uma pasta da central, saber TODO lugar que fala
dela — e separar o que é caminho de verdade (quebra) do que é prosa (não
quebra). Nasceu da etapa 2 da reorg (máquina → motor\\), onde ~170 citações
ambíguas exigiam revisão arquivo a arquivo.

Uma varredura só, sem grep repetido (a pasta da central é lenta por rede).

Uso:
    python bin/mb-mapa-refs.py dna skills modelos
    python bin/mb-mapa-refs.py --json skills > mapa.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

IGNORAR_DIRS = {".git", "__pycache__", ".mb-log", ".mb-backup", ".mb-aspirador",
                "90_arquivo", "99_to_delete", "_github", ".venv", "node_modules",
                ".obsidian", "data"}
EXT_TEXTO = {".py", ".md", ".txt", ".json", ".cmd", ".ps1", ".html", ".css", ".js",
             ".yml", ".yaml", ".toml", ".ini", ".mjs", ".bat", ".sh"}


def classificar(linha: str, nome: str) -> str:
    """CAMINHO = quebra se a pasta mudar de lugar. PROSA = só texto."""
    if re.search(rf'(?:^|[^\w-]){re.escape(nome)}[\\/]', linha):
        return "caminho"
    if re.search(rf'["\'`(\[]\s*{re.escape(nome)}\s*["\'`)\]]', linha):
        return "literal"
    if re.search(rf'/\s*{re.escape(nome)}\b|\b{re.escape(nome)}\s*/', linha):
        return "caminho"
    return "prosa"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("nomes", nargs="+", help="nomes de pasta pra procurar")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--json", action="store_true", dest="como_json")
    ap.add_argument("--so-caminhos", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else Path(__file__).resolve().parent.parent
    achados: dict[str, list[dict]] = {n: [] for n in args.nomes}
    rx = {n: re.compile(rf'(?<![\w-]){re.escape(n)}(?![\w-])') for n in args.nomes}

    arquivos = 0
    for f in raiz.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in EXT_TEXTO:
            continue
        if any(p in IGNORAR_DIRS for p in f.relative_to(raiz).parts[:-1]):
            continue
        try:
            texto = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        arquivos += 1
        rel = str(f.relative_to(raiz))
        for i, linha in enumerate(texto.splitlines(), 1):
            for nome in args.nomes:
                if rx[nome].search(linha):
                    tipo = classificar(linha, nome)
                    if args.so_caminhos and tipo == "prosa":
                        continue
                    achados[nome].append({"arquivo": rel, "linha": i, "tipo": tipo,
                                          "texto": linha.strip()[:200]})

    if args.como_json:
        print(json.dumps({"raiz": str(raiz), "arquivos_lidos": arquivos,
                          "achados": achados}, ensure_ascii=False, indent=1))
        return 0

    print(f"mapa de referências · {arquivos} arquivos de texto lidos · raiz {raiz.name}")
    for nome, itens in achados.items():
        por_tipo: dict[str, int] = {}
        arqs = {}
        for x in itens:
            por_tipo[x["tipo"]] = por_tipo.get(x["tipo"], 0) + 1
            arqs.setdefault(x["arquivo"], {"caminho": 0, "literal": 0, "prosa": 0})
            arqs[x["arquivo"]][x["tipo"]] += 1
        resumo = " · ".join(f"{k}: {v}" for k, v in sorted(por_tipo.items())) or "nenhuma"
        print(f"\n### {nome} — {len(itens)} citações em {len(arqs)} arquivos ({resumo})")
        for arq, c in sorted(arqs.items(), key=lambda x: -(x[1]["caminho"] + x[1]["literal"])):
            marca = "!!" if (c["caminho"] or c["literal"]) else "  "
            print(f"  {marca} {arq}  caminho:{c['caminho']} literal:{c['literal']} prosa:{c['prosa']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

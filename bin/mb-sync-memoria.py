#!/usr/bin/env python3
"""
mb-sync-memoria.py - sincroniza o arquivo de IDENTIDADE (quem e a pessoa,
formato obrigatorio de resposta) para CLAUDE.md / GEMINI.md / AGENTS.md.

Nao confundir com mb-sync.py (esse gerencia a TRAVA de projeto em
HANDOFF.md). Ver referencias/260810_sync-memoria.md para o protocolo
completo.

Uso:
  mb-sync-memoria.py --source CAMINHO --target claude|gemini|kimi [--dir CAMINHO] [--modo import|conteudo]
  mb-sync-memoria.py --source CAMINHO --target all [--dir CAMINHO] [--modo import|conteudo]

--modo import (default pra claude/gemini): garante a linha "@<source>" em
CLAUDE.md/GEMINI.md/AGENTS.md - nao duplica texto, mas o caminho do source
precisa ser "seguro" pra sintaxe @ do agente (sem espaco costuma ser mais
confiavel - caminho com espaco, ex. pasta "MEGA B R A I  N", pode nao ser
parseado igual por todo agente/versao).
--modo conteudo (default pra kimi, e recomendado se o caminho da fonte tem
espaco): injeta o CONTEUDO do source dentro do arquivo de destino, entre
marcadores - idempotente, roda de novo sem duplicar, sem depender de path
parsing nenhum.
"""

import argparse
import sys
from pathlib import Path

MARK_START = "<!-- MEGABRAIN:AUTO-SYNC:START -->"
MARK_END = "<!-- MEGABRAIN:AUTO-SYNC:END -->"

TARGET_FILE = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "kimi": "AGENTS.md",
}


def ensure_import_line(path: Path, import_linha: str) -> str:
    texto = path.read_text(encoding="utf-8") if path.exists() else ""
    if import_linha in texto:
        return "ja_sincronizado"
    novo = texto.rstrip()
    novo = (novo + "\n\n" if novo else "") + import_linha + "\n"
    path.write_text(novo, encoding="utf-8")
    return "sincronizado"


def inject_content(path: Path, conteudo_fonte: str) -> str:
    bloco = f"{MARK_START}\n{conteudo_fonte.rstrip()}\n{MARK_END}\n"
    texto = path.read_text(encoding="utf-8") if path.exists() else ""
    if MARK_START in texto and MARK_END in texto:
        antes = texto.split(MARK_START, 1)[0]
        depois = texto.split(MARK_END, 1)[1]
        novo = antes + bloco + depois
        acao = "atualizado"
    else:
        titulo = f"# {path.stem}\n\n"
        cabeca = texto.rstrip() + "\n\n" if texto.strip() else titulo
        novo = cabeca + bloco
        acao = "criado"
    path.write_text(novo, encoding="utf-8")
    return acao


def sync_um(target: str, source: Path, diretorio: Path, modo: str) -> str:
    destino = diretorio / TARGET_FILE[target]
    modo_efetivo = modo or ("conteudo" if target == "kimi" else "import")
    if modo_efetivo == "conteudo":
        conteudo = source.read_text(encoding="utf-8")
        return f"{target} ({destino.name}, conteúdo): {inject_content(destino, conteudo)}"
    linha = f"@{source.as_posix()}"
    return f"{target} ({destino.name}, import): {ensure_import_line(destino, linha)}"


def main():
    ap = argparse.ArgumentParser(description="Sincroniza identidade entre agentes")
    ap.add_argument("--source", required=True, help="arquivo de identidade fonte")
    ap.add_argument("--target", required=True, choices=["claude", "gemini", "kimi", "all"])
    ap.add_argument("--dir", default=".", help="raiz do projeto (default: .)")
    ap.add_argument("--modo", choices=["import", "conteudo"], default=None,
                     help="default: conteudo pra kimi, import pra claude/gemini")
    args = ap.parse_args()

    source = Path(args.source)
    diretorio = Path(args.dir)
    if not source.exists():
        print(f"erro: fonte não encontrada: {source}")
        sys.exit(1)

    alvos = ["claude", "gemini", "kimi"] if args.target == "all" else [args.target]
    for t in alvos:
        print(sync_um(t, source, diretorio, args.modo))


if __name__ == "__main__":
    main()

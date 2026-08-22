#!/usr/bin/env python3
"""
mb-sync-memoria.py - sincroniza o arquivo de IDENTIDADE (quem e a pessoa,
formato obrigatorio de resposta) para CLAUDE.md / GEMINI.md / AGENTS.md /
output style do Claude Code.

Nao confundir com mb-sync.py (esse gerencia a TRAVA de projeto em
HANDOFF.md). Ver referencias/260810_sync-memoria.md para o protocolo
completo.

Uso:
  mb-sync-memoria.py --source CAMINHO --target claude|gemini|kimi|claude-style [--dir CAMINHO] [--modo import|conteudo] [--usuario NOME]
  mb-sync-memoria.py --source CAMINHO --target all [--dir CAMINHO] [--modo import|conteudo] [--usuario NOME]

--modo import (default pra claude/gemini): garante a linha "@<source>" em
CLAUDE.md/GEMINI.md/AGENTS.md - nao duplica texto, mas o caminho do source
precisa ser "seguro" pra sintaxe @ do agente (sem espaco costuma ser mais
confiavel - caminho com espaco, ex. pasta "MEGA B R A I  N", pode nao ser
parseado igual por todo agente/versao).
--modo conteudo (default pra kimi, e recomendado se o caminho da fonte tem
espaco): injeta o CONTEUDO do source dentro do arquivo de destino, entre
marcadores - idempotente, roda de novo sem duplicar, sem depender de path
parsing nenhum.
--target claude-style gera ~/.claude/output-styles/megabrain.md (system
prompt/output style do Claude Code, com keep-coding-instructions: true). Nao
usa --modo; sempre grava conteudo.
--usuario forca um nome; se omitido, tenta detectar do campo `USUARIO:` no
arquivo fonte. O campo e propagado pros destinos pra diferenciar perfis.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

TARGET_FILE = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "kimi": "AGENTS.md",
    "codex": "AGENTS.md",
    "claude-style": str(Path("output-styles") / "megabrain.md"),
}


def _com_usuario_prefixo(conteudo: str, usuario: str | None) -> str:
    """Garante que o bloco sincronizado comece com `USUARIO:` quando disponivel.

    Remove linhas `USUARIO:` duplicadas do conteudo original para evitar
    repeticao. Se usuario for None, retorna o conteudo sem alterar a secao.
    """
    if not usuario:
        return conteudo
    linhas_limpas = [
        linha
        for linha in conteudo.splitlines()
        if not linha.strip().upper().startswith("USUARIO:")
    ]
    return f"USUARIO: {usuario}\n\n" + "\n".join(linhas_limpas)


def ensure_import_line(path: Path, import_linha: str, usuario: str | None) -> str:
    texto = u.safe_read_text(path) or ""
    prefixo = f"<!-- USUARIO: {usuario} -->\n" if usuario else ""
    bloco = prefixo + import_linha
    if bloco in texto:
        return "ja_sincronizado"
    # Se soh a linha de import existe sem prefixo, atualiza suavemente.
    if import_linha in texto and prefixo:
        novo = texto.replace(import_linha, bloco, 1)
        if u.atomic_write_text(path, novo):
            return "atualizado"
        return "erro_escrita"
    novo = texto.rstrip()
    novo = (novo + "\n\n" if novo else "") + bloco + "\n"
    if u.atomic_write_text(path, novo):
        return "sincronizado"
    return "erro_escrita"


def inject_content(path: Path, conteudo_fonte: str, usuario: str | None) -> str:
    conteudo = _com_usuario_prefixo(conteudo_fonte, usuario)
    bloco = f"{u.MARK_START}\n{conteudo.rstrip()}\n{u.MARK_END}\n"
    texto = u.safe_read_text(path) or ""
    if u.MARK_START in texto and u.MARK_END in texto:
        antes = texto.split(u.MARK_START, 1)[0]
        depois = texto.split(u.MARK_END, 1)[1]
        novo = antes + bloco + depois
        acao = "atualizado"
    else:
        titulo = f"# {path.stem}\n\n"
        cabeca = texto.rstrip() + "\n\n" if texto.strip() else titulo
        novo = cabeca + bloco
        acao = "criado"
    if u.atomic_write_text(path, novo):
        return acao
    return "erro_escrita"


def sync_um(target: str, source: Path, diretorio: Path, modo: str, usuario: str | None) -> str:
    destino = diretorio / TARGET_FILE[target]
    if target == "claude-style":
        conteudo = _com_usuario_prefixo(u.safe_read_text(source) or "", usuario)
        corpo = (
            "---\n"
            "name: megabrain\n"
            "description: Contrato de resposta do usuario (voz, niveis de detalhe, acoes). "
            "Gerado por mb-sync-memoria.py a partir da fonte de identidade - nao editar aqui.\n"
            "keep-coding-instructions: true\n"
            "---\n\n"
            f"{conteudo}\n"
        )
        destino.parent.mkdir(parents=True, exist_ok=True)
        texto_atual = u.safe_read_text(destino) or ""
        acao = "atualizado" if texto_atual.strip() else "criado"
        if u.atomic_write_text(destino, corpo):
            return f"{target} ({destino.name}): {acao}"
        return f"{target} ({destino.name}): erro_escrita"
    modo_efetivo = modo or ("conteudo" if target == "kimi" else "import")
    if modo_efetivo == "conteudo":
        conteudo = u.safe_read_text(source) or ""
        return f"{target} ({destino.name}, conteudo): {inject_content(destino, conteudo, usuario)}"
    linha = f"@{source.as_posix()}"
    return f"{target} ({destino.name}, import): {ensure_import_line(destino, linha, usuario)}"


def main():
    ap = argparse.ArgumentParser(description="Sincroniza identidade entre agentes")
    ap.add_argument("--source", required=True, help="arquivo de identidade fonte")
    ap.add_argument("--target", required=True, choices=["claude", "gemini", "kimi", "codex", "claude-style", "all"])
    ap.add_argument("--dir", default=".", help="raiz do projeto (default: .)")
    ap.add_argument("--modo", choices=["import", "conteudo"], default=None,
                     help="default: conteudo pra kimi, import pra claude/gemini")
    ap.add_argument("--usuario", default=None,
                     help="nome do usuario (se omitido, detecta do campo USUARIO: do source)")
    args = ap.parse_args()

    source = Path(args.source)
    diretorio = Path(args.dir)
    if not source.exists():
        print(f"erro: fonte nao encontrada: {source}")
        sys.exit(1)

    usuario = args.usuario
    if usuario is None:
        usuario = u.extract_usuario(u.safe_read_text(source) or "")

    alvos = ["claude", "gemini", "kimi"] if args.target == "all" else [args.target]
    for t in alvos:
        print(sync_um(t, source, diretorio, args.modo, usuario))


if __name__ == "__main__":
    main()

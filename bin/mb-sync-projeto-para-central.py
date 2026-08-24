#!/usr/bin/env python3
"""
mb-sync-projeto-para-central.py — sobe as mudancas do megabrain de um projeto
para a central. Use quando o projeto estiver mais atualizado que a central.

Uso:
    python bin/mb-sync-projeto-para-central.py --projeto "<PROJETOS_ROOT>/<Projeto>"

Opções:
    --projeto PATH     Pasta do projeto que contém MEGABRAIN/
    --central PATH     Pasta central do megabrain (default: detecta via
                       MEGABRAIN_CENTRAL ou diretório pai de bin/)
    --dry-run          Só reporta, não copia nada

Lições (licoes-megabrain.md) sobem por MERGE: entradas que só existem no
projeto são apendadas ao arquivo da central; nada da central é sobrescrito
ou removido. Isso fecha a mão dupla — antes a lição de projeto ficava presa
no projeto para sempre.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

LICOES_NAME = "licoes-megabrain.md"

MAPEAMENTO = [
    ("MEGABRAIN/MEGABRAIN.md", "MEGABRAIN.md"),
    ("MEGABRAIN/skills/megabrain/SKILL.md", "skills/megabrain/SKILL.md"),
    ("MEGABRAIN/referencias", "referencias"),
    ("MEGABRAIN/VERSAO.txt", "VERSAO.txt"),
]

# Entradas de lição começam com "## " (padrão: "## YYMMDD — contexto").
RE_ENTRADA = re.compile(r"^## ", re.MULTILINE)


def detectar_central():
    """Central via MEGABRAIN_CENTRAL ou diretório pai de bin/ — sem hardcode."""
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def parece_central(pasta: Path) -> bool:
    """Falha fechada: só escreve numa pasta que tem cara de central."""
    return (u.achar(pasta, "VERSAO.txt")).is_file() and (u.achar(pasta, "MEGABRAIN.md")).is_file()


def dividir_entradas(texto: str):
    """Divide o arquivo de lições em (preambulo, [entradas]).

    Cada entrada é o bloco de um "## " até o próximo. A chave de comparação
    é a primeira linha normalizada (espaços colapsados, sem pontuação final).
    """
    posicoes = [m.start() for m in RE_ENTRADA.finditer(texto)]
    if not posicoes:
        return texto, []
    preambulo = texto[: posicoes[0]]
    entradas = []
    for i, inicio in enumerate(posicoes):
        fim = posicoes[i + 1] if i + 1 < len(posicoes) else len(texto)
        entradas.append(texto[inicio:fim])
    return preambulo, entradas


def chave_entrada(bloco: str) -> str:
    primeira = bloco.splitlines()[0] if bloco.splitlines() else ""
    return " ".join(primeira.strip().lower().split())


def merge_licoes(licoes_projeto: Path, licoes_central: Path, dry_run=False) -> bool:
    texto_projeto = u.safe_read_text(licoes_projeto)
    if texto_projeto is None:
        print(f"  ERRO: não consegui ler {licoes_projeto}")
        return False

    texto_central = u.safe_read_text(licoes_central)
    if texto_central is None:
        # Central ainda não tem o arquivo: sobe inteiro.
        if dry_run:
            print(f"  [dry-run] criaria {licoes_central} a partir do projeto")
            return True
        ok = u.atomic_write_text(licoes_central, texto_projeto)
        if ok:
            print(f"  criado {LICOES_NAME} na central (cópia do projeto)")
        return ok

    _, entradas_projeto = dividir_entradas(texto_projeto)
    _, entradas_central = dividir_entradas(texto_central)
    chaves_central = {chave_entrada(e) for e in entradas_central}

    novas = [e for e in entradas_projeto if chave_entrada(e) not in chaves_central]
    if not novas:
        print(f"  {LICOES_NAME}: nada novo no projeto")
        return True

    if dry_run:
        print(f"  [dry-run] apendaria {len(novas)} lição(ões) do projeto na central:")
        for e in novas:
            print(f"    + {e.splitlines()[0].strip()}")
        return True

    resultado = texto_central.rstrip("\n") + "\n\n" + "\n".join(e.rstrip("\n") + "\n" for e in novas)
    ok = u.atomic_write_text(licoes_central, resultado)
    if ok:
        print(f"  {LICOES_NAME}: {len(novas)} lição(ões) apendada(s) na central")
    return ok


def copiar(src: Path, dst: Path, central: Path, dry_run=False) -> bool:
    try:
        u.resolve_within(dst, central)
    except ValueError as e:
        print(f"  ERRO (recusado): {e}")
        return False

    if dry_run:
        print(f"  [dry-run] copiaria {src} -> {dst} (merge, sem apagar o que já existe)")
        return True

    if src.is_dir():
        # 260818: merge, não replace. dirs_exist_ok sobrescreve arquivos com o
        # mesmo nome (o projeto é a fonte da verdade pro que ele de fato tem)
        # mas preserva o que só existe na central.
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
        except OSError as e:
            print(f"  ERRO ao copiar {src} -> {dst}: {e}")
            return False
    else:
        conteudo = u.safe_read_text(src)
        if conteudo is None:
            print(f"  ERRO: não consegui ler {src}")
            return False
        if not u.atomic_write_text(dst, conteudo):
            return False
    print(f"  copiado {src.name} -> {dst}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--projeto", required=True)
    p.add_argument("--central", default=detectar_central())
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    central = Path(args.central).resolve()
    if not central.is_dir():
        print(f"ERRO: central não encontrada em {central}")
        print("Dica: defina MEGABRAIN_CENTRAL ou passe --central")
        sys.exit(1)
    if not parece_central(central):
        print(f"ERRO: {central} não parece uma central do megabrain "
              "(sem VERSAO.txt/MEGABRAIN.md) — recusando escrever nela.")
        print("Dica: defina MEGABRAIN_CENTRAL ou passe --central")
        sys.exit(1)

    projeto = Path(args.projeto).resolve()
    mb_projeto = projeto / "MEGABRAIN"
    if not mb_projeto.is_dir():
        print(f"ERRO: {projeto} não tem MEGABRAIN/")
        sys.exit(1)

    falhas = []
    print("sincronizando projeto -> central...")
    for src_rel, dst_rel in MAPEAMENTO:
        src = projeto / src_rel
        dst = u.achar(central, dst_rel)   # v7.1: resolve motor/ na central
        if not src.exists():
            print(f"  AVISO: {src} não existe no projeto, pulando")
            continue
        if not copiar(src, dst, central, args.dry_run):
            falhas.append(dst_rel)

    licoes_projeto = mb_projeto / LICOES_NAME
    if licoes_projeto.exists():
        if not merge_licoes(licoes_projeto, central / LICOES_NAME, args.dry_run):
            falhas.append(LICOES_NAME)
    else:
        print(f"  AVISO: projeto sem {LICOES_NAME}, pulando merge de lições")

    if falhas:
        print(f"ERRO: falhas em: {falhas}")
        sys.exit(1)

    print("sync projeto -> central concluído")
    print("LEMBRETE: após atualizar a central, rode mb-check-version.py nos outros projetos para propagar.")


if __name__ == "__main__":
    main()

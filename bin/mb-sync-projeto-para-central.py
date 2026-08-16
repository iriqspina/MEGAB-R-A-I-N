#!/usr/bin/env python3
"""
mb-sync-projeto-para-central.py — sobe as mudancas do megabrain de um projeto
para a central. Use quando o projeto estiver mais atualizado que a central.

Uso:
    python bin/mb-sync-projeto-para-central.py --projeto "<PROJETOS_ROOT>/<Projeto>"

Opções:
    --projeto PATH     Pasta do projeto que contém MEGABRAIN/
    --central PATH     Pasta central do megabrain (default: <MEGABRAIN_ROOT>)
    --dry-run          Só reporta, não copia nada
"""

import argparse
import os
import shutil
import sys

CENTRAL_DEFAULT = "<MEGABRAIN_ROOT>"

MAPEAMENTO = [
    ("MEGABRAIN/MEGABRAIN.md", "MEGABRAIN.md"),
    ("MEGABRAIN/skills/megabrain/SKILL.md", "skills/megabrain/SKILL.md"),
    ("MEGABRAIN/referencias", "referencias"),
    ("MEGABRAIN/VERSAO.txt", "VERSAO.txt"),
]


def copiar(src, dst, dry_run=False):
    if dry_run:
        print(f"  [dry-run] copiaria {src} -> {dst}")
        return True
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print(f"  copiado {os.path.basename(src)} -> {dst}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--projeto", required=True)
    p.add_argument("--central", default=CENTRAL_DEFAULT)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not os.path.isdir(args.central):
        print(f"ERRO: central não encontrada em {args.central}")
        sys.exit(1)

    mb_projeto = os.path.join(args.projeto, "MEGABRAIN")
    if not os.path.isdir(mb_projeto):
        print(f"ERRO: {args.projeto} não tem MEGABRAIN/")
        sys.exit(1)

    print("sincronizando projeto -> central...")
    for src_rel, dst_rel in MAPEAMENTO:
        src = os.path.join(args.projeto, src_rel)
        dst = os.path.join(args.central, dst_rel)
        if not os.path.exists(src):
            print(f"  AVISO: {src} não existe no projeto, pulando")
            continue
        copiar(src, dst, args.dry_run)

    print("sync projeto -> central concluído")
    print("LEMBRETE: após atualizar a central, rode mb-check-version.py nos outros projetos para propagar.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
mb-backup-central.py — faz backup compactado da pasta central do megabrain.

A central é a fonte de verdade do protocolo. Se ela for perdida ou
corrompida, todos os projetos derivados param de receber atualizações. Este
script cria um snapshot zipado que pode ser usado para restaurar a central
ou recuperar um projeto via mb-recuperar-megabrain.py.

Uso:
    python bin/mb-backup-central.py [--destino CAMINHO] [--central CAMINHO]

Default do destino: <CENTRAL>/.mb-backup/central-YYYYMMDD-HHMMSS.zip
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import mb_utils as u

u.utf8_console()


def detectar_central():
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


CENTRAL_DEFAULT = detectar_central()
CENTRAL_DEFAULT_PATH = Path(CENTRAL_DEFAULT).resolve()

# Pastas/arquivos que não entram no backup (gerados, caches, repos)
EXCLUIR = {
    ".git",
    "__pycache__",
    ".mb-aspirador",
    ".dna-backup",
    "260810_github-export",
    "_github-repo-local",
    "_to_delete", "99_to_delete",
    "alteracoes-pendentes", "08_alteracoes-pendentes",
    ".mb-backup",  # evita backup recursivo
}


def deve_incluir(rel_path: str) -> bool:
    partes = Path(rel_path).parts
    return not any(x in partes for x in EXCLUIR)


def fazer_backup(central: Path, destino: Path) -> bool:
    if not central.is_dir():
        print(f"ERRO: central não encontrada em {central}")
        return False

    if not u.ensure_parent_dir(destino):
        return False

    try:
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(central):
                # Filtra diretórios no lugar para não descer neles
                dirs[:] = [d for d in dirs if d not in EXCLUIR]
                for f in files:
                    caminho = Path(root) / f
                    rel = caminho.relative_to(central)
                    if not deve_incluir(str(rel)):
                        continue
                    zf.write(caminho, arcname=str(rel))
        print(f"backup criado: {destino}")
        return True
    except OSError as e:
        print(f"ERRO ao criar backup {destino}: {e}")
        return False


def main():
    p = argparse.ArgumentParser(description="Backup da central do megabrain")
    p.add_argument("--central", default=CENTRAL_DEFAULT,
                   help="pasta central do megabrain")
    p.add_argument("--destino", default=None,
                   help="caminho do arquivo zip (default: .mb-backup/central-YYYYMMDD-HHMMSS.zip)")
    args = p.parse_args()

    try:
        central = u.resolve_within(args.central, CENTRAL_DEFAULT_PATH)
    except ValueError as e:
        print(f"ERRO: central inválida: {e}")
        sys.exit(1)

    if args.destino:
        try:
            destino = u.resolve_within(args.destino, CENTRAL_DEFAULT_PATH)
        except ValueError:
            # Permite caminho absoluto fora da central (backup externo)
            destino = Path(args.destino).resolve()
    else:
        backup_dir = central / ".mb-backup"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destino = backup_dir / f"central-{timestamp}.zip"

    ok = fazer_backup(central, destino)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

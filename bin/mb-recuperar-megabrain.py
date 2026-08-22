#!/usr/bin/env python3
"""
mb-recuperar-megabrain.py — recria a pasta MEGABRAIN/ de um projeto a partir
de uma fonte qualquer (outro projeto, backup zip, ou central).

Usar quando:
- A pasta MEGABRAIN/ do projeto foi apagada ou corrompida.
- A central local sumiu, mas outro projeto ainda tem uma cópia.
- Você tem um zip de backup criado por mb-backup-central.py.

Uso:
    python bin/mb-recuperar-megabrain.py --projeto "caminho/do/projeto" --fonte "outro/projeto/MEGABRAIN"
    python bin/mb-recuperar-megabrain.py --projeto "caminho/do/projeto" --fonte "/caminho/central.zip"
    python bin/mb-recuperar-megabrain.py --projeto "caminho/do/projeto"  # tenta detectar fonte
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
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


def listar_backups(central: Path) -> list[Path]:
    backup_dir = central / ".mb-backup"
    if not backup_dir.is_dir():
        return []
    return sorted(
        [f for f in backup_dir.iterdir() if f.suffix == ".zip"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def encontrar_fonte(projeto: Path, central: Path) -> Path | None:
    """Tenta achar uma fonte MEGABRAIN/ sem --fonte explicito."""
    # 1. central
    if central.is_dir():
        return central

    # 2. outro projeto na mesma pasta pai
    pai = projeto.parent
    if pai.is_dir():
        for item in pai.iterdir():
            if item == projeto:
                continue
            candidato = item / "MEGABRAIN" / "VERSAO.txt"
            if candidato.is_file():
                return item / "MEGABRAIN"

    # 3. backup mais recente da central
    backups = listar_backups(central)
    if backups:
        return backups[0]

    return None


def copiar_pasta(src: Path, dst: Path, base: Path) -> bool:
    try:
        u.resolve_within(dst, base)
    except ValueError as e:
        print(f"ERRO (recusado): {e}")
        return False

    if dst.exists():
        print(f"removendo MEGABRAIN/ antigo em {dst}")
        if not u.safe_rmtree(dst, base=base):
            return False

    try:
        shutil.copytree(src, dst)
        print(f"copiado {src} -> {dst}")
        return True
    except OSError as e:
        print(f"ERRO ao copiar {src} -> {dst}: {e}")
        return False


def extrair_zip(zip_path: Path, dst: Path, base: Path) -> bool:
    try:
        u.resolve_within(dst, base)
    except ValueError as e:
        print(f"ERRO (recusado): {e}")
        return False

    if dst.exists():
        print(f"removendo MEGABRAIN/ antigo em {dst}")
        if not u.safe_rmtree(dst, base=base):
            return False

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Se o zip for de pasta central, extrair só o que seria MEGABRAIN/
            nomes = zf.namelist()
            # Verifica se o zip é de uma pasta central (tem bin/, referencias/ no root)
            raiz_eh_central = any(n.startswith("bin/") for n in nomes) and any(n.startswith("referencias/") for n in nomes)
            if raiz_eh_central:
                prefixo = ""
            else:
                # assume MEGABRAIN/ dentro do zip
                prefixo = "MEGABRAIN/"

            dst.mkdir(parents=True, exist_ok=True)
            for membro in nomes:
                if not membro.startswith(prefixo):
                    continue
                resto = membro[len(prefixo):]
                if not resto:
                    continue
                destino_membro = dst / resto
                try:
                    u.resolve_within(destino_membro, base)
                except ValueError:
                    print(f"AVISO: pulando membro fora da área permitida: {membro}")
                    continue
                # Extrai o membro para uma pasta temporária dentro de dst.parent,
                # depois move para o destino final, preservando a estrutura relativa.
                import tempfile
                with tempfile.TemporaryDirectory(dir=dst.parent, prefix=".rec-") as tmpdir:
                    zf.extract(membro, path=tmpdir)
                    origem = Path(tmpdir) / membro
                    if prefixo:
                        # remove o prefixo MEGABRAIN/ do caminho extraído
                        origem = Path(tmpdir) / resto
                    if origem.exists():
                        destino_membro.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(origem), str(destino_membro))
        print(f"extraído {zip_path} -> {dst}")
        return True
    except (OSError, zipfile.BadZipFile) as e:
        print(f"ERRO ao extrair {zip_path}: {e}")
        return False


def normalizar_fonte(fonte: Path, central: Path) -> Path | None:
    """Se a fonte for uma pasta central, retorna ela mesma.
    Se for uma pasta MEGABRAIN/, retorna ela.
    Se for um zip, retorna ele."""
    if not fonte.exists():
        return None
    if fonte.is_file() and fonte.suffix == ".zip":
        return fonte
    if fonte.is_dir():
        # Se for central (tem bin/, referencias/ no root)
        if (fonte / "bin").is_dir() and (fonte / "referencias").is_dir():
            return fonte
        # Se já for MEGABRAIN/
        if (u.achar(fonte, "VERSAO.txt")).is_file():
            return fonte
    return None


def main():
    p = argparse.ArgumentParser(description="Recupera MEGABRAIN/ de um projeto")
    p.add_argument("--projeto", required=True, help="pasta do projeto a recuperar")
    p.add_argument("--fonte", default=None,
                   help="fonte: pasta central, pasta MEGABRAIN/, ou arquivo zip")
    args = p.parse_args()

    projeto = Path(args.projeto).resolve()
    central = CENTRAL_DEFAULT_PATH

    try:
        u.resolve_within(projeto, Path(".").resolve())
    except ValueError:
        # Permite caminho absoluto
        pass

    fonte: Path | None = None
    if args.fonte:
        fonte = Path(args.fonte).resolve()
        if not fonte.exists():
            print(f"ERRO: fonte não encontrada: {fonte}")
            sys.exit(1)
    else:
        fonte = encontrar_fonte(projeto, central)
        if fonte is None:
            print("ERRO: não consegui detectar uma fonte automaticamente.")
            print("Dica: passe --fonte com o caminho de outro projeto, central ou backup zip.")
            sys.exit(1)
        print(f"fonte detectada automaticamente: {fonte}")

    mb_destino = projeto / "MEGABRAIN"
    base_segura = projeto.resolve()

    if fonte.is_file():
        ok = extrair_zip(fonte, mb_destino, base_segura)
    else:
        fonte_normalizada = normalizar_fonte(fonte, central)
        if fonte_normalizada is None:
            print(f"ERRO: fonte não parece uma central, MEGABRAIN/ ou zip válido: {fonte}")
            sys.exit(1)
        ok = copiar_pasta(fonte_normalizada, mb_destino, base_segura)

    if ok:
        print(f"\nMEGABRAIN/ recuperado em {mb_destino}")
        print("Próximo passo: rode mb-check-version.py no projeto para validar.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

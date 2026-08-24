#!/usr/bin/env python3
"""Garante que a biblioteca cryptography esteja disponível para o cofre.

Cria um ambiente virtual em gerenteneuron/.venv e instala cryptography.
Não instala no Python global do usuário.
"""

import subprocess
import sys
from pathlib import Path


raiz = Path(__file__).resolve().parent
venv_dir = raiz / ".venv"


def main():
    try:
        __import__("cryptography")
        print("cryptography já está disponível.")
        return 0
    except ImportError:
        pass

    print(" cryptography não encontrado. Criando ambiente virtual e instalando...")

    if not venv_dir.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print(f"Ambiente virtual criado em {venv_dir}")

    pip = venv_dir / "Scripts" / "pip.exe" if sys.platform == "win32" else venv_dir / "bin" / "pip"
    subprocess.run([str(pip), "install", "cryptography"], check=True)

    print("cryptography instalado no ambiente virtual.")
    print("Use run.cmd ou o Python do .venv para rodar o app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

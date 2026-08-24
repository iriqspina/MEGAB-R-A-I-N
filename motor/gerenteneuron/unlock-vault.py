#!/usr/bin/env python3
"""Desbloqueia o cofre e exporta credenciais como .env temporário."""

import getpass
import sys
from pathlib import Path

from vault import Vault


def main():
    v = Vault()
    if not v.existe():
        print("Cofre não existe. Rode setup-vault.py primeiro.")
        return 1

    senha = getpass.getpass("Senha do cofre: ")
    try:
        v.desbloquear(senha)
    except ValueError:
        print("Senha incorreta.")
        return 1

    env_lines = ["# GerenteNeuron — exportado do cofre"]
    for chave in v.listar():
        env_lines.append(f'{chave}="{v.get(chave)}"')

    env_path = Path("vault") / ".env.unlocked"
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(f"Credenciais exportadas para {env_path.resolve()}")
    print("Este arquivo é temporário. Delete assim que não precisar mais.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Cria o cofre de credenciais do GerenteNeuron."""

import getpass
import sys
from pathlib import Path

from vault import Vault


def main():
    v = Vault()
    if v.existe():
        print("Cofre já existe. Para recriar, delete a pasta vault/ manualmente.")
        return 1

    senha = getpass.getpass("Crie uma senha mestre para o cofre: ")
    senha2 = getpass.getpass("Digite novamente: ")
    if senha != senha2:
        print("Senhas não coincidem.")
        return 1
    if len(senha) < 6:
        print("Senha muito curta. Use pelo menos 6 caracteres.")
        return 1

    recovery = v.criar(senha)
    print("\nCofre criado com sucesso.")
    print(f"Chave de recuperação salva em: {Path('vault/recovery.key').resolve()}")
    print("GUARDE ESTE ARQUIVO EM LOCAL SEGURO. Sem ele, não é possível recuperar a senha.")
    print("\nPrimeiros 8 caracteres da chave (para conferência):")
    print(recovery[:8] + "...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

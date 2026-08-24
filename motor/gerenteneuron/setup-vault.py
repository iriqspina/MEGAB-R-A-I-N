#!/usr/bin/env python3
"""Cria o cofre de credenciais do GerenteNeuron.

A chave de recuperação é gravada FORA da pasta do cofre. Guardar as duas coisas
juntas anula a senha mestre para quem tem acesso ao disco.

    python setup-vault.py
    python setup-vault.py --saida E:\\backup\\chave-gerenteneuron.txt
"""

import argparse
import getpass
import sys
from pathlib import Path

from vault import Vault, VAULT_DIR, destino_padrao_recuperacao


def main() -> int:
    p = argparse.ArgumentParser(description="Cria o cofre de credenciais")
    p.add_argument(
        "--saida",
        help=f"onde gravar a chave de recuperação (padrão: {destino_padrao_recuperacao()})",
    )
    args = p.parse_args()

    v = Vault()
    if v.existe():
        print(f"Cofre já existe em {VAULT_DIR}.")
        print("Para recriar, apague essa pasta manualmente — os dados serão perdidos.")
        return 1

    destino = Path(args.saida) if args.saida else destino_padrao_recuperacao()
    if VAULT_DIR.resolve() in destino.resolve().parents:
        print("Recusado: a chave de recuperação não pode ficar dentro da pasta do cofre.")
        print("Quem tiver a pasta abriria o cofre sem precisar da senha.")
        return 1

    print(f"Cofre        : {VAULT_DIR}")
    print(f"Chave de rec.: {destino}\n")

    senha = getpass.getpass("Crie uma senha mestre para o cofre: ")
    senha2 = getpass.getpass("Digite novamente: ")
    if senha != senha2:
        print("Senhas não coincidem.")
        return 1
    if len(senha) < 6:
        print("Senha muito curta. Use pelo menos 6 caracteres.")
        return 1

    recovery, caminho = v.criar(senha, destino_recuperacao=destino)

    print("\nCofre criado.")
    print(f"Chave de recuperação gravada em: {caminho}")
    print("Conferência (8 primeiros caracteres):", recovery[:8] + "...")
    print()
    print("PRÓXIMO PASSO IMPORTANTE")
    print("Mova esse arquivo para um pendrive ou para o seu gerenciador de senhas.")
    print("Sem ele, esquecer a senha mestre significa perder as credenciais.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""CLI do cofre de credenciais do GerenteNeuron.

Comandos:
    python mb-vault.py add OPENAI_API_KEY sk-...
    python mb-vault.py get OPENAI_API_KEY
    python mb-vault.py rm OPENAI_API_KEY
    python mb-vault.py list
    python mb-vault.py reset --recovery <chave>
"""

import argparse
import getpass
import sys

from vault import Vault, destino_padrao_recuperacao, aviso_recuperacao_exposta


def main():
    parser = argparse.ArgumentParser(description="Cofre de credenciais do GerenteNeuron")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add_p = sub.add_parser("add", help="adiciona ou atualiza uma credencial")
    add_p.add_argument("chave")
    add_p.add_argument("valor")

    get_p = sub.add_parser("get", help="mostra uma credencial")
    get_p.add_argument("chave")

    rm_p = sub.add_parser("rm", help="remove uma credencial")
    rm_p.add_argument("chave")

    sub.add_parser("list", help="lista chaves armazenadas")

    reset_p = sub.add_parser("reset", help="redefine senha com chave de recuperação")
    reset_p.add_argument("--recovery", required=True)

    args = parser.parse_args()

    aviso = aviso_recuperacao_exposta()
    if aviso:
        print(aviso, "\n")

    v = Vault()
    if not v.existe() and args.cmd != "setup":
        print("Cofre não existe. Rode setup-vault.py primeiro.")
        return 1

    if args.cmd == "reset":
        nova = getpass.getpass("Nova senha mestre: ")
        nova2 = getpass.getpass("Repita: ")
        if nova != nova2:
            print("Senhas não coincidem.")
            return 1
        try:
            new_key = v.redefinir_senha_com_recuperacao(args.recovery, nova)
            print("Senha redefinida. A chave antiga foi queimada e outra foi gerada.")
            print(f"Salva em: {getattr(v, 'destino_recuperacao', destino_padrao_recuperacao())}")
            print("Conferência:", new_key[:8] + "...")
        except ValueError as e:
            print(f"Erro: {e}")
            return 1
        return 0

    senha = getpass.getpass("Senha do cofre: ")
    try:
        v.desbloquear(senha)
    except ValueError:
        print("Senha incorreta.")
        return 1

    if args.cmd == "add":
        v.set(args.chave, args.valor)
        print(f"{args.chave} salvo.")
    elif args.cmd == "get":
        print(v.get(args.chave, ""))
    elif args.cmd == "rm":
        v.remover(args.chave)
        print(f"{args.chave} removido.")
    elif args.cmd == "list":
        for chave in v.listar():
            print(chave)

    return 0


if __name__ == "__main__":
    sys.exit(main())

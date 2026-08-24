#!/usr/bin/env python3
"""Instalador único do GerenteNeuron — do zero até as chaves testadas.

Faz, em ordem, o que antes eram quatro scripts e um README:
  1. garante o venv com cryptography
  2. cria o cofre (chave de recuperação FORA da pasta do cofre)
  3. pergunta cada API key, uma por vez, sem ecoar na tela
  4. testa conectividade de cada provedor configurado
  5. confere pricing.json contra a lista viva de modelos

Rode `configurar.cmd`. Pode rodar de novo a qualquer momento: pula o que já
está feito e só pede o que falta.
"""

import getpass
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
PY_VENV = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

PROVEDORES = [
    ("OPENAI_API_KEY", "OpenAI (ChatGPT / GPT-5.6)", "sk-..."),
    ("ANTHROPIC_API_KEY", "Anthropic (Claude)", "sk-ant-..."),
    ("GEMINI_API_KEY", "Google Gemini", "AIza..."),
    ("MOONSHOT_API_KEY", "Moonshot (Kimi)", "sk-..."),
]


def cabecalho(n: int, texto: str):
    print(f"\n{'=' * 62}\n  {n}. {texto}\n{'=' * 62}")


def garantir_venv() -> int:
    cabecalho(1, "Ambiente de criptografia")
    try:
        __import__("cryptography")
        print("cryptography disponível neste Python. Nada a fazer.")
        return 0
    except ImportError:
        pass

    if PY_VENV.exists():
        print(f"Ambiente virtual já existe: {VENV}")
        print("Reabrindo o instalador com o Python do venv...\n")
        return subprocess.call([str(PY_VENV), str(Path(__file__).resolve())])

    print(f"Criando ambiente virtual em {VENV} ...")
    subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    pip = VENV / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")
    subprocess.run([str(pip), "install", "--quiet", "cryptography"], check=True)
    print("cryptography instalado.\nReabrindo o instalador com o Python do venv...\n")
    return subprocess.call([str(PY_VENV), str(Path(__file__).resolve())])


def garantir_cofre(Vault, destino_padrao_recuperacao, VAULT_DIR):
    cabecalho(2, "Cofre de credenciais")
    v = Vault()
    if v.existe():
        print(f"Cofre já existe em {VAULT_DIR}.")
        for _ in range(3):
            senha = getpass.getpass("Senha mestre: ")
            try:
                v.desbloquear(senha)
                print("Cofre aberto.")
                return v
            except ValueError:
                print("Senha incorreta.")
        print("Três tentativas erradas. Se perdeu a senha, use:")
        print("  mb-vault.py reset --recovery <chave>")
        return None

    destino = destino_padrao_recuperacao()
    print("O cofre guarda suas API keys cifradas (Fernet + PBKDF2 600k).")
    print(f"Pasta do cofre     : {VAULT_DIR}")
    print(f"Chave de recuperação: {destino}")
    print("A chave nasce FORA da pasta do cofre de propósito — juntas, elas")
    print("anulam a senha mestre para quem tiver acesso ao disco.\n")

    for _ in range(3):
        senha = getpass.getpass("Crie uma senha mestre (mín. 6 caracteres): ")
        if len(senha) < 6:
            print("Curta demais.")
            continue
        if senha != getpass.getpass("Digite novamente: "):
            print("Não coincidem.")
            continue
        recovery, caminho = v.criar(senha, destino_recuperacao=destino)
        print(f"\nCofre criado. Chave de recuperação em: {caminho}")
        print("Conferência:", recovery[:8] + "...")
        print(">> Mova esse arquivo para um pendrive ou gerenciador de senhas. <<")
        return v
    return None


def cadastrar_chaves(v) -> int:
    cabecalho(3, "Chaves de API")
    print("Enter em branco pula o provedor. A digitação não aparece na tela.")
    print("Você pode rodar este instalador de novo depois para adicionar mais.\n")

    ja_tem = set(v.listar())
    novas = 0
    for chave, rotulo, exemplo in PROVEDORES:
        marca = " [já cadastrada — Enter mantém]" if chave in ja_tem else ""
        valor = getpass.getpass(f"  {rotulo} ({exemplo}){marca}: ").strip()
        if not valor:
            continue
        v.set(chave, valor)
        novas += 1
        print(f"    {chave} salva.")

    if not novas and not ja_tem:
        print("\nNenhuma chave cadastrada. O app vai funcionar só com Ollama local")
        print("e com o mock de validação.")
    return novas


def testar(v) -> None:
    cabecalho(4, "Teste de conectividade")
    import os
    for k, val in v.exportar_env().items():
        os.environ[k] = val

    from config import carregar_config
    from connectors import testar_todos

    for nome, r in testar_todos(carregar_config()).items():
        if r.get("ok"):
            extra = f" ({r['modelos_disponiveis']} modelos)" if "modelos_disponiveis" in r else ""
            print(f"  [ok]   {nome}{extra}")
        else:
            print(f"  [--]   {nome}: {r.get('erro')}")


def main() -> int:
    print("GerenteNeuron — instalador")

    ret = garantir_venv()
    if ret != 0:
        return ret
    try:
        __import__("cryptography")
    except ImportError:
        # O venv foi criado e o instalador rodou de novo lá dentro; nada a fazer aqui.
        return 0

    from vault import Vault, destino_padrao_recuperacao, VAULT_DIR

    v = garantir_cofre(Vault, destino_padrao_recuperacao, VAULT_DIR)
    if v is None:
        return 1

    cadastrar_chaves(v)
    testar(v)

    cabecalho(5, "Tabela de modelos e preços")
    sys.path.insert(0, str(RAIZ))
    import runpy
    sys.argv = ["mb-modelos.py", "--conferir"]
    try:
        runpy.run_path(str(RAIZ / "mb-modelos.py"), run_name="__main__")
    except SystemExit:
        pass

    print(f"\n{'=' * 62}")
    print("  Pronto. Rode run.cmd para abrir o app.")
    print(f"{'=' * 62}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

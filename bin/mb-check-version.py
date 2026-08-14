#!/usr/bin/env python3
"""
mb-check-version.py — compara a versão do megabrain de um projeto com a central.

Regras:
- Se as versões forem iguais: nada a fazer.
- Se a central for mais nova: sincroniza central -> projeto (a menos que --dry-run).
- Se o projeto for mais novo: NÃO sobrescreve; reporta e pergunta/sai com codigo 2.
- Se nao houver MEGABRAIN/ no projeto: cria a partir da central.

A central é detectada automaticamente a partir do diretório do script ou da
variável de ambiente MEGABRAIN_CENTRAL. Isso torna o script portátil.

Uso:
    python bin/mb-check-version.py --projeto "./meu-projeto"
    python bin/mb-check-version.py --projeto "./meu-projeto" --verificar-git

Opções:
    --projeto PATH     Pasta do projeto
    --central PATH     Pasta central do megabrain (default: detecta)
    --dry-run          Só reporta, não copia nada
    --force            Força sincronização mesmo se versões baterem
    --auto             Não pergunta; se projeto for mais novo, só reporta e sai com 2
    --verificar-git    Consulta o repositório remoto e avisa se há versão mais recente
"""

import argparse
import os
import re
import shutil
import sys

def detectar_central():
    """Retorna a pasta central do megabrain via env var ou diretório do script."""
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return os.path.abspath(env)
    # Diretório pai de bin/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


CENTRAL_DEFAULT = detectar_central()

MAPEAMENTO = [
    ("MEGABRAIN.md", "MEGABRAIN.md"),
    ("260810_MEGABRAIN.md", "260810_MEGABRAIN.md"),
    ("skills/megabrain/SKILL.md", "skills/megabrain/SKILL.md"),
    ("referencias", "referencias"),
    ("VERSAO.txt", "VERSAO.txt"),
    ("bin", "bin"),
    ("dna", "dna"),  # pasta DNA (RELATORIO-DNA.html + dna.json + README.md) — desde 260814
]


def parse_versao(linha):
    """Extrai data e numero de versao de uma linha como '2026-08-13 · v3.5 — ...'"""
    if not linha:
        return None, None
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s*·\s*v([\d.]+)", linha.strip())
    if m:
        return m.group(1), m.group(2)
    return None, None


def ler_versao(pasta):
    path = os.path.join(pasta, "VERSAO.txt")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f if l.strip()]
    return linhas[0] if linhas else None


def comparar_versoes(v_central, v_projeto):
    """Retorna 'central', 'projeto', 'igual' ou 'indefinido'."""
    if v_central == v_projeto:
        return "igual"
    d_c, n_c = parse_versao(v_central)
    d_p, n_p = parse_versao(v_projeto)
    if d_c and d_p and d_c != d_p:
        return "central" if d_c > d_p else "projeto"
    if n_c and n_p:
        def tupla(n):
            return tuple(int(x) for x in n.split("."))
        if tupla(n_c) > tupla(n_p):
            return "central"
        if tupla(n_p) > tupla(n_c):
            return "projeto"
    return "indefinido"


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


def verificar_git(remote_url="https://github.com/iriqspina/MEGAB-R-A-I-N.git"):
    """Consulta o remote e retorna o hash do último commit em main."""
    try:
        import subprocess
        resultado = subprocess.run(
            ["git", "ls-remote", remote_url, "refs/heads/main"],
            capture_output=True, text=True, timeout=15, check=False
        )
        if resultado.returncode != 0:
            return None, resultado.stderr.strip()
        linha = resultado.stdout.strip()
        if not linha:
            return None, "remote não retornou refs/heads/main"
        hash_remoto = linha.split()[0]
        return hash_remoto, None
    except Exception as e:
        return None, str(e)


def hash_commit_local(pasta):
    """Retorna o hash do HEAD de um repo git local, ou None se não for repo."""
    try:
        import subprocess
        resultado = subprocess.run(
            ["git", "-C", pasta, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False
        )
        if resultado.returncode != 0:
            return None
        return resultado.stdout.strip()
    except Exception:
        return None


def sincronizar_central_para_projeto(central, mb_projeto, dry_run=False):
    print("sincronizando central -> projeto...")
    for src_rel, dst_rel in MAPEAMENTO:
        src = os.path.join(central, src_rel)
        dst = os.path.join(mb_projeto, dst_rel)
        if not os.path.exists(src):
            print(f"  AVISO: {src} não existe na central, pulando")
            continue
        copiar(src, dst, dry_run)

    licoes_c = os.path.join(central, "licoes-megabrain.md")
    licoes_p = os.path.join(mb_projeto, "licoes-megabrain.md")
    if os.path.exists(licoes_c) and not os.path.exists(licoes_p):
        copiar(licoes_c, licoes_p, dry_run)
    elif os.path.exists(licoes_p):
        print("  licoes-megabrain.md já existe no projeto, não sobrescrevendo")

    if dry_run:
        print("dry-run concluído (teste pós-sync pulado)")
        return True

    faltando = []
    for _, dst_rel in MAPEAMENTO:
        dst = os.path.join(mb_projeto, dst_rel)
        if not os.path.exists(dst):
            faltando.append(dst_rel)
    if faltando:
        print(f"ERRO: após sync, faltam: {faltando}")
        return False

    print("sync concluído com sucesso")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--projeto", required=True)
    p.add_argument("--central", default=CENTRAL_DEFAULT)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--verificar-git", action="store_true",
                   help="consulta o remote do GitHub e avisa se há commit mais recente")
    p.add_argument("--remote", default="https://github.com/iriqspina/MEGAB-R-A-I-N.git",
                   help="URL do repositório remoto (default: GitHub público)")
    args = p.parse_args()

    central = os.path.abspath(args.central)
    if not os.path.isdir(central):
        print(f"ERRO: central não encontrada em {central}")
        print("Dica: defina MEGABRAIN_CENTRAL ou passe --central")
        sys.exit(1)

    mb_projeto = os.path.join(os.path.abspath(args.projeto), "MEGABRAIN")
    tem_mb = os.path.isdir(mb_projeto)

    v_central = ler_versao(central)
    v_projeto = ler_versao(mb_projeto) if tem_mb else None

    print(f"central: {v_central}")
    print(f"projeto: {v_projeto if tem_mb else 'sem MEGABRAIN/'}")

    if args.verificar_git:
        print(f"\nconsultando remote: {args.remote}")
        hash_remoto, erro = verificar_git(args.remote)
        if erro:
            print(f"Não foi possível consultar o git: {erro}")
            print("Verifique sua conexão ou se o repositório ainda existe.")
        else:
            print(f"último commit remoto: {hash_remoto[:12]}")
            # Se a central local for um repo git, compara
            hash_local = hash_commit_local(central)
            if hash_local:
                print(f"commit local da central: {hash_local[:12]}")
                if hash_local == hash_remoto:
                    print("central local está sincronizada com o remote.")
                else:
                    print("ATENÇÃO: existe versão mais recente no git.")
                    print("Sugestão: atualize a central local antes de sincronizar projetos.")
            else:
                print("central local não é um repositório git; não é possível comparar commits.")
        print("")
        # Continua o fluxo normal depois do aviso

    if args.force:
        ok = sincronizar_central_para_projeto(central, mb_projeto, args.dry_run)
        sys.exit(0 if ok else 1)

    if not tem_mb:
        print("projeto não tem MEGABRAIN/ — criando da central")
        ok = sincronizar_central_para_projeto(central, mb_projeto, args.dry_run)
        sys.exit(0 if ok else 1)

    relacao = comparar_versoes(v_central, v_projeto)

    if relacao == "igual":
        print("versões iguais — nada a fazer")
        sys.exit(0)

    if relacao == "central":
        print("central está mais atualizada que o projeto")
        ok = sincronizar_central_para_projeto(central, mb_projeto, args.dry_run)
        sys.exit(0 if ok else 1)

    if relacao == "projeto":
        print("ATENÇÃO: o projeto está mais atualizado que a central.")
        print("Não vou sobrescrever o projeto. Avalie se as mudanças devem subir para a central.")
        if not args.auto:
            resposta = input("Sincronizar projeto -> central? [s/N] ")
            if resposta.lower().strip() == "s":
                print("Para sync projeto -> central, use mb-sync-projeto-para-central.py (ou copie manualmente).")
        sys.exit(2)

    # indefinido
    print("ATENÇÃO: não foi possível determinar qual versão é mais recente.")
    print("Central:", v_central)
    print("Projeto:", v_projeto)
    if not args.auto:
        resposta = input("Sobrescrever projeto com a central? [s/N] ")
        if resposta.lower().strip() != "s":
            print("sync cancelado")
            sys.exit(0)
    ok = sincronizar_central_para_projeto(central, mb_projeto, args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

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
    python bin/mb-check-version.py --projeto "./meu-projeto" --offline

Opções:
    --projeto PATH     Pasta do projeto
    --central PATH     Pasta central do megabrain (default: detecta)
    --dry-run          Só reporta, não copia nada
    --force            Força sincronização mesmo se versões baterem
    --auto             Não pergunta; se projeto for mais novo, só reporta e sai com 2
    --verificar-git    Consulta o repositório remoto e avisa se há versão mais recente
    --offline          Não consulta rede; usa apenas a central local. Equivalente a
                       desligar --verificar-git e aceitar fallback local
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import mb_utils as u


def detectar_central():
    """Retorna a pasta central do megabrain via env var ou diretório do script."""
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return os.path.abspath(env)
    # Diretório pai de bin/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


CENTRAL_DEFAULT = detectar_central()
CENTRAL_DEFAULT_PATH = Path(CENTRAL_DEFAULT).resolve()

MAPEAMENTO = [
    ("MEGABRAIN.md", "MEGABRAIN.md"),
    ("skills/megabrain/SKILL.md", "skills/megabrain/SKILL.md"),
    ("referencias", "referencias"),
    ("VERSAO.txt", "VERSAO.txt"),
    ("bin", "bin"),
    ("dna", "dna"),  # pasta DNA (RELATORIO-DNA.html + dna.json + README.md) — desde 260814
    ("OFFLINE.md", "OFFLINE.md"),
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
    path = Path(pasta) / "VERSAO.txt"
    return u.read_first_non_empty_line(path)


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


def copiar(src, dst, dry_run=False, base=None):
    src_path = Path(src).resolve()
    dst_path = Path(dst).resolve()

    if base is not None:
        try:
            u.resolve_within(dst_path, Path(base).resolve())
        except ValueError as e:
            print(f"  ERRO (recusado): {e}")
            return False

    if dry_run:
        print(f"  [dry-run] copiaria {src_path} -> {dst_path}")
        return True

    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_dir():
            if dst_path.exists():
                if not u.safe_rmtree(dst_path, base=base):
                    return False
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        print(f"  copiado {src_path.name} -> {dst_path}")
        return True
    except OSError as e:
        print(f"  ERRO ao copiar {src_path} -> {dst_path}: {e}")
        return False


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
    central_path = Path(central).resolve()
    mb_projeto_path = Path(mb_projeto).resolve()
    falhas = []

    for src_rel, dst_rel in MAPEAMENTO:
        src = os.path.join(central, src_rel)
        dst = os.path.join(mb_projeto, dst_rel)
        if not os.path.exists(src):
            print(f"  AVISO: {src} não existe na central, pulando")
            continue
        if not copiar(src, dst, dry_run, base=mb_projeto_path):
            falhas.append(dst_rel)

    licoes_c = os.path.join(central, "licoes-megabrain.md")
    licoes_p = os.path.join(mb_projeto, "licoes-megabrain.md")
    if os.path.exists(licoes_c) and not os.path.exists(licoes_p):
        if not copiar(licoes_c, licoes_p, dry_run, base=mb_projeto_path):
            falhas.append("licoes-megabrain.md")
    elif os.path.exists(licoes_p):
        print("  licoes-megabrain.md já existe no projeto, não sobrescrevendo")

    if dry_run:
        print("dry-run concluído (teste pós-sync pulado)")
        return len(falhas) == 0

    for _, dst_rel in MAPEAMENTO:
        dst = os.path.join(mb_projeto, dst_rel)
        if not os.path.exists(dst):
            falhas.append(dst_rel)

    if falhas:
        print(f"ERRO: após sync, falhas/faltando: {falhas}")
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
    p.add_argument("--offline", action="store_true",
                   help="não consulta rede; usa apenas a central local")
    p.add_argument("--remote", default="https://github.com/iriqspina/MEGAB-R-A-I-N.git",
                   help="URL do repositório remoto (default: GitHub público)")
    args = p.parse_args()

    try:
        central = u.resolve_within(args.central, CENTRAL_DEFAULT_PATH)
    except ValueError as e:
        print(f"ERRO: central inválida: {e}")
        print("Dica: defina MEGABRAIN_CENTRAL ou passe --central")
        sys.exit(1)

    if not central.is_dir():
        print(f"ERRO: central não encontrada em {central}")
        print("Dica: defina MEGABRAIN_CENTRAL ou passe --central")
        sys.exit(1)

    projeto_abs = Path(args.projeto).resolve()
    # Só compara samefile se ambos existirem; senão, compara caminho absoluto.
    mesmo_caminho = projeto_abs == central
    try:
        mesmo_caminho = mesmo_caminho or (projeto_abs.exists() and central.exists() and os.path.samefile(projeto_abs, central))
    except OSError:
        pass
    if mesmo_caminho:
        print("ERRO: --projeto aponta para a própria central do megabrain.")
        print("Este script sincroniza a central -> DENTRO de um projeto, não na central.")
        print("Para atualizar a central, edite os arquivos diretamente e use mb-generate-template.py + git.")
        sys.exit(1)

    mb_projeto = os.path.join(projeto_abs, "MEGABRAIN")
    tem_mb = os.path.isdir(mb_projeto)

    v_central = ler_versao(central)
    v_projeto = ler_versao(mb_projeto) if tem_mb else None

    print(f"central: {v_central}")
    print(f"projeto: {v_projeto if tem_mb else 'sem MEGABRAIN/'}")

    if args.offline:
        print("modo offline ativado: não vou consultar rede.")
        print("Use MEGABRAIN/ do projeto diretamente ou a central local.")
        print("Para mais detalhes, leia MEGABRAIN/OFFLINE.md.\n")
    elif args.verificar_git:
        print(f"\nconsultando remote: {args.remote}")
        hash_remoto, erro = verificar_git(args.remote)
        if erro:
            print(f"Não foi possível consultar o git: {erro}")
            print("A cópia local em MEGABRAIN/ continua funcionando normalmente.")
            print("Veja MEGABRAIN/OFFLINE.md para uso sem internet.")
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

#!/usr/bin/env python3
"""
mb-generate-template.py — gera o pacote público (template) do megabrain
a partir da pasta central, removendo informação pessoal.

Uso:
    python bin/mb-generate-template.py [--central PATH] [--destino PATH]

O que faz:
1. Copia arquivos estruturais da central para o destino.
2. Sanitiza caminhos absolutos e nomes pessoais.
3. Não copia arquivos exclusivamente pessoais (memoria-pessoal, licoes).
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
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


CENTRAL_DEFAULT = detectar_central()
DESTINO_DEFAULT = os.path.join(CENTRAL_DEFAULT, "260810_github-export")

# Não copiar: exclusivamente pessoais ou gerados (match por substring no caminho relativo)
EXCLUIR = {
    "260810_memoria-pessoal.md",
    "licoes-megabrain.md",
    "260805_licoes-backup-pre-fix.md",
    "260810_backup-raiz-perfil",
    "260810_variantes",
    "260811_prompt-claude-handoff.txt",
    "260810_github-export",
    "_github-repo-local",
    "_to_delete",
    "alteracoes-pendentes",
    "referencias visuais",
    ".git",
    ".mb-aspirador",
    ".dna-backup",
    "__pycache__",
    "260810_VISAO-GERAL.md",
    "PIPELINE.md",
    "sincronizar-pipeline.cmd",
    "mb-sync-all.cmd",
    "260810_SKILL-divergente.bak.md",
    ".bak",
    "skills/conclusao-megabrain",
}

# Duplicatas legadas sem prefixo de data: match EXATO de nome de arquivo
EXCLUIR_NOME_EXATO = {
    "anti-slop.md",
    "context-engineering.md",
    "design-duplo-diamante.md",
    "evaluation-gates.md",
    "metaprompt-patterns.md",
    "prompt-portatil.md",
}

# Substituir caminhos absolutos por placeholders
SUBSTITUICOES = [
    (re.escape("<MEGABRAIN_ROOT>"), "<MEGABRAIN_ROOT>"),
    (re.escape("S:\\projetos multi i.a\\MEGA B R A I  N"), "<MEGABRAIN_ROOT>"),
    (re.escape("<PROJETOS_ROOT>/"), "<PROJETOS_ROOT>/"),
    (re.escape("S:\\projetos multi i.a\\"), "<PROJETOS_ROOT>\\"),
    (re.escape("<USER_HOME>"), "<USER_HOME>"),
    (re.escape("C:\\Users\\<USUARIO>"), "<USER_HOME>"),
    (re.escape("<AUTOR>"), "<AUTOR>"),
    (re.escape("<USUARIO>"), "<USUARIO>"),
    (re.escape("<USUARIO>raspina"), "<USUARIO>"),
    (re.escape("<USUARIO>"), "<USUARIO>"),
]


def sanitizar(texto):
    for padrao, substituicao in SUBSTITUICOES:
        texto = re.sub(padrao, lambda m: substituicao, texto, flags=re.IGNORECASE)
    return texto


def remover_secoes_pessoais(conteudo):
    """Remove seções que citam projetos pessoais do usuário."""
    # Remove seção 8 (roteamento de projetos pessoais) e 8b (skills derivadas)
    # Mantém a partir de "## 9 · Como esta pipeline evolui"
    padrao = re.compile(r"## 8 · Roteamento de projetos pessoais.*?(?=## 9 · Como esta pipeline evolui)", re.DOTALL)
    conteudo = re.sub(padrao, "## 8 · Roteamento de projetos pessoais → skill dedicada\n\n(Seção removida no template público: os projetos pessoais do usuário são substituídos por exemplos genéricos.)\n\n", conteudo)

    # Remove linha de Origem que cita projetos pessoais
    conteudo = re.sub(
        r"Origem: `PIPELINE\.md` v2 \(Rodada, djinn, megabrain, Financeiro da Silva\)\s*fundida com a v3 multi-agente \(Claude\+Kimi, gates de entrega, bastão\) em\s*260810\. Ver `260810_VISAO-GERAL\.md` para o que mudou nesta fusão e por quê\.",
        "Origem: fusão entre pipeline de projeto v2 e protocolo multi-agente v3.",
        conteudo,
        flags=re.DOTALL
    )
    return conteudo


def copiar_sanitizando(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if src.endswith(".md") or src.endswith(".txt") or src.endswith(".py") or src.endswith(".cmd"):
        with open(src, "r", encoding="utf-8") as f:
            conteudo = f.read()
        conteudo = sanitizar(conteudo)
        if src.endswith("MEGABRAIN.md") or src.endswith("260810_MEGABRAIN.md"):
            conteudo = remover_secoes_pessoais(conteudo)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(conteudo)
    else:
        shutil.copy2(src, dst)


def gerar_template(central, destino):
    if not os.path.isdir(central):
        print(f"ERRO: central não encontrada em {central}")
        return False

    # Limpa destino (recreate)
    if os.path.exists(destino):
        shutil.rmtree(destino)
    os.makedirs(destino)

    # Copia arquivos de topo
    for nome in os.listdir(central):
        if nome in EXCLUIR:
            continue
        src = os.path.join(central, nome)
        dst = os.path.join(destino, nome)
        if os.path.isfile(src):
            copiar_sanitizando(src, dst)
        elif os.path.isdir(src):
            # recursivo para referencias/, bin/, skills/
            for raiz, dirs, files in os.walk(src):
                rel = os.path.relpath(raiz, central)
                for f in files:
                    rel_f = os.path.join(rel, f).replace("\\", "/")
                    # pula .git e excluídos
                    if any(x in rel_f for x in EXCLUIR):
                        continue
                    if f in EXCLUIR_NOME_EXATO:
                        continue
                    src_f = os.path.join(raiz, f)
                    dst_f = os.path.join(destino, rel, f)
                    copiar_sanitizando(src_f, dst_f)

    # .gitignore padrão do pacote público
    gitignore_src = os.path.join(central, ".gitignore")
    if os.path.isfile(gitignore_src):
        copiar_sanitizando(gitignore_src, os.path.join(destino, ".gitignore"))

    # SKILL.md canônico também na raiz do destino (o repo público o espera lá)
    skill_src = os.path.join(central, "skills", "megabrain", "SKILL.md")
    if os.path.isfile(skill_src):
        copiar_sanitizando(skill_src, os.path.join(destino, "SKILL.md"))

    # VERSAO.txt público: só a versão atual, sem histórico com nomes de projeto
    versao_src = os.path.join(central, "VERSAO.txt")
    if os.path.isfile(versao_src):
        with open(versao_src, "r", encoding="utf-8") as f:
            primeira = f.readline().strip()
        primeira = sanitizar(primeira)
        with open(os.path.join(destino, "VERSAO.txt"), "w", encoding="utf-8") as f:
            f.write(primeira + "\n\nHistórico completo: ver repositório privado da pasta central.\n")

    print(f"template gerado em {destino}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--central", default=CENTRAL_DEFAULT)
    p.add_argument("--destino", default=DESTINO_DEFAULT)
    args = p.parse_args()
    ok = gerar_template(args.central, args.destino)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

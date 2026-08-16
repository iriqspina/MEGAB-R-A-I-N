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
from pathlib import Path

import mb_utils as u


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
    # Cópia derivada usada localmente por sincronização de projetos. O pacote
    # público já é a raiz portátil e não deve carregar esta árvore duplicada.
    "MEGABRAIN",
    "_to_delete",
    "alteracoes-pendentes",
    "referencias visuais",
    ".git",
    ".mb-aspirador",
    ".mb-backup",
    ".dna-backup",
    ".claude",
    "__pycache__",
    "260810_VISAO-GERAL.md",
    "PIPELINE.md",
    "sincronizar-pipeline.cmd",
    "mb-sync-all.cmd",
    "260810_SKILL-divergente.bak.md",
    ".bak",
    "skills/conclusao-megabrain",
}

# Estado operacional da central privada. Projetos clonados criam os próprios
# arquivos; publicar estes documentos vaza contexto, nomes e decisões locais.
EXCLUIR_TOPO = {
    "ESTADO.md",
    "HANDOFF.md",
    "DECISOES.md",
    "RELATORIO.html",
    "PAINEL-MEGABRAIN.html",
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

# Substituir caminhos absolutos e nomes pessoais por placeholders.
# Ordenado do termo mais longo para o mais curto evita que "<USUARIO>" corte
# "<USUARIO>" antes do match completo.
_SUBSTITUICOES_BRUTAS = [
    ("<MEGABRAIN_ROOT>", "<MEGABRAIN_ROOT>"),
    ("S:\\projetos multi i.a\\MEGA B R A I  N", "<MEGABRAIN_ROOT>"),
    ("<PROJETOS_ROOT>/", "<PROJETOS_ROOT>/"),
    ("S:\\projetos multi i.a\\", "<PROJETOS_ROOT>\\"),
    ("<USER_HOME>", "<USER_HOME>"),
    ("C:\\Users\\<USUARIO>", "<USER_HOME>"),
    ("<AUTOR>", "<AUTOR>"),
    ("<USUARIO>", "<USUARIO>"),
    ("<USUARIO>", "<USUARIO>"),
    ("<USUARIO>", "<USUARIO>"),
]

SUBSTITUICOES = sorted(
    [(re.escape(p), s) for p, s in _SUBSTITUICOES_BRUTAS],
    key=lambda item: len(item[0]),
    reverse=True,
)

EXTENSOES_TEXTO = {
    ".md",
    ".txt",
    ".py",
    ".cmd",
    ".html",
    ".json",
    ".yaml",
    ".yml",
    ".css",
    ".js",
}

PADROES_PRIVADOS = {
    "caminho de projetos local": re.compile(r"S:[\\/]projetos multi i\.a", re.IGNORECASE),
    "home local": re.compile(
        r"[A-Z]:[\\/]Users[\\/](?!<USER_HOME>)[^\\/\s<>]+", re.IGNORECASE
    ),
    # Construção em partes impede que o próprio gerador reescreva estes
    # detectores ao sanitizar sua cópia pública.
    "nome pessoal": re.compile(r"\b" + "Hen" + "rique" + r"\b", re.IGNORECASE),
    "apelido pessoal": re.compile(r"\b" + "Ir" + "iq" + r"\b", re.IGNORECASE),
}


def sanitizar(texto):
    for padrao, substituicao in SUBSTITUICOES:
        texto = re.sub(padrao, lambda m: substituicao, texto, flags=re.IGNORECASE)
    # Não alterar o username público "iriqspina" usado nas URLs do projeto.
    texto = re.sub(r"\bIriq\b", "<USUARIO>", texto, flags=re.IGNORECASE)
    return texto


def remover_secoes_pessoais(conteudo):
    """Remove seções que citam projetos pessoais do usuário."""
    # Remove seção 8 (roteamento de projetos pessoais) e 8b (skills derivadas)
    # Mantém a partir de "## 9 · Como esta pipeline evolui"
    padrao = re.compile(r"## 8 · Roteamento de projetos pessoais.*?(?=## 9 · Como esta pipeline evolui)", re.DOTALL)
    if padrao.search(conteudo):
        conteudo = padrao.sub(
            "## 8 · Roteamento de projetos pessoais → skill dedicada\n\n"
            "(Seção removida no template público: os projetos pessoais do usuário são substituídos por exemplos genéricos.)\n\n",
            conteudo,
        )

    # Remove linha de Origem que cita projetos pessoais
    padrao_origem = re.compile(
        r"Origem: `PIPELINE\.md` v2 \(Rodada, djinn, megabrain, Financeiro da Silva\)\s*"
        r"fundida com a v3 multi-agente \(Claude\+Kimi, gates de entrega, bastão\) em\s*"
        r"260810\. Ver `260810_VISAO-GERAL\.md` para o que mudou nesta fusão e por quê\.",
        re.DOTALL,
    )
    conteudo = padrao_origem.sub(
        "Origem: fusão entre pipeline de projeto v2 e protocolo multi-agente v3.",
        conteudo,
    )
    return conteudo


def copiar_sanitizando(src, dst):
    dst_path = Path(dst)
    if not u.ensure_parent_dir(dst_path):
        return False

    if Path(src).suffix.lower() in EXTENSOES_TEXTO:
        try:
            with open(src, "r", encoding="utf-8") as f:
                conteudo = f.read()
        except OSError as e:
            print(f"ERRO ao ler {src}: {e}")
            return False
        conteudo = sanitizar(conteudo)
        if src.endswith("MEGABRAIN.md") or src.endswith("260810_MEGABRAIN.md"):
            conteudo = remover_secoes_pessoais(conteudo)
        if not u.atomic_write_text(dst_path, conteudo):
            return False
    else:
        try:
            shutil.copy2(src, dst)
        except OSError as e:
            print(f"ERRO ao copiar {src} -> {dst}: {e}")
            return False
    return True


def validar_privacidade(destino_path):
    """Recusa o pacote se algum texto ainda carregar identificadores privados."""
    achados = []
    for arquivo in destino_path.rglob("*"):
        if not arquivo.is_file() or arquivo.suffix.lower() not in EXTENSOES_TEXTO:
            continue
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            achados.append(f"{arquivo.relative_to(destino_path)}: leitura falhou ({e})")
            continue
        for rotulo, padrao in PADROES_PRIVADOS.items():
            if padrao.search(conteudo):
                achados.append(f"{arquivo.relative_to(destino_path)}: {rotulo}")

    if achados:
        print("ERRO: validação de privacidade recusou o template:")
        for achado in achados:
            print(f"  - {achado}")
        return False
    return True


def gerar_template(central, destino):
    central_path = Path(central).resolve()
    destino_path = Path(destino).resolve()

    if not central_path.is_dir():
        print(f"ERRO: central não encontrada em {central_path}")
        return False

    # O destino deve ficar dentro da central (normalmente 260810_github-export).
    try:
        u.resolve_within(destino_path, central_path)
    except ValueError as e:
        print(f"ERRO: destino inválido: {e}")
        return False

    # Limpa destino (recreate) de forma segura.
    if destino_path.exists():
        if not u.safe_rmtree(destino_path, base=central_path):
            return False
    try:
        destino_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"ERRO: não foi possível criar {destino_path}: {e}")
        return False

    # Versões antigas do gerador podiam deixar uma cópia derivada MEGABRAIN/
    # dentro do export. Ela é obsoleta, pode carregar estado local e impede a
    # validação de privacidade. O destino já foi validado como filho da central.
    legado = destino_path / "MEGABRAIN"
    if legado.exists():
        try:
            if legado.is_dir():
                shutil.rmtree(legado)
            else:
                legado.unlink()
        except OSError as e:
            print(f"ERRO: não foi possível remover cópia legada {legado}: {e}")
            return False

    erros = False

    # Copia arquivos de topo
    for nome in os.listdir(central_path):
        if nome in EXCLUIR or nome in EXCLUIR_TOPO:
            continue
        src = os.path.join(central_path, nome)
        dst = destino_path / nome
        if os.path.isfile(src):
            if not copiar_sanitizando(src, str(dst)):
                erros = True
        elif os.path.isdir(src):
            # recursivo para referencias/, bin/, skills/
            for raiz, dirs, files in os.walk(src):
                rel = os.path.relpath(raiz, central_path)
                for f in files:
                    rel_f = os.path.join(rel, f).replace("\\", "/")
                    # pula .git e excluídos
                    if any(x in rel_f for x in EXCLUIR):
                        continue
                    if f in EXCLUIR_NOME_EXATO:
                        continue
                    src_f = os.path.join(raiz, f)
                    dst_f = destino_path / rel / f
                    if not copiar_sanitizando(src_f, str(dst_f)):
                        erros = True

    # .gitignore padrão do pacote público
    gitignore_src = central_path / ".gitignore"
    if gitignore_src.is_file():
        if not copiar_sanitizando(str(gitignore_src), str(destino_path / ".gitignore")):
            erros = True

    # SKILL.md canônico também na raiz do destino (o repo público o espera lá)
    skill_src = central_path / "skills" / "megabrain" / "SKILL.md"
    if skill_src.is_file():
        if not copiar_sanitizando(str(skill_src), str(destino_path / "SKILL.md")):
            erros = True

    # VERSAO.txt público: só a versão atual, sem histórico com nomes de projeto
    versao_src = central_path / "VERSAO.txt"
    if versao_src.is_file():
        primeira = u.read_first_non_empty_line(versao_src) or ""
        primeira = sanitizar(primeira)
        versao_dst = destino_path / "VERSAO.txt"
        if not u.atomic_write_text(
            versao_dst,
            primeira + "\n\nHistórico completo: ver repositório privado da pasta central.\n",
        ):
            erros = True

    if erros:
        print(f"template gerado em {destino_path} com ERROS parciais")
        return False

    if not validar_privacidade(destino_path):
        return False

    print(f"template gerado em {destino_path}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--central", default=CENTRAL_DEFAULT)
    p.add_argument("--destino", default=DESTINO_DEFAULT)
    args = p.parse_args()

    central_default_path = Path(CENTRAL_DEFAULT).resolve()
    try:
        central = u.resolve_within(args.central, central_default_path)
    except ValueError as e:
        print(f"ERRO: central inválida: {e}")
        sys.exit(1)

    # Destino default já está dentro da central; se o usuário passar outro,
    # gerar_template valida contenção.
    destino = Path(args.destino).resolve()

    ok = gerar_template(central, destino)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

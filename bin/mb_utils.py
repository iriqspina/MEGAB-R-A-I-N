#!/usr/bin/env python3
"""
mb_utils.py — utilitários compartilhados dos scripts do MEGABRAIN.

Concentra funções que aparecem em vários scripts e que, se duplicadas,
tendem a divergir e gerar bugs (path traversal, I/O não atômico,
escaping de HTML/JSON, leitura eficiente).

Regras deste módulo:
- Só depende da stdlib (portabilidade zero-dependência).
- Toda função de I/O retorna de forma controlada (nunca quebra com traceback).
- Toda função de segurança falha fechada (falha = recusa, não permissão).
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Console UTF-8 — Windows abre stdout em cp1252 e quebra em "→", "·", "✓".
# ---------------------------------------------------------------------------

def utf8_console() -> None:
    """Reconfigura stdout/stderr para UTF-8. Chamar no topo de todo script CLI.

    Sem isso, `print("→")` num console Windows padrão levanta
    UnicodeEncodeError (lição 260818). Falha silenciosa: se o stream não
    suportar reconfigure (pipe, testes), segue como está.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


# ---------------------------------------------------------------------------
# Path containment — evita path traversal em --dir, --projeto, --saida etc.
# ---------------------------------------------------------------------------

def resolve_within(caminho: str | os.PathLike[str], base: str | os.PathLike[str]) -> Path:
    """Resolve `caminho` e exige que ele fique dentro de `base`.

    Aceita caminhos relativos, absolutos e symlinks, desde que o destino
    canonizado esteja contido em `base`. Se não estiver, levanta ValueError.
    """
    base_resolvida = Path(base).resolve()
    alvo = Path(caminho).resolve()

    # Verifica contenção: alvo == base ou alvo está abaixo de base.
    if alvo != base_resolvida and base_resolvida not in alvo.parents:
        raise ValueError(f"caminho fora da área permitida: {alvo} (base: {base_resolvida})")

    return alvo


def ensure_parent_dir(path: Path) -> bool:
    """Garante que o diretório pai de `path` exista. Retorna False se falhar."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        print(f"ERRO: não foi possível criar diretório {path.parent}: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# I/O segura e atômica
# ---------------------------------------------------------------------------

def safe_read_text(path: Path, encoding: str = "utf-8", fallback: str = "latin-1") -> str | None:
    """Lê texto de `path`, tentando `encoding` e depois `fallback`.

    Retorna None em caso de erro de I/O (arquivo inexistente, permissão, etc.)
    em vez de propagar exceção.
    """
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding=fallback)
        except OSError:
            return None
    except OSError:
        return None


def safe_read_lines(path: Path, encoding: str = "utf-8") -> list[str] | None:
    """Lê linhas de `path`. Retorna None em erro de I/O."""
    try:
        return path.read_text(encoding=encoding).splitlines()
    except OSError:
        return None


def read_first_non_empty_line(path: Path, encoding: str = "utf-8") -> str | None:
    """Lê apenas a primeira linha não vazia de `path` — evita carregar arquivo inteiro."""
    try:
        with path.open("r", encoding=encoding) as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    return linha
        return None
    except OSError:
        return None


def atomic_write_text(path: Path, conteudo: str, encoding: str = "utf-8") -> bool:
    """Escreve `conteudo` em `path` de forma atômica (temp + os.replace).

    Em Windows, os.replace não sobrescreve se o destino estiver aberto,
    mas é atômico o suficiente para evitar leitura de arquivo parcial.
    Retorna True em caso de sucesso, False em caso de erro.
    """
    if not ensure_parent_dir(path):
        return False

    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
                f.write(conteudo)
            os.replace(tmp_name, path)
            return True
        except Exception:
            # Limpa o temporário se algo deu errado antes do replace.
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except OSError as e:
        print(f"ERRO: falha ao escrever {path}: {e}", file=sys.stderr)
        return False


def safe_rmtree(path: Path, base: Path | None = None) -> bool:
    """Remove árvore de diretórios apenas se estiver contida em `base`.

    Se `base` for None, não faz verificação de segurança (use com cuidado).
    Retorna True se removeu, False se recusou ou falhou.
    """
    try:
        alvo = path.resolve()
    except OSError as e:
        print(f"ERRO: não foi possível resolver {path}: {e}", file=sys.stderr)
        return False

    if base is not None:
        try:
            resolve_within(alvo, base)
        except ValueError as e:
            print(f"ERRO: recusado — {e}", file=sys.stderr)
            return False

    try:
        import shutil
        shutil.rmtree(alvo)
        return True
    except OSError as e:
        print(f"ERRO: falha ao remover {alvo}: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# File locking leve (sem dependências externas)
# ---------------------------------------------------------------------------

def acquire_lock(lock_path: Path, timeout: float = 10.0, retry: float = 0.05) -> bool:
    """Tenta criar um lockfile exclusivo usando O_CREAT | O_EXCL.

    Funciona em Windows, Linux e macOS sem bibliotecas externas.
    Retorna True se conseguiu a trava, False se timeout ou erro.
    """
    import time

    if timeout < 0:
        timeout = 0.0
    deadline = time.monotonic() + timeout

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                info = f"pid={os.getpid()}\ntime={dt.datetime.now(dt.timezone.utc).isoformat()}\n"
                os.write(fd, info.encode("utf-8"))
            finally:
                os.close(fd)
            return True
        except FileExistsError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(retry)
        except OSError as e:
            print(f"ERRO: não foi possível criar lock {lock_path}: {e}", file=sys.stderr)
            return False


def release_lock(lock_path: Path) -> bool:
    """Remove lockfile. Ignora se não existir."""
    try:
        lock_path.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        print(f"AVISO: não foi possível remover lock {lock_path}: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# HTML / JSON escaping
# ---------------------------------------------------------------------------

def escape_href(href: str) -> str:
    """Escapa atributo href para evitar XSS via markdown links."""
    return html.escape(href, quote=True).replace("\n", "").replace("\r", "")


def html_json_safe(json_str: str) -> str:
    """Torna JSON embutido em <script> seguro contra </script> e <!-- -->."""
    return json_str.replace("</", "<\\/").replace("<!--", "<\\!--")


def safe_json_dumps(obj, **kwargs) -> str:
    """json.dumps com escaping seguro para uso dentro de <script>."""
    return html_json_safe(json.dumps(obj, **kwargs))


# ---------------------------------------------------------------------------
# Marcadores de sincronização
# ---------------------------------------------------------------------------

MARK_START = "<!-- MEGABRAIN:AUTO-SYNC:START -->"
MARK_END = "<!-- MEGABRAIN:AUTO-SYNC:END -->"

# ---------------------------------------------------------------------------
# Identidade / usuário
# ---------------------------------------------------------------------------

IDENTIDADE_DEFAULT = "260810_memoria-pessoal.md"

# ---------------------------------------------------------------------------
# v6.3 (260822): raiz da central sem arquivo solto. Cada arquivo canônico
# mora numa pasta. achar() mantém a API comum para a central e para arquivos
# de estado que pertencem à raiz de um projeto.
# ---------------------------------------------------------------------------
# Nomes lógicos apontam para os locais canônicos da central v7.5.
PASTAS_NUMERADAS = {
    "nucleo": "memoria/nucleo", "estado": "memoria/estado", "identidade": "memoria/identidade",
    "cerebro": "memoria/cerebro", "relatorios": "00_painel", "scripts": "01_acoes",
    "dist": "motor/dist", "docs": "03_docs", "alteracoes-pendentes": "memoria/pendencias",
    "_arquivo": "90_arquivo", "_to_delete": "99_to_delete",
    # v7.1 (260824) — etapa 2 da reorg: a MÁQUINA mora em motor/. A raiz só
    # mostra o que é do humano. bin/ é a exceção (hook externo aponta pra ele).
    "skills": "motor/skills", "referencias": "motor/referencias",
    "modelos": "motor/modelos", "dna": "motor/dna", "tests": "motor/tests",
    "plugin-megabrain": "motor/plugin-megabrain",
    "plugin-megabrain-claude": "motor/plugin-megabrain-claude",
    "gerenteneuron": "motor/gerenteneuron",
}
NOMES_ANTIGOS = {v: k for k, v in PASTAS_NUMERADAS.items()}

# Pastas de máquina ficam em motor/ na central. O fallback plano permanece
# somente para restaurações cheias e backups anteriores à cópia magra.
PASTAS_MAQUINA = ("skills", "referencias", "modelos", "dna", "tests", "dist",
                  "plugin-megabrain", "plugin-megabrain-claude", "gerenteneuron")
MOTOR = "motor"

def pasta(raiz, nome: str) -> Path:
    """Pasta pelo nome lógico.

    A central tem um único layout canônico. Pasta plana só ganha quando já
    existe, para ler restauração cheia ou backup anterior à cópia magra.
    """
    base = Path(raiz)
    num = base / PASTAS_NUMERADAS.get(nome, nome)
    if num.is_dir():
        return num
    plana = base / nome
    if plana.is_dir():
        return plana
    return num


PASTAS_RAIZ = {
    "MEGABRAIN.md": "nucleo", "VERSAO.txt": "nucleo", "README.md": "nucleo",
    "OFFLINE.md": "nucleo", "licoes-megabrain.md": "nucleo",
    "ESTADO.md": "estado", "HANDOFF.md": "estado", "DECISOES.md": "estado",
    "META.md": "estado", "CHECKLIST-ABERTURA.md": "estado",
    "ALINHAMENTO-AGENTES.md": "estado", "PROGRESSO.json": "estado",
    "260810_memoria-pessoal.md": "identidade",
    "RELATORIO.html": "relatorios", "RELATORIO-VIVO.html": "relatorios",
    "RELATORIO-AGENTES.html": "relatorios", "PAINEL-MEGABRAIN.html": "relatorios",
}


def achar(raiz, nome: str) -> Path:
    """Caminho canônico na central ou arquivo direto na raiz de um projeto.

    Nome que começa por pasta de máquina resolve o primeiro pedaço por
    pasta(). O plano continua legível para restauração cheia; se os dois
    existirem, o caminho canônico da central ganha.

    Nome CANÔNICO de PASTAS_RAIZ solto na raiz não sobrepõe o da pasta
    lógica (ex.: licoes-megabrain.md órfão não sombreia memoria/nucleo/).
    """
    base = Path(raiz)
    partes = str(nome).replace("\\", "/").split("/", 1)
    if partes[0] in PASTAS_MAQUINA:
        d = pasta(base, partes[0])
        return (d / partes[1]) if len(partes) == 2 else d
    plano = base / nome
    logica = PASTAS_RAIZ.get(nome)
    if logica is not None:
        d = pasta(base, logica)
        if d.is_dir():
            return d / nome
        return plano
    return plano


def e_central(raiz) -> bool:
    """Central válida = VERSAO.txt + MEGABRAIN.md (em qualquer layout) + bin/."""
    base = Path(raiz)
    return (achar(base, "VERSAO.txt").is_file() and achar(base, "MEGABRAIN.md").is_file()
            and (base / "bin").is_dir())


def extract_usuario(texto: str) -> str | None:
    """Extrai o valor da linha `USUARIO:` do arquivo de identidade.

    Aceita `USUARIO: Nome` ou `USUARIO:` seguido de conteúdo na mesma linha.
    Ignora espaços, comentários HTML e linhas vazias. Retorna None se não
    encontrar.
    """
    for linha in texto.splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith(("<!--", "#")):
            continue
        if limpa.upper().startswith("USUARIO:"):
            valor = limpa.split(":", 1)[1].strip()
            return " ".join(valor.split()) or None
    return None


def detectar_usuario(identidade_path: Path | None = None) -> str:
    """Tenta ler o nome do usuário no arquivo de identidade padrão.

    Se `identidade_path` for None, procura `260810_memoria-pessoal.md` no
    diretório atual. Retorna "<USUARIO>" se não conseguir detectar.
    """
    if identidade_path is None:
        identidade_path = achar(Path("."), IDENTIDADE_DEFAULT)
    texto = safe_read_text(identidade_path)
    if texto is None:
        return "<USUARIO>"
    return extract_usuario(texto) or "<USUARIO>"


# ---------------------------------------------------------------------------
# Markdown helpers leves
# ---------------------------------------------------------------------------

def link_replacer(match) -> str:
    """Substituição segura para [texto](url)."""
    texto = html.escape(match.group(1))
    href = escape_href(match.group(2))
    return f'<a href="{href}">{texto}</a>'


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def die(mensagem: str, code: int = 1) -> None:
    """Imprime mensagem de erro e encerra o processo."""
    print(f"ERRO: {mensagem}", file=sys.stderr)
    sys.exit(code)


def parse_csv_extensoes(texto: str) -> set[str]:
    """Converte string de extensões separadas por vírgula em conjunto limpo."""
    return {e.strip().lstrip(".").lower() for e in texto.split(",") if e.strip()}


# ---------------------------------------------------------------------------
# Iteração segura de diretórios
# ---------------------------------------------------------------------------

def walk_files(
    raiz: Path,
    exts: set[str] | None = None,
    ignorar: set[str] | None = None,
) -> Iterable[Path]:
    """Yields arquivos dentro de `raiz`, opcionalmente filtrando extensões.

    `ignorar` é um conjunto de nomes de diretório a pular.
    """
    if ignorar is None:
        ignorar = {".git", ".venv", "node_modules", "__pycache__"}

    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in ignorar]
        for nome in filenames:
            caminho = Path(dirpath) / nome
            if exts is None or caminho.suffix.lstrip(".").lower() in exts:
                yield caminho

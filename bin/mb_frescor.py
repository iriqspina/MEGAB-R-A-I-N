#!/usr/bin/env python3
"""Fingerprint determinístico das fontes do estado e do relatório.

O relatório é rastreado, portanto nunca pode conter o hash do commit que o
contém. O gate usa o conteúdo das fontes em três visões explícitas:

- ``worktree``: arquivos no disco, para o Gate 0 durante a edição;
- ``staged``: objetos no índice do Git, para o pré-commit;
- ``head``: objetos do HEAD, para o pós-commit.

HEAD, horário, caminho absoluto e estado dirty ficam fora do fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import mb_utils as u


ALGORITMO = "sha256-path-lf-v1"
MODOS = {"worktree", "staged", "head"}
FONTES_ESTADO = (
    "VERSAO.txt",
    "ESTADO.md",
    "HANDOFF.md",
    "META.md",
    "PROGRESSO.json",
    "DECISOES.md",
)
ID_HTML = "mb-frescor"
PADRAO_HTML = re.compile(
    rb'<script\s+id=["\']mb-frescor["\']\s+type=["\']application/json["\']>(.*?)</script>',
    re.DOTALL,
)


def fontes_relativas(central: Path) -> list[str]:
    """Resolve a lista canônica uma vez e devolve caminhos portáveis."""
    caminhos = []
    for nome in FONTES_ESTADO:
        p = u.achar(central, nome)
        try:
            relativo = p.relative_to(central).as_posix()
        except ValueError:
            relativo = nome.replace("\\", "/")
        caminhos.append(relativo)
    return caminhos


def _normalizar(conteudo: bytes) -> bytes:
    """Normaliza só quebras de linha; espaços e conteúdo continuam significativos."""
    return conteudo.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _ler_git(central: Path, relativo: str, modo: str) -> bytes | None:
    spec = f":{relativo}" if modo == "staged" else f"HEAD:{relativo}"
    try:
        r = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(central), "show", spec],
            capture_output=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def ler_visao(central: Path, relativo: str, modo: str) -> bytes | None:
    if modo not in MODOS:
        raise ValueError(f"modo de frescor inválido: {modo}")
    if modo == "worktree":
        try:
            return (central / relativo).read_bytes()
        except OSError:
            return None
    return _ler_git(central, relativo, modo)


def calcular(central: Path, modo: str = "worktree",
             fontes: list[str] | None = None) -> dict:
    """Calcula o fingerprint com enquadramento de caminho e tamanho."""
    fontes = list(fontes or fontes_relativas(central))
    itens: list[tuple[str, bytes]] = []
    faltantes = []
    for relativo in sorted(dict.fromkeys(fontes)):
        conteudo = ler_visao(central, relativo, modo)
        if conteudo is None:
            faltantes.append(relativo)
        else:
            itens.append((relativo, _normalizar(conteudo)))

    valor = None
    if not faltantes:
        digest = hashlib.sha256()
        digest.update(b"MEGABRAIN-FRESCOR\0")
        for relativo, conteudo in itens:
            digest.update(relativo.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(len(conteudo)).encode("ascii"))
            digest.update(b"\0")
            digest.update(conteudo)
            digest.update(b"\0")
        valor = digest.hexdigest()

    return {
        "algoritmo": ALGORITMO,
        "valor": valor,
        "fontes": fontes,
        "faltantes": faltantes,
        "visao": modo,
    }


def dados_html(proveniencia: dict) -> dict:
    fp = (proveniencia or {}).get("fingerprint") or {}
    return {
        "algoritmo": fp.get("algoritmo"),
        "valor": fp.get("valor"),
        "fontes": list(proveniencia.get("fontes") or fp.get("fontes") or []),
    }


def bloco_html(proveniencia: dict) -> str:
    payload = json.dumps(dados_html(proveniencia), ensure_ascii=False,
                         separators=(",", ":")).replace("</", "<\\/")
    return f'<script id="{ID_HTML}" type="application/json">{payload}</script>'


def extrair_html(conteudo: bytes) -> tuple[dict | None, str | None]:
    m = PADRAO_HTML.search(conteudo)
    if not m:
        return None, "metadado mb-frescor ausente"
    try:
        dados = json.loads(m.group(1).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        return None, f"metadado mb-frescor ilegível: {e}"
    if not isinstance(dados, dict):
        return None, "metadado mb-frescor não é objeto JSON"
    return dados, None

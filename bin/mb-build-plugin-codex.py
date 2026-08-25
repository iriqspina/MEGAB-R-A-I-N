#!/usr/bin/env python3
"""Monta e confere o plugin Codex a partir de fontes rastreadas da central.

As cinco skills compartilhadas vêm de ``motor/skills``. O manifesto e a skill
``registrar-licao`` são específicos do Codex e vivem em
``motor/plugin-megabrain-codex``. Nenhum arquivo preexistente no destino é
tratado como fonte.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

PLUGIN_FONTE = "plugin-megabrain-codex"
SKILLS_CANONICAS = (
    "megabrain",
    "ingerir",
    "grelhar",
    "traycer",
    "leigolanguage",
)
SKILLS_PLUGIN = (*SKILLS_CANONICAS, "registrar-licao")


def _manifesto_bytes(caminho: Path) -> bytes:
    """JSON determinístico; CRLF preserva os bytes do plugin Codex instalado."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    texto = json.dumps(dados, ensure_ascii=True, indent=2) + "\n"
    return texto.replace("\n", "\r\n").encode("utf-8")


def arquivos_esperados(central: Path) -> dict[str, bytes]:
    """Mapa completo ``caminho relativo → bytes`` do pacote reproduzível."""
    fonte_plugin = u.pasta(central, PLUGIN_FONTE)
    manifesto = fonte_plugin / ".codex-plugin" / "plugin.json"
    registrar = fonte_plugin / "skills" / "registrar-licao" / "SKILL.md"
    faltantes = [p for p in (manifesto, registrar) if not p.is_file()]
    if faltantes:
        raise FileNotFoundError("fonte Codex ausente: " + ", ".join(map(str, faltantes)))

    arquivos = {
        ".codex-plugin/plugin.json": _manifesto_bytes(manifesto),
        "skills/registrar-licao/SKILL.md": registrar.read_bytes(),
    }
    for nome in SKILLS_CANONICAS:
        pasta = u.achar(central, f"skills/{nome}")
        if not (pasta / "SKILL.md").is_file():
            raise FileNotFoundError(f"fonte ausente: {pasta / 'SKILL.md'}")
        for fonte in sorted(pasta.rglob("*")):
            if fonte.is_file() and "__pycache__" not in fonte.parts:
                rel = (Path("skills") / nome / fonte.relative_to(pasta)).as_posix()
                arquivos[rel] = fonte.read_bytes()
    return dict(sorted(arquivos.items()))


def _arquivos_atuais(destino: Path) -> dict[str, bytes]:
    if not destino.is_dir():
        return {}
    return {
        p.relative_to(destino).as_posix(): p.read_bytes()
        for p in sorted(destino.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def conferir_drift(central: Path, destino: Path) -> list[str]:
    try:
        esperados = arquivos_esperados(central)
    except (OSError, ValueError) as e:
        return [str(e)]
    atuais = _arquivos_atuais(destino)
    faltam = sorted(set(esperados) - set(atuais))
    sobram = sorted(set(atuais) - set(esperados))
    divergem = sorted(
        rel for rel in set(esperados) & set(atuais)
        if esperados[rel] != atuais[rel]
    )
    return ([f"AUSENTE: {rel}" for rel in faltam] +
            [f"EXTRA: {rel}" for rel in sobram] +
            [f"DIVERGE: {rel}" for rel in divergem])


def _frontmatter_ok(texto: str) -> bool:
    m = re.match(r"---\n(.*?)\n---\n", texto, re.DOTALL)
    return bool(m and re.search(r"^name:\s*\S+", m.group(1), re.MULTILINE)
                and re.search(r"^description:\s*\S+", m.group(1), re.MULTILINE))


def validar(destino: Path) -> list[str]:
    erros = []
    try:
        manifesto = json.loads(
            (destino / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        if manifesto.get("name") != "megabrain" or manifesto.get("skills") != "./skills/":
            erros.append(".codex-plugin/plugin.json: name/skills inválidos")
    except (OSError, ValueError) as e:
        erros.append(f".codex-plugin/plugin.json: {e}")
    for nome in SKILLS_PLUGIN:
        caminho = destino / "skills" / nome / "SKILL.md"
        try:
            texto = caminho.read_text(encoding="utf-8")
        except OSError as e:
            erros.append(f"skills/{nome}/SKILL.md: {e}")
            continue
        if not _frontmatter_ok(texto):
            erros.append(f"skills/{nome}/SKILL.md: frontmatter inválido")
    return erros


def montar(central: Path, destino: Path) -> None:
    """Reconstrói o destino inteiro; não preserva fonte implícita ou extra."""
    esperados = arquivos_esperados(central)  # valida tudo antes de apagar
    if destino.exists() and not u.safe_rmtree(destino, base=destino.parent):
        raise OSError(f"não foi possível limpar destino: {destino}")
    destino.mkdir(parents=True, exist_ok=True)
    for rel, conteudo in esperados.items():
        caminho = destino / rel
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)
    erros = validar(destino)
    if erros:
        raise ValueError("plugin Codex inválido: " + "; ".join(erros))


def instalar_skill_direta(central: Path, home: Path) -> Path:
    fonte = u.achar(central, "skills/megabrain")
    destino = home / ".codex" / "skills" / "megabrain"
    shutil.copytree(fonte, destino, dirs_exist_ok=True)
    return destino


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--central", default=str(Path(__file__).resolve().parent.parent))
    p.add_argument("--destino", default=str(Path.home() / "plugins" / "megabrain"))
    p.add_argument("--check", action="store_true")
    p.add_argument("--instalar-direta", action="store_true",
                   help="sincroniza também ~/.codex/skills/megabrain")
    args = p.parse_args()

    central = Path(args.central).resolve()
    destino = Path(args.destino).resolve()
    if args.check:
        divergencias = conferir_drift(central, destino)
        if divergencias:
            print("plugin Codex DIVERGE:")
            for item in divergencias:
                print(f"  - {item}")
            return 1
        print(f"plugin Codex em dia: {len(SKILLS_PLUGIN)} skills · "
              f"{len(arquivos_esperados(central))} arquivos")
        return 0

    try:
        montar(central, destino)
    except (OSError, ValueError) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"plugin Codex montado: {destino}")
    if args.instalar_direta:
        print(f"skill direta instalada: {instalar_skill_direta(central, Path.home())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

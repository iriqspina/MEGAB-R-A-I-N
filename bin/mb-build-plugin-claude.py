#!/usr/bin/env python3
"""
mb-build-plugin-claude.py — regenera e empacota o plugin Cowork/Claude do
megabrain (plugin-megabrain-claude/) a partir das fontes da central. v6.1 (260821)

Por que existe: a skill `megabrain` do plugin é cópia da skill central e a
`registrar-licao` é cópia da versão Kimi — cópia editada à mão drifta (lição
recorrente do projeto: "registrado != disco"). Aqui as edições são código.

O que faz:
  1. skills/megabrain/SKILL.md   ← <central>/skills/megabrain/SKILL.md
     (remove os gatilhos legados "/metaprotocolo" e "metaclaude" da description)
  2. skills/registrar-licao/SKILL.md ← <central>/plugin-megabrain/skills/registrar-licao/SKILL.md
     (/megabrain:licao → /registrar-licao; ~/.kimi-code/SYSTEM.md → genérico;
      aviso de que o hook pode não rodar)
  3. valida: plugin.json, hooks.json, frontmatter das skills, `node --check` e
     smoke test do hook (saída JSON com hookSpecificOutput).
  4. zipa em <central>/YYMMDD_megabrain-v<versão>.plugin (conteúdo na raiz do zip,
     .claude-plugin/ incluso). O .plugin fica fora do pacote público.

Uso:
    python bin/mb-build-plugin-claude.py            # regenera + valida + zipa
    python bin/mb-build-plugin-claude.py --check    # só confere drift (exit 1)
    python bin/mb-build-plugin-claude.py --sem-zip
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import mb_utils as u

u.utf8_console()

PLUGIN_DIR = "plugin-megabrain-claude"
HOOK = "scripts/260821_session-start.js"


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def derivar_skill_megabrain(fonte: str) -> str:
    """Mesmo texto da skill central; só a description perde os gatilhos legados."""
    linhas = fonte.split("\n")
    for i, linha in enumerate(linhas[:6]):
        if linha.startswith("description:"):
            nova = linha.replace("digitar /megabrain ou /metaprotocolo,", "digitar /megabrain,")
            nova = nova.replace('escrever "megabrain" ou "metaclaude",', 'escrever "megabrain",')
            linhas[i] = nova
            break
    return "\n".join(linhas)


def derivar_skill_licao(fonte: str) -> str:
    t = fonte.replace("Use quando o usuário digitar /megabrain:licao, disser",
                      "Use quando o usuário digitar /registrar-licao, disser")
    t = t.replace("isso vai pro `SYSTEM.md` do plugin ou pro `~/.kimi-code/SYSTEM.md`, não aqui",
                  "isso vai pro `SYSTEM.md` do plugin ou do agente, não aqui")
    t = t.replace(
        "Grava 3 linhas num arquivo de lições. O hook `SessionStart` do plugin encontra esse "
        "arquivo na pasta de trabalho e injeta o conteúdo automaticamente — o usuário nunca "
        "precisa lembrar de abrir.",
        "Grava 3 linhas num arquivo de lições. O hook `SessionStart` do plugin (quando o "
        "ambiente roda hooks — Claude Code/Desktop; no Cowork cloud, verificado em 260821, "
        "ele NÃO roda) encontra esse arquivo na pasta de trabalho e injeta o conteúdo "
        "automaticamente. Sem hook, leia o arquivo no Gate 0 — o caminho está abaixo.")
    return t


def frontmatter_ok(texto: str) -> bool:
    m = re.match(r"---\n(.*?)\n---\n", texto, re.DOTALL)
    if not m:
        return False
    campos = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.MULTILINE))
    return "name" in campos and "description" in campos


def validar(plugin: Path) -> list[str]:
    erros = []
    for rel in (".claude-plugin/plugin.json", "hooks/hooks.json"):
        try:
            json.loads((plugin / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            erros.append(f"{rel}: {e}")
    for rel in ("skills/megabrain/SKILL.md", "skills/registrar-licao/SKILL.md", "skills/ingerir/SKILL.md"):
        t = u.safe_read_text(plugin / rel) or ""
        if not frontmatter_ok(t):
            erros.append(f"{rel}: frontmatter sem name/description")
    hook = plugin / HOOK
    if not hook.is_file():
        erros.append(f"{HOOK}: ausente")
    elif shutil.which("node"):
        r = subprocess.run(["node", "--check", str(hook)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            erros.append(f"node --check: {r.stderr.strip()[:200]}")
        else:
            # smoke test: roda o hook numa pasta temporária com uma lição
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp, "licoes-megabrain.md").write_text("## 000000 — teste\nGATILHO: x\n", encoding="utf-8")
                env = dict(os.environ, CLAUDE_PROJECT_DIR=tmp)
                r = subprocess.run(["node", str(hook)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=15)
                try:
                    saida = json.loads(r.stdout)
                    ctx = saida["hookSpecificOutput"]["additionalContext"]
                    if "megabrain — ativo" not in ctx or "000000 — teste" not in ctx:
                        erros.append("hook rodou mas não injetou núcleo + lição")
                except (ValueError, KeyError):
                    erros.append(f"hook não devolveu JSON hookSpecificOutput: {r.stdout[:120]!r}")
    else:
        print("aviso: node não encontrado — hook não testado")
    return erros


def versao_plugin(plugin: Path) -> str:
    try:
        return json.loads((plugin / ".claude-plugin/plugin.json").read_text(encoding="utf-8")).get("version", "0")
    except (OSError, ValueError):
        return "0"


def zipar(plugin: Path, destino: Path) -> None:
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(plugin.rglob("*")):
            if arq.is_file() and "__pycache__" not in arq.parts:
                z.write(arq, arq.relative_to(plugin).as_posix())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="só confere drift contra as fontes")
    p.add_argument("--sem-zip", action="store_true")
    args = p.parse_args()

    c = central()
    plugin = c / PLUGIN_DIR
    fontes = {
        "skills/megabrain/SKILL.md": (c / "skills/megabrain/SKILL.md", derivar_skill_megabrain),
        "skills/registrar-licao/SKILL.md": (c / "plugin-megabrain/skills/registrar-licao/SKILL.md", derivar_skill_licao),
        "skills/ingerir/SKILL.md": (c / "skills/ingerir/SKILL.md", lambda t: t),  # v6.2
    }
    drift = []
    for rel, (fonte, derivar) in fontes.items():
        texto = u.safe_read_text(fonte)
        if texto is None:
            print(f"ERRO: fonte ausente: {fonte}")
            return 1
        esperado = derivar(texto)
        atual = u.safe_read_text(plugin / rel)
        if atual != esperado:
            drift.append(rel)
            if not args.check:
                if not u.atomic_write_text(plugin / rel, esperado):
                    return 1
                print(f"regenerado: {rel}")
    if args.check:
        if drift:
            print("DRIFT no plugin-megabrain-claude (rode sem --check pra regenerar):")
            for d in drift:
                print(f"  ✗ {d}")
            return 1
        print("plugin-megabrain-claude: skills iguais às fontes.")
        return 0

    erros = validar(plugin)
    if erros:
        print("ERRO na validação do plugin:")
        for e in erros:
            print(f"  ✗ {e}")
        return 1
    print("validação: plugin.json, hooks.json, frontmatter, node --check, smoke test do hook — ok")

    if not args.sem_zip:
        nome = f"{dt.datetime.now():%y%m%d}_megabrain-v{versao_plugin(plugin)}.plugin"
        destino = u.pasta(c, "dist") / nome   # v6.2: instaláveis em dist/ (v6.4: 06_dist/)
        destino.parent.mkdir(exist_ok=True)
        zipar(plugin, destino)
        print(f"pacote: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

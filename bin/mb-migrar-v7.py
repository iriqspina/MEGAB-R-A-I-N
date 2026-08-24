#!/usr/bin/env python3
"""mb-migrar-v7.py — migração de layout v6.7 → v7.0 (Etapa 1, 260824).

Reorganiza a central no layout humano/máquina aprovado (board 15·B do doc
260824_megabrain-do-zero.html):

  VOCÊ:    00_painel  01_acoes  02_entrada  03_docs  04_visuais  90  99
  MEMÓRIA: memoria/{nucleo, estado, identidade, cerebro, pendencias}
  GIT:     _github/{export, repo-local}
  MÁQUINA (ficam na raiz nesta etapa): bin dna skills referencias modelos
           tests plugin-megabrain plugin-megabrain-claude gerenteneuron dist

Segurança: --dry-run lista tudo sem tocar; execução real copia cada arquivo
editado para 90_arquivo/migracao-v7-260824/ antes de mexer e grava manifest.
Nada é apagado — só movido e editado.
"""
from __future__ import annotations
import argparse, json, os, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None

MOVES = [
    ("00_nucleo",              "memoria/nucleo"),
    ("01_estado",              "memoria/estado"),
    ("02_identidade",          "memoria/identidade"),
    ("03_cerebro",             "memoria/cerebro"),
    ("08_alteracoes-pendentes","memoria/pendencias"),
    ("04_relatorios",          "00_painel"),
    ("05_scripts",             "01_acoes"),
    ("07_docs",                "03_docs"),
    ("09_visuais",             "04_visuais"),
    ("06_dist",                "dist"),
    ("260810_github-export",   "_github/export"),
    ("_github-repo-local",     "_github/repo-local"),
    ("relatorio-megabrain",    "90_arquivo/relatorio-megabrain"),
    ("modelos/LEIAME-copia-de-projeto.txt", "modelos/LEIAME-megabrain-do-projeto.txt"),
]

CMD_RENAMES = [  # dentro de 01_acoes, depois do move
    ("260810_publicar-github.cmd",      "260824_publicar-e-fotografar.cmd"),
    ("260821_push-github.cmd",          "260824_enviar-pro-github.cmd"),
    ("sincronizar-pipeline.cmd",        "260824_sincronizar-projetos.cmd"),
    ("novo-projeto.cmd",                "260824_novo-projeto.cmd"),
    ("260810_instalar-identidade.cmd",  "260824_instalar-identidade.cmd"),
    ("260810_sincronizar-identidade.cmd","260824_sincronizar-identidade.cmd"),
    ("260819_refresh-plugin-kimi.cmd",  "260824_refresh-plugin-kimi.cmd"),
    ("260810_abrir-kimi-visual.cmd",    "260824_abrir-kimi-visual.cmd"),
]

# ordem não importa: aplicação em duas fases (placeholder) evita re-substituição
TOKENS = [
    ("260810_github-export",   "_github/export"),
    ("_github-repo-local",     "_github/repo-local"),
    ("00_nucleo",              "memoria/nucleo"),
    ("01_estado",              "memoria/estado"),
    ("02_identidade",          "memoria/identidade"),
    ("03_cerebro",             "memoria/cerebro"),
    ("08_alteracoes-pendentes","memoria/pendencias"),
    ("04_relatorios",          "00_painel"),
    ("05_scripts",             "01_acoes"),
    ("07_docs",                "03_docs"),
    ("09_visuais",             "04_visuais"),
    ("06_dist",                "dist"),
    ("LEIAME-copia-de-projeto","LEIAME-megabrain-do-projeto"),
    ("260810_publicar-github.cmd",  "260824_publicar-e-fotografar.cmd"),
    ("260821_push-github.cmd",      "260824_enviar-pro-github.cmd"),
    ("sincronizar-pipeline.cmd",    "260824_sincronizar-projetos.cmd"),
    ("novo-projeto.cmd",            "260824_novo-projeto.cmd"),
    ("260810_instalar-identidade.cmd",  "260824_instalar-identidade.cmd"),
    ("260810_sincronizar-identidade.cmd","260824_sincronizar-identidade.cmd"),
    ("260819_refresh-plugin-kimi.cmd",  "260824_refresh-plugin-kimi.cmd"),
    ("260810_abrir-kimi-visual.cmd",    "260824_abrir-kimi-visual.cmd"),
]

UTILS_PATCH_OLD = "NOMES_ANTIGOS = {v: k for k, v in PASTAS_NUMERADAS.items()}"
UTILS_PATCH_NEW = """NOMES_ANTIGOS = {v: k for k, v in PASTAS_NUMERADAS.items()}

# v7.0 (260824): layout humano/maquina. Fallback pro layout v6.4 (numerado
# antigo) - centrais e copias antigas continuam legiveis sem sincronizar.
PASTAS_V64 = {
    "nucleo": "00_nucleo", "estado": "01_estado", "identidade": "02_identidade",
    "cerebro": "03_cerebro", "relatorios": "04_relatorios", "scripts": "05_scripts",
    "dist": "06_dist", "docs": "07_docs", "alteracoes-pendentes": "08_alteracoes-pendentes",
    "_arquivo": "90_arquivo", "_to_delete": "99_to_delete",
}"""
PASTA_PATCH_OLD = """    if num.is_dir():
        return num
    plana = base / nome"""
PASTA_PATCH_NEW = """    if num.is_dir():
        return num
    antiga = base / PASTAS_V64.get(nome, nome)
    if antiga.is_dir():
        return antiga
    plana = base / nome"""

ENTRADA_LEIAME = """# 02_entrada — jogue fontes aqui

Qualquer coisa que deva virar conhecimento do megabrain: PDF, artigo salvo,
print, briefing, e-mail exportado, link num .md.

O que acontece depois: o comando /ingerir (ou a manutenção do cérebro) lê o
que está aqui, move o original para memoria/cerebro/raw/ (a prova, intocada)
e destila em páginas de memoria/cerebro/wiki/ (a leitura). Nada é apagado.

Regra da casa: arquivo novo ganha data no nome (YYMMDD_nome.ext).
"""


def apply_tokens(text: str, pairs, sep: str) -> str:
    # duas fases com placeholders — nenhuma saída vira entrada de outra troca
    for i, (old, _new) in enumerate(pairs):
        text = text.replace(old, f"\x00MB{i}\x00")
    for i, (_old, new) in enumerate(pairs):
        if sep == "\\":
            new = new.replace("/", "\\")
        text = text.replace(f"\x00MB{i}\x00", new)
    return text


def collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    def add_glob(base: str, patterns):
        b = root / base
        if not b.exists():
            return
        for pat in patterns:
            files.extend(p for p in b.rglob(pat) if p.is_file())
    add_glob("bin", ["*.py", "*.cmd"])
    add_glob("01_acoes", ["*.cmd"])
    add_glob("tests", ["*.py"])
    add_glob("plugin-megabrain", ["*.py", "*.js", "*.mjs", "*.md", "*.json", "*.txt"])
    add_glob("plugin-megabrain-claude", ["*.py", "*.js", "*.mjs", "*.md", "*.json", "*.txt"])
    add_glob("skills", ["*.md"])
    add_glob("referencias", ["*.md"])
    add_glob("modelos", ["*.md", "*.txt", "*.html"])
    add_glob("memoria/nucleo", ["*.md"])
    add_glob("memoria/estado", ["*.md"])
    add_glob("memoria/pendencias", ["*.md"])
    add_glob("03_docs", ["*.md"])
    add_glob("dna", ["README.md"])
    add_glob("dna/usuario", ["README.md"])
    add_glob(".claude", ["*.md"])
    for extra in (root / ".gitignore",):
        if extra.is_file():
            files.append(extra)
    skip_parts = {"__pycache__", "node_modules", ".venv", ".git"}
    return [f for f in files if not (set(f.parts) & skip_parts) and f.name != "mb-migrar-v7.py"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    if not (root / "bin").is_dir():
        print(f"ERRO: raiz invalida: {root}"); return 2
    dry = args.dry_run
    log = {"moves": [], "renames": [], "edits": [], "avisos": []}
    backup = root / "90_arquivo" / "migracao-v7-260824"

    # 1. pastas novas
    for d in ("memoria", "_github", "02_entrada"):
        p = root / d
        if not p.exists():
            print(f"[mkdir] {d}")
            if not dry:
                p.mkdir(parents=True)
    leiame = root / "02_entrada" / "LEIAME.md"
    if not leiame.exists():
        print("[novo ] 02_entrada/LEIAME.md")
        if not dry:
            leiame.write_text(ENTRADA_LEIAME, encoding="utf-8")

    # 2. moves
    for src_s, dst_s in MOVES:
        src, dst = root / src_s, root / dst_s
        if not src.exists():
            log["avisos"].append(f"fonte ausente (pulado): {src_s}"); continue
        if dst.exists():
            log["avisos"].append(f"destino ja existe (pulado): {dst_s}"); continue
        print(f"[move ] {src_s}  ->  {dst_s}")
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        log["moves"].append([src_s, dst_s])

    # 3. renomear cmds
    acoes = root / "01_acoes"
    for old, new in CMD_RENAMES:
        src, dst = acoes / old, acoes / new
        if src.exists() and not dst.exists():
            print(f"[nome ] 01_acoes/{old} -> {new}")
            if not dry:
                src.rename(dst)
            log["renames"].append([old, new])

    # 4. edits de texto
    for f in collect_files(root):
        try:
            with open(f, "r", encoding="utf-8", newline="") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            try:
                with open(f, "r", encoding="latin-1", newline="") as fh:
                    text = fh.read()
            except OSError:
                log["avisos"].append(f"ilegivel: {f}"); continue
        sep = "\\" if f.suffix.lower() == ".cmd" else "/"
        new_text = apply_tokens(text, TOKENS, sep)
        if f.name == "mb_utils.py":
            if UTILS_PATCH_OLD in new_text and "PASTAS_V64" not in new_text:
                new_text = new_text.replace(UTILS_PATCH_OLD, UTILS_PATCH_NEW)
                new_text = new_text.replace(PASTA_PATCH_OLD, PASTA_PATCH_NEW)
        if new_text != text:
            rel = f.relative_to(root)
            print(f"[edit ] {rel}")
            if not dry:
                bkp = backup / rel
                bkp.parent.mkdir(parents=True, exist_ok=True)
                if not bkp.exists():
                    shutil.copy2(str(f), str(bkp))
                with open(f, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new_text)
            log["edits"].append(str(rel))

    print(f"\nresumo: {len(log['moves'])} moves, {len(log['renames'])} renomes, "
          f"{len(log['edits'])} arquivos editados, {len(log['avisos'])} avisos")
    for a in log["avisos"]:
        print("  aviso:", a)
    if not dry:
        backup.mkdir(parents=True, exist_ok=True)
        (backup / "manifest.json").write_text(
            json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"backup + manifest: {backup.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

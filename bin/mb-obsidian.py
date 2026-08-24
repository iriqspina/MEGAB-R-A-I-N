#!/usr/bin/env python3
"""mb-obsidian.py — aponta o Obsidian pro cérebro do megabrain (v7.1, 260824).

DECISÃO 260824: você instala o Obsidian; o megabrain aponta o vault pra
`memoria/cerebro`. O Obsidian passa a ser a JANELA do cérebro — links entre
páginas, grafo, busca — sem virar dono de nada: quem escreve ali continua
sendo o `/ingerir`, e o formato continua sendo markdown puro.

Por que só `memoria/cerebro` e não a `memoria` inteira: cérebro é conhecimento
de conteúdo (o que você sabe). `estado/`, `nucleo/` e `pendencias/` são
operação do protocolo — quem lê é a IA, e abrir tudo junto vira ruído no grafo.

O que este script faz:
  --preparar (padrão)  cria memoria/cerebro/.obsidian/ com uma config inicial
                       (tema escuro, links relativos, anexos em raw/) SEM
                       sobrescrever nada que já exista, e escreve o leia-me.
  --registrar          registra o vault na config do Obsidian
                       (%APPDATA%/obsidian/obsidian.json), com backup. Precisa
                       do app FECHADO — ele reescreve esse arquivo ao sair.
  --abrir              registra (se preciso) e abre o vault no Obsidian.

LIÇÃO 260824: `obsidian://open?path=...` só abre vault JÁ REGISTRADO. Com a
pasta desconhecida o app responde "Vault not found" — foi o que aconteceu na
primeira tentativa. Por isso --abrir passou a registrar antes de chamar a URI.

A pasta `.obsidian/` é config LOCAL: já está no .gitignore e nunca sobe.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_utils as u  # noqa: E402

u.utf8_console()

CONFIG = {
    "app.json": {
        "attachmentFolderPath": "raw",
        "newLinkFormat": "relative",
        "useMarkdownLinks": False,
        "alwaysUpdateLinks": True,
        "showUnsupportedFiles": True,
        "readableLineLength": True,
        "strictLineBreaks": False,
        "promptDelete": True,
    },
    "appearance.json": {
        "theme": "obsidian",
        "baseFontSize": 15,
        "showViewHeader": True,
    },
    "core-plugins.json": {
        "file-explorer": True, "global-search": True, "switcher": True,
        "graph": True, "backlink": True, "outgoing-link": True,
        "tag-pane": True, "page-preview": True, "templates": True,
        "note-composer": True, "command-palette": True, "editor-status": True,
        "bookmarks": True, "outline": True, "word-count": True,
        "file-recovery": True, "random-note": False, "daily-notes": False,
        "canvas": True, "properties": True,
    },
    "hotkeys.json": {},
}

LEIAME = """# Cérebro no Obsidian — como usar (260824)

O Obsidian é só uma JANELA pra esta pasta. Ele não muda nada de lugar e não
inventa formato: os arquivos continuam markdown puro, e continuam sendo
escritos pelo `/ingerir`.

## Abrir

Dois cliques em `01_acoes\\260824_abrir-cerebro-obsidian.cmd`.
Na primeira vez o Obsidian pergunta qual pasta é o vault: escolha
**Open folder as vault** e aponte pra esta pasta (o caminho já está na sua
área de transferência).

## O que você ganha

- **Links entre páginas**: escreva `[[nome-do-arquivo]]` e vira link.
- **Grafo**: o mapa de como os assuntos se ligam (ícone de grafo na lateral).
- **Busca de verdade** em tudo que a IA já destilou.
- **Backlinks**: em qualquer página, quem aponta pra ela.

## O que NÃO fazer

- Não renomeie `raw/`, `wiki/` e `pessoas/` — o `/ingerir` e o índice contam
  com esses nomes.
- Não apague a página que o índice cita: quem arquiva é
  `bin\\mb-manutencao-cerebro.py --arquivar`, que move pra `90_arquivo\\` em
  vez de apagar.
- Não instale plugin que reescreve arquivo sozinho (formatadores automáticos):
  eles brigam com o que a IA escreve.

## Onde fica a configuração

`.obsidian/` aqui dentro. É local, está no `.gitignore` e nunca sobe pro
GitHub — inclusive porque guarda o layout da SUA tela.
"""


def config_obsidian() -> Path | None:
    """obsidian.json — a lista de vaults conhecidos pelo app."""
    import os
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "obsidian" / "obsidian.json"
        return None
    caseiro = Path.home()
    for cand in (caseiro / ".config" / "obsidian" / "obsidian.json",
                 caseiro / "Library" / "Application Support" / "obsidian" / "obsidian.json"):
        if cand.parent.is_dir():
            return cand
    return None


def obsidian_rodando() -> bool:
    import os
    try:
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/fi", "imagename eq Obsidian.exe", "/nh"],
                               capture_output=True, text=True, timeout=15, check=False)
            return "Obsidian.exe" in (r.stdout or "")
        r = subprocess.run(["pgrep", "-f", "[Oo]bsidian"], capture_output=True,
                           text=True, timeout=15, check=False)
        return bool((r.stdout or "").strip())
    except (OSError, subprocess.SubprocessError):
        return False


def registrar(central: Path, forcar: bool = False) -> int:
    """Põe o vault do cérebro na lista de vaults do Obsidian.

    Sem isso, `obsidian://open?path=` responde "Vault not found" — a URI só
    abre vault que o app já conhece.
    """
    import datetime as _dt
    import secrets
    v = vault(central)
    if not v.is_dir():
        print(f"ERRO: não achei o cérebro em {v}")
        return 1
    cfg = config_obsidian()
    if cfg is None or not cfg.parent.is_dir():
        print("Obsidian ainda não rodou nesta máquina (sem obsidian.json).")
        print("Abra o app uma vez e rode de novo — ou use Open folder as vault:")
        print(f"  {v}")
        return 1
    if obsidian_rodando() and not forcar:
        print("O Obsidian está ABERTO. Ele reescreve a config ao sair e apagaria")
        print("o registro. Feche o app e rode de novo (ou use --forcar).")
        return 1

    alvo = str(v.resolve())
    dados = {"vaults": {}}
    if cfg.is_file():
        try:
            dados = json.loads(cfg.read_text(encoding="utf-8")) or {"vaults": {}}
        except (OSError, ValueError):
            print(f"AVISO: {cfg.name} ilegível — vou escrever um novo.")
            dados = {"vaults": {}}
        backup = central / ".mb-backup" / f"obsidian-json-{_dt.datetime.now():%y%m%d-%H%M%S}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        try:
            backup.write_text(cfg.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  backup da config: {backup}")
        except OSError:
            pass

    vaults = dados.setdefault("vaults", {})
    ja = [k for k, val in vaults.items() if str(val.get("path", "")).rstrip("\\/") == alvo.rstrip("\\/")]
    agora_ms = int(_dt.datetime.now().timestamp() * 1000)
    for val in vaults.values():
        val["open"] = False
    if ja:
        vaults[ja[0]].update({"ts": agora_ms, "open": True})
        print(f"  vault já estava registrado ({ja[0]}) — marquei como o que abre.")
    else:
        novo = secrets.token_hex(8)
        vaults[novo] = {"path": alvo, "ts": agora_ms, "open": True}
        print(f"  vault registrado: {novo}")
    cfg.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    outros = [val.get("path") for k, val in vaults.items() if val.get("path") != alvo]
    print(f"  config: {cfg}")
    if outros:
        print("  outros vaults na lista (intocados, só não abrem sozinhos): "
              + " · ".join(str(o) for o in outros))
    return 0


def vault(central: Path) -> Path:
    return u.pasta(central, "cerebro")


def preparar(central: Path) -> int:
    v = vault(central)
    if not v.is_dir():
        print(f"ERRO: não achei o cérebro em {v}")
        return 1
    cfg = v / ".obsidian"
    cfg.mkdir(exist_ok=True)
    criados, mantidos = [], []
    for nome, conteudo in CONFIG.items():
        alvo = cfg / nome
        if alvo.exists():
            mantidos.append(nome)
            continue
        u.atomic_write_text(alvo, json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n")
        criados.append(nome)
    leiame = v / "260824_obsidian-leiame.md"
    if not leiame.exists():
        u.atomic_write_text(leiame, LEIAME)
        criados.append(leiame.name)
    print(f"vault do Obsidian: {v}")
    if criados:
        print("  criado(s): " + ", ".join(criados))
    if mantidos:
        print("  já existia(m), não toquei: " + ", ".join(mantidos))
    print("  no Obsidian: Open folder as vault → escolha a pasta acima")
    return 0


def vault_registrado(v: Path) -> bool:
    cfg = config_obsidian()
    if cfg is None or not cfg.is_file():
        return False
    try:
        dados = json.loads(cfg.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return False
    alvo = str(v.resolve()).rstrip("\\/")
    return any(str(val.get("path", "")).rstrip("\\/") == alvo
               for val in (dados.get("vaults") or {}).values())


def abrir(central: Path) -> int:
    v = vault(central)
    if not v.is_dir():
        print(f"ERRO: não achei o cérebro em {v}")
        return 1
    preparar(central)
    # a URI só abre vault CONHECIDO: registrar antes evita o "Vault not found"
    if not vault_registrado(v):
        registrar(central)
    caminho = str(v.resolve())
    try:  # deixa o caminho pronto pra colar, caso o Obsidian peça a pasta
        subprocess.run("clip", input=caminho, text=True, shell=True, check=False)
    except OSError:
        pass
    uri = "obsidian://open?path=" + quote(caminho, safe="")
    print(f"abrindo: {uri}")
    try:
        import os
        os.startfile(uri)  # type: ignore[attr-defined]  # Windows
    except (AttributeError, OSError):
        import webbrowser
        if not webbrowser.open(uri):
            print("Não consegui abrir o Obsidian. Abra ele e use "
                  f"'Open folder as vault' apontando pra:\n  {caminho}")
            return 1
    return 0


def conferir(central: Path) -> int:
    """Todo [[wikilink]] do vault aponta pra arquivo que existe?

    Link quebrado é nó fantasma no grafo: aparece como bolinha vazia e some
    quando alguém limpa. Vale rodar depois de cada /ingerir.
    """
    v = vault(central)
    if not v.is_dir():
        print(f"ERRO: não achei o cérebro em {v}")
        return 1
    arquivos = {f.stem: f for f in v.rglob("*.md") if ".obsidian" not in f.parts}
    quebrados, total = [], 0
    for f in sorted(arquivos.values()):
        texto = u.safe_read_text(f) or ""
        # [[x]] dentro de crase é EXEMPLO, não link — o Obsidian também não
        # desenha aresta pra código. Tirar antes de contar.
        texto = re.sub(r"```.*?```", " ", texto, flags=re.S)
        texto = re.sub(r"`[^`\n]*`", " ", texto)
        for m in re.finditer(r"\[\[([^\]|#]+)", texto):
            alvo = m.group(1).strip()
            if alvo.upper().startswith("YYMMDD"):
                continue  # placeholder dos MODELOs, de propósito
            total += 1
            if alvo not in arquivos:
                quebrados.append((str(f.relative_to(v)), alvo))
    print(f"vault: {v}")
    print(f"  {len(arquivos)} arquivo(s) · {total} wikilink(s) reais")
    if not quebrados:
        print("  todos os links resolvem — o grafo não tem nó fantasma.")
        return 0
    print(f"  {len(quebrados)} link(s) QUEBRADO(s):")
    for onde, alvo in quebrados:
        print(f"    {onde} → [[{alvo}]]")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--abrir", action="store_true")
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--registrar", action="store_true")
    ap.add_argument("--conferir", action="store_true",
                    help="checa se todo [[wikilink]] do vault aponta pra arquivo existente")
    ap.add_argument("--forcar", action="store_true",
                    help="registra mesmo com o Obsidian aberto (ele pode desfazer ao sair)")
    args = ap.parse_args()
    central = Path(args.dir).resolve() if args.dir else Path(__file__).resolve().parent.parent
    if args.conferir:
        return conferir(central)
    if args.registrar:
        preparar(central)
        return registrar(central, forcar=args.forcar)
    return abrir(central) if args.abrir else preparar(central)


if __name__ == "__main__":
    raise SystemExit(main())

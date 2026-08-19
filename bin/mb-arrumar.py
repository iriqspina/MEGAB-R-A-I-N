#!/usr/bin/env python3
"""
mb-arrumar.py — poe a pasta do megabrain em ordem sem quebrar quem depende dela.

Faz cinco coisas, nesta ordem:
  1. mostra o plano (dry-run e o padrao - nada e tocado sem --aplicar);
  2. so remove duplicata se o hash for identico ao do arquivo que fica;
  3. faz backup .zip da raiz antes de qualquer escrita;
  4. move arquivo e conserta as referencias que apontavam pro lugar antigo;
  5. varre o resultado atras de referencia orfa e diz o que sobrou.

Uso:
  python bin/mb-arrumar.py --raiz .              # so mostra o plano
  python bin/mb-arrumar.py --raiz . --aplicar    # executa, com backup antes
  python bin/mb-arrumar.py --raiz . --verificar  # so procura referencia orfa
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

import mb_utils as u

u.utf8_console()

TEXTO = {".md", ".txt", ".py", ".cmd", ".json", ".yaml", ".yml", ".html"}


def sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# --------------------------------------------------------------------- plano
# tipo, origem, destino, motivo
PLANO: list[tuple[str, str, str, str]] = [
    ("dedup", "SKILL.md", "skills/megabrain/SKILL.md",
     "duplicata byte a byte; os scripts do pacote elegem skills/megabrain como fonte"),
    ("dedup", "260810_MEGABRAIN.md", "MEGABRAIN.md",
     "duplicata byte a byte; prefixo de data nao serve a arquivo canonico"),
    ("remover", "LEIAME.md", "",
     "so aponta pro README.md e se justifica com uma premissa falsa"),
    ("remover", "bin/260810_mb-sync.py", "",
     "versao antiga do mb-sync: sem campo USUARIO, release sem --agente, --force sem protecao"),
    ("mover", "LEIAME.txt", "modelos/LEIAME-copia-de-projeto.txt",
     "e marcador da copia dentro do projeto; na raiz da fonte manda nao editar a fonte"),
    ("mover", "requirements.txt", "docs/dependencias-sugeridas.txt",
     "nenhuma das dependencias e importada por bin/; e sugestao, nao requisito"),
    ("mover", "260810_abrir-kimi-visual.cmd", "scripts/abrir-kimi-visual.cmd", "executavel sai da raiz"),
    ("mover", "260810_instalar-identidade.cmd", "scripts/instalar-identidade.cmd", "executavel sai da raiz"),
    ("mover", "260810_publicar-github.cmd", "scripts/publicar-github.cmd", "executavel sai da raiz"),
    ("mover", "260810_sincronizar-identidade.cmd", "scripts/sincronizar-identidade.cmd", "executavel sai da raiz"),
    ("mover", "novo-projeto.cmd", "scripts/novo-projeto.cmd", "executavel sai da raiz"),
]

# arquivo alvo, trecho antigo, trecho novo  (aplicado so se o trecho existir)
PATCHES: list[tuple[str, str, str]] = [
    ("scripts/instalar-identidade.cmd", '%~dp0260810_memoria-pessoal.md', '%~dp0..\\260810_memoria-pessoal.md'),
    ("scripts/instalar-identidade.cmd", '%~dp0bin\\', '%~dp0..\\bin\\'),
    ("scripts/publicar-github.cmd", '%~dp0260810_github-export', '%~dp0..\\260810_github-export'),
    ("scripts/publicar-github.cmd", '%~dp0_github-repo-local', '%~dp0..\\_github-repo-local'),
    ("scripts/publicar-github.cmd",
     'git commit -m "megabrain v3.1: pacote sanitizado (gates, multi-agente, sync de identidade sem dado pessoal); remove memoria-global.md do HEAD"',
     'for /f "usebackq delims=" %%V in ("%CLONE%\\VERSAO.txt") do (set "MBVER=%%V" & goto :temversao)\n:temversao\ngit commit -m "megabrain: %MBVER%"'),
    ("scripts/novo-projeto.cmd",
     'set "ARQ=260810_MEGABRAIN.md VERSAO.txt licoes-megabrain.md LEIAME.txt"',
     'set "ARQ=MEGABRAIN.md VERSAO.txt licoes-megabrain.md"'),
    ("scripts/novo-projeto.cmd",
     'robocopy "%FONTE%\\skills\\megabrain"',
     'robocopy "%FONTE%\\modelos" "%DEST%\\MEGABRAIN" LEIAME-copia-de-projeto.txt /R:1 /W:1 >nul\nrobocopy "%FONTE%\\skills\\megabrain"'),
    ("scripts/novo-projeto.cmd", 'MEGABRAIN\\260810_MEGABRAIN.md', 'MEGABRAIN\\MEGABRAIN.md'),
    ("scripts/novo-projeto.cmd", 'MEGABRAIN v3 - projeto novo', 'MEGABRAIN - projeto novo'),
    ("README.md", '- `SKILL.md` — o protocolo:', '- `skills/megabrain/SKILL.md` — o protocolo:'),
    ("bin/mb-check-version.py", '    ("260810_MEGABRAIN.md", "260810_MEGABRAIN.md"),\n', ''),
    ("bin/mb-sync-projeto-para-central.py",
     '    ("MEGABRAIN/260810_MEGABRAIN.md", "260810_MEGABRAIN.md"),\n', ''),
    ("skills/megabrain/SKILL.md",
     '`MEGABRAIN.md`, `260810_MEGABRAIN.md`, `referencias/`',
     '`MEGABRAIN.md`, `referencias/`'),
    ("MEGABRAIN.md", '| `260810_MEGABRAIN.md` (este) |', '| `MEGABRAIN.md` (este) |'),
    ("bin/mb-generate-template.py",
     'if src.endswith("MEGABRAIN.md") or src.endswith("260810_MEGABRAIN.md"):',
     'if src.endswith("MEGABRAIN.md"):'),
]

# arquivos que FALAM dos nomes antigos por oficio - nao sao referencia quebrada
IGNORAR_NA_VARREDURA = ("bin/mb-arrumar.py", "docs/", "AUDITORIA-", "PAINEL-MEGABRAIN.html")

# nomes que nao podem sobrar referenciados depois da arrumacao
ORFAOS = ["260810_MEGABRAIN.md", "260810_mb-sync.py", "LEIAME.md", "requirements.txt"]


def cabecalho_dependencias() -> str:
    return (
        "DEPENDENCIAS SUGERIDAS (nao obrigatorias)\n"
        "=========================================\n\n"
        "Nenhum script de bin/ importa qualquer uma destas bibliotecas. O nucleo\n"
        "roda em stdlib pura e continua rodando sem instalar nada. A lista abaixo\n"
        "e um roteiro de evolucao, nao um requisito de execucao - por isso deixou\n"
        "de se chamar requirements.txt.\n\n"
    )


def executar(raiz: Path, aplicar: bool) -> int:
    print(f"raiz: {raiz}\nmodo: {'APLICAR' if aplicar else 'dry-run (nada sera tocado)'}\n")
    acoes: list[tuple[str, str, str, str]] = []

    for tipo, origem, destino, motivo in PLANO:
        o = raiz / origem
        if not o.exists():
            print(f"  --    {origem}: nao existe, pulando")
            continue
        if tipo == "dedup":
            d = raiz / destino
            if not d.exists():
                print(f"  !!    {origem}: o par {destino} nao existe — nao removo nada")
                continue
            if sha(o) != sha(d):
                print(f"  !!    {origem}: hash DIFERENTE de {destino} — divergiram, resolva na mao")
                continue
            print(f"  del   {origem}\n        idêntico a {destino} · {motivo}")
            acoes.append(("remover", origem, "", motivo))
        elif tipo == "remover":
            print(f"  del   {origem}\n        {motivo}")
            acoes.append(("remover", origem, "", motivo))
        else:
            print(f"  mv    {origem} → {destino}\n        {motivo}")
            acoes.append(("mover", origem, destino, motivo))

    if not aplicar:
        print(f"\n{len(acoes)} ação(ões) no plano. Rode de novo com --aplicar para executar.")
        return 0
    if not acoes:
        print("\nnada a mover ou remover — só conferindo referências.")
        return patches_e_verificacao(raiz)

    carimbo = dt.datetime.now().strftime("%y%m%d-%H%M")
    backup = raiz / f".mb-backup/arrumar-{carimbo}.zip"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
        for f in raiz.rglob("*"):
            if f.is_file() and ".mb-backup" not in f.parts and ".git" not in f.parts:
                z.write(f, f.relative_to(raiz))
    print(f"\nbackup: {backup.relative_to(raiz)}")

    for tipo, origem, destino, _ in acoes:
        o = raiz / origem
        if tipo == "remover":
            o.unlink()
        else:
            d = raiz / destino
            d.parent.mkdir(parents=True, exist_ok=True)
            if destino.endswith("dependencias-sugeridas.txt"):
                d.write_text(cabecalho_dependencias() + o.read_text(encoding="utf-8"), encoding="utf-8")
                o.unlink()
            else:
                shutil.move(str(o), str(d))
    print(f"{len(acoes)} ação(ões) executada(s).")
    return patches_e_verificacao(raiz)


def patches_e_verificacao(raiz: Path) -> int:
    print("\nreferências:")
    for alvo, antes, depois in PATCHES:
        f = raiz / alvo
        if not f.exists():
            print(f"  --    {alvo}: nao existe")
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        if depois in txt:
            print(f"  ja    {alvo}: já ajustado")
        elif antes in txt:
            f.write_text(txt.replace(antes, depois), encoding="utf-8")
            print(f"  ok    {alvo}: {antes[:48]}…")
        else:
            print(f"  --    {alvo}: trecho ausente")

    return verificar(raiz)


def verificar(raiz: Path) -> int:
    print("\nvarredura de referência órfã:")
    achou = 0
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or f.suffix not in TEXTO:
            continue
        rel = f.relative_to(raiz).as_posix()
        if ".git" in f.parts or ".mb-backup" in f.parts:
            continue
        if any(marca in rel for marca in IGNORAR_NA_VARREDURA):
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for orfao in ORFAOS:
            if orfao in txt and not (raiz / orfao).exists():
                for n, linha in enumerate(txt.splitlines(), 1):
                    if orfao in linha:
                        print(f"  {f.relative_to(raiz)}:{n} → {orfao}")
                        achou += 1
    if achou:
        print(f"\n{achou} referência(s) apontando pra arquivo que nao existe mais. Conserte antes de commitar.")
        return 1
    print("  nenhuma. arvore consistente.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--verificar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if not (raiz / "VERSAO.txt").exists():
        print(f"{raiz} nao parece ser a raiz do megabrain (sem VERSAO.txt).")
        return 1
    if args.verificar:
        return verificar(raiz)
    return executar(raiz, args.aplicar)


if __name__ == "__main__":
    sys.exit(main())

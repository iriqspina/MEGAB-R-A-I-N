#!/usr/bin/env python3
"""
mb-magra.py — converte a cópia MEGABRAIN/ de um projeto para o formato MAGRO.

O QUE MUDA (260825, decisão 260825aa)
-------------------------------------
Antes: cada projeto carregava uma fotocópia do motor — 157 a 182 MB em 19
cópias. Medido por hash: **173 arquivos idênticos em 5 ou mais cópias** e
apenas **10 realmente únicos** no conjunto todo, dos quais a maioria é derivada
(`RELATORIO.html`) ou é resíduo de nome antigo.

Depois: a pasta guarda **um ponteiro** e um LEIAME. A máquina vive num lugar só.

    MEGABRAIN/
      .mb-origem.json   ← onde está a central, de qual commit, quando
      LEIAME.md         ← o que aconteceu e como voltar atrás
      90_arquivo/magra-260825/   ← TUDO que saiu, nada apagado

Por que isso é conserto e não economia de disco: enquanto existiam dois
layouts vivos (central aninhada × cópia plana), `mb_utils` precisava resolver
os dois — 63 linhas de resolvedor, 100 chamadas em 24 de 34 scripts — e **dois
dos bugs de 260825 nasceram nessa costura**. Sem cópia gorda, não há costura.

SEGURANÇA
---------
- `--aplicar` é obrigatório pra escrever. Sem ele, é dry-run.
- Nada é apagado: tudo vai pra `90_arquivo/magra-260825/` dentro da própria
  cópia, com LEIAME dizendo de onde veio.
- Arquivo que NÃO existe na central e não é derivado conhecido é **preservado
  na raiz da cópia** e listado no relatório. Na dúvida, fica.
- `dna/usuario/` encontrado numa cópia é tratado como VAZAMENTO (a v7.2 fechou
  isso no gerador; cópia antiga pode ter): vai pra `99_to_delete/` da central,
  fora do projeto, e é reportado em separado.

Uso:
  mb-magra.py --projeto CAMINHO              # dry-run de um
  mb-magra.py --todos                        # dry-run de todos
  mb-magra.py --todos --aplicar              # executa
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

DESTINO_ARQUIVO = "90_arquivo/magra-260825"

# Derivados: regeneráveis por script, saem sem dó.
DERIVADOS = {"RELATORIO.html", "RELATORIO-VIVO.html", "MEGABRAIN-RELATORIO-DNA.html",
             "RELATORIO-AGENTES.html", "PAINEL-MEGABRAIN.html", "estado.json"}

# O que a cópia magra guarda.
FICAM = {".mb-origem.json", "LEIAME.md"}


def _h(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def indice_central(central: Path) -> dict[str, set]:
    """nome do arquivo -> hashes que a central tem, em qualquer lugar dela."""
    idx: dict[str, set] = {}
    pular = {".git", ".mb-backup", "_github", "__pycache__", "dados", ".mb-log"}
    for p in central.rglob("*"):
        if not p.is_file() or (set(p.parts) & pular):
            continue
        idx.setdefault(p.name, set()).add(_h(p))
    return idx


def copias(raiz: Path, central: Path) -> list[Path]:
    achadas = []
    for p in sorted(raiz.rglob("MEGABRAIN")):
        if not p.is_dir() or p.resolve() == central.resolve():
            continue
        if (p / "VERSAO.txt").is_file() or (p / ".mb-origem.json").is_file():
            achadas.append(p)
    return achadas


def ja_magra(mb: Path) -> bool:
    restantes = [f for f in mb.iterdir()
                 if f.name not in FICAM and f.name != "90_arquivo"]
    return not restantes


def indice_compartilhado(alvos: list[Path], minimo: int = 5) -> set:
    """(caminho relativo, hash) que aparece em N+ cópias.

    260825: a regra "na dúvida fica" preservava 168 arquivos que NÃO eram do
    projeto — `anti-slop.md`, `metaprompt-patterns.md`, `260810_MEGABRAIN.md`,
    `novo-projeto.cmd` — todos legado que a central já renomeou ou aposentou,
    e que o índice por NOME não reconhecia mais. Em vez de uma lista fixa (que
    envelhece), a evidência: arquivo byte-idêntico em 5+ projetos diferentes é,
    por definição, cópia compartilhada — nenhum conteúdo de projeto se repete
    em 5 projetos por acaso.
    """
    import collections
    cont = collections.Counter()
    for mb in alvos:
        if not mb.is_dir():
            continue
        vistos = set()
        for f in mb.rglob("*"):
            if not f.is_file() or "90_arquivo" in f.parts or "__pycache__" in f.parts:
                continue
            vistos.add((f.relative_to(mb).as_posix(), _h(f)))
        cont.update(vistos)
    return {k for k, n in cont.items() if n >= minimo}


def planejar(mb: Path, central: Path, idx: dict, compartilhado: set | None = None) -> dict:
    """Classifica cada arquivo: sai, fica, ou é vazamento."""
    compartilhado = compartilhado or set()
    sai, fica, vazamento = [], [], []
    for f in mb.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(mb)
        if rel.parts and rel.parts[0] == "90_arquivo":
            continue
        if "__pycache__" in rel.parts:
            sai.append(rel)
            continue
        if f.name in FICAM and len(rel.parts) == 1:
            fica.append(rel)
            continue
        if "usuario" in rel.parts and "dna" in rel.parts:
            vazamento.append(rel)
            continue
        if f.name in DERIVADOS:
            sai.append(rel)
            continue
        if _h(f) in idx.get(f.name, set()):
            sai.append(rel)          # existe igual na central
            continue
        # nome que a central conhece, conteúdo diferente = cópia velha
        if f.name in idx:
            sai.append(rel)
            continue
        # idêntico em 5+ cópias = legado compartilhado, não conteúdo de projeto
        if (rel.as_posix(), _h(f)) in compartilhado:
            sai.append(rel)
            continue
        fica.append(rel)             # na dúvida, fica
    return {"sai": sai, "fica": fica, "vazamento": vazamento}


def ponteiro(mb: Path, central: Path) -> dict:
    atual = {}
    txt = u.safe_read_text(mb / ".mb-origem.json")
    if txt:
        try:
            atual = json.loads(txt)
        except (json.JSONDecodeError, ValueError):
            atual = {}
    versao = u.read_first_non_empty_line(u.achar(central, "VERSAO.txt")) or ""
    curta = versao.split("—")[0].strip() if "—" in versao else versao[:40]
    return {
        "formato": "magra",
        "central": str(central),
        "versao_curta": curta,
        "commit_central": atual.get("commit_central"),
        "sincronizado_em": atual.get("sincronizado_em"),
        "como_usar": ("A máquina do megabrain NÃO está aqui — está em `central`. "
                      "Rode os scripts de lá apontando pra este projeto: "
                      "python <central>/bin/mb-check-version.py --projeto <este> --auto"),
        "restaurar_copia_cheia": "python <central>/bin/mb-recuperar-megabrain.py --projeto <este>",
    }


LEIAME = """# MEGABRAIN deste projeto — formato MAGRO

Esta pasta **não guarda mais o motor do megabrain**. Ele vive num lugar só,
na central apontada por `.mb-origem.json`.

## Por quê

Medido em 260825: as 19 cópias somavam 157-182 MB, com **173 arquivos
idênticos em 5+ cópias** e apenas 10 realmente únicos no conjunto todo. Pior
que o disco: manter dois formatos vivos (central aninhada × cópia plana)
obrigava `mb_utils` a resolver os dois, e **dois dos bugs de 260825 nasceram
nessa costura** — o índice de lições que rodou um dia com 8 de 166, e o
relatório de agentes que dizia "nenhuma candidata" com os dados presentes.

## Onde está cada coisa agora

| O que | Onde |
|---|---|
| Scripts, skills, referências, modelos | na central (`.mb-origem.json` → `central`) |
| Lições, cérebro, DNA | na central — fonte única, sem cópia pra derivar |
| **O estado DESTE projeto** | na raiz do projeto (`ESTADO.md`, `HANDOFF.md`, `DECISOES.md`), fora desta pasta |
| O que estava aqui antes | `90_arquivo/magra-260825/` — movido, nada apagado |

## Como rodar

Da central, apontando pra cá:

```
python <central>/bin/mb-check-version.py --projeto <este projeto> --auto
python <central>/bin/mb-estado.py --campo versao.atual
```

## Se precisar da cópia cheia de volta

```
python <central>/bin/mb-recuperar-megabrain.py --projeto <este projeto>
```

Ele monta a cópia plana a partir da central (ou do git dela, ou de um backup)
e **confere** que restaurou — não declara sucesso só porque terminou.
"""


def aplicar(mb: Path, central: Path, plano: dict) -> dict:
    dest = mb / DESTINO_ARQUIVO
    movidos = 0
    for rel in plano["sai"]:
        origem = mb / rel
        if not origem.is_file():
            continue
        alvo = dest / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        try:
            origem.rename(alvo)
            movidos += 1
        except OSError:
            try:
                shutil.move(str(origem), str(alvo))
                movidos += 1
            except OSError:
                pass

    vazados = 0
    if plano["vazamento"]:
        quarentena = central / "99_to_delete" / f"260825_dna-usuario-vazado-{mb.parent.name}"
        for rel in plano["vazamento"]:
            origem = mb / rel
            if not origem.is_file():
                continue
            alvo = quarentena / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(origem), str(alvo))
                vazados += 1
            except OSError:
                pass

    # limpa diretórios vazios que sobraram
    for d in sorted([x for x in mb.rglob("*") if x.is_dir()],
                    key=lambda x: len(x.parts), reverse=True):
        if "90_arquivo" in d.parts:
            continue
        try:
            next(d.iterdir())
        except StopIteration:
            try:
                d.rmdir()
            except OSError:
                pass
        except OSError:
            pass

    (mb / ".mb-origem.json").write_text(
        json.dumps(ponteiro(mb, central), ensure_ascii=False, indent=2), encoding="utf-8")
    (mb / "LEIAME.md").write_text(LEIAME, encoding="utf-8")
    return {"movidos": movidos, "vazados": vazados}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projeto", default=None)
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()

    central = Path(__file__).resolve().parent.parent
    if a.projeto:
        alvos = [Path(a.projeto).resolve() / "MEGABRAIN"]
    elif a.todos:
        alvos = copias(central.parent, central)
    else:
        print("use --projeto CAMINHO ou --todos")
        return 2

    idx = indice_central(central)
    compartilhado = indice_compartilhado(alvos)
    print(f"central: {central}")
    print(f"índice: {len(idx)} nome(s) conhecidos · "
          f"{len(compartilhado)} arquivo(s) idêntico(s) em 5+ cópias")
    print()

    cab = f"{'projeto':<26} {'sai':>5} {'fica':>5} {'vaza':>5}  situação"
    print(cab); print("-" * len(cab))
    total = {"sai": 0, "fica": 0, "vazamento": 0, "movidos": 0, "vazados": 0}
    detalhes = []
    for mb in alvos:
        if not mb.is_dir():
            print(f"{mb.parent.name:<26} — pasta não existe")
            continue
        if ja_magra(mb):
            print(f"{mb.parent.name:<26} {'':>5} {'':>5} {'':>5}  já magra")
            continue
        plano = planejar(mb, central, idx, compartilhado)
        for k in ("sai", "fica", "vazamento"):
            total[k] += len(plano[k])
        nota = ""
        if plano["vazamento"]:
            nota = "VAZAMENTO dna/usuario → quarentena"
        elif plano["fica"]:
            nota = "arquivo(s) preservado(s) na raiz"
        print(f"{mb.parent.name:<26} {len(plano['sai']):>5} {len(plano['fica']):>5} "
              f"{len(plano['vazamento']):>5}  {nota}")
        if plano["fica"]:
            detalhes.append((mb.parent.name, plano["fica"]))
        if a.aplicar:
            r = aplicar(mb, central, plano)
            total["movidos"] += r["movidos"]
            total["vazados"] += r["vazados"]

    print(f"\ntotal: {total['sai']} sai · {total['fica']} fica · "
          f"{total['vazamento']} vazamento")
    if detalhes:
        print("\npreservados na raiz da cópia (não reconhecidos como da central):")
        for nome, itens in detalhes:
            for x in itens:
                if x.name not in FICAM:
                    print(f"  {nome}: {x.as_posix()}")
    if a.aplicar:
        print(f"\nAPLICADO: {total['movidos']} movido(s) pra 90_arquivo/magra-260825/, "
              f"{total['vazados']} vazamento(s) em quarentena na central")
    else:
        print("\ndry-run — nada foi tocado. Use --aplicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

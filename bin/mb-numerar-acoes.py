#!/usr/bin/env python3
"""
mb-numerar-acoes.py — numera os botões de 01_acoes/ com prefixo estável.

Por que existe (260825, decisão 260825l): ele pediu "clica no script 3" em vez
de "clica no publicar-e-fotografar". Número só serve se NÃO MUDAR — se sair da
ordem alfabética da pasta, entra um botão novo e o 3 vira outro na semana
seguinte. Aqui o número vem de REGISTRO DECLARADO abaixo: botão novo pega o
próximo livre, número aposentado nunca é reusado.

O prefixo entra no NOME DO ARQUIVO, não só no relatório — é na pasta que ele
se perde, e é lá que o número precisa existir.

Uso:
  mb-numerar-acoes.py            # confere: mostra o que mudaria (dry-run)
  mb-numerar-acoes.py --aplicar  # renomeia + reescreve as referências
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

# O registro mora em mb_registro.py — mesma lista que o painel do relatório
# monta. Dois lugares com a mesma numeração é como o número passa a mentir.
from mb_registro import ACOES as REGISTRO  # noqa: E402

# CAMINHO VIVO × PROSA HISTÓRICA — a distinção que faz este script ser seguro.
#
# Reescrever `DECISOES.md` seria falsificar o passado: uma decisão de 260824
# que cita o nome COM PREFIXO DE DATA está CERTA — era esse o nome naquele dia.
# O mesmo vale pra VERSAO.txt, pras lições e pras pendências — são
# registro, não instrução. Só entra aqui o que um agente ou um .cmd LÊ PARA
# EXECUTAR, e o que é derivado se regenera sozinho.
VIVOS = ("bin", "motor/skills", "motor/modelos", "motor/plugin-megabrain",
         "motor/plugin-megabrain-claude", "01_acoes", ".claude")
# Arquivos soltos que são instrução/estado atual, não história.
VIVOS_AVULSOS = ("memoria/nucleo/MEGABRAIN.md", "memoria/estado/ESTADO.md",
                 "memoria/estado/HANDOFF.md", "memoria/estado/META.md",
                 "memoria/estado/PROGRESSO.json")
# Nunca tocar, mesmo dentro de pasta viva: registro do que aconteceu.
HISTORICO = ("DECISOES.md", "VERSAO.txt", "licoes-megabrain.md")
EXT_VIVAS = {".py", ".md", ".cmd", ".json", ".txt"}


def alvo(pasta: Path, apelido: str) -> Path | None:
    """Arquivo atual do botão, com ou sem prefixo antigo."""
    for p in sorted(pasta.glob("*.cmd")):
        nome = p.stem
        sem_prefixo = re.sub(r"^\d{2}_|^\d{6}_", "", nome)
        if sem_prefixo == apelido or nome == apelido:
            return p
    return None


def plano(central: Path) -> list[tuple[Path, Path]]:
    pasta = u.pasta(central, "acoes") if "acoes" in u.PASTAS_NUMERADAS else central / "01_acoes"
    if not pasta.is_dir():
        pasta = central / "01_acoes"
    movs = []
    for n, apelido, *_resto in REGISTRO:
        atual = alvo(pasta, apelido)
        if atual is None:
            print(f"  AUSENTE  {n:02d} {apelido} — sem arquivo na pasta")
            continue
        novo = pasta / f"{n:02d}_{apelido}.cmd"
        if atual.name != novo.name:
            movs.append((atual, novo))
    return movs


def arquivos_vivos(central: Path):
    vistos = set()
    for raiz in VIVOS:
        base = central / raiz
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXT_VIVAS:
                continue
            if "__pycache__" in p.parts or p.name in HISTORICO:
                continue
            if p not in vistos:
                vistos.add(p)
                yield p
    for rel in VIVOS_AVULSOS:
        p = central / rel
        if p.is_file() and p not in vistos:
            vistos.add(p)
            yield p


def reescrever(central: Path, movs, aplicar: bool) -> int:
    """Troca o nome antigo pelo novo em todo arquivo vivo. Duas fases com
    placeholder: saída de uma troca não pode virar entrada de outra (lição
    260824)."""
    mapa = {a.name: b.name for a, b in movs}
    mapa.update({a.stem: b.stem for a, b in movs})
    tocados = 0
    for arq in arquivos_vivos(central):
        try:
            # newline="" preserva CRLF dos .cmd — sem isso o cmd.exe quebra.
            texto = arq.read_text(encoding="utf-8", newline="")
        except (UnicodeDecodeError, OSError):
            continue
        novo = texto
        for i, (velho, atual) in enumerate(mapa.items()):
            novo = novo.replace(velho, f"\x00MB{i}\x00")
        for i, (velho, atual) in enumerate(mapa.items()):
            novo = novo.replace(f"\x00MB{i}\x00", atual)
        if novo != texto:
            tocados += 1
            rel = arq.relative_to(central)
            n = sum(1 for v in mapa if v in texto)
            print(f"  ref  {rel} ({n} nome(s))")
            if aplicar:
                arq.write_text(novo, encoding="utf-8", newline="")
    return tocados


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--dir", default=".")
    a = ap.parse_args()
    central = Path(a.dir).resolve()

    movs = plano(central)
    if not movs:
        print("nada a renomear — os 11 já estão numerados")
    else:
        print(f"renomear {len(movs)}:")
        for velho, novo in movs:
            print(f"  {velho.name}  ->  {novo.name}")

    print("referências a reescrever:")
    tocados = reescrever(central, movs, a.aplicar)

    if a.aplicar:
        for velho, novo in movs:
            velho.rename(novo)
        print(f"\nAPLICADO: {len(movs)} renomeados, {tocados} arquivos reescritos")
    else:
        print(f"\ndry-run: {len(movs)} renomeariam, {tocados} arquivos seriam reescritos")
        print("rode com --aplicar pra valer")
    return 0


if __name__ == "__main__":
    sys.exit(main())

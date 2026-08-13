#!/usr/bin/env python3
"""
mb-sync.py — utilitario de handoff multi-agente do MEGABRAIN (Gate 0 / Gate 6).

Le e escreve a trava em HANDOFF.md (TRAVADO_POR / ATE / ESCOPO) para que
Claude e Kimi nao pisem no mesmo arquivo ao mesmo tempo. Nao substitui os
gates - so torna a trava uma garantia de script em vez de disciplina de
markdown (regra de ouro 21: garantia real e script, nao markdown).

Uso:
  mb-sync.py status  [--dir CAMINHO]
  mb-sync.py lock    --agente NOME --escopo CAMINHO [CAMINHO ...] [--horas N] [--dir CAMINHO]
  mb-sync.py release [--dir CAMINHO]

Sem argumentos: roda "status" no diretorio atual.
Saida de "status" tem codigo de saida 0 (livre/vencida - pode escrever) ou
1 (travado por outro agente, dentro do prazo) - use em script/CI.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

HANDOFF_NAME = "HANDOFF.md"
FMT = "%Y-%m-%d %H:%M"

MARK_START = "<!-- mb-sync:lock:start -->"
MARK_END = "<!-- mb-sync:lock:end -->"


def lock_block(agente: str, ate: dt.datetime, escopo: list[str]) -> str:
    linhas = [
        MARK_START,
        f"TRAVADO_POR: {agente}",
        f"ATE: {ate.strftime(FMT)}",
        "ESCOPO:",
    ]
    linhas += [f"  - {e}" for e in escopo]
    linhas.append(MARK_END)
    return "\n".join(linhas) + "\n"


def parse_lock(texto: str):
    if MARK_START not in texto or MARK_END not in texto:
        return None
    bloco = texto.split(MARK_START, 1)[1].split(MARK_END, 1)[0]
    agente = None
    ate = None
    escopo = []
    for linha in bloco.splitlines():
        linha = linha.strip()
        if linha.startswith("TRAVADO_POR:"):
            agente = linha.split(":", 1)[1].strip()
        elif linha.startswith("ATE:"):
            try:
                ate = dt.datetime.strptime(linha.split(":", 1)[1].strip(), FMT)
            except ValueError:
                ate = None
        elif linha.startswith("- "):
            escopo.append(linha[2:].strip())
    if agente is None or agente.lower() == "livre":
        return None
    return {"agente": agente, "ate": ate, "escopo": escopo}


def read_handoff(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_handoff(path: Path, novo_bloco: str, texto_atual: str):
    if MARK_START in texto_atual and MARK_END in texto_atual:
        antes = texto_atual.split(MARK_START, 1)[0]
        depois = texto_atual.split(MARK_END, 1)[1]
        conteudo = antes + novo_bloco + depois
    else:
        cabeca = texto_atual.rstrip() + "\n\n" if texto_atual.strip() else "# HANDOFF\n\n"
        conteudo = cabeca + novo_bloco
    path.write_text(conteudo, encoding="utf-8")


def cmd_status(args):
    caminho = Path(args.dir) / HANDOFF_NAME
    texto = read_handoff(caminho)
    lock = parse_lock(texto)
    if not caminho.exists():
        print(f"status: SEM {HANDOFF_NAME} ainda em {args.dir} -> livre (crie ao travar)")
        return 0
    if lock is None:
        print(f"status: LIVRE ({caminho})")
        return 0
    agora = dt.datetime.now()
    if lock["ate"] and lock["ate"] < agora:
        print(f"status: TRAVA VENCIDA - {lock['agente']} ate {lock['ate']} (pode assumir)")
        print(f"  escopo antigo: {', '.join(lock['escopo']) or '(nao declarado)'}")
        return 0
    print(f"status: TRAVADO por {lock['agente']} ate {lock['ate'] or '(sem prazo)'}")
    print(f"  escopo: {', '.join(lock['escopo']) or '(nao declarado)'}")
    return 1


def cmd_lock(args):
    caminho = Path(args.dir) / HANDOFF_NAME
    texto = read_handoff(caminho)
    lock_existente = parse_lock(texto)
    agora = dt.datetime.now()
    if lock_existente and lock_existente["agente"] != args.agente:
        if lock_existente["ate"] and lock_existente["ate"] >= agora:
            print(
                f"recusado: travado por {lock_existente['agente']} ate "
                f"{lock_existente['ate']} - escopo {', '.join(lock_existente['escopo'])}"
            )
            return 1
    ate = agora + dt.timedelta(hours=args.horas)
    bloco = lock_block(args.agente, ate, args.escopo)
    write_handoff(caminho, bloco, texto)
    print(f"travado: {args.agente} ate {ate.strftime(FMT)} - escopo: {', '.join(args.escopo)}")
    return 0


def cmd_release(args):
    caminho = Path(args.dir) / HANDOFF_NAME
    texto = read_handoff(caminho)
    if not texto or parse_lock(texto) is None:
        print("nada para liberar (ja estava livre)")
        return 0
    bloco = f"{MARK_START}\nTRAVADO_POR: livre\n{MARK_END}\n"
    write_handoff(caminho, bloco, texto)
    print("liberado: TRAVADO_POR: livre")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Handoff multi-agente do MEGABRAIN")
    ap.add_argument("--dir", default=".", help="pasta do projeto (default: .)")
    sub = ap.add_subparsers(dest="comando")

    sub.add_parser("status")

    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--agente", required=True)
    p_lock.add_argument("--escopo", nargs="+", required=True)
    p_lock.add_argument("--horas", type=float, default=2.0)

    sub.add_parser("release")

    args = ap.parse_args()
    comando = args.comando or "status"

    if comando == "status":
        sys.exit(cmd_status(args))
    elif comando == "lock":
        sys.exit(cmd_lock(args))
    elif comando == "release":
        sys.exit(cmd_release(args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
mb-sync.py — utilitario de handoff multi-agente do MEGABRAIN (Gate 0 / Gate 6).

Le e escreve a trava em HANDOFF.md (USUARIO / TRAVADO_POR / ATE / ESCOPO)
para que Claude e Kimi nao pisem no mesmo arquivo ao mesmo tempo. Nao
substitui os gates - so torna a trava uma garantia de script em vez de
disciplina de markdown (regra de ouro 21: garantia real e script, nao
markdown).

Uso:
  mb-sync.py status  [--dir CAMINHO]
  mb-sync.py lock    --agente NOME --escopo CAMINHO [CAMINHO ...] [--horas N] [--usuario NOME] [--dir CAMINHO]
  mb-sync.py release --agente NOME [--force] [--dir CAMINHO]

Sem argumentos: roda "status" no diretorio atual.
Saida de "status" tem codigo de saida 0 (livre/vencida - pode escrever) ou
1 (travado por outro agente, dentro do prazo) - use em script/CI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import sys
from dataclasses import dataclass
from pathlib import Path

import mb_utils as u

u.utf8_console()

HANDOFF_NAME = "HANDOFF.md"
FMT = "%Y-%m-%d %H:%M"

MARK_START = "<!-- mb-sync:lock:start -->"
MARK_END = "<!-- mb-sync:lock:end -->"


@dataclass
class LockInfo:
    usuario: str | None = None
    agente: str | None = None
    ate: dt.datetime | None = None
    escopo: list[str] | None = None

    def esta_livre(self) -> bool:
        return self.agente is None or self.agente.lower() == "livre"

    def esta_vencido(self, agora: dt.datetime) -> bool:
        if self.ate is None:
            return False
        return self.ate < agora


def sanitizar_campo(valor: str) -> str:
    """Remove quebras de linha que poderiam quebrar o formato da trava."""
    return " ".join(valor.replace("\r", " ").replace("\n", " ").split())


def lock_block(usuario: str, agente: str, ate: dt.datetime, escopo: list[str]) -> str:
    agente = sanitizar_campo(agente)
    usuario = sanitizar_campo(usuario)
    escopo = [sanitizar_campo(e) for e in escopo]
    linhas = [
        MARK_START,
        f"USUARIO: {usuario}",
        f"TRAVADO_POR: {agente}",
        f"ATE: {ate.strftime(FMT)}",
        "ESCOPO:",
    ]
    linhas += [f"  - {e}" for e in escopo]
    linhas.append(MARK_END)
    return "\n".join(linhas) + "\n"


def parse_lock(texto: str) -> LockInfo | None:
    idx_start = texto.find(MARK_START)
    idx_end = texto.find(MARK_END)
    if idx_start == -1 or idx_end == -1 or idx_start >= idx_end:
        return None

    bloco = texto[idx_start + len(MARK_START): idx_end]
    info = LockInfo(escopo=[])
    for linha in bloco.splitlines():
        linha = linha.strip()
        if linha.startswith("USUARIO:"):
            info.usuario = linha.split(":", 1)[1].strip() or None
        elif linha.startswith("TRAVADO_POR:"):
            info.agente = linha.split(":", 1)[1].strip() or None
        elif linha.startswith("ATE:"):
            try:
                info.ate = dt.datetime.strptime(linha.split(":", 1)[1].strip(), FMT)
            except ValueError:
                info.ate = None
        elif linha.startswith("- "):
            if info.escopo is None:
                info.escopo = []
            info.escopo.append(linha[2:].strip())

    if info.esta_livre():
        return None
    return info


def write_handoff(path: Path, novo_bloco: str | None, texto_atual: str) -> bool:
    """Reescreve HANDOFF.md substituindo o bloco de trava.

    Se `novo_bloco` for None, remove o bloco inteiro (inclusive marcadores).
    """
    idx_start = texto_atual.find(MARK_START)
    idx_end = texto_atual.find(MARK_END)

    if idx_start != -1 and idx_end != -1 and idx_start < idx_end:
        antes = texto_atual[:idx_start]
        depois = texto_atual[idx_end + len(MARK_END):]
        if novo_bloco is None:
            conteudo = antes.rstrip() + depois.lstrip()
        else:
            conteudo = antes + novo_bloco + depois
    else:
        if novo_bloco is None:
            conteudo = texto_atual
        else:
            cabeca = texto_atual.rstrip() + "\n\n" if texto_atual.strip() else "# HANDOFF\n\n"
            conteudo = cabeca + novo_bloco

    # Garante terminar com uma nova linha.
    if not conteudo.endswith("\n"):
        conteudo += "\n"

    return u.atomic_write_text(path, conteudo)


def base_dir_validada(args_dir: str) -> Path:
    """Resolve --dir e exige que seja uma pasta existente.

    O projeto quase nunca fica dentro da pasta do megabrain: o comando
    documentado e `python <MEGABRAIN_ROOT>/bin/mb-sync.py --dir <projeto>`,
    rodado de qualquer lugar. Exigir contencao no diretorio atual (v4.9)
    quebrava exatamente esse uso.

    A trava so escreve HANDOFF.md dentro da pasta que o usuario apontou,
    entao nao ha superficie de traversal a proteger aqui.
    """
    alvo = Path(args_dir).expanduser().resolve()
    if not alvo.exists():
        u.die(f"pasta nao encontrada: {alvo}")
    if not alvo.is_dir():
        u.die(f"--dir precisa ser uma pasta, nao arquivo: {alvo}")
    return alvo


def cmd_status(args) -> int:
    base = base_dir_validada(args.dir)
    caminho = u.achar(base, HANDOFF_NAME)
    texto = u.safe_read_text(caminho) or ""

    if not caminho.exists():
        print(f"status: SEM {HANDOFF_NAME} ainda em {base} -> livre (crie ao travar)")
        return 0

    lock = parse_lock(texto)
    if lock is None:
        print(f"status: LIVRE ({caminho})")
        return 0

    agora = dt.datetime.now()
    ate_str = lock.ate.strftime(FMT) if lock.ate else "(sem prazo)"
    escopo_str = ", ".join(lock.escopo) if lock.escopo else "(nao declarado)"
    usuario_str = lock.usuario if lock.usuario else "(nao declarado)"

    if lock.ate and lock.esta_vencido(agora):
        print(f"status: TRAVA VENCIDA - {lock.agente} ate {ate_str} (pode assumir)")
        print(f"  usuario: {usuario_str}")
        print(f"  escopo antigo: {escopo_str}")
        return 0

    print(f"status: TRAVADO por {lock.agente} ate {ate_str} (usuario: {usuario_str})")
    print(f"  escopo: {escopo_str}")
    return 1


def cmd_lock(args) -> int:
    base = base_dir_validada(args.dir)
    caminho = u.achar(base, HANDOFF_NAME)
    lock_path = caminho.parent / f".{HANDOFF_NAME}.lock"

    if not u.acquire_lock(lock_path, timeout=5.0):
        print(f"recusado: nao foi possivel obter lock exclusivo ({lock_path})")
        return 1

    try:
        texto = u.safe_read_text(caminho) or ""
        lock_existente = parse_lock(texto)
        agora = dt.datetime.now()

        if lock_existente and lock_existente.agente != args.agente:
            if not lock_existente.esta_vencido(agora):
                ate_str = lock_existente.ate.strftime(FMT) if lock_existente.ate else "sem prazo"
                escopo_str = ", ".join(lock_existente.escopo) if lock_existente.escopo else "nao declarado"
                usuario_str = lock_existente.usuario if lock_existente.usuario else "nao declarado"
                print(
                    f"recusado: travado por {lock_existente.agente} ate "
                    f"{ate_str} - usuario {usuario_str} - escopo {escopo_str}"
                )
                return 1

        usuario = args.usuario
        if usuario is None:
            # 1) arquivo de identidade na pasta do projeto/central.
            usuario = u.detectar_usuario(base / u.IDENTIDADE_DEFAULT)
            # 2) sem identidade: usa o login do SO. Gravar "<USUARIO>" no
            #    HANDOFF nao identifica ninguem e quebra a trava entre pessoas.
            if usuario == "<USUARIO>":
                usuario = getpass.getuser() or "desconhecido"
        ate = agora + dt.timedelta(hours=args.horas)
        bloco = lock_block(usuario, args.agente, ate, args.escopo)
        if not write_handoff(caminho, bloco, texto):
            return 1

        print(
            f"travado: {args.agente} (usuario: {usuario}) ate {ate.strftime(FMT)} "
            f"- escopo: {', '.join(args.escopo)}"
        )
        return 0
    finally:
        u.release_lock(lock_path)


def cmd_release(args) -> int:
    base = base_dir_validada(args.dir)
    caminho = u.achar(base, HANDOFF_NAME)
    lock_path = caminho.parent / f".{HANDOFF_NAME}.lock"

    if not u.acquire_lock(lock_path, timeout=5.0):
        print(f"recusado: nao foi possivel obter lock exclusivo ({lock_path})")
        return 1

    try:
        texto = u.safe_read_text(caminho) or ""
        lock = parse_lock(texto)
        if not texto or lock is None:
            print("nada para liberar (ja estava livre)")
            return 0

        agora = dt.datetime.now()
        vencida = lock.esta_vencido(agora)
        if lock.agente != args.agente and not vencida and not args.force:
            ate_str = lock.ate.strftime(FMT) if lock.ate else "sem prazo"
            print(
                f"recusado: a trava e de {lock.agente} (ate {ate_str}), "
                f"nao de {args.agente}. Use --force so se souber o que esta fazendo."
            )
            return 1

        if not write_handoff(caminho, None, texto):
            return 1

        print("liberado: trava removida")
        return 0
    finally:
        u.release_lock(lock_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Handoff multi-agente do MEGABRAIN")
    ap.add_argument("--dir", default=".", help="pasta do projeto (default: .)")
    sub = ap.add_subparsers(dest="comando")

    sub.add_parser("status", help="mostra estado atual da trava")

    p_lock = sub.add_parser("lock", help="trava o projeto para um agente")
    p_lock.add_argument("--agente", required=True)
    p_lock.add_argument("--escopo", nargs="+", required=True)
    p_lock.add_argument("--horas", type=float, default=2.0)
    p_lock.add_argument(
        "--usuario",
        default=None,
        help="nome do usuario (default: detecta de 260810_memoria-pessoal.md)",
    )

    p_rel = sub.add_parser("release", help="libera a trava do projeto")
    p_rel.add_argument("--agente", required=True)
    p_rel.add_argument(
        "--force",
        action="store_true",
        help="liberar trava de outro agente ainda no prazo (use com consciencia)",
    )

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

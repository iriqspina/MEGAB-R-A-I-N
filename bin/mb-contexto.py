#!/usr/bin/env python3
"""
mb-contexto.py — hook de contexto unificado (v6, fases 2+3).

Roda no UserPromptSubmit do Claude Code e do Kimi (o .mjs do plugin chama
este script e repassa o stdout). O que sai no stdout VIRA CONTEXTO da sessão,
então o contrato é o inverso do mb-observar: aqui o stdout é o produto.

O que injeta:
- 1ª mensagem da sessão: META.md do projeto (meta + histórico de intenção),
  a instrução de alinhamento pré-prompt (decisão 260819: todo prompt,
  desligável com "ALINHAMENTO: off" no META.md) e as lições mais próximas
  do prompt (índice da fase 3).
- Mensagens seguintes: só lições relevantes AINDA NÃO injetadas na sessão.
  Sem novidade → stdout vazio (custo zero de contexto).

Fail-open: qualquer erro → stdout vazio, exit 0. Nunca derruba sessão.

Uso (hooks):
    python bin/mb-contexto.py --agente claude
    python bin/mb-contexto.py --agente kimi

Teste manual:
    echo {"prompt":"...","cwd":"...","session_id":"x"} | python bin/mb-contexto.py --teste
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import mb_utils as u

MAX_META_CHARS = 3000
MAX_LICOES = 5
MAX_PAGINAS_CEREBRO = 3   # v6.2: páginas de cerebro/ (wiki+pessoas) mais próximas do prompt
SCORE_MINIMO_EMBED = 0.55   # abaixo disso a lição é ruído, não ajuda
SENTINEL_DIR = Path(tempfile.gettempdir()) / "megabrain-sessoes"


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def projetos_root() -> Path:
    env = os.environ.get("MEGABRAIN_PROJETOS_ROOT")
    if env:
        return Path(env).resolve()
    return central().parent


def achar_projeto(cwd: str | None) -> Path | None:
    try:
        if not cwd:
            return None
        alvo = Path(cwd).resolve()
        raiz = projetos_root()
        if alvo == raiz or raiz not in alvo.parents:
            return None
        projeto = alvo
        while projeto.parent != raiz:
            projeto = projeto.parent
        return projeto
    except OSError:
        return None


def carregar_indice_licoes():
    """Importa mb-indice-licoes.py como módulo (nome com hífen)."""
    caminho = Path(__file__).resolve().parent / "mb-indice-licoes.py"
    spec = importlib.util.spec_from_file_location("mb_indice_licoes", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def carregar_indice_cerebro():
    caminho = Path(__file__).resolve().parent / "mb-indice-cerebro.py"
    spec = importlib.util.spec_from_file_location("mb_indice_cerebro", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def estado_sessao(session_id: str) -> tuple[Path, dict]:
    SENTINEL_DIR.mkdir(parents=True, exist_ok=True)
    arq = SENTINEL_DIR / f"{session_id}.ctx.json"
    texto = u.safe_read_text(arq)
    if texto:
        try:
            return arq, json.loads(texto)
        except (json.JSONDecodeError, ValueError):
            pass
    return arq, {"primeira": True, "injetadas": []}


def instrucao_alinhamento(meta_existe: bool) -> str:
    criar = ("" if meta_existe else
             " Este projeto ainda não tem META.md — crie a partir de "
             "modelos/META.md da central na abertura da primeira tarefa.")
    return (
        "### Alinhamento pré-prompt (decisão do <USUARIO>, 260819 — vale pra TODO prompt)\n"
        "Antes de executar qualquer prompt de tarefa: (1) devolva a versão "
        "retrabalhada do prompt — objetivo, entregável, critérios verificáveis, "
        "restrições — e confirme as intenções (máx. 1 pergunta se houver "
        "ambiguidade); (2) grave o par PEDIDO ORIGINAL / PROMPT RETRABALHADO / "
        "INTENÇÃO CONFIRMADA no Histórico de intenção do META.md do projeto; "
        "(3) ao fim da tarefa, preencha RESULTADO ALINHOU." + criar + "\n"
        "Respostas curtas de continuação (\"sim\", \"continua\", \"ok\") não "
        "passam pelo retrabalho. Pra desligar neste projeto: linha "
        "\"ALINHAMENTO: off\" no META.md."
    )


def montar(payload: dict, agente: str) -> str:
    prompt = payload.get("prompt") or payload.get("user_prompt") or ""
    session_id = str(payload.get("session_id") or "sem-id")
    projeto = achar_projeto(payload.get("cwd") or os.getcwd())

    arq_sent, estado = estado_sessao(session_id)
    primeira = estado.get("primeira", True)
    injetadas = set(estado.get("injetadas", []))

    partes: list[str] = []

    # META.md + instrução: só na primeira mensagem da sessão.
    meta_existe = False
    if primeira:
        meta_txt = None
        if projeto:
            meta_txt = u.safe_read_text(u.achar(projeto, "META.md"))
        if meta_txt:
            meta_existe = True
            recorte = meta_txt.strip()
            if len(recorte) > MAX_META_CHARS:
                recorte = recorte[:MAX_META_CHARS] + "\n[META truncado]"
            partes.append("### META do projeto (META.md — a meta vale mais que "
                          "qualquer suposição)\n" + recorte)
        alinhado_off = bool(meta_txt) and "ALINHAMENTO: off" in meta_txt
        if not alinhado_off:
            partes.append(instrucao_alinhamento(meta_existe))

    # Lições por relevância — em toda mensagem, só as inéditas na sessão.
    if prompt.strip():
        try:
            indice = carregar_indice_licoes()
            achadas = indice.buscar(prompt, MAX_LICOES)
        except Exception:
            achadas = []
        novas = []
        for e in achadas:
            if e["chave"] in injetadas:
                continue
            if e.get("score", 0) < SCORE_MINIMO_EMBED and not primeira:
                continue
            novas.append(e)
        if novas:
            blocos = "\n\n".join(e["texto"] for e in novas)
            partes.append(
                f"### Lições relevantes pra este prompt ({len(novas)} de 126+, "
                "por proximidade — cada uma já foi paga em erro)\n" + blocos)
            injetadas.update(e["chave"] for e in novas)

    # Páginas do cérebro (v6.2) — conteúdo, não processo. Só inéditas na sessão.
    if prompt.strip():
        try:
            cer = carregar_indice_cerebro()
            pags = cer.buscar(prompt, MAX_PAGINAS_CEREBRO, None, payload.get("cwd") or os.getcwd())
        except Exception:
            pags = []
        novas_p = [e for e in pags if e["chave"] not in injetadas
                   and e.get("score", 0) >= SCORE_MINIMO_EMBED]
        if novas_p:
            blocos = "\n\n".join(f"**{e['chave']}**\n{e['texto'][:900]}" for e in novas_p)
            partes.append(
                f"### Páginas do cérebro relevantes ({len(novas_p)}, por proximidade — "
                "responda a partir delas e cite o path; se não cobrem, diga "
                "'não encontrado no cérebro')\n" + blocos)
            injetadas.update(e["chave"] for e in novas_p)

    estado_novo = {
        "primeira": False,
        "injetadas": sorted(injetadas),
        "ts": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "agente": agente,
    }
    u.atomic_write_text(arq_sent, json.dumps(estado_novo, ensure_ascii=False))

    if not partes:
        return ""
    return ("## Contexto megabrain (hook mb-contexto · v6)\n\n"
            + "\n\n".join(partes)
            + "\n\n> Ao fim de tarefa não-trivial, registre a lição sem pedir "
              "permissão (autorização permanente 260805).")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agente", default="claude")
    p.add_argument("--teste", action="store_true",
                   help="modo manual: mostra o bloco no stderr também")
    args = p.parse_args()

    try:
        buf = getattr(sys.stdin, "buffer", None)
        if buf is not None:
            # bytes + utf-8-sig: independe da codepage do console (cp1252
            # corromperia o BOM) e já o remove — ver mb-observar.py.
            bruto = buf.read().decode("utf-8-sig", errors="replace")
        else:
            bruto = sys.stdin.read()
        bruto = bruto.lstrip("﻿").strip()
        payload = json.loads(bruto) if bruto else {}
    except Exception:
        payload = {}

    try:
        bloco = montar(payload, args.agente)
    except Exception:
        bloco = ""

    if bloco:
        # stdout precisa sair em UTF-8 — é contexto, não console.
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError, AttributeError):
            pass
        sys.stdout.write(bloco)
    if args.teste:
        print(f"\n[teste] {len(bloco)} chars injetados", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except Exception:
        codigo = 0
    raise SystemExit(codigo)

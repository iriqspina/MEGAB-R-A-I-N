#!/usr/bin/env python3
"""
mb-observar.py — endpoint de observabilidade do megabrain (v6, fase 1).

Recebe o payload JSON de um hook de CLI (Claude Code, Kimi, Codex) no stdin
e apenda UMA linha JSONL em `<projeto>/.mb-log/eventos-YYMMDD.jsonl`.

Contrato de hook (inviolável):
- exit 0 SEMPRE — observabilidade nunca pode derrubar uma sessão;
- NADA no stdout — em UserPromptSubmit o stdout vira contexto injetado.

Uso como hook:
    python bin/mb-observar.py --agente claude --evento prompt
    python bin/mb-observar.py --agente claude --evento stop
    python bin/mb-observar.py --agente claude --evento arquivo

Uso como importador (fora de hook, imprime resumo):
    python bin/mb-observar.py --importar-feedback [--feedback PATH]

Schema da linha (campos ausentes ficam null — grava o que houver):
    ts, agente, modelo, evento, prompt, resposta, arquivo, cwd, session_id, extra

Onde grava: no `.mb-log/` do projeto (cwd do payload) quando o cwd está
dentro da raiz de projetos (env MEGABRAIN_PROJETOS_ROOT, default o diretório
pai da central). Fora dela, grava em `<central>/.mb-log/fora-de-projeto/`
para não espalhar `.mb-log/` por pastas que não são projeto.

Retenção: sem limite, poda manual (decisão do <USUARIO>, 260819).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

MAX_CAMPO_CHARS = 20000          # teto por campo de texto (prompt/resposta)
TAIL_TRANSCRIPT_BYTES = 262144   # quanto ler do fim do transcript do Claude


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


def pasta_log(cwd: str | None) -> Path:
    """`.mb-log/` do projeto, ou o balde central quando o cwd não é projeto."""
    try:
        if cwd:
            alvo = Path(cwd).resolve()
            raiz = projetos_root()
            if alvo == raiz or raiz in alvo.parents:
                # Sobe até a pasta imediatamente abaixo da raiz de projetos.
                projeto = alvo
                while projeto.parent != raiz and projeto != raiz:
                    projeto = projeto.parent
                if projeto != raiz:
                    return projeto / ".mb-log"
    except OSError:
        pass
    return central() / ".mb-log" / "fora-de-projeto"


def truncar(texto, teto=MAX_CAMPO_CHARS):
    if not isinstance(texto, str):
        return texto
    if len(texto) <= teto:
        return texto
    return texto[:teto] + f"\n[truncado — {len(texto)} chars no original]"


def tail_transcript(transcript_path: str):
    """Extrai (modelo, ultima_resposta_texto) do fim de um transcript JSONL
    do Claude Code. Fail-open: (None, None) em qualquer problema."""
    try:
        p = Path(transcript_path)
        tamanho = p.stat().st_size
        with p.open("rb") as f:
            if tamanho > TAIL_TRANSCRIPT_BYTES:
                f.seek(tamanho - TAIL_TRANSCRIPT_BYTES)
                f.readline()  # descarta linha possivelmente cortada
            linhas = f.read().decode("utf-8", errors="replace").splitlines()
        modelo = None
        resposta = None
        for linha in linhas:
            try:
                obj = json.loads(linha)
            except (json.JSONDecodeError, ValueError):
                continue
            msg = obj.get("message") or {}
            if obj.get("type") == "assistant" or msg.get("role") == "assistant":
                modelo = msg.get("model") or modelo
                conteudo = msg.get("content")
                if isinstance(conteudo, list):
                    textos = [b.get("text", "") for b in conteudo
                              if isinstance(b, dict) and b.get("type") == "text"]
                    if any(textos):
                        resposta = "\n".join(t for t in textos if t)
                elif isinstance(conteudo, str) and conteudo:
                    resposta = conteudo
        return modelo, resposta
    except Exception:
        return None, None


def gravar(linha: dict, cwd: str | None) -> Path | None:
    pasta = pasta_log(cwd)
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo = pasta / f"eventos-{dt.datetime.now():%y%m%d}.jsonl"
        with arquivo.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return arquivo
    except OSError:
        return None


def modo_hook(args) -> int:
    try:
        buf = getattr(sys.stdin, "buffer", None)
        if buf is not None:
            # bytes + utf-8-sig: independe da codepage do console (cp1252
            # corromperia o BOM antes do lstrip abaixo) e já remove o BOM.
            bruto = buf.read().decode("utf-8-sig", errors="replace")
        else:
            bruto = sys.stdin.read()
    except Exception:
        bruto = ""
    # PowerShell 5.1 injeta BOM no pipe (lição 260819); json.loads recusa.
    bruto = bruto.lstrip("﻿").strip()
    try:
        payload = json.loads(bruto) if bruto else {}
    except (json.JSONDecodeError, ValueError):
        payload = {"_payload_invalido": True}

    cwd = payload.get("cwd") or os.getcwd()
    modelo = payload.get("model") or None
    resposta = payload.get("resposta") or payload.get("response") or None

    # No stop do Claude Code a resposta não vem no payload, mas o transcript sim.
    if args.evento == "stop" and payload.get("transcript_path") and not resposta:
        m, r = tail_transcript(payload["transcript_path"])
        modelo = modelo or m
        resposta = r

    arquivo_tocado = None
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        arquivo_tocado = tool_input.get("file_path") or tool_input.get("path")

    linha = {
        "ts": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "agente": args.agente,
        "modelo": modelo,
        "evento": args.evento,
        "prompt": truncar(payload.get("prompt") or payload.get("user_prompt")),
        "resposta": truncar(resposta),
        "arquivo": arquivo_tocado,
        "cwd": cwd,
        "session_id": payload.get("session_id"),
        "extra": {
            k: payload[k]
            for k in ("hook_event_name", "tool_name", "stop_hook_active")
            if k in payload
        } or None,
    }
    gravar(linha, cwd)
    return 0


def modo_importar_feedback(args) -> int:
    """Converte gerenteneuron/data/feedback.jsonl pro schema do .mb-log.

    Incremental: um marcador guarda o último timestamp importado; só entra o
    que for mais novo. As linhas caem no .mb-log do próprio gerenteneuron.
    """
    origem = (Path(args.feedback) if args.feedback
              else u.pasta(central(), "gerenteneuron") / "data" / "feedback.jsonl")
    if not origem.is_file():
        print(f"ERRO: feedback não encontrado em {origem}")
        return 1

    destino_dir = origem.parent.parent / ".mb-log"
    marcador = destino_dir / ".feedback-import-marker"
    ultimo = u.read_first_non_empty_line(marcador) or ""

    novas = 0
    maior_ts = ultimo
    for linha_bruta in origem.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            fb = json.loads(linha_bruta)
        except (json.JSONDecodeError, ValueError):
            continue
        ts = fb.get("timestamp") or ""
        if ts <= ultimo:
            continue
        linha = {
            "ts": ts,
            "agente": "gerenteneuron",
            "modelo": fb.get("modelo_usado"),
            "evento": "prompt",
            "prompt": truncar(fb.get("mensagem")),
            "resposta": None,
            "arquivo": None,
            "cwd": str(origem.parent.parent),
            "session_id": None,
            "extra": {
                "aba": fb.get("aba"),
                "estrategia": fb.get("estrategia"),
                "provider": fb.get("provider"),
                "custo_estimado_usd": fb.get("custo_estimado_usd"),
                "tokens_entrada": fb.get("tokens_entrada"),
                "tokens_saida": fb.get("tokens_saida"),
                "erro": fb.get("erro"),
                "feedback": fb.get("feedback"),
            },
        }
        try:
            destino_dir.mkdir(parents=True, exist_ok=True)
            dia = (ts[:10] or "0000-00-00").replace("-", "")[2:]
            arquivo = destino_dir / f"eventos-{dia}.jsonl"
            with arquivo.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(linha, ensure_ascii=False) + "\n")
            novas += 1
            if ts > maior_ts:
                maior_ts = ts
        except OSError as e:
            print(f"ERRO ao gravar em {destino_dir}: {e}")
            return 1

    if novas and maior_ts:
        u.atomic_write_text(marcador, maior_ts + "\n")
    print(f"importadas {novas} linha(s) de {origem} -> {destino_dir}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agente", default="desconhecido",
                   help="claude | kimi | codex | gerenteneuron | ...")
    p.add_argument("--evento", default="prompt",
                   help="prompt | stop | arquivo | sessao-inicio | erro | ...")
    p.add_argument("--importar-feedback", action="store_true",
                   help="importa gerenteneuron/data/feedback.jsonl pro .mb-log")
    p.add_argument("--feedback", default=None,
                   help="caminho alternativo do feedback.jsonl")
    args = p.parse_args()

    if args.importar_feedback:
        return modo_importar_feedback(args)
    return modo_hook(args)


if __name__ == "__main__":
    try:
        codigo = main()
    except SystemExit:
        # argparse com argumento inválido: hook nunca pode falhar.
        codigo = 0
    except Exception:
        codigo = 0
    raise SystemExit(codigo)

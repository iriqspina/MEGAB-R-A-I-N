#!/usr/bin/env python3
"""
mb-checar-meta.py — compara a META do projeto com as mudanças reais e emite
ALINHADO ou DESVIO (v6, fase 2). Juiz: qwen local via Ollama.

O veredito é heurístico: SINALIZA desvio, não aprova entrega — humano aprova
(risco declarado no plano v6). Vai pro .mb-log como evento "meta-check" e
aparece no RELATORIO-AGENTES.html.

Evidência de mudança:
- repo git: `git diff HEAD --stat` + `git log -5 --oneline`
- sem git: arquivos modificados nas últimas 24h (top 20, por mtime)

Uso:
    python bin/mb-checar-meta.py --projeto "<PROJETOS_ROOT>/<Projeto>"

Códigos de saída: 0 ALINHADO · 2 DESVIO · 3 juiz indisponível · 1 erro de uso.
Modelo default: qwen3.8-2bit-ptbr (o 27B q4 compete com Figma/Photoshop na
GPU); troque com MEGABRAIN_MODELO_SCORING.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import urllib.request
from pathlib import Path

import mb_utils as u

u.utf8_console()

OLLAMA_URL = os.environ.get("MEGABRAIN_OLLAMA", "http://localhost:11434")
MODELO = os.environ.get("MEGABRAIN_MODELO_SCORING", "qwen3.8-2bit-ptbr:latest")
IGNORAR_MTIME = {".git", ".mb-log", ".mb-backup", "__pycache__", "node_modules", ".venv"}


def evidencia_git(projeto: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(projeto), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return None
        diff = subprocess.run(["git", "-C", str(projeto), "diff", "HEAD", "--stat"],
                              capture_output=True, text=True, timeout=20).stdout
        log = subprocess.run(["git", "-C", str(projeto), "log", "-5", "--oneline"],
                             capture_output=True, text=True, timeout=20).stdout
        return f"git diff --stat:\n{diff or '(limpo)'}\n\núltimos commits:\n{log}"
    except Exception:
        return None


def evidencia_mtime(projeto: Path) -> str:
    agora = dt.datetime.now().timestamp()
    recentes = []
    for f in u.walk_files(projeto, ignorar=IGNORAR_MTIME):
        try:
            idade_h = (agora - f.stat().st_mtime) / 3600
        except OSError:
            continue
        if idade_h <= 24:
            recentes.append((idade_h, f.relative_to(projeto)))
    recentes.sort()
    if not recentes:
        return "nenhum arquivo modificado nas últimas 24h"
    linhas = [f"  {rel} (há {h:.1f}h)" for h, rel in recentes[:20]]
    extra = f"\n  … +{len(recentes) - 20} arquivo(s)" if len(recentes) > 20 else ""
    return "arquivos modificados nas últimas 24h:\n" + "\n".join(linhas) + extra


def perguntar_juiz(meta: str, evidencia: str) -> tuple[str, str] | None:
    """Retorna (veredito, motivo). None = juiz indisponível ou fora do formato.

    format=json do Ollama evita o eco de instrução que modelos 2-bit produzem
    com formatos de texto livre (visto no primeiro teste, 260819)."""
    prompt = (
        "Compare a META do projeto com as MUDANÇAS recentes e julgue se o "
        "trabalho está alinhado à meta.\n\n"
        f"META:\n{meta[:2000]}\n\n"
        f"MUDANÇAS:\n{evidencia[:2000]}\n\n"
        'Responda em JSON: {"veredito": "ALINHADO" ou "DESVIO", '
        '"motivo": "uma frase curta"}'
    )
    corpo = json.dumps({
        "model": MODELO, "prompt": prompt, "stream": False, "format": "json",
        "options": {"num_predict": 150, "temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=corpo,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        obj = json.loads(dados.get("response") or "{}")
        veredito = str(obj.get("veredito", "")).strip().upper()
        motivo = " ".join(str(obj.get("motivo", "")).split())[:200]
        if veredito in ("ALINHADO", "DESVIO"):
            return veredito, motivo or "(sem motivo)"
        return None
    except Exception:
        return None


def registrar(projeto: Path, veredito: str, motivo: str) -> None:
    linha = {
        "ts": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "agente": "mb-checar-meta",
        "modelo": MODELO,
        "evento": "meta-check",
        "prompt": None, "resposta": None, "arquivo": None,
        "cwd": str(projeto), "session_id": None,
        "extra": {"veredito": veredito, "motivo": motivo, "projeto": projeto.name},
    }
    pasta = projeto / ".mb-log"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        arq = pasta / f"eventos-{dt.datetime.now():%y%m%d}.jsonl"
        with arq.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--projeto", default=".")
    args = p.parse_args()

    projeto = Path(args.projeto).resolve()
    meta = u.safe_read_text(u.achar(projeto, "META.md"))
    if meta is None:
        print(f"ERRO: {projeto} não tem META.md — crie a partir de modelos/META.md (motor\\modelos\\META.md na central v7.1)")
        return 1

    evidencia = evidencia_git(projeto) or evidencia_mtime(projeto)
    resultado = perguntar_juiz(meta, evidencia)
    if resultado is None:
        print(f"juiz indisponível ou fora do formato (Ollama em {OLLAMA_URL}, "
              f"modelo {MODELO}) — sem veredito, não vou inventar um")
        registrar(projeto, "INDISPONIVEL", "sem resposta válida do juiz")
        return 3

    veredito, motivo = resultado
    registrar(projeto, veredito, motivo)
    print(f"{veredito} — {motivo}")
    return 0 if veredito == "ALINHADO" else 2


if __name__ == "__main__":
    raise SystemExit(main())

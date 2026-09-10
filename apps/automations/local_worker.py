"""Ollama local worker: sonda de saude e despacho HTTP para apps/automations.

Standalone e stdlib-only (mesma restricao do automations.py) para ser testado
sem subprocess/CLI. Ollama nao tem rate limit externo como Claude/Codex, entao
"pacing" aqui nao mede cota — mede disponibilidade: servidor de pe + modelo
presente. Ver memoria/estado/DECISOES.md 260909h para o desenho completo.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import urllib.error
import urllib.request

__all__ = ["LocalWorkerError", "health", "call"]


class LocalWorkerError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _settings(config):
    try:
        return config["providers"]["ollama"]
    except KeyError as exc:
        raise LocalWorkerError("Provider 'ollama' nao configurado em providers") from exc


def _request(method, url, timeout, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LocalWorkerError(f"Ollama respondeu HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LocalWorkerError("Ollama inacessivel") from exc
    except ValueError as exc:
        raise LocalWorkerError("Ollama devolveu corpo invalido") from exc


def health(config):
    """Snapshot no formato de Quotas.snapshot(): sem janela de cota (nao ha
    limite externo), o status vira sinal de disponibilidade — "ok" (servidor
    de pe, modelo presente), "pause" (servidor fora ou modelo ausente; nunca
    inventa 0% de uso), "NAO_MEDIDO" nao ocorre aqui porque qualquer falha de
    sonda ja e um "pause" conhecido, nao uma ausencia de leitura. Mesmo
    GET /api/tags que pets/backend/integrations.py:probe_local usa, mesma
    comparacao de nome (exato ou base antes do ':')."""
    settings = _settings(config)
    url = str(settings["local_url"]).rstrip("/") + "/api/tags"
    timeout = settings.get("health_timeout_seconds", 3)
    configured = str(settings["model"])
    try:
        body = _request("GET", url, timeout)
    except LocalWorkerError as exc:
        return {"provider": "ollama", "status": "pause", "windows": [], "fetched_at": _now(), "reason": str(exc)}
    names = [str(item.get("name") or "") for item in body.get("models", []) if isinstance(item, dict)]
    present = configured in names or any(name.split(":", 1)[0] == configured.split(":", 1)[0] for name in names)
    if not present:
        return {"provider": "ollama", "status": "pause", "windows": [], "fetched_at": _now(), "reason": "modelo ausente no Ollama"}
    return {"provider": "ollama", "status": "ok", "windows": [], "fetched_at": _now(), "reason": None}


def call(config, request, folder=None):
    """Despacha `request` ({"system", "schema", "input"}, mesmo envelope que
    Engine.call() monta para os provedores CLI) via /api/chat.

    num_ctx/num_predict/keep_alive sao SEMPRE explicitos, nunca omitidos: sem
    isso o Ollama herda o contexto global (131072 na maquina do <USUARIO>) e
    isso ja travou/atrasou resposta simples em outro projeto (licao 260825,
    memoria/nucleo/licoes-megabrain.md). "format": "json" restringe a
    decodificacao a JSON sintatico — o chamador (Engine.call) ainda valida o
    schema; isto so garante sintaxe, nao o contrato.
    """
    settings = _settings(config)
    url = str(settings["local_url"]).rstrip("/") + "/api/chat"
    timeout = settings.get("dispatch_timeout_seconds", 45)
    payload = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": request["system"]},
            {"role": "user", "content": json.dumps({"schema": request["schema"], "input": request["input"]}, ensure_ascii=False)},
        ],
        "format": "json",
        "stream": False,
        "keep_alive": settings.get("keep_alive", "60s"),
        "options": {
            "num_ctx": settings.get("context_tokens", 8192),
            "num_predict": settings.get("max_output_tokens", 512),
        },
    }
    if folder is not None:
        (folder / "ollama-payload.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    body = _request("POST", url, timeout, payload)
    if folder is not None:
        (folder / "ollama-response.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        value = json.loads(body["message"]["content"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LocalWorkerError("Ollama devolveu conteudo fora do contrato JSON") from exc
    return value, {"usage": {"prompt_eval_count": body.get("prompt_eval_count"), "eval_count": body.get("eval_count")}}

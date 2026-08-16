"""Funções base para provedores de IA usando apenas stdlib."""

import json
import urllib.error
import urllib.request


def http_post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    """Faz POST JSON e retorna dict; em erro, retorna dict com campo 'erro'."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
            return {"erro": f"HTTP {e.code}: {detail}"}
        except Exception:
            return {"erro": f"HTTP {e.code}: {body[:400]}"}
    except Exception as e:
        return {"erro": str(e)}


def http_get_json(url: str, headers: dict | None = None, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"erro": str(e)}


def estimar_tokens_por_palavras(texto: str) -> int:
    """Heurística simples: ~0.75 tokens por palavra em português."""
    return max(1, int(len(texto.split()) * 1.0))


def resposta_padrao(
    resposta: str,
    provider: str,
    modelo: str,
    tokens_entrada: int = 0,
    tokens_saida: int = 0,
    custo_estimado_usd: float = 0.0,
    erro: str | None = None,
) -> dict:
    return {
        "resposta": resposta,
        "provider": provider,
        "modelo_usado": modelo,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "custo_estimado_usd": custo_estimado_usd,
        "erro": erro,
    }


def historico_para_openai(historico: list[dict] | None, mensagem: str) -> list[dict]:
    msgs = []
    if historico:
        for h in historico:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant", "system"):
                msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": mensagem})
    return msgs

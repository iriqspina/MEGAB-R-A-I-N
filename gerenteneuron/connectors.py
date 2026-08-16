"""Testes de conectividade para cada provedor de IA."""

import precos
from providers.base import http_get_json, http_post_json


def _modelo_mais_barato(provider: str, padrao: str) -> str:
    """Usa o modelo mais barato do provedor para o ping de conectividade.

    Antes o teste da Anthropic carregava um ID fixo que divergia da tabela — o
    teste passava a falhar sozinho quando o modelo saía de linha, e o usuário
    lia isso como 'minha key está errada'.
    """
    candidatos = [m for m in precos.modelos() if m["provider"] == provider]
    if not candidatos:
        return padrao
    return min(candidatos, key=precos.custo_ponderado)["api_id"]


def testar_openai(config: dict) -> dict:
    key = config.get("key")
    base_url = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
    if not key:
        return {"ok": False, "erro": "API key não configurada"}
    url = f"{base_url}/models"
    data = http_get_json(url, {"Authorization": f"Bearer {key}"}, timeout=15)
    if "erro" in data:
        return {"ok": False, "erro": str(data["erro"])}
    if "data" in data:
        return {"ok": True, "modelos_disponiveis": len(data["data"])}
    return {"ok": False, "erro": "resposta inesperada"}


def testar_anthropic(config: dict) -> dict:
    key = config.get("key")
    base_url = config.get("base_url", "https://api.anthropic.com").rstrip("/")
    if not key:
        return {"ok": False, "erro": "API key não configurada"}
    url = f"{base_url}/v1/messages"
    payload = {
        "model": _modelo_mais_barato("anthropic", "claude-haiku-4-5"),
        "messages": [{"role": "user", "content": "diga 'ok'"}],
        "max_tokens": 10,
    }
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    data = http_post_json(url, headers, payload, timeout=15)
    if "erro" in data:
        return {"ok": False, "erro": str(data["erro"])}
    if "content" in data:
        return {"ok": True}
    return {"ok": False, "erro": "resposta inesperada"}


def testar_gemini(config: dict) -> dict:
    key = config.get("key")
    base_url = config.get("base_url", "https://generativelanguage.googleapis.com").rstrip("/")
    if not key:
        return {"ok": False, "erro": "API key não configurada"}
    modelo = _modelo_mais_barato("gemini", "gemini-3.1-flash-lite")
    url = f"{base_url}/v1beta/models/{modelo}:generateContent?key={key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "diga ok"}]}]}
    data = http_post_json(url, {}, payload, timeout=15)
    if "erro" in data:
        return {"ok": False, "erro": str(data["erro"])}
    if "candidates" in data:
        return {"ok": True}
    return {"ok": False, "erro": "resposta inesperada"}


def testar_moonshot(config: dict) -> dict:
    key = config.get("key")
    base_url = config.get("base_url", "https://api.moonshot.ai/v1").rstrip("/")
    if not key:
        return {"ok": False, "erro": "API key não configurada"}
    url = f"{base_url}/models"
    data = http_get_json(url, {"Authorization": f"Bearer {key}"}, timeout=15)
    if "erro" in data:
        return {"ok": False, "erro": str(data["erro"])}
    if "data" in data:
        return {"ok": True, "modelos_disponiveis": len(data["data"])}
    return {"ok": False, "erro": "resposta inesperada"}


def testar_ollama(config: dict) -> dict:
    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    url = f"{base_url}/api/tags"
    data = http_get_json(url, {}, timeout=10)
    if "erro" in data:
        return {"ok": False, "erro": str(data["erro"])}
    if "models" in data:
        return {"ok": True, "modelos_disponiveis": len(data["models"])}
    return {"ok": False, "erro": "resposta inesperada"}


def testar_todos(cfg: dict) -> dict:
    testers = {
        "openai": testar_openai,
        "anthropic": testar_anthropic,
        "gemini": testar_gemini,
        "moonshot": testar_moonshot,
        "ollama": testar_ollama,
    }
    resultados = {}
    for nome, fn in testers.items():
        info = cfg["providers"].get(nome, {})
        try:
            resultados[nome] = fn(info)
        except Exception as e:
            resultados[nome] = {"ok": False, "erro": str(e)}
    return resultados

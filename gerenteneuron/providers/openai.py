"""Provedor OpenAI e compatíveis (OpenAI, Moonshot)."""

from .base import http_post_json, estimar_tokens_por_palavras, estimar_custo, resposta_padrao, historico_para_openai


class OpenAIProvider:
    nome = "OpenAI"

    @staticmethod
    def send(mensagem: str, config: dict, historico: list | None = None, modelo: str = "gpt-5.6-terra", timeout: int = 120, max_tokens: int = 4096):
        key = config.get("key")
        base_url = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        if not key:
            return resposta_padrao("", "openai", modelo, erro="API key não configurada")

        url = f"{base_url}/chat/completions"
        payload = {
            "model": modelo,
            "messages": historico_para_openai(historico, mensagem),
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        data = http_post_json(url, {"Authorization": f"Bearer {key}"}, payload, timeout=timeout)
        if "erro" in data:
            return resposta_padrao("", "openai", modelo, erro=str(data["erro"]))

        try:
            texto = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tok_in = usage.get("prompt_tokens", estimar_tokens_por_palavras(mensagem))
            tok_out = usage.get("completion_tokens", estimar_tokens_por_palavras(texto))
            custo = estimar_custo("openai", modelo, tok_in, tok_out)
            return resposta_padrao(texto, "openai", modelo, tok_in, tok_out, custo)
        except Exception as e:
            return resposta_padrao("", "openai", modelo, erro=f"parse: {e}")

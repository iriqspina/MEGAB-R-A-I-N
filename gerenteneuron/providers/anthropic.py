"""Provedor Anthropic Claude."""

from .base import http_post_json, estimar_tokens_por_palavras, resposta_padrao, historico_para_openai


class AnthropicProvider:
    nome = "Anthropic"

    @staticmethod
    def send(mensagem: str, config: dict, historico: list | None = None, modelo: str = "claude-sonnet-4"):
        key = config.get("key")
        base_url = config.get("base_url", "https://api.anthropic.com").rstrip("/")
        if not key:
            return resposta_padrao("", "anthropic", modelo, erro="API key não configurada")

        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": modelo,
            "messages": historico_para_openai(historico, mensagem),
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        # Claude não aceita 'system' em messages; remove se presente.
        payload["messages"] = [m for m in payload["messages"] if m.get("role") != "system"]

        data = http_post_json(url, headers, payload)
        if "erro" in data:
            return resposta_padrao("", "anthropic", modelo, erro=str(data["erro"]))

        try:
            texto = data["content"][0]["text"]
            usage = data.get("usage", {})
            tok_in = usage.get("input_tokens", estimar_tokens_por_palavras(mensagem))
            tok_out = usage.get("output_tokens", estimar_tokens_por_palavras(texto))
            custo = estimar_custo(modelo, tok_in, tok_out)
            return resposta_padrao(texto, "anthropic", modelo, tok_in, tok_out, custo)
        except Exception as e:
            return resposta_padrao("", "anthropic", modelo, erro=f"parse: {e}")


def estimar_custo(modelo: str, tok_in: int, tok_out: int) -> float:
    tabela = {
        "claude-opus-4": (15.0, 75.0),
        "claude-sonnet-4": (3.0, 15.0),
    }
    pin, pout = tabela.get(modelo, (3.0, 15.0))
    return (tok_in * pin + tok_out * pout) / 1_000_000

"""Provedor OpenAI e compatíveis (OpenAI, Moonshot)."""

from .base import http_post_json, estimar_tokens_por_palavras, resposta_padrao, historico_para_openai


class OpenAIProvider:
    nome = "OpenAI"

    @staticmethod
    def send(mensagem: str, config: dict, historico: list | None = None, modelo: str = "gpt-5.6-terra"):
        key = config.get("key")
        base_url = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        if not key:
            return resposta_padrao("", "openai", modelo, erro="API key não configurada")

        url = f"{base_url}/chat/completions"
        payload = {
            "model": modelo,
            "messages": historico_para_openai(historico, mensagem),
            "temperature": 0.7,
        }
        data = http_post_json(url, {"Authorization": f"Bearer {key}"}, payload)
        if "erro" in data:
            return resposta_padrao("", "openai", modelo, erro=str(data["erro"]))

        try:
            texto = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tok_in = usage.get("prompt_tokens", estimar_tokens_por_palavras(mensagem))
            tok_out = usage.get("completion_tokens", estimar_tokens_por_palavras(texto))
            custo = estimar_custo(modelo, tok_in, tok_out)
            return resposta_padrao(texto, "openai", modelo, tok_in, tok_out, custo)
        except Exception as e:
            return resposta_padrao("", "openai", modelo, erro=f"parse: {e}")


def estimar_custo(modelo: str, tok_in: int, tok_out: int) -> float:
    # Preços de referência [ESTIMATIVA] — atualizar em pricing.json
    tabela = {
        "gpt-5.6-sol": (3.0, 15.0),
        "gpt-5.6-terra": (0.8, 4.0),
        "gpt-5.6-luna": (0.2, 0.8),
    }
    pin, pout = tabela.get(modelo, (0.8, 4.0))
    return (tok_in * pin + tok_out * pout) / 1_000_000

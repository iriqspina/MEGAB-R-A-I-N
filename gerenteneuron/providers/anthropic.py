"""Provedor Anthropic Claude."""

from .base import http_post_json, estimar_tokens_por_palavras, estimar_custo, resposta_padrao, historico_para_openai


class AnthropicProvider:
    nome = "Anthropic"

    @staticmethod
    def send(mensagem: str, config: dict, historico: list | None = None, modelo: str = "claude-sonnet-5", timeout: int = 120, max_tokens: int = 4096):
        key = config.get("key")
        base_url = config.get("base_url", "https://api.anthropic.com").rstrip("/")
        if not key:
            return resposta_padrao("", "anthropic", modelo, erro="API key não configurada")

        url = f"{base_url}/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
        msgs = historico_para_openai(historico, mensagem)
        # Claude recebe 'system' como parâmetro próprio, não dentro de messages.
        # Descartar essas mensagens (comportamento anterior) jogava fora a
        # instrução de sistema em vez de aplicá-la.
        sistema = "\n\n".join(m["content"] for m in msgs if m.get("role") == "system")
        payload = {
            "model": modelo,
            "messages": [m for m in msgs if m.get("role") != "system"],
            "max_tokens": max_tokens,
        }
        if sistema:
            payload["system"] = sistema

        data = http_post_json(url, headers, payload, timeout=timeout)
        if "erro" in data:
            return resposta_padrao("", "anthropic", modelo, erro=str(data["erro"]))

        try:
            texto = "\n\n".join(
                bloco["text"] for bloco in data.get("content", []) if bloco.get("type") == "text"
            )
            if not texto:
                raise ValueError("nenhum bloco de texto na resposta")
            usage = data.get("usage", {})
            tok_in = usage.get("input_tokens", estimar_tokens_por_palavras(mensagem))
            tok_out = usage.get("output_tokens", estimar_tokens_por_palavras(texto))
            custo = estimar_custo("anthropic", modelo, tok_in, tok_out)
            return resposta_padrao(texto, "anthropic", modelo, tok_in, tok_out, custo)
        except Exception as e:
            return resposta_padrao("", "anthropic", modelo, erro=f"parse: {e}")

"""Provedor Google Gemini."""

from .base import http_post_json, estimar_tokens_por_palavras, estimar_custo, resposta_padrao


class GeminiProvider:
    nome = "Google Gemini"

    @staticmethod
    def send(mensagem: str, config: dict, historico: list | None = None, modelo: str = "gemini-3.5-flash"):
        key = config.get("key")
        base_url = config.get("base_url", "https://generativelanguage.googleapis.com").rstrip("/")
        if not key:
            return resposta_padrao("", "gemini", modelo, erro="API key não configurada")

        contents = []
        if historico:
            for h in historico:
                role = "user" if h.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": mensagem}]})

        url = f"{base_url}/v1beta/models/{modelo}:generateContent?key={key}"
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7},
        }
        data = http_post_json(url, {}, payload)
        if "erro" in data:
            return resposta_padrao("", "gemini", modelo, erro=str(data["erro"]))

        try:
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
            uso = data.get("usageMetadata", {})
            tok_in = uso.get("promptTokenCount") or estimar_tokens_por_palavras(mensagem)
            tok_out = uso.get("candidatesTokenCount") or estimar_tokens_por_palavras(texto)
            custo = estimar_custo("gemini", modelo, tok_in, tok_out)
            return resposta_padrao(texto, "gemini", modelo, tok_in, tok_out, custo)
        except Exception as e:
            return resposta_padrao("", "gemini", modelo, erro=f"parse: {e}")

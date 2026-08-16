"""Provedor Ollama local."""

from .base import http_post_json, http_get_json, estimar_tokens_por_palavras, resposta_padrao, historico_para_openai


class OllamaProvider:
    nome = "Ollama local"

    @staticmethod
    def send(mensagem: str, config: dict, historico: list | None = None, modelo: str = "qwen3:8b"):
        base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
        url = f"{base_url}/api/chat"

        modelos_disponiveis = OllamaProvider.listar_modelos(config)
        candidatos = [modelo] + modelos_disponiveis

        for m in candidatos:
            payload = {
                "model": m,
                "messages": historico_para_openai(historico, mensagem),
                "stream": False,
                "options": {"temperature": 0.7},
            }
            data = http_post_json(url, {}, payload, timeout=120)
            if "erro" not in data:
                try:
                    texto = data["message"]["content"]
                    tok_in = estimar_tokens_por_palavras(mensagem)
                    tok_out = estimar_tokens_por_palavras(texto)
                    return resposta_padrao(texto, "ollama", m, tok_in, tok_out, 0.0)
                except Exception as e:
                    return resposta_padrao("", "ollama", m, erro=f"parse: {e}")
            erro_str = str(data["erro"])
            if "not found" not in erro_str.lower():
                return resposta_padrao("", "ollama", m, erro=erro_str)

        return resposta_padrao("", "ollama", modelo, erro="nenhum modelo local disponível respondeu")

    @staticmethod
    def listar_modelos(config: dict) -> list[str]:
        base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
        data = http_get_json(f"{base_url}/api/tags")
        if "erro" in data or "models" not in data:
            return []
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]

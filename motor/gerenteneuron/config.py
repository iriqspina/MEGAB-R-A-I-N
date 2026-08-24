"""Configuração do GerenteNeuron.

Credenciais vêm do cofre (vault/) ou de variáveis de ambiente / .env.
A lista de modelos vem de pricing.json — nunca hardcoded aqui.
"""

import os
from pathlib import Path

import precos


raiz_app = Path(__file__).resolve().parent

caminho_env = raiz_app / ".env"

# Chaves que o app aceita gravar/limpar. Fonte única para .env, cofre e limpeza.
CHAVES_CONHECIDAS = (
    "OPENAI_API_KEY", "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
    "GEMINI_API_KEY", "GEMINI_BASE_URL",
    "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL",
    "OLLAMA_BASE_URL", "GERENTENEURON_MODO",
)

BASE_URL_PADRAO = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "gemini": "https://generativelanguage.googleapis.com",
    "moonshot": "https://api.moonshot.ai/v1",
    "ollama": "http://localhost:11434",
}

NOME_PROVIDER = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Google Gemini",
    "moonshot": "Moonshot (Kimi)",
    "ollama": "Ollama local",
    "mock": "Mock (validação local)",
}

PROVIDERS_LOCAIS = {"ollama", "mock"}


def _carregar_dotenv():
    """Parser mínimo de .env — não requer python-dotenv."""
    if not caminho_env.exists():
        return
    try:
        for linha in caminho_env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            chave = chave.strip()
            valor = valor.strip().strip("'\"")
            if chave and chave not in os.environ:
                os.environ[chave] = valor
    except OSError:
        pass


def _env(chave: str, padrao=None) -> str | None:
    valor = os.environ.get(chave)
    if valor is None:
        return padrao
    return valor.strip().strip("'\"")


def carregar_config() -> dict:
    _carregar_dotenv()

    agrupado = precos.por_provider()
    providers = {}

    for pid in list(BASE_URL_PADRAO) + ["mock"]:
        local = pid in PROVIDERS_LOCAIS
        providers[pid] = {
            "nome": NOME_PROVIDER.get(pid, pid),
            "key": "mock" if pid == "mock" else _env(f"{pid.upper()}_API_KEY"),
            "base_url": _env(f"{pid.upper()}_BASE_URL", BASE_URL_PADRAO.get(pid)),
            "local": local,
            "modelos": [
                {
                    "id": m["api_id"],
                    "nome": m["nome"],
                    "classe": m["classe"],
                    "in": m["in"],
                    "out": m["out"],
                }
                for m in agrupado.get(pid, [])
            ],
        }

    return {
        "modo": _env("GERENTENEURON_MODO", "auto"),
        "providers": providers,
        "precos_verificado_em": precos.carregar().get("verificado_em"),
        "precos_aviso": precos.aviso_validade(),
    }

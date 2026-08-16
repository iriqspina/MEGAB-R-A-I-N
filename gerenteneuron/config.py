"""Configuração do GerenteNeuron.

Tudo é carregado de variáveis de ambiente ou do arquivo gerenteneuron/.env.
Nenhuma credencial é versionada.
"""

import os
from pathlib import Path


raiz_app = Path(__file__).resolve().parent

caminho_env = raiz_app / ".env"


def _carregar_dotenv():
    """Parser mínimo de .env — não requer python-dotenv."""
    if not caminho_env.exists():
        return
    try:
        for linha in caminho_env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            chave = chave.strip()
            valor = valor.strip().strip("'\"\"")
            if chave and chave not in os.environ:
                os.environ[chave] = valor
    except Exception:
        pass


def _env(chave: str, padrao=None) -> str | None:
    valor = os.environ.get(chave)
    if valor is None:
        return padrao
    return valor.strip().strip("'\"\"")


def carregar_config() -> dict:
    _carregar_dotenv()

    providers = {
        "openai": {
            "nome": "OpenAI",
            "key": _env("OPENAI_API_KEY"),
            "base_url": _env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "local": False,
            "modelos": [
                {"id": "gpt-5.6-sol", "nome": "GPT-5.6 Sol", "classe": "deep"},
                {"id": "gpt-5.6-terra", "nome": "GPT-5.6 Terra", "classe": "standard"},
                {"id": "gpt-5.6-luna", "nome": "GPT-5.6 Luna", "classe": "quick"},
            ],
        },
        "anthropic": {
            "nome": "Anthropic",
            "key": _env("ANTHROPIC_API_KEY"),
            "base_url": _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            "local": False,
            "modelos": [
                {"id": "claude-opus-4", "nome": "Claude Opus 4", "classe": "deep"},
                {"id": "claude-sonnet-4", "nome": "Claude Sonnet 4", "classe": "standard"},
            ],
        },
        "gemini": {
            "nome": "Google Gemini",
            "key": _env("GEMINI_API_KEY"),
            "base_url": _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
            "local": False,
            "modelos": [
                {"id": "gemini-2.5-pro", "nome": "Gemini 2.5 Pro", "classe": "deep"},
                {"id": "gemini-2.5-flash", "nome": "Gemini 2.5 Flash", "classe": "standard"},
            ],
        },
        "moonshot": {
            "nome": "Moonshot (Kimi)",
            "key": _env("MOONSHOT_API_KEY"),
            "base_url": _env("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
            "local": False,
            "modelos": [
                {"id": "kimi-k2", "nome": "Kimi K2", "classe": "quick"},
                {"id": "kimi-k1.5", "nome": "Kimi K1.5", "classe": "standard"},
            ],
        },
        "ollama": {
            "nome": "Ollama local",
            "key": None,
            "base_url": _env("OLLAMA_BASE_URL", "http://localhost:11434"),
            "local": True,
            "modelos": [
                {"id": "qwen3:8b", "nome": "Qwen 3 8B local", "classe": "quick"},
            ],
        },
        "mock": {
            "nome": "Mock (validação local)",
            "key": "mock",
            "base_url": None,
            "local": True,
            "modelos": [
                {"id": "mock/validacao-local", "nome": "Mock local", "classe": "quick"},
            ],
        },
    }

    return {
        "modo": _env("GERENTENEURON_MODO", "auto"),
        "providers": providers,
    }

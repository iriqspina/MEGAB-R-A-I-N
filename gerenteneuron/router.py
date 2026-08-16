"""Roteador de modelo por custo/capacidade e estratégia de uso.

Estratégias:
- local_code: código, debugging, refactor → Ollama local primeiro (economia).
- cheap: perguntas curtas, extração, formatação → modelo pago barato.
- standard: explanação, decisão moderada, síntese → modelo pago equilibrado.
- deep: arquitetura, auditoria, decisão crítica → modelo pago forte.
"""

from config import carregar_config
from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.gemini import GeminiProvider
from providers.moonshot import MoonshotProvider
from providers.ollama import OllamaProvider
from providers.mock import MockProvider


# Mapa de estratégia para fila de (provider_id, modelo_id), do mais barato/eficiente ao fallback.
MODELOS_POR_ESTRATEGIA = {
    "local_code": [
        ("ollama", "qwen3:8b"),
        ("moonshot", "kimi-k2"),
        ("openai", "gpt-5.6-luna"),
    ],
    "cheap": [
        ("ollama", "qwen3:8b"),
        ("moonshot", "kimi-k2"),
        ("openai", "gpt-5.6-luna"),
        ("gemini", "gemini-2.5-flash"),
    ],
    "standard": [
        ("moonshot", "kimi-k1.5"),
        ("openai", "gpt-5.6-terra"),
        ("anthropic", "claude-sonnet-4"),
        ("gemini", "gemini-2.5-pro"),
    ],
    "deep": [
        ("openai", "gpt-5.6-sol"),
        ("anthropic", "claude-opus-4"),
        ("gemini", "gemini-2.5-pro"),
    ],
}

# Boost: próximo nível acima para quando o usuário acha a resposta fraca.
BOOST_DE = {
    "local_code": "standard",
    "cheap": "standard",
    "standard": "deep",
    "deep": "deep",
}

PALAVRAS_DEEP = {
    "arquitetura", "auditar", "auditoria", "refatorar", "refatoração", "decidir",
    "decisão", "comparar", "comparação", "design system", "estrutura", "risco",
    "segurança", "review", "revisar", "slop", "critico", "crítico", "final",
    "definir", "definição", "escolher", "escolha",
}

PALAVRAS_CODE = {
    "codigo", "código", "debug", "debugar", "refactor", "funcao", "função",
    "script", "python", "javascript", "html", "css", "api", "endpoint", "erro",
    "exception", "traceback", "teste", "testar", "implementar", "bug",
}

PALAVRAS_CHEAP = {
    "resumir", "sintetizar", "síntese", "extrair", "formatar", "listar",
    "enumerar", "traduzir", "defina", "o que é", "quem foi", "quando",
}


def classificar_estrategia(mensagem: str) -> str:
    texto = mensagem.lower()
    palavras = set(texto.split())
    tem_deep = len(palavras & PALAVRAS_DEEP) >= 1
    tem_code = len(palavras & PALAVRAS_CODE) >= 1
    tem_cheap = len(palavras & PALAVRAS_CHEAP) >= 1
    comprimento = len(mensagem)
    linhas = mensagem.count("\n")

    if tem_deep or comprimento > 1200 or (linhas > 8 and comprimento > 600):
        return "deep"
    if tem_code:
        return "local_code"
    if tem_cheap and comprimento < 400:
        return "cheap"
    if comprimento > 250 or "\n" in mensagem:
        return "standard"
    return "cheap"


def _provider_classe(provider_id: str):
    return {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "moonshot": MoonshotProvider,
        "ollama": OllamaProvider,
        "mock": MockProvider,
    }.get(provider_id)


def _disponivel(provider_id: str, info: dict) -> bool:
    if provider_id == "mock":
        return True
    if info.get("local"):
        return True
    return bool(info.get("key"))


def _candidatos(cfg: dict, estrategia: str):
    for provider_id, modelo_id in MODELOS_POR_ESTRATEGIA.get(estrategia, MODELOS_POR_ESTRATEGIA["standard"]):
        info = cfg["providers"].get(provider_id)
        if info and _disponivel(provider_id, info):
            yield provider_id, modelo_id
    yield "mock", "mock/validacao-local"


def _parse_modelo(modelo_str: str):
    if "/" not in modelo_str:
        return None, None
    provider_id, modelo_id = modelo_str.split("/", 1)
    return provider_id, modelo_id


def _executar_fila(mensagem: str, cfg: dict, fila: list[tuple], modo: str, estrategia: str | None) -> dict:
    ultimo_erro = "nenhum candidato disponível"
    for provider_id, modelo_id in fila:
        info = cfg["providers"].get(provider_id)
        provider_cls = _provider_classe(provider_id)
        if not provider_cls or not info:
            continue

        resultado = provider_cls.send(mensagem, info, None, modelo_id)
        if not resultado.get("erro"):
            resultado["modo"] = modo
            resultado["estrategia"] = estrategia
            return resultado
        ultimo_erro = resultado.get("erro", "erro desconhecido")

    return {
        "resposta": f"Nenhum modelo conseguiu responder. Último erro: {ultimo_erro}",
        "provider": "nenhum",
        "modelo_usado": "nenhum",
        "custo_estimado_usd": 0.0,
        "tokens_entrada": 0,
        "tokens_saida": 0,
        "erro": ultimo_erro,
        "modo": modo,
        "estrategia": estrategia,
    }


def route(mensagem: str, modo: str = "auto", modelo_forcado: str = "auto", historico: list | None = None, boost: bool = False) -> dict:
    cfg = carregar_config()
    estrategia = classificar_estrategia(mensagem)

    if modo == "manual" and modelo_forcado and modelo_forcado != "auto":
        provider_id, modelo_id = _parse_modelo(modelo_forcado)
        fila = [(provider_id, modelo_id)] if provider_id else []
    else:
        if boost:
            estrategia = BOOST_DE.get(estrategia, "deep")
        fila = list(_candidatos(cfg, estrategia))

    return _executar_fila(mensagem, cfg, fila, modo, estrategia)


def boost_route(resposta_anterior: dict, mensagem: str) -> dict:
    """Reenvia a mensagem para o próximo nível de capacidade."""
    estrategia_atual = resposta_anterior.get("estrategia", "standard")
    estrategia_nova = BOOST_DE.get(estrategia_atual, "deep")
    return route(mensagem, modo="auto", modelo_forcado="auto", boost=True)

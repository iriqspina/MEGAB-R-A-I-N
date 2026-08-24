"""Roteador de modelo — v7.0 (260824): triagem por custo DESLIGADA.

Decisão do <USUARIO> (DECISOES.md 260824b): o Neuron observa, não escolhe
modelo. Toda mensagem vai pra classe de ponta ("deep"); a escolha fina de
modelo é do processamento normal da sessão. O classificador antigo fica
guardado abaixo, desligado, pra era das faixas. Cada resposta vira telemetria
em ../.mb-log/neuron.jsonl (modelo, custo, tokens, duração).

Texto original do roteador por custo/capacidade:

Estratégias:
- local_code: código, debug, refactor → modelo local primeiro (custo zero).
- cheap: pergunta curta, extração, formatação → classe quick.
- standard: explanação, decisão moderada, síntese → classe standard.
- deep: arquitetura, auditoria, decisão crítica → classe deep.

A ordem dentro de cada estratégia é DERIVADA de pricing.json (do mais barato ao
mais caro), não escrita à mão. Trocar de modelo é editar pricing.json.
"""

import re
import unicodedata

import precos
from config import carregar_config
from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.gemini import GeminiProvider
from providers.moonshot import MoonshotProvider
from providers.ollama import OllamaProvider
from providers.mock import MockProvider


CLASSE_DA_ESTRATEGIA = {
    "local_code": "standard",
    "cheap": "quick",
    "standard": "standard",
    "deep": "deep",
}

# Boost: próximo nível acima para quando o usuário acha a resposta fraca.
BOOST_DE = {
    "local_code": "standard",
    "cheap": "standard",
    "standard": "deep",
    "deep": "deep",
}

PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "moonshot": MoonshotProvider,
    "ollama": OllamaProvider,
    "mock": MockProvider,
}

TERMOS_DEEP = (
    "arquitetura", "auditar", "auditoria", "refatorar", "refatoracao", "decidir",
    "decisao", "comparar", "comparacao", "design system", "estrutura", "risco",
    "seguranca", "review", "revisar", "slop", "critico", "final", "definir",
    "definicao", "escolher", "escolha", "trade-off", "tradeoff",
)

TERMOS_CODE = (
    "codigo", "debug", "debugar", "refactor", "funcao", "script", "python",
    "javascript", "html", "css", "api", "endpoint", "erro", "exception",
    "traceback", "teste", "testar", "implementar", "bug", "stacktrace",
)

TERMOS_CHEAP = (
    "resumir", "sintetizar", "sintese", "extrair", "formatar", "listar",
    "enumerar", "traduzir", "defina", "o que e", "quem foi", "quando",
)


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento, pontuação virando espaço.

    Sem isso, 'auditoria?' não casava com 'auditoria' e nenhum termo de duas
    palavras ('design system', 'o que é') casava nunca — o classificador tinha
    regras que jamais disparavam.
    """
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\-\s]", " ", texto)
    return " " + re.sub(r"\s+", " ", texto).strip() + " "


def _contem(texto_norm: str, termos) -> bool:
    return any(f" {t} " in texto_norm for t in termos)


def classificar_estrategia(mensagem: str) -> str:
    norm = _normalizar(mensagem)
    comprimento = len(mensagem)
    linhas = mensagem.count("\n")

    if _contem(norm, TERMOS_DEEP) or comprimento > 1200 or (linhas > 8 and comprimento > 600):
        return "deep"
    if _contem(norm, TERMOS_CODE):
        return "local_code"
    if _contem(norm, TERMOS_CHEAP) and comprimento < 400:
        return "cheap"
    if comprimento > 250 or "\n" in mensagem:
        return "standard"
    return "cheap"


def _disponivel(provider_id: str, info: dict) -> bool:
    if provider_id == "mock" or info.get("local"):
        return True
    return bool(info.get("key"))


def montar_fila(cfg: dict, estrategia: str) -> list[tuple[str, str]]:
    """Fila de candidatos, do mais barato ao mais caro, só com provedor utilizável."""
    classe = CLASSE_DA_ESTRATEGIA.get(estrategia, "standard")

    bruta: list[tuple[str, str]] = []
    if estrategia == "local_code":
        bruta.extend(precos.modelos_locais())
    bruta.extend(precos.fila_por_classe(classe))

    fila: list[tuple[str, str]] = []
    for provider_id, modelo_id in bruta:
        info = cfg["providers"].get(provider_id)
        if not info or not _disponivel(provider_id, info):
            continue
        if (provider_id, modelo_id) not in fila:
            fila.append((provider_id, modelo_id))

    fila.append(("mock", "mock/validacao-local"))
    return fila


def _parse_modelo(modelo_str: str) -> tuple[str | None, str | None]:
    if not modelo_str or "/" not in modelo_str:
        return None, None
    provider_id, modelo_id = modelo_str.split("/", 1)
    return provider_id, modelo_id


def _executar_fila(mensagem, cfg, fila, modo, estrategia, historico=None) -> dict:
    ultimo_erro = "nenhum candidato disponível"
    tentativas = []

    for provider_id, modelo_id in fila:
        info = cfg["providers"].get(provider_id)
        provider_cls = PROVIDERS.get(provider_id)
        if not provider_cls or not info:
            continue

        resultado = provider_cls.send(mensagem, info, historico, modelo_id)
        if not resultado.get("erro"):
            resultado["modo"] = modo
            resultado["estrategia"] = estrategia
            resultado["tentativas"] = tentativas
            return resultado

        ultimo_erro = resultado.get("erro", "erro desconhecido")
        tentativas.append({"modelo": f"{provider_id}/{modelo_id}", "erro": ultimo_erro})

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
        "tentativas": tentativas,
    }


def route(
    mensagem: str,
    modo: str = "auto",
    modelo_forcado: str = "auto",
    historico: list | None = None,
    boost: bool = False,
) -> dict:
    cfg = carregar_config()
    # v7.0 (260824): triagem desligada — sempre classe de ponta. O
    # classificar_estrategia() fica guardado pra quando as faixas voltarem.
    estrategia = "deep"

    if modo == "manual" and modelo_forcado and modelo_forcado != "auto":
        provider_id, modelo_id = _parse_modelo(modelo_forcado)
        fila = [(provider_id, modelo_id)] if provider_id else []
        if provider_id and provider_id not in PROVIDERS:
            fila = []
    else:
        if boost:
            estrategia = BOOST_DE.get(estrategia, "deep")
        fila = montar_fila(cfg, estrategia)

    import time as _t
    _ini = _t.time()
    resultado = _executar_fila(mensagem, cfg, fila, modo, estrategia, historico)
    _telemetria(resultado, _t.time() - _ini)
    return resultado


def _telemetria(resultado: dict, duracao_s: float) -> None:
    """Anexa 1 linha JSONL em ../.mb-log/neuron.jsonl — dado bruto local
    (spec 03_docs/260824_spec-fase2.md §4). Valores nunca generalizados;
    nada sobe pra lugar nenhum sem opt-in. Falha em silêncio."""
    try:
        import datetime as _dt, json as _j
        from pathlib import Path as _P
        log = _P(__file__).resolve().parent.parent / ".mb-log" / "neuron.jsonl"
        log.parent.mkdir(exist_ok=True)
        linha = {
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
            "modelo": resultado.get("modelo_usado"),
            "provider": resultado.get("provider"),
            "estrategia": resultado.get("estrategia"),
            "modo": resultado.get("modo"),
            "custo_usd": resultado.get("custo_estimado_usd"),
            "tokens_in": resultado.get("tokens_entrada"),
            "tokens_out": resultado.get("tokens_saida"),
            "duracao_s": round(duracao_s, 2),
            "erro": bool(resultado.get("erro")),
        }
        with log.open("a", encoding="utf-8") as f:
            f.write(_j.dumps(linha, ensure_ascii=False) + "\n")
    except Exception:
        pass

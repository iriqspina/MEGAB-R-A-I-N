"""Tabela de modelos e preços do GerenteNeuron.

Fonte única: pricing.json. Antes disso, cada provider carregava a própria
tabela de preços — quatro tabelas divergentes, todas desatualizadas, e a fila
do roteador era hardcoded em vez de derivada do preço. Aqui a fila é ordenada
pelo custo real, então corrigir pricing.json corrige o roteamento.
"""

import json
from datetime import date
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
PRICING_FILE = RAIZ / "pricing.json"

# Peso do custo de saída na ordenação. Resposta de chat gera muito mais token
# de saída que de entrada, então o preço de output domina a conta real.
PESO_SAIDA = 0.75

_cache: dict | None = None


def carregar(forcar: bool = False) -> dict:
    global _cache
    if _cache is not None and not forcar:
        return _cache
    if not PRICING_FILE.exists():
        _cache = {"verificado_em": None, "revalidar_em_dias": 60, "modelos": [], "notas": []}
        return _cache
    _cache = json.loads(PRICING_FILE.read_text(encoding="utf-8"))
    _cache.setdefault("modelos", [])
    return _cache


def modelos() -> list[dict]:
    return carregar()["modelos"]


def buscar(provider: str, api_id: str) -> dict | None:
    for m in modelos():
        if m["provider"] == provider and m["api_id"] == api_id:
            return m
    return None


def custo_ponderado(m: dict) -> float:
    """Custo comparável entre modelos, ponderando entrada e saída."""
    return m["in"] * (1 - PESO_SAIDA) + m["out"] * PESO_SAIDA


def custo(provider: str, api_id: str, tokens_entrada: int, tokens_saida: int) -> float:
    """Custo estimado em USD. Retorna 0.0 para modelo desconhecido ou local."""
    m = buscar(provider, api_id)
    if m is None:
        return 0.0
    fator = m.get("fator_token", 1.0)
    tin = tokens_entrada * fator
    tout = tokens_saida * fator
    return (tin * m["in"] + tout * m["out"]) / 1_000_000


def fila_por_classe(classe: str, apenas_local: bool = False) -> list[tuple[str, str]]:
    """Modelos daquela classe, do mais barato ao mais caro."""
    cands = [m for m in modelos() if m["classe"] == classe and m["provider"] != "mock"]
    if apenas_local:
        cands = [m for m in cands if m.get("fonte") == "local"]
    cands.sort(key=custo_ponderado)
    return [(m["provider"], m["api_id"]) for m in cands]


def modelos_locais() -> list[tuple[str, str]]:
    locais = [m for m in modelos() if m.get("fonte") == "local" and m["provider"] != "mock"]
    locais.sort(key=custo_ponderado)
    return [(m["provider"], m["api_id"]) for m in locais]


def por_provider() -> dict[str, list[dict]]:
    agrupado: dict[str, list[dict]] = {}
    for m in sorted(modelos(), key=custo_ponderado):
        agrupado.setdefault(m["provider"], []).append(m)
    return agrupado


def idade_em_dias(hoje: date | None = None) -> int | None:
    """Dias desde a última verificação da tabela. None se nunca verificada."""
    cfg = carregar()
    bruto = cfg.get("verificado_em")
    if not bruto:
        return None
    try:
        verificado = date.fromisoformat(bruto)
    except ValueError:
        return None
    return ((hoje or date.today()) - verificado).days


def esta_vencida(hoje: date | None = None) -> bool:
    idade = idade_em_dias(hoje)
    if idade is None:
        return True
    return idade > carregar().get("revalidar_em_dias", 60)


def aviso_validade(hoje: date | None = None) -> str | None:
    """Texto de aviso quando a tabela de preços passou da validade."""
    if not esta_vencida(hoje):
        return None
    idade = idade_em_dias(hoje)
    if idade is None:
        return "pricing.json nunca foi verificado — o custo exibido é chute."
    return (
        f"pricing.json foi verificado há {idade} dias. Preço de modelo muda; "
        f"rode 'python mb-modelos.py --conferir' antes de confiar no custo."
    )

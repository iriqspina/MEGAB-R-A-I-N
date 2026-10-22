"""Estado de conta (ativo/cancelado/encerrado) lido do orçamento compartilhado.

O widget NUNCA escreve ``estados_conta``: a chave vive solta no
``dados/orcamento_ia.json`` justamente porque ``budget_status.write``
substitui a chave inteira do provedor a cada poll (revisão 261020, R1).
Legado ``<provider>_cancelado`` continua valendo como fonte.
"""

from __future__ import annotations

import json
import time
from typing import Any

_ESTADOS_VALIDOS = {"ativo", "cancelado", "encerrado", "expirado", "nao_verificado"}
_CACHE_SEGUNDOS = 60
_cache: dict[str, Any] = {"lido_em": 0.0, "dados": {}}


def ler_estados(caminho) -> dict[str, dict]:
    """Lê ``estados_conta`` + chaves legadas ``<p>_cancelado`` do JSON."""
    agora = time.time()
    if agora - _cache["lido_em"] < _CACHE_SEGUNDOS:
        return _cache["dados"]
    dados: dict[str, dict] = {}
    try:
        raw = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = None
    if isinstance(raw, dict):
        novos = raw.get("estados_conta")
        if isinstance(novos, dict):
            for provedor, estado in novos.items():
                if isinstance(estado, dict) and estado.get("estado") in _ESTADOS_VALIDOS:
                    dados[str(provedor)] = estado
        for chave, valor in raw.items():
            # Legado: codex_gpt2_cancelado -> estados_conta["codex_gpt2"].
            if isinstance(chave, str) and chave.endswith("_cancelado") and isinstance(valor, dict):
                provedor = chave[: -len("_cancelado")]
                if provedor not in dados:
                    dados[provedor] = {
                        "estado": "cancelado",
                        "acesso_ate": valor.get("acesso_ate"),
                        "observacao": valor.get("observacao", ""),
                    }
    _cache["lido_em"] = agora
    _cache["dados"] = dados
    return dados


def estado_de(provider_id: str, caminho=None) -> dict | None:
    """Estado da conta do provedor, ou ``None`` quando nada declarado."""
    if caminho is None:
        from . import paths

        caminho = paths.BUDGET_STATUS_PATH
    estado = ler_estados(caminho).get(provider_id)
    if not estado:
        return None
    return {
        "estado": estado.get("estado"),
        "acesso_ate": estado.get("acesso_ate"),
        "observacao": str(estado.get("observacao") or "")[:240],
        "api_respondeu_em": estado.get("api_respondeu_em"),
    }


def texto_curto(estado: dict) -> str:
    """'CANCELADO · até 16/10' — uma linha pro hint do card."""
    rotulo = {
        "cancelado": "CANCELADO",
        "encerrado": "ENCERRADO",
        "expirado": "EXPIRADO",
        "nao_verificado": "NÃO VERIFICADO",
    }.get(estado.get("estado"), str(estado.get("estado")).upper())
    acesso = estado.get("acesso_ate")
    if acesso:
        try:
            from datetime import datetime

            data = datetime.fromisoformat(str(acesso).replace("Z", "+00:00"))
            rotulo += f" · até {data:%d/%m}"
        except (ValueError, TypeError):
            pass
    return rotulo

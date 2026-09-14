"""Ritmo adaptativo de cota — quanto dá pra gastar por hora/dia sem estourar
antes do próximo reset.

Contrato:

    window_pacing(window, now) -> {
        "status":              "ok" | "desacelerar" | "pause" | "NAO_MEDIDO",
        "used_percent":        float,
        "remaining_percent":   float,
        "hours_to_reset":      float,
        "elapsed_fraction":    float,   # 0–1, quanto da janela já passou
        "ideal_used_by_now":   float,   # uso esperado se o gasto fosse uniforme
        "ahead_by":            float,   # used_percent - ideal_used_by_now
        "target_per_hour":     float,   # ritmo seguro dali pra frente
        "target_per_business_day": float | None,  # só quando a janela é >= 1 dia
        "reason":              str,     # motivo curto quando NAO_MEDIDO
    }

Recalcula do zero a cada leitura — não guarda histórico. É isso que faz "reduzir
o orçamento restante quando atrasado" sair de graça da própria fórmula: uma
leitura tardia já chega com `remaining_percent` menor e o mesmo tempo restante,
então `target_per_hour` cai sozinho na leitura seguinte.

``pause`` aqui é só o espelho informativo do corte de verdade que já existe em
``apps/automations/automations.py::Engine.call()`` (>=100% de uso) — este módulo
nunca bloqueia despacho sozinho.

Só stdlib, sem import de ``providers`` nem de Qt — consumido tanto pelo motor
de orquestração quanto pela UI do widget, direto do dicionário de janela já no
formato do contrato (``id``, ``used_percent``, ``resets_at`` ISO UTC com offset
explícito, ``duration_minutes``).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

__all__ = ["window_pacing", "provider_pacing", "STATUS_RANK"]

DEFAULT_BUSINESS_DAYS = 6
DEFAULT_DECELERATE_THRESHOLD = 60.0

# pior status primeiro — usado tanto pra status agregado quanto pra desempate
# em escolha automática de provedor (ok é o melhor).
STATUS_RANK: dict[str, int] = {"ok": 0, "NAO_MEDIDO": 1, "desacelerar": 2, "pause": 3}


def _not_measured(reason: str) -> dict[str, Any]:
    return {
        "status": "NAO_MEDIDO",
        "used_percent": None,
        "remaining_percent": None,
        "hours_to_reset": None,
        "elapsed_fraction": None,
        "ideal_used_by_now": None,
        "ahead_by": None,
        "target_per_hour": None,
        "target_per_business_day": None,
        "reason": reason,
    }


def _parse_resets_at(value: Any) -> datetime | None:
    """``resets_at`` já sai de ``providers.py`` como ISO UTC com offset
    explícito — não precisa tolerar ``Z`` nem fração de segundo longa aqui."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def window_pacing(
    window: dict[str, Any],
    now: datetime | None = None,
    *,
    business_days: int = DEFAULT_BUSINESS_DAYS,
    decelerate_threshold: float = DEFAULT_DECELERATE_THRESHOLD,
) -> dict[str, Any]:
    """Ritmo de uma janela (5h, semanal, ...). Ver contrato no topo do módulo."""
    now = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)

    used_percent = window.get("used_percent")
    if used_percent is None or isinstance(used_percent, bool) or not isinstance(used_percent, (int, float)):
        return _not_measured("sem used_percent")
    used_percent = float(used_percent)
    if not math.isfinite(used_percent):
        return _not_measured("used_percent não finito")

    resets_at = _parse_resets_at(window.get("resets_at"))
    if resets_at is None:
        return _not_measured("sem resets_at")

    seconds_to_reset = (resets_at - now).total_seconds()
    if seconds_to_reset <= 0:
        # resets_at no passado pelo nosso relógio: a janela real já rolou e o
        # dado que temos está desatualizado, não dá pra confiar no ritmo.
        return _not_measured("resets_at no passado")
    hours_to_reset = seconds_to_reset / 3600.0

    duration_minutes = window.get("duration_minutes")
    duration_is_fallback = not isinstance(duration_minutes, (int, float)) or isinstance(duration_minutes, bool) or duration_minutes <= 0
    if duration_is_fallback:
        duration_minutes = business_days * 1440

    total_seconds = duration_minutes * 60.0
    window_start = resets_at - timedelta(seconds=total_seconds)
    elapsed_seconds = (now - window_start).total_seconds()
    elapsed_fraction = min(1.0, max(0.0, elapsed_seconds / total_seconds)) if total_seconds > 0 else 1.0

    remaining_percent = 100.0 - used_percent
    ideal_used_by_now = elapsed_fraction * 100.0
    ahead_by = used_percent - ideal_used_by_now
    target_per_hour = remaining_percent / hours_to_reset

    # Só exibimos um número por dia quando a duração real da janela é
    # conhecida — com duração adivinhada (fallback), o dado ainda alimenta o
    # status (ok/desacelerar), mas mostrar uma cifra por dia inventaria
    # precisão que não existe (achado da revisão Fable 5.1, 260909).
    target_per_business_day = None
    if duration_minutes >= 1440 and not duration_is_fallback:
        # equivale a (1 - elapsed_fraction) * (duration_minutes / 1440); usar
        # hours_to_reset direto evita divergir da mesma conta em duas formas.
        business_days_remaining = hours_to_reset / 24.0
        if business_days_remaining > 0:
            target_per_business_day = remaining_percent / business_days_remaining

    if used_percent >= 100.0:
        status = "pause"
    elif used_percent >= decelerate_threshold and ahead_by > 0:
        status = "desacelerar"
    else:
        status = "ok"

    return {
        "status": status,
        "used_percent": round(used_percent, 1),
        "remaining_percent": round(remaining_percent, 1),
        "hours_to_reset": round(hours_to_reset, 2),
        "elapsed_fraction": round(elapsed_fraction, 4),
        "ideal_used_by_now": round(ideal_used_by_now, 1),
        "ahead_by": round(ahead_by, 1),
        "target_per_hour": round(target_per_hour, 2),
        "target_per_business_day": round(target_per_business_day, 2) if target_per_business_day is not None else None,
        "reason": "",
    }


def provider_pacing(
    snapshot: dict[str, Any],
    now: datetime | None = None,
    *,
    business_days: int = DEFAULT_BUSINESS_DAYS,
    decelerate_threshold: float = DEFAULT_DECELERATE_THRESHOLD,
) -> dict[str, Any]:
    """Ritmo de todas as janelas de um snapshot de ``providers.fetch_provider``.

    Seguro de chamar mesmo quando ``snapshot["status"] != "ok"`` — devolve
    NAO_MEDIDO em vez de levantar, porque ausência de leitura não é uma
    condição excepcional aqui, é o caso normal (rate limit, token vencido).
    """
    now = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    windows_out: dict[str, dict[str, Any]] = {}

    if not isinstance(snapshot, dict) or snapshot.get("status") != "ok":
        return {"provider": snapshot.get("provider") if isinstance(snapshot, dict) else None, "status": "NAO_MEDIDO", "windows": {}}

    for win in snapshot.get("windows") or []:
        if not isinstance(win, dict) or not win.get("id"):
            continue
        windows_out[str(win["id"])] = window_pacing(
            win, now, business_days=business_days, decelerate_threshold=decelerate_threshold
        )

    worst_status = "NAO_MEDIDO"
    if windows_out:
        worst_status = max(windows_out.values(), key=lambda w: STATUS_RANK.get(w["status"], 1))["status"]

    return {"provider": snapshot.get("provider"), "status": worst_status, "windows": windows_out}

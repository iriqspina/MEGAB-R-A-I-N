import re
from datetime import datetime, timezone


def parse_iso(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def age_seconds(iso_value):
    dt = parse_iso(iso_value)
    if dt is None:
        return None
    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    return max(0.0, delta.total_seconds())


def age_label(iso_value) -> str:
    seconds = age_seconds(iso_value)
    if seconds is None:
        return "sem leitura"
    seconds = int(seconds)
    if seconds < 60:
        return "agora"
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 48:
        return f"há {hours} h"
    days = hours // 24
    return f"há {days} d"


def reset_label(iso_value) -> str:
    dt = parse_iso(iso_value)
    if dt is None:
        return "renovação desconhecida"
    delta = dt.astimezone(timezone.utc) - datetime.now(timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "renova em breve"
    minutes = seconds // 60
    if minutes < 60:
        return f"renova em {minutes} min"
    hours = minutes // 60
    if hours < 48:
        return f"renova em {hours} h"
    days = hours // 24
    return f"renova em {days} d"


_WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def reset_label_absolute(iso_value, now: datetime | None = None) -> str:
    """"renova hoje 21:58" / "renova amanhã 09:00" / "renova sáb 13:19" (hora local)."""
    dt = parse_iso(iso_value)
    if dt is None:
        return "renovação desconhecida"
    now = now or datetime.now(timezone.utc)
    if dt.astimezone(timezone.utc) <= now.astimezone(timezone.utc):
        return "renova em breve"
    local, today = dt.astimezone(), now.astimezone().date()
    days = (local.date() - today).days
    if days == 0:
        day = "hoje"
    elif days == 1:
        day = "amanhã"
    elif days < 7:
        day = _WEEKDAYS[local.weekday()]
    else:
        day = f"{local:%d/%m}"
    return f"renova {day} {local:%H:%M}"


def percent_label(value) -> str:
    if value is None:
        return "—"
    # 0,3 % arredondado vira "0%", que lê como "nada usado" — e não é.
    if 0 < value < 0.5:
        return "<1%"
    return f"{round(value)}%"


_DURATION_SUFFIX = re.compile(r"^\d+ (h|d|min)$")
_DURATION_NAMES = {"5 h": "Sessão", "7 d": "Semana"}


def friendly_window_label(label) -> str:
    """Rótulo de janela para gente, não para log.

    A linha do provedor já diz de quem é a cota, então o prefixo de modelo cai:
    "codex · 7 d" -> "Semana"; "GPT-5.3-Codex-Spark · 5 h" -> "Sessão".
    Sufixo que não é duração é informação ("Semana · Fable") e fica.
    """
    if not label:
        return ""
    text = str(label)
    parts = [part.strip() for part in text.split(" · ")]
    if len(parts) >= 2 and _DURATION_SUFFIX.match(parts[-1]):
        return _DURATION_NAMES.get(parts[-1], parts[-1])
    return text

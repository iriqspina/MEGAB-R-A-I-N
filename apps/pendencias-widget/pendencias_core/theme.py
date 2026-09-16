"""Tokens visuais — subconjunto do theme.py do Cotas IA (mesma linguagem).

Nenhuma cor nova de propósito: o widget nasce gêmeo visual do Cotas IA
(carvão, raio 14, Segoe UI, status verde/âmbar/cinza).
"""

FONT_FAMILY = "Segoe UI"
CORNER_RADIUS = 14
DEFAULT_OPACITY_PERCENT = 76

# superfície carvão (preset default do irmão)
BG_BASE = (20, 22, 28)          # #14161c
BORDER = (255, 255, 255, 35)
INK = (232, 234, 240, 255)      # texto principal
INK_FAINT = (162, 168, 177, 255)  # rótulos/idade — irmão STATUS_GREY #a2a8b1
INK_DIM = (120, 126, 136, 255)

STATUS_GREEN = (124, 196, 143, 255)  # #7cc48f — nova (<7d)
STATUS_AMBER = (224, 180, 106, 255)  # #e0b46a — velha (>7d)
STATUS_GREY = (162, 168, 177, 255)   # sem idade conhecida

IDADE_AMBAR_DIAS = 7

SIZE_TITLE = 13
SIZE_GROUP = 10
SIZE_ITEM = 12
SIZE_HINT = 11


def rgba(tup) -> str:
    return f"rgba({tup[0]}, {tup[1]}, {tup[2]}, {tup[3] / 255:.3f})"


def cor_idade(mtime_iso: str | None) -> tuple:
    if not mtime_iso:
        return STATUS_GREY
    from datetime import datetime, timezone

    try:
        mt = datetime.fromisoformat(mtime_iso)
    except ValueError:
        return STATUS_GREY
    dias = (datetime.now(timezone.utc) - mt.astimezone(timezone.utc)).days
    return STATUS_AMBER if dias >= IDADE_AMBAR_DIAS else STATUS_GREEN

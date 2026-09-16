from . import theme
from .providers_bridge import now_iso

_DEMO_WINDOWS = {
    "codex": [
        {"id": "codex:primary", "label": "codex · 7 d", "used_percent": 42.0, "resets_at": "2026-10-05T00:00:00Z"},
        {"id": "codex_bengalfox:primary", "label": "GPT-5.3-Codex-Spark · 5 h", "used_percent": 8.0, "resets_at": "2026-09-14T21:00:00Z"},
    ],
    "codex_gpt2": [
        {"id": "codex:primary", "label": "5 h", "used_percent": 3.0, "resets_at": "2026-09-14T21:00:00Z"},
        {"id": "codex:secondary", "label": "Semana", "used_percent": 1.0, "resets_at": "2026-09-20T00:00:00Z"},
    ],
    "claude": [
        {"id": "session", "label": "Sessão 5h", "used_percent": 61.0, "resets_at": "2026-09-14T21:00:00Z"},
        {"id": "week", "label": "7 dias", "used_percent": 78.0, "resets_at": "2026-09-20T00:00:00Z"},
    ],
    "zai": [
        {"id": "CREDIT_LIMIT:3x5", "label": "Sessão", "used_percent": 12.0, "resets_at": "2026-09-14T21:00:00Z"},
        {"id": "CREDIT_LIMIT:6x1", "label": "Semana", "used_percent": 4.0, "resets_at": "2026-09-20T00:00:00Z"},
    ],
    "gemini_cli": [{"id": "daily", "label": "Diário", "used_percent": 15.0, "resets_at": "2026-09-15T00:00:00Z"}],
    "antigravity": [{"id": "monthly", "label": "Mensal", "used_percent": 93.0, "resets_at": "2026-10-05T00:00:00Z"}],
    "gemini_web": [{"id": "daily", "label": "Diário", "used_percent": None, "resets_at": None}],
}
_DEMO_STATUS = {"gemini_web": "auth_required"}
_DEMO_MESSAGE = {"gemini_web": "reautenticação necessária (demo)"}


def demo_snapshot(provider_id: str) -> dict:
    # Fonte distinta por provider (mesma logica do PROVIDER_SOURCE_HINT real):
    # todos com o mesmo texto genérico "dados de demonstração..." faz o
    # detalhe expandido repetir a MESMA linha em toda coluna — informação
    # igual pra todos não é conteúdo de coluna, é rodapé (o banner MODO DEMO
    # já cobre isso uma vez só).
    status = _DEMO_STATUS.get(provider_id, "ok")
    return {
        "provider": provider_id,
        "label": provider_id,
        "status": status,
        "source": theme.PROVIDER_SOURCE_HINT.get(provider_id, provider_id),
        "fetched_at": now_iso(),
        "windows": [] if status != "ok" else _DEMO_WINDOWS.get(provider_id, []),
        "message": _DEMO_MESSAGE.get(provider_id, ""),
    }

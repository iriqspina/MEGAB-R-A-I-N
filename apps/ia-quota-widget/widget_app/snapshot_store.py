from .formatting import age_seconds
from .theme import STALE_GRACE_SECONDS


class SnapshotStore:
    """Último dado de cada FONTE (provedor consultado).

    Linha de tela que deriva de outra fonte (Spark sai da leitura do Codex)
    passa ``window_filter``: o recorte é feito na leitura, sem copiar o
    snapshot — assim idade e estado continuam sendo os da fonte.
    """

    def __init__(self):
        self._last_any: dict[str, dict] = {}
        self._last_good: dict[str, dict] = {}

    def update(self, provider_id: str, snapshot: dict) -> None:
        self._last_any[provider_id] = snapshot
        if snapshot.get("status") == "ok":
            self._last_good[provider_id] = snapshot

    def display(self, provider_id: str, window_filter=None) -> dict | None:
        current = self._last_any.get(provider_id)
        if current is None:
            return None
        if current.get("status") == "ok":
            age = age_seconds(current.get("fetched_at"))
            result = {
                "status": "ok",
                "windows": current.get("windows", []),
                "message": current.get("message", ""),
                "source": current.get("source"),
                "fetched_at": current.get("fetched_at"),
                "stale": age is None or age >= STALE_GRACE_SECONDS,
            }
        else:
            good = self._last_good.get(provider_id)
            if good is not None:
                result = {
                    "status": current.get("status"),
                    "windows": good.get("windows", []),
                    "message": current.get("message", ""),
                    "source": good.get("source"),
                    "fetched_at": good.get("fetched_at"),
                    "stale": True,
                }
            else:
                result = {
                    "status": current.get("status"),
                    "windows": [],
                    "message": current.get("message", ""),
                    "source": current.get("source"),
                    "fetched_at": None,
                    "stale": False,
                }
        if window_filter is not None:
            result["windows"] = [w for w in result["windows"] if window_filter(w)]
        return result

    def worst_window(self, provider_id: str, window_filter=None):
        display = self.display(provider_id, window_filter)
        if display is None:
            return None
        numeric = [w for w in display["windows"] if w.get("used_percent") is not None]
        if numeric:
            return max(numeric, key=lambda w: w["used_percent"])
        if display["windows"]:
            return display["windows"][0]
        return None

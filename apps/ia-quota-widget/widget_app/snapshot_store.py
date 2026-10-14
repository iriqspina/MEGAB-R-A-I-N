import json
import os
from pathlib import Path

from .formatting import age_seconds, parse_iso
from .theme import STALE_GRACE_SECONDS


class SnapshotStore:
    """Último dado de cada FONTE (provedor consultado).

    Linha de tela que deriva de outra fonte (Spark sai da leitura do Codex)
    passa ``window_filter``: o recorte é feito na leitura, sem copiar o
    snapshot — assim idade e estado continuam sendo os da fonte.
    """

    def __init__(self, cache_path=None):
        self._last_any: dict[str, dict] = {}
        self._last_good: dict[str, dict] = {}
        self._disk_good: dict[str, dict] = {}
        self._cache_path = Path(cache_path) if cache_path is not None else None
        if self._cache_path is not None:
            try:
                cached = json.loads(self._cache_path.read_text(encoding="utf-8"))
                if cached.get("schema_version") == 1:
                    for provider, snapshot in cached.get("providers", {}).items():
                        if isinstance(snapshot, dict) and snapshot.get("status") == "ok" and isinstance(snapshot.get("windows"), list):
                            from .providers_bridge import normalize_snapshot
                            snapshot = normalize_snapshot(provider, snapshot)
                            if not snapshot['windows'] or not parse_iso(snapshot.get('fetched_at')):
                                continue
                            self._last_good[provider] = snapshot
                            self._disk_good[provider] = snapshot
                            self._last_any[provider] = {"status": "cached", "message": "Última leitura salva; aguardando nova consulta."}
            except (OSError, ValueError, AttributeError, TypeError):
                pass

    def update(self, provider_id: str, snapshot: dict) -> None:
        self._last_any[provider_id] = snapshot
        if snapshot.get("status") == "ok":
            self._last_good[provider_id] = snapshot
            if self._cache_path is not None and snapshot.get('windows') and parse_iso(snapshot.get('fetched_at')):
                self._disk_good[provider_id] = snapshot
                temporary = self._cache_path.with_name(self._cache_path.name + ".tmp")
                try:
                    self._cache_path.parent.mkdir(parents=True, exist_ok=True)
                    temporary.write_text(json.dumps({"schema_version": 1, "providers": self._disk_good}, ensure_ascii=False), encoding="utf-8")
                    os.replace(temporary, self._cache_path)
                except (OSError, TypeError, ValueError):
                    pass

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
                "details": current.get("details") or {},
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
                    "details": good.get("details") or {},
                }
            else:
                result = {
                    "status": current.get("status"),
                    "windows": [],
                    "message": current.get("message", ""),
                    "source": current.get("source"),
                    "fetched_at": None,
                    "stale": False,
                    "details": {},
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

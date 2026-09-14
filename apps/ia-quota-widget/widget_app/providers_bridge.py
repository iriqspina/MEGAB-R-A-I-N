import math
import re
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

FALLBACK_PROVIDER_IDS = ["codex", "claude", "zai", "gemini_cli", "antigravity", "gemini_web"]
VALID_STATUSES = {"ok", "unavailable", "auth_required", "error", "rate_limited"}
MODULE_MISSING_MESSAGE = "módulo de dados (providers.py) ainda não disponível"

_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}"),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
]


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redigido]", text)
    return text


def _load_providers_module():
    try:
        import providers
    except Exception:
        return None
    return providers


def load_pacing_module():
    try:
        import budget_pacing
    except Exception:
        return None
    return budget_pacing


def provider_ids() -> list[str]:
    module = _load_providers_module()
    if module is not None and hasattr(module, "PROVIDER_IDS"):
        ids = list(module.PROVIDER_IDS)
        if ids:
            return ids
    return list(FALLBACK_PROVIDER_IDS)


def provider_labels() -> dict:
    module = _load_providers_module()
    if module is not None and hasattr(module, "PROVIDER_LABELS"):
        return dict(module.PROVIDER_LABELS)
    return {}


def _empty_snapshot(provider_id: str, status: str, message: str) -> dict:
    return {
        "provider": provider_id,
        "label": provider_id,
        "status": status,
        "source": None,
        "fetched_at": None,
        "windows": [],
        "message": message,
    }


def _clamp_percent(value):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value):
        return None
    return max(0.0, min(100.0, value))


def _clamp_duration_minutes(value):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        return None
    return int(value)


def _normalize_window(raw: dict) -> dict:
    return {
        "id": str(raw.get("id", "")),
        "label": str(raw.get("label", raw.get("id", ""))),
        "used_percent": _clamp_percent(raw.get("used_percent")),
        "resets_at": raw.get("resets_at"),
        "duration_minutes": _clamp_duration_minutes(raw.get("duration_minutes")),
    }


def normalize_snapshot(provider_id: str, raw: dict) -> dict:
    status = raw.get("status")
    if status not in VALID_STATUSES:
        status = "error"
    windows_raw = raw.get("windows") or []
    windows = [_normalize_window(w) for w in windows_raw if isinstance(w, dict)]
    message = str(raw.get("message") or "")[:240]
    return {
        "provider": provider_id,
        "label": str(raw.get("label") or provider_id),
        "status": status,
        "source": raw.get("source"),
        "fetched_at": raw.get("fetched_at"),
        "windows": windows,
        "message": _redact(message),
    }


def fetch_provider_safe(provider_id: str) -> dict:
    module = _load_providers_module()
    if module is None or not hasattr(module, "fetch_provider"):
        return _empty_snapshot(provider_id, "unavailable", MODULE_MISSING_MESSAGE)
    try:
        raw = module.fetch_provider(provider_id)
        if not isinstance(raw, dict):
            raise TypeError("fetch_provider must return dict")
        return normalize_snapshot(provider_id, raw)
    except Exception as exc:
        # Never surface str(exc): adapter exceptions can embed request URLs,
        # headers or payload fragments from the underlying HTTP/CLI call.
        return _empty_snapshot(provider_id, "error", f"falha no adaptador ({type(exc).__name__})")


class _FetchSignals(QObject):
    finished = Signal(str, dict)


class _FetchRunnable(QRunnable):
    def __init__(self, provider_id: str, signals: _FetchSignals):
        super().__init__()
        self._provider_id = provider_id
        self._signals = signals

    def run(self):
        try:
            snapshot = fetch_provider_safe(self._provider_id)
        except Exception as exc:
            snapshot = _empty_snapshot(self._provider_id, "error", f"falha inesperada ({type(exc).__name__})")
        self._signals.finished.emit(self._provider_id, snapshot)


class ProviderPoller(QObject):
    snapshot_ready = Signal(str, dict)

    def __init__(self, parent=None, max_workers: int = 5):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_workers)
        self._signals = _FetchSignals()
        self._signals.finished.connect(self._on_finished)
        self._in_flight: set[str] = set()

    def _on_finished(self, provider_id: str, snapshot: dict):
        self._in_flight.discard(provider_id)
        self.snapshot_ready.emit(provider_id, snapshot)

    def poll(self, ids: list[str]) -> None:
        for provider_id in ids:
            if provider_id in self._in_flight:
                continue
            self._in_flight.add(provider_id)
            self._pool.start(_FetchRunnable(provider_id, self._signals))

    def is_busy(self) -> bool:
        return bool(self._in_flight)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

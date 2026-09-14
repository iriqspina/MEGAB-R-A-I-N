import math
import time
import types

import pytest

from widget_app import providers_bridge as pb


def _fake_module(*, fetch_provider=None, provider_ids=None, labels=None):
    module = types.ModuleType("providers")
    if provider_ids is not None:
        module.PROVIDER_IDS = provider_ids
    if labels is not None:
        module.PROVIDER_LABELS = labels
    if fetch_provider is not None:
        module.fetch_provider = fetch_provider
    return module


def test_provider_ids_fallback_when_module_missing(monkeypatch):
    monkeypatch.setattr(pb, "_load_providers_module", lambda: None)
    assert pb.provider_ids() == pb.FALLBACK_PROVIDER_IDS


def test_provider_labels_empty_when_module_missing(monkeypatch):
    monkeypatch.setattr(pb, "_load_providers_module", lambda: None)
    assert pb.provider_labels() == {}


def test_provider_ids_from_module(monkeypatch):
    monkeypatch.setattr(pb, "_load_providers_module", lambda: _fake_module(provider_ids=("codex", "claude")))
    assert pb.provider_ids() == ["codex", "claude"]


def test_clamp_percent_rejects_bool_nan_inf_via_normalize():
    raw = {
        "status": "ok",
        "windows": [
            {"id": "a", "label": "A", "used_percent": True, "resets_at": None},
            {"id": "b", "label": "B", "used_percent": float("nan"), "resets_at": None},
            {"id": "c", "label": "C", "used_percent": float("inf"), "resets_at": None},
            {"id": "d", "label": "D", "used_percent": 55.5, "resets_at": None},
            {"id": "e", "label": "E", "used_percent": 150, "resets_at": None},
            {"id": "f", "label": "F", "used_percent": -20, "resets_at": None},
        ],
    }
    normalized = pb.normalize_snapshot("codex", raw)
    values = {w["id"]: w["used_percent"] for w in normalized["windows"]}
    assert values["a"] is None
    assert values["b"] is None
    assert values["c"] is None
    assert values["d"] == 55.5
    assert values["e"] == 100.0
    assert values["f"] == 0.0


def test_normalize_snapshot_invalid_status_becomes_error():
    normalized = pb.normalize_snapshot("codex", {"status": "not-a-real-status"})
    assert normalized["status"] == "error"


def test_fetch_provider_safe_module_missing(monkeypatch):
    monkeypatch.setattr(pb, "_load_providers_module", lambda: None)
    result = pb.fetch_provider_safe("codex")
    assert result["status"] == "unavailable"
    assert result["message"] == pb.MODULE_MISSING_MESSAGE


def test_fetch_provider_safe_never_leaks_exception_text(monkeypatch):
    sentinel_secret = "FAKE-TOKEN-not-a-real-secret-1234567890abcdef"

    def boom(provider_id):
        raise RuntimeError(f"request failed for http://example.invalid/?token={sentinel_secret}")

    monkeypatch.setattr(pb, "_load_providers_module", lambda: _fake_module(fetch_provider=boom))
    result = pb.fetch_provider_safe("codex")
    assert result["status"] == "error"
    assert sentinel_secret not in result["message"]
    assert "http://" not in result["message"]
    assert "RuntimeError" in result["message"]


def test_fetch_provider_safe_rejects_non_dict_return(monkeypatch):
    monkeypatch.setattr(pb, "_load_providers_module", lambda: _fake_module(fetch_provider=lambda pid: "not a dict"))
    result = pb.fetch_provider_safe("codex")
    assert result["status"] == "error"


def test_message_is_redacted_and_truncated():
    long_secret = "a" * 40
    raw = {"status": "ok", "message": f"token {long_secret} in header", "windows": []}
    normalized = pb.normalize_snapshot("claude", raw)
    assert long_secret not in normalized["message"]
    assert "[redigido]" in normalized["message"]


def test_fetch_runnable_always_emits_even_on_unexpected_exception(monkeypatch, qt_app):
    monkeypatch.setattr(pb, "fetch_provider_safe", lambda provider_id: (_ for _ in ()).throw(ValueError("boom")))
    signals = pb._FetchSignals()
    received = []
    signals.finished.connect(lambda pid, snap: received.append((pid, snap)))

    runnable = pb._FetchRunnable("claude", signals)
    runnable.run()

    assert len(received) == 1
    provider_id, snapshot = received[0]
    assert provider_id == "claude"
    assert snapshot["status"] == "error"
    assert "ValueError" in snapshot["message"]


def test_provider_poller_clears_in_flight_after_failure(monkeypatch, qt_app):
    monkeypatch.setattr(pb, "fetch_provider_safe", lambda provider_id: (_ for _ in ()).throw(RuntimeError("x")))
    poller = pb.ProviderPoller()
    poller.poll(["codex"])

    assert poller.is_busy()
    poller._pool.waitForDone(5000)

    deadline = time.time() + 5
    while poller.is_busy() and time.time() < deadline:
        qt_app.processEvents()

    assert not poller.is_busy()


def test_clamp_percent_finite_check():
    assert pb._clamp_percent(math.inf) is None
    assert pb._clamp_percent(math.nan) is None
    assert pb._clamp_percent(True) is None
    assert pb._clamp_percent("50") is None
    assert pb._clamp_percent(50) == 50.0

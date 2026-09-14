from widget_app.snapshot_store import SnapshotStore


def _snap(status, windows=None, fetched_at=None, message="", source="src"):
    return {
        "status": status,
        "windows": windows or [],
        "fetched_at": fetched_at,
        "message": message,
        "source": source,
    }


def test_no_reading_yet_returns_none():
    store = SnapshotStore()
    assert store.display("codex") is None


def test_ok_snapshot_passthrough():
    from datetime import datetime, timezone
    store = SnapshotStore()
    store.update("codex", _snap("ok", windows=[{"id": "a", "used_percent": 40}], fetched_at=datetime.now(timezone.utc).isoformat()))
    display = store.display("codex")
    assert display["status"] == "ok"
    assert display["stale"] is False
    assert display["windows"][0]["used_percent"] == 40


def test_error_keeps_last_good_marked_stale():
    store = SnapshotStore()
    store.update("codex", _snap("ok", windows=[{"id": "a", "used_percent": 40}], fetched_at="2026-09-08T10:00:00Z"))
    store.update("codex", _snap("error", message="rede fora"))
    display = store.display("codex")
    assert display["status"] == "error"
    assert display["stale"] is True
    assert display["windows"][0]["used_percent"] == 40
    assert display["fetched_at"] == "2026-09-08T10:00:00Z"
    assert display["message"] == "rede fora"


def test_error_without_prior_good_has_no_fabricated_data():
    store = SnapshotStore()
    store.update("codex", _snap("auth_required", message="reautenticar"))
    display = store.display("codex")
    assert display["windows"] == []
    assert display["stale"] is False
    assert display["fetched_at"] is None


def test_worst_window_never_averages_picks_highest_percent():
    store = SnapshotStore()
    store.update(
        "claude",
        _snap(
            "ok",
            windows=[
                {"id": "session", "label": "Sessão", "used_percent": 20},
                {"id": "week", "label": "Semana", "used_percent": 78},
                {"id": "model", "label": "Modelo X", "used_percent": 55},
            ],
        ),
    )
    worst = store.worst_window("claude")
    assert worst["id"] == "week"
    assert worst["used_percent"] == 78


def test_worst_window_skips_none_values():
    store = SnapshotStore()
    store.update(
        "claude",
        _snap(
            "ok",
            windows=[
                {"id": "a", "used_percent": None},
                {"id": "b", "used_percent": 33},
            ],
        ),
    )
    worst = store.worst_window("claude")
    assert worst["id"] == "b"


def test_worst_window_falls_back_to_first_when_all_none():
    store = SnapshotStore()
    store.update("claude", _snap("ok", windows=[{"id": "a", "used_percent": None}]))
    worst = store.worst_window("claude")
    assert worst["id"] == "a"
    assert worst["used_percent"] is None

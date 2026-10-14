from widget_app import theme
from widget_app.ui_provider_segment import WindowBar, PercentTrack, ProviderSegment
from widget_app.snapshot_store import SnapshotStore
from widget_app.providers_bridge import now_iso


def test_same_codex_slot_obeys_each_accounts_duration():
    assert theme.window_category({"id": "codex:primary", "duration_minutes": 300}) == "session"
    assert theme.window_category({"id": "codex:primary", "duration_minutes": 10080}) == "weekly"
    assert theme.window_category({"id": "codex:primary", "label": "codex · 5 h"}) == "session"


def test_reused_bar_updates_duration_and_visible_small_percent(qt_app):
    bar = WindowBar({"id": "codex:primary", "duration_minutes": 10080, "used_percent": 8})
    bar.update_window({"id": "codex:primary", "duration_minutes": 300, "used_percent": 0.3})
    assert bar._label.text() == "5 h"
    assert bar._track._text == bar._pct.text() == "<1%"
    assert bar._track._color == theme.window_category_color("session")
    bar.deleteLater()


def test_gpt2_reserve_stays_identifiable_and_session_sorts_first(qt_app):
    windows = [
        {"id": "base_model_inference:primary", "label": "gpt-reserve · 7 d", "duration_minutes": 10080, "used_percent": 0},
        {"id": "codex:primary", "label": "codex · 5 h", "duration_minutes": 300, "used_percent": 0},
        {"id": "codex:secondary", "label": "codex · 7 d", "duration_minutes": 10080, "used_percent": 8},
    ]
    store = SnapshotStore()
    for window in windows:
        window["resets_at"] = None
    store.update("codex_gpt2", {"status": "ok", "windows": windows, "fetched_at": now_iso()})
    segment = ProviderSegment("codex_gpt2", "Codex GPT2", None)
    segment.update_from_store(store, expanded=True)
    assert [b._label.text() for b in segment._bars] == ["5 h", "gpt-reserve · semana", "semana"]
    assert [b._track._text for b in segment._bars] == ["0%", "0%", "8%"]
    segment.deleteLater()


def test_zero_missing_and_fraction_are_distinct_on_visible_track(qt_app):
    track = PercentTrack()
    for value, expected in [(0, "0%"), (None, "—"), (0.2, "<1%"), (0.5, "<1%"), (8, "8%")]:
        track.set_value(value, "#9eb4da")
        assert track._text == expected
    track.deleteLater()


def test_remaining_mode_changes_visible_bar(qt_app):
    bar = WindowBar({"id": "week", "used_percent": 8})
    bar.update_window({"id": "week", "used_percent": 8}, remaining=True)
    assert bar._track._text == "92%"
    assert "livre" in bar.toolTip()
    bar.deleteLater()


def test_hidden_claude_never_runs_health_cli(qt_app, monkeypatch, tmp_path):
    from widget_app import persistence
    from widget_app.main_window import MainWindow
    from PySide6.QtCore import QProcess
    monkeypatch.setattr(persistence.paths, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(persistence.paths, "CACHE_PATH", tmp_path / "cache.json")
    win = MainWindow(session_only=True)
    win.settings.set_visible("claude", False)
    calls = []
    monkeypatch.setattr(QProcess, "startDetached", lambda *a: calls.append(a))
    monkeypatch.setattr(win.poller, "poll", lambda ids: calls.append(list(ids)))
    win.poll_now()
    win._update_mcp_status()
    assert all("claude" not in call for call in calls)
    assert len(calls) == 1
    assert win._mcp_status.text() == "Claude pausado"
    win.deleteLater()

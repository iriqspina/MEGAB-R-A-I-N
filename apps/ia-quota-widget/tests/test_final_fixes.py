from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import Qt
from widget_app import persistence, theme
from widget_app.demo_data import demo_snapshot
from widget_app.main_window import MainWindow
from widget_app.poll_backoff import PollBackoff


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(persistence.paths, 'SETTINGS_PATH', tmp_path / 'settings.json')
    win = MainWindow()
    monkeypatch.setattr(win.poller, 'poll', lambda ids: None)
    yield win
    win.deleteLater()


def old_snapshot(provider='codex'):
    snapshot = demo_snapshot(provider)
    snapshot['fetched_at'] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    return snapshot


@pytest.mark.parametrize('trigger', ['expand', 'second_provider', 'age_tick'])
def test_pending_provider_cannot_resurrect_cached_number(window, trigger):
    window.store.update('gemini_cli', old_snapshot('gemini_cli'))
    window._toggle_provider_visibility('gemini_cli', True)
    if trigger == 'expand':
        window._toggle_expanded()
    elif trigger == 'second_provider':
        window._toggle_provider_visibility('antigravity', True)
    else:
        window._refresh_ages()
    segment = window._segments['gemini_cli']
    assert segment._value.text() == '—'
    assert segment._hint.text() == 'consultando…'


@pytest.mark.parametrize('preset', theme.SURFACE_PRESET_ORDER)
def test_old_ok_snapshot_degrades_without_fetch_failure(window, preset):
    window._set_surface_preset(preset)
    window._on_snapshot('codex', old_snapshot())
    assert window.store.display('codex')['stale']
    segment = window._segments['codex']
    assert segment._track._color == theme.status_colors_for(preset)['grey']
    assert 'há 2 h' in segment._hint.text()


def test_age_tick_degrades_a_previously_fresh_ok_value(window):
    snapshot = demo_snapshot('codex')
    snapshot['fetched_at'] = datetime.now(timezone.utc).isoformat()
    window._on_snapshot('codex', snapshot)
    assert not window.store.display('codex')['stale']
    snapshot['fetched_at'] = old_snapshot()['fetched_at']
    window._refresh_ages()
    assert window._segments['codex']._track._color == theme.STATUS_GREY


def test_provider_menu_marks_old_value(window):
    window.store.update('gemini_cli', old_snapshot('gemini_cli'))
    label = window._provider_menu_label('gemini_cli')
    assert 'há 2 h' in label and 'dado antigo' in label
    assert '% ok' not in label


def test_session_overrides_cannot_write_even_on_close(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(persistence.paths, 'SETTINGS_PATH', tmp_path / 'settings.json')
    persistence.save_settings(persistence.Settings())
    before = persistence.paths.SETTINGS_PATH.read_bytes()
    win = MainWindow(demo=True, session_only=True)
    win._set_surface_preset('nevoa')
    win._toggle_expanded()
    win._save_settings()
    win.close()
    assert persistence.paths.SETTINGS_PATH.read_bytes() == before
    win.deleteLater()


def test_backoff_doubles_caps_and_resets_only_on_success():
    now = [100.0]
    backoff = PollBackoff(clock=lambda: now[0])
    for delay in (240, 480, 900, 900):
        backoff.observe('claude', 'rate_limited')
        assert backoff.ready('codex')
        now[0] += delay - 1
        assert not backoff.ready('claude')
        now[0] += 1
        assert backoff.ready('claude')
    backoff.observe('claude', 'error')
    backoff.observe('claude', 'rate_limited')
    assert backoff._delays['claude'] == 900
    backoff.observe('claude', 'ok')
    assert backoff.ready('claude')
    backoff.observe('claude', 'rate_limited')
    assert backoff._delays['claude'] == 240


def test_backoff_covers_timer_manual_and_visibility_toggle(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window.poller, 'poll', lambda ids: calls.extend(ids))
    window._on_snapshot('claude', {'status': 'rate_limited', 'windows': [], 'message': 'HTTP 429'})
    window.poll_now()
    assert calls == ['codex', 'zai']
    window._on_snapshot('codex', demo_snapshot('codex'))
    window._on_snapshot('zai', demo_snapshot('zai'))
    window.manual_refresh()
    assert calls == ['codex', 'zai', 'codex', 'zai']
    window._toggle_provider_visibility('claude', False)
    window._toggle_provider_visibility('claude', True)
    assert 'claude' not in calls
    assert 'claude' not in window._querying
    assert window._segments['claude']._hint.text() == 'limitado'


def test_due_retry_only_fetches_limited_visible_provider(window, monkeypatch):
    now = [100.0]
    window._backoff = PollBackoff(clock=lambda: now[0])
    calls = []
    monkeypatch.setattr(window.poller, 'poll', lambda ids: calls.extend(ids))
    window._on_snapshot('claude', {'status': 'rate_limited', 'windows': []})
    assert window._retry_timers['claude'].isActive()
    now[0] += 240
    window._retry_provider('claude')
    window._retry_provider('claude')
    assert calls == ['claude']
    window._on_snapshot('claude', demo_snapshot('claude'))
    assert not window._retry_timers['claude'].isActive()


def test_due_retry_does_not_enable_or_fetch_hidden_provider(window, monkeypatch):
    now = [100.0]
    window._backoff = PollBackoff(clock=lambda: now[0])
    calls = []
    monkeypatch.setattr(window.poller, 'poll', lambda ids: calls.extend(ids))
    window._on_snapshot('claude', {'status': 'rate_limited', 'windows': []})
    window._toggle_provider_visibility('claude', False)
    now[0] += 240
    window._retry_provider('claude')
    assert calls == []

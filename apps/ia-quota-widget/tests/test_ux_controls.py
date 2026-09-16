import pytest
from PySide6.QtCore import Qt
from widget_app import persistence
from widget_app.main_window import MainWindow
from widget_app.demo_data import demo_snapshot


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(persistence.paths, 'SETTINGS_PATH', tmp_path / 'settings.json')
    win = MainWindow()
    monkeypatch.setattr(win.poller, 'poll', lambda ids: None)
    yield win
    win.deleteLater()


def test_failed_attempt_never_claims_success_and_waits_for_all(window):
    window.poll_now()
    assert window._refresh_status.text() == 'Consultando…'
    assert not window._refresh_btn.isEnabled()
    failure = dict(provider='codex', status='error', windows=[], fetched_at=None, source=None, message='rede')
    window._on_snapshot('codex', failure)
    assert window._refresh_status.text() == 'Consultando…'
    window._on_snapshot('codex_gpt2', {**failure, 'provider': 'codex_gpt2'})
    assert window._refresh_status.text() == 'Consultando…'
    window._on_snapshot('claude', {**failure, 'provider': 'claude'})
    assert window._refresh_status.text() == 'Consultando…'
    window._on_snapshot('zai', {**failure, 'provider': 'zai'})
    assert window._refresh_status.text() == 'Tentativa agora'
    assert window._refresh_btn.isEnabled()
    assert window._segments['codex']._value.text() == '—'


def test_empty_state_offers_recovery_and_pauses_refresh(window):
    for pid in window.provider_ids:
        window._toggle_provider_visibility(pid, False)
    assert not window._empty.isHidden()
    assert window._refresh_status.text() == 'Consulta pausada'
    assert not window._refresh_btn.isEnabled()
    window._toggle_provider_visibility('claude', True)
    assert window._empty.isHidden()
    assert window._refresh_status.text() == 'Consultando…'


def test_hiding_inflight_provider_does_not_leave_busy_indicator(window):
    window.poll_now()
    # Spark lê da mesma fonte: com ele visível, a consulta do Codex continua valendo.
    window._toggle_provider_visibility('codex', False)
    window._toggle_provider_visibility('spark', False)
    # gpt2 é fonte própria: escondido em flight, sai da espera como o Codex.
    window._toggle_provider_visibility('codex_gpt2', False)
    window._on_snapshot('claude', demo_snapshot('claude'))
    window._on_snapshot('zai', demo_snapshot('zai'))
    assert window._refresh_status.text() == 'Tentativa agora'
    assert window._refresh_btn.isEnabled()


def test_refresh_shortcut_cannot_bypass_pending_request(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window.poller, 'poll', lambda ids: calls.append(ids))
    window.poll_now()
    window.manual_refresh()
    assert len(calls) == 1


def test_pin_reports_saved_state_and_toggle_in_accessibility(window):
    assert window._top_btn.isChecked()
    assert 'ligado' in window._top_btn.accessibleName()
    window._toggle_always_on_top()
    assert not window._top_btn.isChecked()
    assert 'desligado' in window._top_btn.accessibleName()
    assert not window.windowFlags() & Qt.WindowStaysOnTopHint
    assert not persistence.load_settings().always_on_top


def test_source_is_complete_without_multiline_technical_path(window):
    snapshot = demo_snapshot('claude')
    snapshot['source'] = 'example.test/' + 'long-path/' * 15
    window._on_snapshot('claude', snapshot)
    segment = window._segments['claude']
    assert snapshot['source'] in segment._name_wrap.toolTip()
    assert snapshot['source'] in segment._name_wrap.accessibleName()
    for bar in segment._bars:
        assert snapshot['source'] not in bar._extra.text()


def test_demo_feedback_cannot_look_like_real_fetch(window):
    window.demo = True
    window.poll_now()
    assert 'sem consulta real' in window._refresh_status.text()


def test_attempt_ages_without_fetch_and_preserves_exact_time_in_tooltip(window):
    from datetime import datetime, timedelta
    window._last_attempt = datetime.now().astimezone() - timedelta(minutes=2)
    window._update_refresh_feedback()
    assert window._refresh_status.text() == 'Tentativa há 2 min'
    assert window._last_attempt.strftime('%H:%M:%S') in window._refresh_status.toolTip()
    assert 'Não indica sucesso' in window._refresh_status.toolTip()

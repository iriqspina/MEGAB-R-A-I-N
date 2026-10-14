import pytest

from widget_app import persistence
from widget_app.demo_data import demo_snapshot
from widget_app.main_window import MainWindow


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, "DATA_DIR", tmp_path)
    monkeypatch.setattr(persistence.paths, "SETTINGS_PATH", tmp_path / "settings.json")
    win = MainWindow(demo=True)
    yield win
    win.deleteLater()


def test_default_state_shows_codex_gpt2_claude_and_zai(window):
    visible = [pid for pid in window.provider_ids if window.settings.is_visible(pid)]
    assert visible == ["codex", "spark", "codex_gpt2", "claude", "zai"]
    # Cards no fluxo (spark aninhado não conta).
    assert window._top_card_rows() == ["codex", "codex_gpt2", "claude", "zai"]
    assert window._body_layout.count() == 4


def test_spark_nests_inside_codex_card_but_is_removable(window):
    codex = window._segments["codex"]
    spark = window._segments["spark"]
    assert codex._nested is spark
    assert not spark.isHidden()
    window._toggle_provider_visibility("spark", False)
    assert window.settings.is_visible("spark") is False
    assert codex._nested is None
    assert window._top_card_rows() == ["codex", "codex_gpt2", "claude", "zai"]


def test_collapsed_keeps_renewal_but_hides_pacing_even_after_rebuild(window):
    # Superseded 2026-10-11 ("expanded=False também conserva informações"):
    # recolhido mostra a renovação de cada janela; só o ritmo fica para o
    # expandido. Rebuild não pode mudar o que set_expanded() decidiu.
    assert window.settings.expanded is False
    window._on_snapshot("claude", demo_snapshot("claude"))
    window._rebuild_segments()
    for provider_id in ("codex", "claude"):
        segment = window._segments[provider_id]
        for bar in segment._bars:
            assert bar._extra.isHidden() is False
            assert "renova" in bar._extra_full
            assert "dá ~" not in bar._extra_full and "ritmo" not in bar._extra_full


def test_toggling_expanded_shows_bar_extras(window):
    # isHidden() reflete o setVisible() explicito deste widget; isVisible()
    # tambem depende da top-level window estar mostrada na tela.
    window._on_snapshot("claude", demo_snapshot("claude"))
    window._toggle_expanded()
    assert window.settings.expanded is True
    for bar in window._segments["claude"]._bars:
        assert bar._extra.text()  # renovação/ritmo existe
        assert bar._extra.isHidden() is False


def test_enabling_hidden_provider_adds_card_and_persists(window):
    window._toggle_provider_visibility("gemini_cli", True)
    assert window.settings.is_visible("gemini_cli") is True
    assert window._top_card_rows() == ["codex", "codex_gpt2", "claude", "zai", "gemini_cli"]

    reloaded = persistence.load_settings()
    assert reloaded.is_visible("gemini_cli") is True


def test_hidden_providers_become_dock_balls(window):
    window._toggle_provider_visibility("claude", False)
    assert "claude" in window.dock._hidden
    window._toggle_provider_visibility("claude", True)
    assert "claude" not in window.dock._hidden


def test_disabling_all_providers_leaves_header_usable(window, qt_app):
    window.show()
    qt_app.processEvents()
    for pid in list(window.provider_ids):
        window._toggle_provider_visibility(pid, False)
    assert window._body_layout.count() == 0
    assert window.dock._hidden == list(window.provider_ids)
    assert not window.strip.isHidden()  # Compact legacy keeps its toolbar/menu accessible.
    assert window.strip.menu.isVisible()


def test_surface_preset_persists_and_restyles_panel(window):
    window._set_surface_preset("nevoa")
    assert window.settings.surface_preset == "nevoa"
    assert "#E8EAEE" not in window.panel.styleSheet()  # vira rgba(...), nao o hex cru
    reloaded = persistence.load_settings()
    assert reloaded.surface_preset == "nevoa"


def test_enabling_provider_shows_querying_not_stale_number(window, monkeypatch):
    # liga, finge que ainda nao respondeu (nao-demo), verifica que NAO mostra
    # numero antigo sem marca
    window.demo = False
    monkeypatch.setattr(window.poller, "poll", lambda ids: None)
    window._toggle_provider_visibility("gemini_cli", True)
    segment = window._segments["gemini_cli"]
    assert segment._value.text() == "—"
    assert segment._hint.text() == "consultando…"


def test_spark_shares_codex_fetch_and_never_polls_twice(window, monkeypatch):
    window.demo = False
    calls = []
    monkeypatch.setattr(window.poller, "poll", lambda ids: calls.extend(ids))
    window.poll_now()
    assert calls.count("codex") == 1
    assert "spark" not in calls


def test_arriving_data_reclamps_window_inside_screen(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window, "_resize_to_content", lambda: calls.append(1))
    from widget_app.demo_data import demo_snapshot

    window._on_snapshot("zai", demo_snapshot("zai"))
    assert calls


def test_light_preset_border_is_dark_not_invisible_white(window):
    window._set_surface_preset("papel")
    assert "rgba(0,0,0" in window.panel.styleSheet()
    window._set_surface_preset("carvao")
    assert "rgba(255,255,255" in window.panel.styleSheet()

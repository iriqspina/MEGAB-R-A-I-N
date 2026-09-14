from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QFont, QMouseEvent

from widget_app import persistence, screen_geometry
from widget_app.demo_data import demo_snapshot
from widget_app.formatting import reset_label_absolute
from widget_app.main_window import MainWindow


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, "DATA_DIR", tmp_path)
    monkeypatch.setattr(persistence.paths, "SETTINGS_PATH", tmp_path / "settings.json")
    win = MainWindow()
    monkeypatch.setattr(win.poller, "poll", lambda ids: None)
    yield win
    # Nenhum timer pode sobreviver ao monkeypatch e salvar no settings.json real.
    win._size_save_timer.stop()
    win._resize_watch_timer.stop()
    win._session_only = True
    if win._settings_dialog is not None:
        win._settings_dialog.close()
        win._settings_dialog.deleteLater()
    win.deleteLater()


def _mouse(kind, local: QPoint, global_: QPoint, buttons=Qt.LeftButton):
    return QMouseEvent(kind, QPointF(local), QPointF(global_), Qt.LeftButton, buttons, Qt.NoModifier)


# ------------------------------------------------------------------ geometria pura


def test_edges_sides_corners_and_interior():
    e = screen_geometry.resize_edges_at
    assert e(3, 100, 400, 300) == Qt.LeftEdge
    assert e(396, 100, 400, 300) == Qt.RightEdge
    assert e(200, 2, 400, 300) == Qt.TopEdge
    assert e(200, 298, 400, 300) == Qt.BottomEdge
    assert e(2, 10, 400, 300) == (Qt.LeftEdge | Qt.TopEdge)
    assert e(398, 290, 400, 300) == (Qt.RightEdge | Qt.BottomEdge)
    assert not e(200, 150, 400, 300)


def test_cursor_matches_edge_direction():
    c = screen_geometry.cursor_for_edges
    assert c(Qt.LeftEdge | Qt.TopEdge) == Qt.SizeFDiagCursor
    assert c(Qt.RightEdge | Qt.TopEdge) == Qt.SizeBDiagCursor
    assert c(Qt.LeftEdge) == Qt.SizeHorCursor
    assert c(Qt.BottomEdge) == Qt.SizeVerCursor
    assert c(screen_geometry.NO_EDGE) is None


def test_resized_rect_never_goes_below_minimum():
    rect = QRect(100, 100, 400, 300)
    grown = screen_geometry.resized_rect(rect, Qt.RightEdge | Qt.BottomEdge, QPoint(50, 20), QSize(240, 150))
    assert grown.size() == QSize(450, 320) and grown.topLeft() == rect.topLeft()
    shrunk = screen_geometry.resized_rect(rect, Qt.LeftEdge, QPoint(390, 0), QSize(240, 150))
    assert shrunk.width() == 240 and shrunk.right() == rect.right()


def test_snap_point_glues_to_area_edges():
    area = QRect(0, 0, 1000, 800)
    assert screen_geometry.snap_point(QPoint(9, 400), QSize(200, 100), area) == QPoint(0, 400)
    assert screen_geometry.snap_point(QPoint(795, 695), QSize(200, 100), area) == QPoint(800, 700)
    assert screen_geometry.snap_point(QPoint(300, 300), QSize(200, 100), area) == QPoint(300, 300)


def test_reset_label_absolute_today_tomorrow_and_weekday():
    now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    today = now + timedelta(hours=2)
    assert reset_label_absolute(today.isoformat(), now) == f"renova hoje {today.astimezone():%H:%M}"
    tomorrow = now + timedelta(days=1)
    assert reset_label_absolute(tomorrow.isoformat(), now) == f"renova amanhã {tomorrow.astimezone():%H:%M}"
    later = reset_label_absolute((now + timedelta(days=3)).isoformat(), now)
    assert later.startswith("renova ") and later[-3] == ":"
    assert reset_label_absolute(None) == "renovação desconhecida"


# ------------------------------------------------------------------ redimensionar


def test_manual_size_is_respected_and_fit_to_content_resets(window):
    # 260914: sem scrollbar, tamanho manual ACIMA do conteúdo é respeitado;
    # abaixo do conteúdo clampa no mínimo (não corta, não rola).
    big = QSize(900, 700)
    window.settings.window_width, window.settings.window_height = big.width(), big.height()
    window._resize_to_content()
    assert window.size() == big
    window.settings.window_width, window.settings.window_height = 200, 150
    window._resize_to_content()
    assert window.size() == QSize(window.minimumWidth(), window.minimumHeight())
    window._fit_to_content()
    assert window.settings.window_width is None
    assert persistence.load_settings().window_width is None


def test_dragging_right_edge_resizes_and_persists_without_system_resize(window, monkeypatch):
    monkeypatch.setattr(window, "windowHandle", lambda: None)
    start = QPoint(window.width() - 2, window.height() // 2)
    window.mousePressEvent(_mouse(QEvent.MouseButtonPress, start, QPoint(1000, 500)))
    assert window._user_resize_active
    width_before = window.width()
    window.mouseMoveEvent(_mouse(QEvent.MouseMove, start, QPoint(1060, 500)))
    assert window.width() == width_before + 60
    window.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, start, QPoint(1060, 500), Qt.NoButton))
    assert not window._user_resize_active
    assert persistence.load_settings().window_width == width_before + 60


def test_window_cannot_shrink_below_content_no_scrollbars(window, monkeypatch):
    # 260914: sem barra de rolagem — o mínimo da janela É o conteúdo;
    # tentar encolher abaixo disso clampa no mínimo.
    monkeypatch.setattr(window, "windowHandle", lambda: None)
    window.update_settings({"expanded": True})
    for source in ("codex", "claude", "zai"):
        window._on_snapshot(source, demo_snapshot(source))
    window._resize_to_content()
    content_height = window._content.sizeHint().height()
    assert content_height > 150  # com dado e detalhes, o conteúdo passa do mínimo antigo
    assert window.minimumHeight() >= content_height
    start = QPoint(window.width() // 2, window.height() - 2)
    window.mousePressEvent(_mouse(QEvent.MouseButtonPress, start, QPoint(500, 1200)))
    window.mouseMoveEvent(_mouse(QEvent.MouseMove, start, QPoint(500, 1200 - window.height())))
    window.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, start, QPoint(500, 1200 - window.height()), Qt.NoButton))
    assert window.height() == window.minimumHeight()  # clampa, não corta
    assert window.height() >= content_height


def test_locked_window_ignores_edge_press_and_drag(window, monkeypatch):
    monkeypatch.setattr(window, "windowHandle", lambda: None)
    window.update_settings({"lock_position": True})
    press = QPoint(window.width() - 2, window.height() // 2)
    window.mousePressEvent(_mouse(QEvent.MouseButtonPress, press, QPoint(0, 0)))
    assert not window._user_resize_active
    assert not window.header._can_drag()


# ------------------------------------------------------------------ configurações


def test_font_and_detail_size_apply_everywhere_and_persist(window):
    window._on_snapshot("claude", demo_snapshot("claude"))
    window.update_settings({"font_family": "Consolas", "size_detail": 15})
    segment = window._segments["claude"]
    assert "Consolas" in segment._name.styleSheet()
    extra = segment._bars[0]._extra
    assert "font-size:15px" in extra.styleSheet() and "Consolas" in extra.styleSheet()
    saved = persistence.load_settings()
    assert saved.font_family == "Consolas" and saved.size_detail == 15


def test_default_detail_font_is_bigger_than_before():
    assert persistence.Settings().size_detail >= 12
    assert persistence.Settings().size_hint >= 11


def test_remaining_mode_absolute_reset_and_hidden_pacing(window):
    window._on_snapshot("claude", demo_snapshot("claude"))
    window.update_settings({"number_mode": "remaining", "reset_mode": "absolute", "show_pacing": False})
    segment = window._segments["claude"]
    assert "22%" in segment._value.text() and "livre" in segment._value.text()  # pior janela 78 % usada
    assert "renova" in segment._hint.text() and ":" in segment._hint.text()
    texts = [bar._extra.text() for bar in segment._bars]
    assert not any("dá ~" in t for t in texts)


def test_provider_order_changes_card_stack_order(window):
    window.update_settings({"provider_order": ["zai", "claude"]})
    assert window.provider_ids[:2] == ["zai", "claude"]
    assert window._top_card_rows()[:2] == ["zai", "claude"]


def test_poll_interval_and_invalid_values_are_sanitized(window):
    window.update_settings({"poll_minutes": 5})
    assert window._poll_timer.interval() == 300_000
    window.update_settings({"poll_minutes": 1, "size_detail": 500, "number_mode": "xyz"})
    assert window.settings.poll_minutes == 2
    assert window.settings.size_detail == 28
    assert window.settings.number_mode == "used"


def test_click_through_sets_input_transparency_flag(window):
    window.update_settings({"click_through": True})
    assert window.windowFlags() & Qt.WindowTransparentForInput
    window.update_settings({"click_through": False})
    assert not window.windowFlags() & Qt.WindowTransparentForInput


def test_alert_fires_once_per_window_until_reset(window, monkeypatch):
    sent = []
    monkeypatch.setattr(window, "_notify", lambda title, body: sent.append(title))
    window.update_settings({"alert_percent": 75})
    snapshot = demo_snapshot("claude")  # Semana 78 %
    window._on_snapshot("claude", snapshot)
    window._on_snapshot("claude", snapshot)
    assert len(sent) == 1 and "78%" in sent[0]


def test_hover_opaque_mode_makes_panel_solid(window):
    window.update_settings({"hover_mode": "opaque", "bg_opacity_percent": 40})
    window._hovering = True
    window._apply_hover()
    assert "0.4)" not in window.panel.styleSheet() and "1.0)" in window.panel.styleSheet()


# ------------------------------------------------------------------ janela de configurações


def test_dialog_live_font_change_updates_widget_and_preview_and_undo(window):
    dialog = window.open_settings(show=False)
    dialog.font_combo.setCurrentFont(QFont("Consolas"))
    assert window.settings.font_family == "Consolas"
    assert "Consolas" in dialog.preview.segment._name.styleSheet()
    assert "Consolas" in window._segments["claude"]._name.styleSheet()
    dialog.detail_spin.setValue(16)
    assert window.settings.size_detail == 16
    dialog.undo_changes()
    assert window.settings.font_family == "Segoe UI"
    assert window.settings.size_detail == 12


def test_dialog_reorders_and_toggles_providers(window):
    dialog = window.open_settings(show=False)
    rows = list(window.provider_ids)
    zai = rows.index("zai")
    dialog.provider_list.setCurrentRow(zai)
    dialog.move_selected(-1)
    assert window.provider_ids.index("zai") == zai - 1
    first = dialog.provider_list.item(0)
    first.setCheckState(Qt.Unchecked)
    assert not window.settings.is_visible(first.data(Qt.UserRole))


def test_dialog_restore_visual_defaults(window):
    dialog = window.open_settings(show=False)
    window.update_settings({"font_family": "Consolas", "surface_preset": "papel", "size_value": 30})
    dialog.restore_visual_defaults()
    assert window.settings.font_family == "Segoe UI"
    assert window.settings.surface_preset == "carvao"
    assert window.settings.size_value == 19

import copy
import json
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QFontInfo, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from widget_app import persistence, theme
from widget_app.layout_policy import strip_policy
from widget_app.main_window import MainWindow
from widget_app.quota_focus import duration_label, exhausted_windows, focus_window, general_windows


def quota(key, minutes, used, **kwargs):
    return dict(id=key, label=key, duration_minutes=minutes, used_percent=used,
                resets_at=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(), **kwargs)


def snapshot(windows, **kwargs):
    return dict(status='ok', windows=windows, source='DEMO isolated test',
                fetched_at=datetime.now(timezone.utc).isoformat(), message='', **kwargs)


def test_five_hours_wins_over_worse_or_shorter_window_without_mutating_order():
    windows = [quota('weekly', 10080, 100), quota('short', 60, 80), quota('five', 300, 4)]
    before = copy.deepcopy(windows)
    assert focus_window(windows) is windows[2]
    assert windows == before
    assert exhausted_windows(windows, focus_window(windows)) == [windows[0]]


def test_missing_number_in_five_hours_does_not_fall_back_to_week():
    windows = [quota('week', 10080, 94), quota('five', 300, None)]
    assert focus_window(windows) is windows[1]


def test_fallback_uses_duration_not_usage_reset_or_primary_slot():
    windows = [quota('primary', 10080, 5), quota('secondary', 1440, 10), quota('unknown', None, 100)]
    windows[0]['resets_at'] = '2000-01-01T00:00:00Z'
    assert focus_window(windows) is windows[1]
    assert focus_window([windows[2]]) is windows[2]
    assert duration_label(windows[2]) == 'janela ?'
    assert focus_window([]) is None


@pytest.mark.parametrize('duration', [None, 0, -300, True, '300', float('inf'), float('nan')])
def test_invalid_duration_never_infers_five_hours(duration):
    w = quota('codex:primary', duration, 40)
    w['label'] = '5 h'
    assert duration_label(w) == 'janela ?'


def test_buckets_are_separate_but_exhaustion_is_visible():
    windows = [quota('base_model_inference:primary', 300, 100),
               quota('codex_bengalfox:primary', 300, 80), quota('codex:primary', 10080, 12)]
    assert focus_window(general_windows(windows, 'codex')) is windows[2]
    assert focus_window(general_windows(windows, 'spark')) is windows[1]
    assert focus_window(general_windows(windows, 'codex_gpt2')) is windows[2]
    assert exhausted_windows(windows, windows[2]) == [windows[0]]


def test_migration_preserves_unknown_values_is_idempotent_and_does_not_activate(tmp_path):
    path = persistence.paths.SETTINGS_PATH
    original = {'font_family': 'Consolas', 'window_width': 932, 'window_height': 380,
                'number_mode': 'remaining', 'future': {'nested': [1, 2]}, 'visible_providers': {'spark': False}}
    path.write_text(json.dumps(original), encoding='utf-8')
    before = path.read_bytes()
    loaded = persistence.load_settings()
    assert loaded.visual_mode == 'legacy'
    assert loaded.strip_width == 800 and loaded.strip_height == 72
    assert path.read_bytes() == before
    persistence.save_settings(loaded)
    saved = json.loads(path.read_text(encoding='utf-8'))
    assert all(saved[k] == v for k, v in original.items())
    assert saved['schema_version'] == 2
    assert persistence.migrate_settings(saved) == saved
    persistence.save_settings(persistence.load_settings())
    assert json.loads(path.read_text(encoding='utf-8')) == saved


def test_geometry_policy_uses_capacity_instead_of_wrap():
    assert strip_policy(800, 72, 8).capacity == 4
    assert strip_policy(360, 72, 8).capacity == 1
    assert strip_policy(800, 40, 4).height == 40
    # Superseded 2026-10-11 (ALTURA FIXA DA FAIXA INTEIRA): a large font no
    # longer promotes the height; content scrolls inside the column.
    assert strip_policy(800, 40, 4, line_height=50).height == 40
    assert strip_policy(800, 72, 4, line_height=80).height == 72


def test_compact_header_leaves_room_for_body_at_every_height():
    # Replaces the micro inline-text check: the header font is capped by the
    # strip height (never the reverse) and the scrolling body keeps the rest.
    from widget_app.layout_policy import EDGE, compact_header_px
    for height in range(40, 301):
        inner = height - 2 * EDGE
        for preferred in range(8, 49):
            px = compact_header_px(inner, preferred)
            assert 1 <= px <= preferred
            assert px >= min(preferred, 10)
            assert round(px * 1.45) + 2 <= inner // 2 + 4


@pytest.fixture
def strip_window(qt_app, monkeypatch):
    settings = persistence.Settings(visual_mode='trilho')
    settings.set_visible('spark', False)
    persistence.save_settings(settings)
    window = MainWindow(demo=True)
    monkeypatch.setattr(window, '_available_rect', lambda: QRect(0, 0, 2000, 1200))
    window.show_positioned()
    window.poll_now()
    qt_app.processEvents()
    yield window
    window._session_only = True
    window.close()
    window.deleteLater()


def test_native_800_72_four_providers_and_real_windows_font(strip_window):
    win = strip_window
    assert win.size() == QSize(800, 72)
    assert win.strip.height() == 66  # resize margin 2 + panel border 1 on each side
    assert win.strip.mapTo(win, QPoint(0, 0)) == QPoint(3, 3)
    assert win.strip.policy.capacity == 4
    assert sum(cell.isVisible() for cell in win.strip.cells.values()) == 4
    assert QFontInfo(win.strip.fonts()[0]).family() == 'Segoe UI'
    assert not win.strip.policy.inline
    for cell in win.strip.cells.values():
        if cell.isVisible():
            assert QFontMetrics(win.strip.fonts()[2]).horizontalAdvance(cell.meta) <= cell.width() - 22
            assert win.strip.rect().contains(cell.geometry())
    assert win.header.isHidden() and win.dock.isHidden()


@pytest.mark.parametrize('height', [40, 72, 112])
def test_height_stays_fixed_through_refresh_and_details(strip_window, qt_app, height):
    win = strip_window
    win.update_settings({'strip_height': height})
    qt_app.processEvents()
    assert win.height() == height
    size = win.size()
    win._on_snapshot('claude', snapshot([quota('week', 10080, 100), quota('five', 300, 3)]))
    win._refresh_ages()
    qt_app.processEvents()
    cell = win.strip.cells['claude']
    assert cell.focus['id'] == 'five' and cell.shown == 3
    assert cell.warning_count == 1
    assert 'esgotada' in cell.accessibleName()
    details = win.open_quota_details('claude', cell)
    qt_app.processEvents()
    assert details.isVisible() and len(details.rows) == 2
    assert details.rows[0].text().startswith('week')
    assert win.size() == size
    details.reject()
    qt_app.processEvents()
    assert win.size() == size


def test_keyboard_overflow_enter_escape_focus_and_refresh(strip_window, qt_app):
    win = strip_window
    win.update_settings({'strip_width': 360})
    qt_app.processEvents()
    assert win.strip.policy.capacity == 1
    win.activateWindow()
    first = win.strip.cells[win.strip.order[0]]
    first.setFocus()
    QTest.keyClick(first, Qt.Key_Right)
    qt_app.processEvents()
    second = win.strip.cells[win.strip.order[1]]
    assert second.isVisible() and QApplication.focusWidget() is second
    position, size, start, order = win.pos(), win.size(), win.strip.start, list(win.strip.order)
    win.poll_now()
    win._refresh_ages()
    qt_app.processEvents()
    assert win.pos() == position and win.size() == size
    assert win.strip.start == start and win.strip.order == order
    assert QApplication.focusWidget() is second
    QTest.keyClick(second, Qt.Key_Return)
    qt_app.processEvents()
    dialog = win._quota_details
    assert dialog.isVisible()
    assert dialog.screen().availableGeometry().contains(dialog.frameGeometry())
    QTest.keyClick(dialog, Qt.Key_Escape)
    qt_app.processEvents()
    assert not dialog.isVisible() and QApplication.focusWidget() is second
    QTest.keyClick(second, Qt.Key_End)
    qt_app.processEvents()
    assert win.strip.cells[win.strip.order[-1]].hasFocus()


@pytest.mark.parametrize('used,remaining,label', [(0, False, '0%'), (.2, False, '<1%'), (100, False, '100%'),
                                                  (None, False, '—'), (0, True, '100%'), (100, True, '0%'),
                                                  (99.8, True, '<1%'), (None, True, '—')])
def test_number_and_bar_share_same_value(strip_window, used, remaining, label):
    win = strip_window
    win.update_settings({'number_mode': 'remaining' if remaining else 'used'})
    win._on_snapshot('claude', snapshot([quota('week', 10080, 94), quota('five', 300, used)]))
    cell = win.strip.cells['claude']
    assert cell.focus['id'] == 'five'
    assert f'· {label} ' in cell.accessibleName()
    assert cell.shown == (100 - used if used is not None and remaining else used)
    if used is None:
        assert 'sem dado' in cell.meta


def test_details_use_same_store_all_buckets_and_honest_stale_error(strip_window, qt_app, monkeypatch):
    win = strip_window
    windows = [quota('base_model_inference:primary', 300, 100), quota('codex_bengalfox:primary', 300, 17),
               quota('codex:primary', 10080, 41), quota('codex:secondary', 300, None)]
    win._on_snapshot('codex', snapshot(windows))
    calls = []
    monkeypatch.setattr(win.poller, 'poll', lambda ids: calls.append(ids))
    cell = win.strip.cells['codex']
    assert cell.focus is windows[3]
    QTest.mouseClick(cell, Qt.LeftButton)
    qt_app.processEvents()
    details = win._quota_details
    assert len(details.rows) == 4
    assert 'Reserva · não é uso geral' in details.rows[0].text()
    assert 'Spark · cota separada' in details.rows[1].text()
    rows = list(details.rows)
    error = {'status': 'error', 'windows': [], 'message': 'erro DEMO', 'fetched_at': None}
    win._on_snapshot('codex', error)
    qt_app.processEvents()
    assert details.rows == rows
    assert 'erro DEMO' in details.summary.text() and 'leitura antiga' in details.summary.text()
    assert 'erro' in cell.meta
    assert calls == [] and win.height() == 72


@pytest.mark.parametrize('preset', theme.SURFACE_PRESET_ORDER)
def test_settings_mode_height_preset_undo_legacy_and_persistence(strip_window, qt_app, preset):
    win = strip_window
    win.settings.window_width, win.settings.window_height = 920, 320
    dialog = win.open_settings(show=False)
    dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData(preset))
    dialog.height_combo.setCurrentIndex(dialog.height_combo.findData(112))
    qt_app.processEvents()
    assert win.height() == 112 and win.settings.surface_preset == preset
    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData('legacy'))
    qt_app.processEvents()
    assert not win.strip.isHidden() and win.header.isHidden()
    assert win.settings.visual_mode == 'legacy'  # Compact adaptation preserves the selected mode.
    # Superseded 2026-10-11: one exact "Altura da faixa" in both modes.
    assert win.width() == 920 and win.height() == 112
    dialog.undo_changes()
    qt_app.processEvents()
    assert win.size() == QSize(800, 72)
    assert win.settings.surface_preset == 'carvao'
    win.move(QPoint(65, 80))
    win.update_settings({'strip_width': 600, 'strip_height': 112})
    stored = persistence.load_settings()
    assert (stored.pos_x, stored.pos_y, stored.strip_width, stored.strip_height) == (65, 80, 600, 112)
    other = MainWindow(demo=True, session_only=True)
    other.show_positioned()
    qt_app.processEvents()
    assert other.size() == QSize(600, 112) and other.pos() == QPoint(65, 80)
    other.close()
    other.deleteLater()


def test_large_font_preferences_survive_explicit_compact_overview(strip_window, qt_app):
    win = strip_window
    win.update_settings({'size_name': 22, 'size_value': 36, 'size_hint': 19})
    qt_app.processEvents()
    assert win.height() == 72
    assert [f.pixelSize() for f in win.strip.fonts()] == [22, 36, 19]
    assert (win.settings.size_name, win.settings.size_value, win.settings.size_hint) == (22, 36, 19)
    for cell in win.strip.cells.values():
        if cell.isVisible():
            assert cell.glance.isVisible() and not cell.body.isVisible()
            assert cell.glance.font_px() == 9
            assert 'nome reduzido' in cell.accessibleName()
            assert all(row['widgets'][0].font().pixelSize() == 9 for row in cell.glance.rows)


def test_zero_providers_keeps_menu_and_height(strip_window, qt_app):
    win = strip_window
    win.update_settings({'visible_providers': {pid: False for pid in win.provider_ids}})
    qt_app.processEvents()
    assert win.strip.empty.isVisible() and win.strip.menu.isVisible()
    assert win.height() == 72 and win.strip.counter.text() == '0/0'


def test_navigation_controls_follow_font_family(strip_window, qt_app):
    win = strip_window
    win.update_settings({'font_family': 'Consolas'})
    qt_app.processEvents()
    for widget in (win.strip.counter, win.strip.mode, win.strip.menu):
        assert QFontInfo(widget.font()).family() == 'Consolas'


@pytest.mark.parametrize('height', [40, 72, 112])
@pytest.mark.parametrize('width', [360, 800, 1200])
@pytest.mark.parametrize('count', [1, 4, 8])
def test_density_matrix_never_wraps_and_exposes_all_providers(strip_window, qt_app, height, width, count):
    win = strip_window
    order = list(win.provider_ids)[:count]
    win.update_settings({'visible_providers': {pid: pid in order for pid in win.provider_ids},
                         'strip_height': height, 'strip_width': width})
    win.poll_now()
    qt_app.processEvents()
    assert win.height() == height
    assert win.strip.height() == height - 6
    paged = win.strip.policy.capacity < len(order)
    assert win.strip.counter.isVisible() == paged
    assert win.strip.previous.isVisible() == paged and win.strip.next.isVisible() == paged
    seen = set()
    win.strip.menu.setFocus()
    win.strip.start = 0
    win.strip.arrange()
    for _ in range(count):
        cells = [cell for cell in win.strip.cells.values() if cell.isVisible()]
        assert all(cell.y() == 0 and cell.height() == height - 6 for cell in cells)
        assert all(win.strip.rect().contains(cell.geometry()) for cell in cells)
        seen.update(cell.row_id for cell in cells)
        if not win.strip.next.isEnabled():
            break
        win.strip.next.click()
    assert seen == set(order)


def test_trilho_refuses_click_through_without_tray(strip_window, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, 'isSystemTrayAvailable', lambda: False)
    strip_window.update_settings({'click_through': True})
    assert not strip_window.settings.click_through
    assert not strip_window.windowFlags() & Qt.WindowTransparentForInput


def test_tray_action_recovers_input_transparency(qt_app, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, 'isSystemTrayAvailable', lambda: True)
    persistence.save_settings(persistence.Settings(visual_mode='trilho'))
    win = MainWindow(demo=True, session_only=True)
    win.show_positioned()
    win.update_settings({'click_through': True})
    assert win.windowFlags() & Qt.WindowTransparentForInput
    assert win._tray.isVisible()
    win._tray_click_action.trigger()
    assert not win.windowFlags() & Qt.WindowTransparentForInput
    win.close()
    win.deleteLater()


def test_strip_mouse_width_save_does_not_replace_legacy_geometry(strip_window, qt_app):
    win = strip_window
    win.settings.window_width, win.settings.window_height = 917, 333
    win._user_resize_active = True
    win.resize(650, 72)
    qt_app.processEvents()
    win._finish_user_resize()
    saved = persistence.load_settings()
    assert saved.strip_width == 650
    assert (saved.window_width, saved.window_height) == (917, 333)


def test_details_constrained_screen_long_text_scroll_and_keyboard(strip_window, qt_app, monkeypatch):
    win = strip_window
    windows = [quota('Modelo com contexto longo ' + str(i), 300 + i, i) for i in range(30)]
    data = snapshot(windows)
    data['source'] = 'DEMO/' + 'origem-sem-espacos/' * 30
    win._on_snapshot('claude', data)
    anchor = win.strip.cells['claude']
    class SmallScreen:
        def availableGeometry(self):
            return QRect(0, 0, 390, 640)
    monkeypatch.setattr(anchor, 'screen', lambda: SmallScreen())
    details = win.open_quota_details('claude', anchor)
    qt_app.processEvents()
    assert QRect(0, 0, 390, 640).contains(details.frameGeometry())
    assert len(details.rows) == 30
    assert details.scroll.verticalScrollBar().maximum() > 0
    details.scroll.setFocus()
    QTest.keyClick(details.scroll, Qt.Key_End, Qt.ControlModifier)
    qt_app.processEvents()
    scroll_before = details.scroll.verticalScrollBar().value()
    win._refresh_ages()
    qt_app.processEvents()
    assert details.scroll.verticalScrollBar().value() == scroll_before
    assert win.height() == 72

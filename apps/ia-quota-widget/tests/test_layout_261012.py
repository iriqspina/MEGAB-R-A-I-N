"""Layout 261012 (síntese do teste cego): pílulas coloridas sob o nome,
tabela de janelas em largura total e número do cabeçalho colorido pelo ritmo."""
from PySide6.QtGui import QColor

from widget_app import theme
from widget_app.ui_glance_quota import has_value, is_primary, pill_text
from widget_app.glance_contract import GlanceEntry
from tests.test_glance_quota import real_window  # noqa: F401  (fixture real, datada)


def test_has_value_separates_positive_from_zero_and_unknown():
    assert has_value('1/1') and has_value('USD 250') and has_value('sem limite')
    assert not has_value('0') and not has_value('BRL 0') and not has_value('USD 0 + 0')
    assert not has_value('—') and not has_value('n/d') and not has_value('0 cr')


def test_pill_color_is_the_information_type_in_every_provider():
    resets = [GlanceEntry('reset:0', '♻ Estoque', '1', ''), GlanceEntry('reset:0', '♻ Completo*', '1/1', ''),
              GlanceEntry('reset:unknown', '♻ Resets', '—', '')]
    assert {theme.chip_kind(i.id, i.label) for i in resets} == {'reset'}
    assert theme.chip_kind('balance:0', 'Nuvem') == 'cloud'
    assert theme.chip_kind('balance:0', 'Extra') == theme.chip_kind('browser:balance', 'Extra*') == 'extra'
    assert theme.chip_kind('browser:balance', 'API*') == 'api'
    colors = list(theme.CHIP_COLORS_DARK.values())
    assert len(set(colors)) == len(colors)
    # Pill hues never reuse pacing state colors (lesson 260822: state ≠ category).
    assert not set(c.lower() for c in colors) & {theme.STATUS_GREEN, theme.STATUS_AMBER, theme.STATUS_RED}


def test_manual_star_becomes_dashed_outline_not_text():
    item = GlanceEntry('reset:0', '♻ Completo*', '1/1', '', manual_date='2026-10-12T14:29:19Z')
    assert pill_text(item) == '♻ Completo 1/1'
    assert not is_primary(GlanceEntry('balance:plan', 'Plano', '—', ''))
    assert not is_primary(GlanceEntry('browser:parts', 'Caixa+bônus', 'USD 0 + 0', ''))


def test_pills_sit_under_the_name_and_windows_use_full_width(real_window, qt_app):
    win = real_window
    for cell in (c for c in win.strip.cells.values() if c.isVisible()):
        glance = cell.glance
        pills = [r['widgets'][0] for r in glance.rows if not r['quota'] and r['shown']]
        quotas = [r for r in glance.rows if r['quota']]
        assert pills and all(p.y() == 0 for p in pills)
        first_row = min(r['widgets'][0].y() for r in quotas)
        assert all(p.geometry().bottom() < first_row for p in pills)
        # Bars span the column: no wallet column on the right any more.
        for row in quotas:
            bar = row['widgets'][1]
            assert bar.geometry().right() > glance.width() * 0.55
        # Primary information never folds at the human width.
        assert all(not is_primary(i) for i in glance.hidden_items)
        if glance.hidden_items:
            assert glance.more.isVisible() and glance.more.text() == f'+{len(glance.hidden_items)}'
            assert all(pill_text(i) in glance.more.toolTip() for i in glance.hidden_items)


def test_filled_pill_has_tint_and_empty_pill_only_outline(real_window, qt_app):
    win = real_window
    for cell in win.strip.cells.values():
        for row in cell.glance.rows:
            if row['quota'] or not row['shown']:
                continue
            style = row['widgets'][0].styleSheet()
            filled = has_value(row['item'].value)
            assert ('background:transparent' in style) != filled
            assert ('dashed' in style) == (bool(row['item'].manual_date) or row['item'].label.endswith('*'))


def test_hero_color_follows_real_pacing_and_alert(real_window, qt_app):
    win = real_window
    cell = win.strip.cells['codex']
    windows = (win.store.display('codex') or {}).get('windows') or []
    ids = [w['id'] for w in windows]
    win._pacing_by_provider['codex'] = {'status': 'desacelerar', 'windows': {i: {'status': 'desacelerar'} for i in ids}}
    cell.refresh()
    if cell.shown is not None and cell.shown > 100 - win.settings.alert_percent:
        assert cell.tone == 'amber' and 'desacelerar' in cell.tone_reason
    win._pacing_by_provider['codex'] = {'status': 'ok', 'windows': {i: {'status': 'ok'} for i in ids}}
    cell.shown = 100 - win.settings.alert_percent  # exatamente no limiar do alerta
    tone, reason = cell.hero_tone(win, windows)
    assert tone == 'red' and 'alerta' in reason
    assert QColor(win._palette()['status']['red']).isValid()

"""Layout 261012 (síntese do teste cego): pílulas coloridas sob o nome,
tabela de janelas em largura total e número do cabeçalho colorido pelo ritmo."""
import pytest
from datetime import datetime,timedelta,timezone
from PySide6.QtGui import QColor

from widget_app import theme
from widget_app.ui_glance_quota import GlanceView, has_value, is_primary, pill_text
from widget_app.glance_contract import GlanceEntry
from tests.test_audit_261012 import fixed_now  # noqa: F401 (scoped formatting clock)
from tests.test_glance_quota import real_window  # noqa: F401  (fixture real, datada)


@pytest.mark.parametrize('value, expected', [
    ('0/1', False), ('0/2 retido', False), ('0/2', False),
    ('1/1', True), ('1/2 retido', True), ('1/1 retido', True),
    (' 0 / 2 retido ', False), (' 1 / 2 retido ', True),
    ('—/1', False), ('—', False), ('n/d', False), (None, False),
    ('USD 250', True), ('BRL 0,50', True), ('sem limite', True),
    ('0', False), ('BRL 0', False), ('0 cr', False),
    ('USD 0 + 0', False), ('USD 0 + 5', True),
    # Each fraction contributes its count, never its total, in any composition.
    ('0/2+0', False), ('0/2+5', True), ('1/2+0', True),
    ('0/2retido+0', False), ('1/2retido+0', True),
    ('0/2+0/5', False), ('0/2+1/5', True),
    ('0/2 + 0', False), ('0/2 + 5', True), ('1/2 + 0', True),
    ('0/2 retido + 0', False), ('1/2 retido + 0', True),
    ('0/2 + 0/5', False), ('0/2 + 1/5', True),
    ('USD 0/250 + 0', False), ('USD 0/250 + 5', True),
])
def test_has_value_separates_positive_from_zero_and_unknown(value, expected):
    assert has_value(value) is expected


@pytest.fixture
def stock_glance(qt_app):
    view = GlanceView(None)
    view.resize(1200, 180)
    view.show()
    yield view
    view.close()
    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize('manual', [False, True])
@pytest.mark.parametrize('kind, count, total, usable, value, filled, tooltip', [
    ('full', 0, 1, False, '0/1', False, 'Indisponível agora.'),
    ('full', 0, 2, False, '0/2', False, 'Indisponível agora.'),
    ('full', 1, 1, True, '1/1', True, 'Disponível agora.'),
    ('full', 1, 1, False, '1/1 retido', True, 'Indisponível agora.'),
    ('full', 1, 2, False, '1/2 retido', True, 'Indisponível agora.'),
    ('full', None, 1, False, '—', False, 'Indisponível agora.'),
    ('account', 1, 2, False, '1/2', True, 'Estoque gratuito sujeito à elegibilidade; não significa uso imediato.'),
])
def test_stock_pills_keep_count_fill_availability_and_manual_outline(
        stock_glance, qt_app, manual, kind, count, total, usable, value, filled, tooltip):
    stamp = datetime.now(timezone.utc).isoformat()
    reset = {'kind': kind, 'count': count, 'total': total, 'usable': usable,
             'expires_at': (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}
    display = {'status': 'ok', 'fetched_at': stamp, 'windows': [],
               'details': {'resets': [] if manual else [reset]}}
    browser = {'resets': [reset], 'reset_observed_at': stamp} if manual else None
    if manual:display['fetched_at']=None  # isolated manual source; no newer poll
    stock_glance.set_data('codex_gpt2', display, number_mode='remaining', reset_mode='relative',
                          browser=browser, name='Codex 2', palette={'text_secondary': '#a7b0c4'}, family='Inter')
    qt_app.processEvents()
    row, = [r for r in stock_glance.rows if r['item'].id == 'reset:0']
    label = row['widgets'][0]
    assert row['shown'] and label.isVisible()
    assert row['item'].value == value
    assert label.text() == pill_text(row['item'])
    style = label.styleSheet()
    assert ('background:transparent;' in style) is (not filled)
    assert ('background:rgba(' in style) is filled
    assert f'border:1px {"dashed" if manual else "solid"} ' in style
    assert label.toolTip() == row['item'].tooltip
    assert label.toolTip().startswith(tooltip)
    assert ('Navegador, verificado' in label.toolTip()) is manual
    assert row['item'].manual_date == (stamp if manual else '')


def test_zero_retained_literal_is_also_unfilled_in_glance(stock_glance, monkeypatch):
    # Current overview emits '0/2' for zero stock. Exercise the supported
    # 'retido' text directly as well, without changing its production contract.
    tooltip = 'Indisponível agora. Total 2; validade 21/10/2026 09:00 BRT.'
    item = GlanceEntry('reset:0', '♻ Completo', '0/2 retido', tooltip, 'reset')
    monkeypatch.setattr('widget_app.ui_glance_quota.overview', lambda *args, **kwargs: ([], [item]))
    stock_glance.set_data('codex_gpt2', None, number_mode='remaining', reset_mode='relative',
                          browser=None, name='Codex 2', palette={'text_secondary': '#a7b0c4'}, family='Inter')
    row, = stock_glance.rows
    label = row['widgets'][0]
    assert row['shown'] and label.isVisible()
    assert label.text() == '♻ Completo 0/2 retido'
    assert 'background:transparent;' in label.styleSheet()
    assert 'border:1px solid ' in label.styleSheet()
    assert label.toolTip() == tooltip


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


def test_pills_sit_under_the_name_and_windows_use_full_width(fixed_now, real_window, qt_app):
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


def test_filled_pill_has_tint_and_empty_pill_only_outline(fixed_now, real_window, qt_app):
    win = real_window
    for cell in win.strip.cells.values():
        for row in cell.glance.rows:
            if row['quota'] or not row['shown']:
                continue
            style = row['widgets'][0].styleSheet()
            filled = has_value(row['item'].value)
            assert ('background:transparent' in style) != filled
            assert ('dashed' in style) == (bool(row['item'].manual_date) or row['item'].label.endswith('*'))


def test_hero_color_follows_real_pacing_and_alert(fixed_now, real_window, qt_app):
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

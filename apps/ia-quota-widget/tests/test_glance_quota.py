"""No-scroll reading contract: real dated snapshot, geometry and wallet semantics."""
import copy
import json
from pathlib import Path
import pytest
from PySide6.QtCore import QPoint,QRect, Qt, QTimer
from PySide6.QtGui import QFontDatabase, QFontInfo,QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QScrollArea
from widget_app import persistence
from widget_app.glance_contract import overview
from widget_app.main_window import MainWindow
from widget_app.ui_glance_quota import GlanceView


def snap(amount=None, used=None):
    return {'status':'ok','windows':[{'id':'session','duration_minutes':300,'used_percent':used}],
            'details':{'financial':[{'title':'Créditos de uso','currency':'BRL','amount':amount}], 'resets':[]}}


@pytest.mark.parametrize('value',[None,float('nan'),float('inf'),True])
def test_unknown_money_and_quota_never_become_zero(value):
    quotas,items=overview('claude',snap(value,value),number_mode='remaining')
    assert quotas[0].percent is None
    assert next(i for i in items if i.kind=='balance').value=='—'
    assert next(i for i in items if i.kind=='reset').value=='—'


def test_zero_and_positive_money_keep_units_and_dated_source():
    data=snap(None,0); before=copy.deepcopy(data)
    browser={'balance':1234.5,'currency':'BRL','scope':'créditos de uso','observed_at':'2026-10-11T21:00:00-03:00','source':'https://claude.ai/settings/billing'}
    quotas,items=overview('claude',data,browser=browser,number_mode='remaining')
    assert quotas[0].percent==100 and data==before
    balances=[i for i in items if i.kind=='balance']
    assert len(balances)==1 and balances[0].label=='Extra*'
    assert balances[0].value=='BRL 1 234,50' and balances[0].manual_date==browser['observed_at']
    assert browser['source'] in balances[0].tooltip and '11/10' in balances[0].tooltip
    _,zero=overview('claude',snap(0,0));assert next(i for i in zero if i.kind=='balance').value=='BRL 0'


def test_expenses_and_ceiling_are_not_wallets_and_reset_stock_is_conditional():
    data=snap(0,1)
    data['details']['financial'] += [{'title':'Gasto neste período','amount':90,'currency':'USD'}, {'title':'Teto mensal','amount':1200,'currency':'BRL'}]
    data['details']['resets']=[{'kind':'account','count':1,'usable':False},{'kind':'full','count':1,'total':2,'usable':False}]
    _,items=overview('claude',data)
    assert len([i for i in items if i.kind=='balance'])==1
    assert 'elegibilidade' in items[0].tooltip and items[0].value=='1'
    assert items[1].value=='1/2 retido'


def test_plan_api_cash_bonus_are_separate_and_dates_not_freshened():
    browser={'balance':7,'currency':'USD','cash':2,'bonus':5,'observed_at':'2026-10-11T19:00:00-03:00',
             'reset_observed_at':'2026-10-10T18:00:00-03:00','resets':[{'kind':'full','count':1,'usable':True}]}
    _,items=overview('zai',{'status':'ok','windows':[],'details':{}},browser=browser)
    byid={i.id:i for i in items}
    assert byid['balance:plan'].value=='—' and byid['browser:balance'].value=='USD 7'
    assert byid['browser:parts'].value=='USD 2 + 5'
    assert byid['reset:0'].manual_date==browser['reset_observed_at']
    assert byid['browser:balance'].manual_date==browser['observed_at']


@pytest.fixture
def real_window(qt_app,monkeypatch,tmp_path):
    # Same locally captured provider schema as production; dates remain historical.
    source=Path(__file__).resolve().parent/'fixtures'
    cache=json.loads((source/'glance_snapshot.json').read_text(encoding='utf-8'))
    (tmp_path/'account_balance_observed.json').write_bytes((source/'glance_browser.json').read_bytes())
    for folder in (Path('C:/Windows/Fonts'),Path('<USER_HOME>/AppData/Local/Microsoft/Windows/Fonts')):
        for file in folder.glob('Inter-*.ttf'):QFontDatabase.addApplicationFont(str(file))
    s=persistence.Settings(visual_mode='trilho',strip_width=1038,strip_height=112,font_family='Inter',size_name=32,size_value=28,size_hint=9,size_detail=18,scale=.8)
    s.set_visible('spark',False);s.window_width=1038;s.expanded=False
    persistence.save_settings(s)
    win=MainWindow(session_only=True)
    monkeypatch.setattr(win,'_available_rect',lambda:QRect(0,0,2400,1600))
    monkeypatch.setattr(win.poller,'poll',lambda ids:None)
    for pid,data in cache['providers'].items():win._on_snapshot(pid,data)
    win.show_positioned();qt_app.processEvents()
    yield win
    for timer in win.findChildren(QTimer):timer.stop()
    win.close();win.deleteLater()


@pytest.mark.parametrize('mode',['trilho','legacy'])
@pytest.mark.parametrize('width,height',[(1038,112),(1080,72)])
@pytest.mark.parametrize('scale',[.8,1])
def test_all_quotas_resets_balances_are_visible_without_scrolling(real_window,qt_app,mode,width,height,scale):
    win=real_window
    win.update_settings({'visual_mode':mode,'strip_width':width,'window_width':width,'strip_height':height,'scale':scale})
    qt_app.processEvents();win._refresh_ages();qt_app.processEvents()
    assert win.height()==height and win.strip.isVisible()
    assert not win.strip.counter.isVisible() and len([c for c in win.strip.cells.values() if c.isVisible()])==4
    views=[c.glance for c in win.strip.cells.values() if c.isVisible()]
    assert sum(len(v.quotas) for v in views)==8
    assert not any(s.isVisible() for s in win.findChildren(QScrollArea))
    for v in views:
        assert v.isVisible() and v.fits and not v.warning.isVisible()
        assert QFontInfo(v.rows[0]['widgets'][0].font()).family()=='Inter'
        assert all(r['contained'] and r['text_fits'] for r in v.geometry_checks())
        assert all(i.kind in ('reset','balance') for i in v.items)
    items=[i for v in views for i in v.items]
    assert any(i.label=='Completo*' or 'Completo*' in i.label for i in items)
    assert any(i.value=='USD 250' for i in items) and any(i.label=='API*' for i in items)


def test_theme_refresh_preserves_geometry_and_enter_details(real_window,qt_app):
    win=real_window;cell=win.strip.cells['claude'];before=cell.glance.geometry()
    for surface in ('papel','meia_noite'):
        if surface in __import__('widget_app.theme',fromlist=['SURFACE_PRESETS']).SURFACE_PRESETS:
            win.update_settings({'surface_preset':surface});win._refresh_ages();qt_app.processEvents()
            assert cell.glance.geometry()==before and cell.glance.fits and win.height()==112
    win.activateWindow();cell.setFocus();QTest.keyClick(cell,Qt.Key_Return);qt_app.processEvents()
    assert win._quota_details.isVisible() and win.height()==112


def test_large_money_pages_accounts_without_truncating_values(real_window,qt_app):
    win=real_window;data=copy.deepcopy(win.store.display('claude'))
    data['details']['financial'][0]['amount']=1e30
    win._on_snapshot('claude',data);qt_app.processEvents()
    assert win.height()==112 and win.strip.counter.isVisible()
    win.strip.start=win.strip.order.index('claude');win.strip.arrange();qt_app.processEvents()
    v=win.strip.cells['claude'].glance
    assert v.isVisible() and v.fits
    assert any(len(r['text'])>40 and 'Nuvem' in r['text'] for r in v.geometry_checks())
    assert all(r['text_fits'] and r['contained'] for r in v.geometry_checks())


def test_settings_survive_isolated_relaunch(real_window,qt_app):
    win=real_window;path=persistence.paths.SETTINGS_PATH
    before=path.read_bytes();win.close();qt_app.processEvents()
    assert path.read_bytes()==before
    relaunched=MainWindow(session_only=True);relaunched.show_positioned();qt_app.processEvents()
    assert relaunched.settings.strip_height==112 and relaunched.settings.font_family=='Inter'
    relaunched.close();qt_app.processEvents();assert path.read_bytes()==before


@pytest.mark.parametrize('expanded',[False,True])
def test_large_legacy_keeps_overview_inside_first_view(real_window,qt_app,expanded):
    win=real_window
    win.update_settings({'visual_mode':'legacy','window_width':1440,'window_height':300,'strip_height':300,'expanded':expanded})
    qt_app.processEvents();win._refresh_all_segments();qt_app.processEvents()
    assert win.height()==300 and win._board.isVisible()
    viewport=win._board.viewport()
    for pid,segment in win._segments.items():
        if not segment.isVisible():continue
        v=segment.glance
        assert v.fits and v.isVisible()
        for row in v.rows:
            for child in row['widgets']:
                assert viewport.rect().contains(QRect(child.mapTo(viewport,QPoint(0,0)),child.size()))
        assert segment._fields.isVisible()==expanded


def test_empty_single_and_long_names_have_explicit_navigation(real_window,qt_app):
    win=real_window
    for pid in win.provider_ids:win.settings.set_visible(pid,False)
    win._rebuild_segments();qt_app.processEvents()
    assert win.strip.empty.isVisible() and win.height()==112
    win.settings.set_visible('claude',True);win._rebuild_segments();qt_app.processEvents()
    assert win.strip.cells['claude'].glance.fits and not win.strip.counter.isVisible()
    for pid in ('codex','codex_gpt2','zai'):win.settings.set_visible(pid,True)
    win._canonical_labels['codex']='Conta Codex com nome excepcionalmente longo'
    win._rebuild_segments();qt_app.processEvents()
    assert win.strip.counter.isVisible()
    for c in win.strip.cells.values():
        if c.isVisible():assert c.width()>=c.header_required_width()


@pytest.mark.parametrize('browser_value',[None,12.5])
@pytest.mark.parametrize('automatic_value',[0,45.5])
def test_known_automatic_extra_is_not_replaced_by_manual_unknown_or_old_value(browser_value,automatic_value):
    browser={'balance':browser_value,'currency':'BRL','scope':'créditos de uso','observed_at':'2026-10-11T21:00:00-03:00'}
    _,items=overview('claude',snap(automatic_value,10),browser=browser)
    balances=[i for i in items if i.kind=='balance']
    assert len(balances)==1 and balances[0].label=='Extra'
    assert balances[0].value==('BRL 0' if automatic_value==0 else 'BRL 45,50')
    assert not balances[0].manual_date

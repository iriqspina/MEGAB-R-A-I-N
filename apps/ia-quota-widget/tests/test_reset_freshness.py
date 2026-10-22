"""Regression: a 13 October manual reset must not become live stock on the 21st."""
from datetime import datetime,timedelta,timezone
import json
import pytest
from quota_details_data import claude_details,codex_details,resolve_resets,sanitize_details,reset_summary
from widget_app.inline_contract import provider_fields
from widget_app.glance_contract import overview
from widget_app.snapshot_store import SnapshotStore
from widget_app.providers_bridge import normalize_snapshot

NOW=datetime(2026,10,21,18,0,tzinfo=timezone.utc)
OLD='2026-10-13T17:05:30+00:00'
OFFER={'title':'Reset completo','kind':'full','count':1,'total':1,'usable':True,'expires_at':'2026-10-22T16:00:00Z'}
BROWSER={'resets':[OFFER],'reset_observed_at':OLD,'observed_at':OLD}

@pytest.mark.parametrize('payload,status',[({},'unknown'),({'cedar_ember':None},'unknown'),({'cedar_ember':{'grants':[]}},'none'),({'cedar_ember':{'grants':[{'resets_left':None}]}},'unknown')])
def test_absence_is_not_zero(payload,status):
    details=sanitize_details(claude_details(payload))
    assert details['resets_status']==status

@pytest.mark.parametrize('details',[
    {'resets':[]}, {'resets':[],'resets_status':'unknown'},
    {'resets':[OFFER],'resets_status':'reported'},
])
def test_old_stock_never_counts_as_current(details):
    result=resolve_resets(details,BROWSER,fetched_at=OLD,now=NOW)
    assert result['current']==[] and result['status']=='unknown'
    assert result['history'][0]['count']==1

def test_current_explicit_empty_beats_old_browser_and_survives_restart(tmp_path):
    details=sanitize_details(claude_details({'cedar_ember':{'grants':[]}}))
    stamp=datetime.now(timezone.utc).isoformat()
    raw={'status':'ok','fetched_at':stamp,'windows':[{'id':'session','used_percent':2,'duration_minutes':300}],'details':details}
    cache=tmp_path/'snapshot.json'
    store=SnapshotStore(cache);store.update('claude',normalize_snapshot('claude',raw))
    assert resolve_resets(store.display('claude')['details'],BROWSER,fetched_at=stamp)['current'][0]['count']==0
    loaded=SnapshotStore(cache).display('claude')
    assert loaded['details']['resets_status']=='none'
    assert resolve_resets(loaded['details'],BROWSER,fetched_at=loaded['fetched_at'],stale=loaded['stale'])['current']==[]
    assert json.loads(cache.read_text())['providers']['claude']['details']['resets_status']=='none'

def test_zero_reported_keeps_total_and_expired_offer_is_history():
    zero={**OFFER,'count':0,'usable':False}
    current=resolve_resets({'resets':[zero]},BROWSER,fetched_at=NOW.isoformat(),now=NOW)
    assert reset_summary({'resets':current['current']})=='0'
    expired=resolve_resets({'resets':[{**OFFER,'expires_at':OLD}]},fetched_at=NOW.isoformat(),now=NOW)
    assert expired['current']==[] and expired['status']=='expired' and expired['history'][0]['expired']

@pytest.mark.parametrize('state',['ok','error','cached'])
def test_both_board_contracts_reject_old_browser_in_all_states(state):
    display={'status':state,'stale':state!='ok','fetched_at':datetime.now(timezone.utc).isoformat(),'windows':[],'details':{'resets':[]}}
    fields=provider_fields('claude',display,browser=BROWSER)
    assert all('1/1' not in f.text and 'disponível' not in f.text for f in fields if f.kind=='reset')
    _,items=overview('claude',display,browser=BROWSER)
    assert [i.value for i in items if i.kind=='reset']==['—']

def test_manual_offer_requires_own_recent_clock_future_expiry_and_no_newer_poll():
    browser={**BROWSER,'reset_observed_at':NOW.isoformat()}
    result=resolve_resets({},browser,now=NOW)
    assert result['source']=='browser' and result['current']==[OFFER]
    assert not resolve_resets({},browser,fetched_at=(NOW+timedelta(seconds=1)).isoformat(),now=NOW+timedelta(seconds=2))['current']
    assert not resolve_resets({},browser,now=NOW+timedelta(days=2))['current']
    assert not resolve_resets({},{**browser,'unavailable':True},now=NOW)['current']

def test_codex_zero_is_explicit_but_missing_credit_is_unknown():
    assert codex_details({'rateLimitResetCredits':{'availableCount':0}})['resets_status']=='reported'
    assert codex_details({})['resets_status']=='unknown'

def test_wallet_timestamp_does_not_renew_undated_reset():
    browser={'resets':[OFFER],'observed_at':NOW.isoformat()}
    assert resolve_resets({},browser,now=NOW)['current']==[]

def test_old_codex_availability_note_is_removed_from_restart_data():
    details=codex_details({'rateLimitResetCredits':{'availableCount':2}})
    assert not details['notes']
    old={'resets':[OFFER],'notes':['Redefinições gratuitas disponíveis: 2.','Outra nota']}
    assert sanitize_details(old)['notes']==['Outra nota']

@pytest.mark.parametrize('mode',['trilho','legacy'])
def test_actual_widgets_share_unknown_and_preserve_dated_history(qt_app,tmp_path,monkeypatch,mode):
    from widget_app import persistence
    from widget_app.main_window import MainWindow
    from widget_app.providers_bridge import ProviderPoller
    monkeypatch.setattr(ProviderPoller,'poll',lambda *a,**k:None)
    (tmp_path/'account_balance_observed.json').write_text(json.dumps({'accounts':{'claude':BROWSER}}),encoding='utf-8')
    persistence.save_settings(persistence.Settings(visual_mode=mode))
    win=MainWindow(demo=False,session_only=True)
    raw={'status':'ok','fetched_at':datetime.now(timezone.utc).isoformat(),'windows':[{'id':'session','duration_minutes':300,'used_percent':3}],'details':claude_details({})}
    win._on_snapshot('claude',normalize_snapshot('claude',raw));win.show_positioned();qt_app.processEvents()
    cell=win.strip.cells['claude']
    assert cell.reset_count=='—'
    assert all('1/1' not in f.text for f in cell.fields if f.kind=='reset')
    segment=win._segments['claude']
    assert any('não confirmado' in t for t in segment._fields.texts())
    detail=win.open_quota_details('claude');qt_app.processEvents()
    assert 'Resets atuais: — não confirmado' in detail.extras.text()
    assert 'histórico do navegador' in detail.extras.text() and '13/10/2026' in detail.extras.text()
    detail.close()
    comparison=win.open_quota_details('all');qt_app.processEvents()
    assert 'Resets atuais: — não confirmado' in comparison.copy_text
    assert 'histórico do navegador' in comparison.copy_text
    comparison.close();win.close();win.deleteLater()

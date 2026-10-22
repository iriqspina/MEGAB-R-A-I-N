from datetime import datetime,timezone,timedelta
import copy,json,subprocess,sys
from pathlib import Path
import pytest
from widget_app import paths,account_state
from widget_app.scheduled_refresh import run_once
from widget_app.snapshot_store import SnapshotStore
from json_io import update_json


def reading(provider='claude',*,stamp=None,used=17):
    return {'provider':provider,'status':'ok','source':'official.test','fetched_at':stamp or datetime.now(timezone.utc).isoformat(),
            'windows':[{'id':'session','used_percent':used,'duration_minutes':300}],
            'details':{'resets':[],'resets_status':'unknown'}}


@pytest.fixture(autouse=True)
def reset_account_cache(monkeypatch):
    monkeypatch.setattr(account_state,'_cache',{'lido_em':0.,'dados':{}})


def test_collects_without_models_and_preserves_browser_original(tmp_path):
    original={'accounts':{'claude':{'reset_observed_at':'2026-10-13T10:00:00Z','resets':[{'count':1,'usable':True}]}}}
    observed=tmp_path/'account_balance_observed.json';observed.write_text(json.dumps(original))
    before=observed.read_bytes();calls=[]
    def fetch(provider):calls.append(provider);return reading(provider)
    result=run_once(fetch=fetch)
    assert calls==['codex','claude','zai'] and result['status']=='complete'
    assert result['model_calls']==0 and not result['browser_observations_updated']
    assert observed.read_bytes()==before
    assert result['providers']['claude']['resets_status']=='unknown'
    assert json.loads(paths.CACHE_PATH.read_text())['providers']['claude']['details']['resets']==[]
    assert 'codex' in json.loads(paths.BUDGET_STATUS_PATH.read_text())


def test_failed_attempt_keeps_last_good_dates_and_success_time():
    good=run_once(fetch=lambda p:reading(p))
    cache=paths.CACHE_PATH.read_bytes();budget=paths.BUDGET_STATUS_PATH.read_bytes()
    failed=run_once(fetch=lambda p:{'status':'rate_limited','windows':[],'fetched_at':None})
    assert failed['status']=='failed' and cache==paths.CACHE_PATH.read_bytes() and budget==paths.BUDGET_STATUS_PATH.read_bytes()
    assert failed['providers']['claude']['last_success_at']==good['providers']['claude']['last_success_at']
    assert all(row['status']=='rate_limited' for row in failed['providers'].values())


def test_canceled_accounts_are_not_queried():
    paths.BUDGET_STATUS_PATH.write_text(json.dumps({'estados_conta':{'claude':{'estado':'cancelado'}}}))
    calls=[]
    def fetch(p):calls.append(p);return reading(p)
    result=run_once(fetch=fetch)
    assert calls==['codex','zai'] and result['providers']['claude']['status']=='skipped_account'
    assert json.loads(paths.BUDGET_STATUS_PATH.read_text())['estados_conta']['claude']['estado']=='cancelado'


def test_budget_failure_is_not_mistaken_for_old_success(monkeypatch):
    from widget_app import budget_status
    good=run_once(fetch=lambda p:reading(p))
    old=paths.BUDGET_STATUS_PATH.read_bytes()
    monkeypatch.setattr(budget_status,'write',lambda *a:False)
    failed=run_once(fetch=lambda p:reading(p,used=40))
    assert failed['status']=='failed' and paths.BUDGET_STATUS_PATH.read_bytes()==old
    assert all(r['status']=='storage_error' for r in failed['providers'].values())
    assert failed['providers']['claude']['last_success_at']==good['providers']['claude']['last_success_at']


@pytest.mark.parametrize('fault',['empty','undated','old','future','unknown'])
def test_invalid_ok_does_not_replace_good_reading(fault):
    run_once(fetch=lambda p:reading(p));before=paths.CACHE_PATH.read_bytes()
    def fetch(p):
        value=reading(p)
        if fault=='empty':value['windows']=[]
        if fault=='undated':value['fetched_at']=None
        if fault=='old':value['fetched_at']=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        if fault=='future':value['fetched_at']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        if fault=='unknown':value['windows'][0]['used_percent']=None
        return value
    result=run_once(fetch=fetch)
    assert result['status']=='failed' and paths.CACHE_PATH.read_bytes()==before


def test_two_stale_stores_merge_accounts_and_preserve_newer_timestamp(tmp_path):
    cache=tmp_path/'shared.json';first=SnapshotStore(cache);second=SnapshotStore(cache)
    old=reading(stamp='2026-10-20T10:00:00Z');new=reading(stamp='2026-10-21T10:00:00Z',used=45)
    first.update('claude',new);second.update('codex',reading('codex'));second.update('claude',old)
    saved=json.loads(cache.read_text())['providers']
    assert set(saved)=={'claude','codex'} and saved['claude']['windows'][0]['used_percent']==45


def test_empty_ok_does_not_destroy_last_good_memory_after_error():
    store=SnapshotStore();store.update('claude',reading())
    store.update('claude',{'status':'ok','fetched_at':datetime.now(timezone.utc).isoformat(),'windows':[]})
    store.update('claude',{'status':'error'})
    assert store.display('claude')['windows'][0]['used_percent']==17


def test_shared_json_transaction_does_not_lose_other_processes(tmp_path):
    path=tmp_path/'shared.json';module_dir=str(Path(__file__).resolve().parents[1])
    code='import sys;sys.path.insert(0,sys.argv[1]);from json_io import update_json;from pathlib import Path;update_json(Path(sys.argv[2]),lambda d:dict(d,**{sys.argv[3]:1}))'
    workers=[subprocess.Popen([sys.executable,'-c',code,module_dir,str(path),str(i)]) for i in range(6)]
    assert all(p.wait(timeout=15)==0 for p in workers)
    assert len(json.loads(path.read_text()))==6


def test_routine_status_is_visible_without_claiming_browser_refresh(tmp_path):
    from widget_app.observed_info import balance_evidence_sections
    (tmp_path/'quota_refresh.json').write_text(json.dumps({'kind':'windows_task_scheduler','scope':['codex']}))
    run_once(fetch=lambda p:reading(p))
    text=str(balance_evidence_sections('codex',tmp_path))
    assert '09:00 e 21:00' in text and 'sem IA' in text and 'histórico do navegador mantém sua data' in text

"""Twice-daily quota collection using existing read-only adapters, no inference."""
from datetime import datetime,timezone
import json
from math import isfinite
from pathlib import Path
import uuid

from json_io import file_lock,update_json
from . import paths,budget_status,account_state
from .providers_bridge import fetch_provider_safe,normalize_snapshot
from .snapshot_store import SnapshotStore

SOURCES=('codex','claude','zai')


def read_object(path):
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}


def valid_reading(snapshot,now):
    try:
        stamp=datetime.fromisoformat(snapshot['fetched_at'].replace('Z','+00:00'))
        current=stamp.tzinfo is not None and 0 <= (now-stamp).total_seconds() <= 300
    except (ValueError,TypeError,KeyError,AttributeError):return False
    return bool(snapshot.get('status')=='ok' and current and any(
        isinstance(w.get('used_percent'),(int,float)) and not isinstance(w.get('used_percent'),bool)
        and isfinite(w['used_percent']) and 0<=w['used_percent']<=100
        for w in snapshot.get('windows') or [] if isinstance(w,dict)))


def run_once(*,fetch=None,sources=SOURCES):
    """Errors preserve last good values and their date; attempts have a separate clock."""
    fetch=fetch or fetch_provider_safe
    data_dir=paths.DATA_DIR;data_dir.mkdir(parents=True,exist_ok=True)
    with file_lock(data_dir/'quota-refresh-run',timeout=.1):
        started=datetime.now(timezone.utc).isoformat()
        previous=read_object(data_dir/'quota_refresh_status.json')
        states=account_state.ler_estados(paths.BUDGET_STATUS_PATH)
        store=SnapshotStore(paths.CACHE_PATH)
        results={};successes=0;attempts=0
        import budget_pacing
        for provider in sources:
            if (states.get(provider) or {}).get('estado') in ('cancelado','encerrado','expirado'):
                results[provider]={'status':'skipped_account','attempted':False};continue
            attempts+=1
            try:snapshot=normalize_snapshot(provider,fetch(provider))
            except Exception:snapshot={'provider':provider,'status':'error','source':None,'fetched_at':None,'windows':[],'details':{}}
            now=datetime.now(timezone.utc)
            valid=valid_reading(snapshot,now)
            status=snapshot.get('status','error') if not valid else 'ok'
            if status=='ok' and not valid:status='invalid_reading'
            row={'status':status,'attempted':True,'attempted_at':now.isoformat(),
                 'source':snapshot.get('source'),'fetched_at':snapshot.get('fetched_at'),
                 'last_success_at':(previous.get('providers',{}).get(provider) or {}).get('last_success_at')}
            if valid:
                store.update(provider,snapshot)
                pacing=budget_pacing.provider_pacing(snapshot)
                budget_saved=budget_status.write(provider,pacing)
                saved=read_object(paths.CACHE_PATH).get('providers',{}).get(provider) or {}
                try:
                    saved_at=datetime.fromisoformat(saved['fetched_at'].replace('Z','+00:00'))
                    expected=datetime.fromisoformat(snapshot['fetched_at'].replace('Z','+00:00'))
                    cache_ok=saved_at>=expected
                except (TypeError,ValueError,KeyError,AttributeError):cache_ok=False
                budget=read_object(paths.BUDGET_STATUS_PATH).get(provider) or {}
                if cache_ok and budget_saved is True and budget.get('pacing'):
                    successes+=1;row['last_success_at']=now.isoformat()
                else:row['status']='storage_error'
                row['resets_status']=(snapshot.get('details') or {}).get('resets_status','unknown')
            results[provider]=row
        status='complete' if attempts and successes==attempts else 'partial' if successes else 'failed'
        report={'schema_version':1,'run_id':uuid.uuid4().hex,'started_at':started,
                'finished_at':datetime.now(timezone.utc).isoformat(),'status':status,
                'execution':'deterministic_read_only','model_calls':0,'providers':results,
                'browser_observations_updated':False}
        update_json(data_dir/'quota_refresh_status.json',lambda _:report,recover_invalid=True)
        update_json(data_dir/'quota_refresh_history.json',lambda old:{'schema_version':1,'runs':(old.get('runs',[])+[report])[-180:]},recover_invalid=True)
        return report

"""Read subscription observations; open the existing widget through a fixed local route."""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import threading
import time
import sys

ROOT=Path(__file__).resolve().parents[2]
LABELS={'codex':'Codex · conta principal','codex_gpt2':'Codex · segunda conta','claude':'Claude','zai':'Z.ai','spark':'Codex Spark','gemini_cli':'Gemini CLI','gemini_web':'Gemini','antigravity':'Antigravity'}
_launch_lock=threading.Lock()
_last_launch=0.0

def _json(path):
    try:
        value=json.loads(path.read_text(encoding='utf-8-sig'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}

def _age(value,now):
    try:
        stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.tzinfo is None:return None
        age=(now-stamp).total_seconds()
        return age if math.isfinite(age) and age>=-60 else None
    except (TypeError,ValueError,AttributeError):return None

def _number(value,low=0,high=100):
    if isinstance(value,bool) or not isinstance(value,(int,float)):return None
    return float(value) if math.isfinite(value) and low<=value<=high else None

def _reset(value):
    try:
        stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return value if stamp.tzinfo is not None else None
    except (TypeError,ValueError,AttributeError):return None

def quota_view(root=ROOT,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    budget=_json(root/'dados/orcamento_ia.json')
    cache=_json(root/'apps/ia-quota-widget/app/data/last_snapshot.json').get('providers',{})
    if not isinstance(cache,dict):cache={}
    accounts=[]
    for provider,label in LABELS.items():
        saved=budget.get(provider,{})
        if not isinstance(saved,dict):saved={}
        cached=cache.get(provider,{})
        if not isinstance(cached,dict):cached={}
        if cached.get('provider',provider)!=provider:cached={}
        stamp=saved.get('updated_at');age=_age(stamp,now)
        cstamp=cached.get('fetched_at');cage=_age(cstamp,now)
        pacing=saved.get('pacing',{})
        if not isinstance(pacing,dict):pacing={}
        def rows_for(value):
            if isinstance(value,dict):return [dict(v,id=k) for k,v in value.items() if isinstance(v,dict)]
            return value if isinstance(value,list) else []
        brows=rows_for(pacing.get('windows',[]));crows=rows_for(cached.get('windows',[]))
        bstatus=pacing.get('status','NAO_MEDIDO');cstatus=cached.get('status','NAO_MEDIDO')
        # Budget status describes pacing, not whether a percentage was read.
        # NAO_MEDIDO can mean unknown duration while usage remains observed.
        budget_statuses={'ok','desacelerar','pause','NAO_MEDIDO'}
        def eligible(rows,status,age,allowed):
            return age is not None and any(isinstance(w,dict) and w.get('status',status) in allowed and _number(w.get('used_percent')) is not None for w in rows)
        bgood=eligible(brows,bstatus,age,budget_statuses);cgood=cstatus=='ok' and eligible(crows,cstatus,cage,{'ok'})
        use_cache=cgood and (not bgood or cage<age)
        rows=crows if use_cache else brows
        status=cstatus if use_cache else bstatus
        if use_cache:stamp,age=cstamp,cage
        windows=[]
        for w in rows[:24]:
            if not isinstance(w,dict):continue
            measured=age is not None and w.get('status',status) in ({'ok'} if use_cache else budget_statuses) and (not use_cache or cstatus=='ok')
            used=_number(w.get('used_percent')) if measured else None
            minutes=_number(w.get('duration_minutes'),1,525600)
            period='5 horas' if minutes==300 else 'Semana' if minutes==10080 else f'{minutes:g} minutos' if minutes else 'Período não informado'
            if minutes and w.get('duration_is_fallback'):period+=' [ESTIMATIVA]'
            windows.append(dict(id=str(w.get('id',''))[:120],label=str(w.get('label') or w.get('id') or 'Janela')[:160],period=period,used_percent=used,remaining_percent=None if used is None else round(100-used,2),duration_minutes=minutes,resets_at=_reset(w.get('resets_at'))))
        # Same allowlisted supplementary data as the widget: zero remains zero.
        folder=str(ROOT/'apps/ia-quota-widget')
        if folder not in sys.path:sys.path.insert(0,folder)
        from quota_details_data import sanitize_details
        from widget_app.observed_info import balance_evidence_sections,observed_info,observed_sections
        detail=sanitize_details(cached.get('details'))
        data_dir=root/'apps/ia-quota-widget/app/data'
        sections=[{'title':title,'text':body} for title,body in balance_evidence_sections(provider,data_dir)+observed_sections(observed_info(provider,data_dir))]
        detail['observed_sections']=sections
        accounts.append(dict(id=provider,label=label,observed_at=stamp if isinstance(stamp,str) else None,age_seconds=None if age is None else round(max(0,age)),fresh=age is not None and age<=300 and any(w['used_percent'] is not None for w in windows),source=str(cached.get('source') or 'Cache do widget')[:160] if use_cache else 'Leitor local de assinatura · dados/orcamento_ia.json',windows=windows,details=detail,details_observed_at=cstamp if isinstance(cstamp,str) else None))
    return dict(observed_at=now.isoformat(),freshness_seconds=300,accounts=accounts,notice='Consumo compartilhado da conta. Percentual não equivale a tokens, dinheiro ou consumo deste projeto. Dados antigos permanecem identificados; reler não consulta o fornecedor.')

def open_widget(action, tab=1):
    if not isinstance(action,str) or action not in {'show','settings'}:raise ValueError('Ação de cotas inválida.')
    if isinstance(tab,bool) or not isinstance(tab,int) or not 0<=tab<=4:raise ValueError('Categoria de configuração inválida.')
    global _last_launch
    with _launch_lock:
        if time.monotonic()-_last_launch<2:raise ValueError('Aguarde a janela de cotas abrir.')
        folder=ROOT/'apps/ia-quota-widget'
        executable=folder/'.venv/Scripts/pythonw.exe'
        script=folder/'widget.py'
        if not executable.is_file() or not script.is_file():raise ValueError('Aplicativo de cotas indisponível neste computador.')
        process=subprocess.Popen([str(executable),str(script),*(['--settings','--settings-tab',str(tab)] if action=='settings' else [])],cwd=folder,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        _last_launch=time.monotonic()
    return dict(status='requested',message='Pedido enviado ao Cotas IA neste computador.',pid=process.pid)


def _settings_exchange():
    folder=str(ROOT/'apps/ia-quota-widget')
    if folder not in sys.path:sys.path.insert(0,folder)
    from widget_app import settings_exchange
    return settings_exchange


def widget_settings():
    return _settings_exchange().settings_view()


def request_widget_settings(changes, expected_revision):
    result=_settings_exchange().request_patch(changes,expected_revision)
    ensure_widget()
    return result


def widget_settings_status(request_id):
    return _settings_exchange().request_status(request_id)


def ensure_widget():
    """Fixed startup route: singleton guard shows an existing instance, without settings."""
    try:return open_widget('show')
    except ValueError as exc:
        if 'Aguarde a janela' in str(exc):return {'status':'requested','message':'A abertura do widget já foi solicitada.'}
        return {'status':'unavailable','message':str(exc)}
    except OSError:
        return {'status':'unavailable','message':'Não foi possível abrir o widget neste computador.'}

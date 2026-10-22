"""Observe allowlisted project manifests. This module never dispatches executors."""
from __future__ import annotations
import argparse, hashlib, json, logging, math, time, re
from datetime import datetime, timezone
from pathlib import Path
from central_store import ROOT, Store, ident, now

RELATIVE = Path('evidence/operations')
MAX_BYTES = 500_000

def text(value, limit=600):
    from central_sources import redact
    return redact(str(value or ''))[:limit]

def read(path):
    """Reject links, oversized and malformed data; missing means not measured."""
    if not path.is_file(): return None
    for item in (path, *path.parents):
        info=item.lstat()
        if item.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('Fonte não pode ser atalho ou junção.')
    if path.stat().st_size>MAX_BYTES: raise ValueError('Fonte grande demais.')
    raw=path.read_bytes()
    if len(raw)>MAX_BYTES: raise ValueError('Fonte grande demais.')
    data=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data,dict): raise ValueError('Fonte deve ser objeto JSON.')
    return data

def age(value, at):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if not parsed.tzinfo: return None
        delta=(at-parsed).total_seconds()
        return round(delta) if delta>=0 else None
    except (ValueError,TypeError,AttributeError): return None

def quotas(snapshot, at=None):
    at=at or datetime.now(timezone.utc)
    rows=[]
    for p in (snapshot or {}).get('providers',[])[:20]:
        if not isinstance(p,dict): continue
        elapsed=age(p.get('fetched_at'),at)
        windows=[]
        for w in p.get('windows',[])[:20]:
            if not isinstance(w,dict): continue
            used=w.get('used_percent')
            valid=type(used) in (int,float) and math.isfinite(used) and 0<=used<=100
            measured=p.get('status')=='ok' and elapsed is not None and valid
            windows.append(dict(id=text(w.get('id'),100),label=text(w.get('label'),100),used_percent=used if measured else None,remaining_percent=round(100-used,2) if measured else None,duration_minutes=w.get('duration_minutes') if type(w.get('duration_minutes')) in (int,float) else None,resets_at=text(w.get('resets_at'),100) or None,measurement='measured' if measured else 'NAO_MEDIDO'))
        rows.append(dict(provider=text(p.get('provider'),80),label=text(p.get('label'),80),status=text(p.get('status'),80),source=text(p.get('source'),300),fetched_at=text(p.get('fetched_at'),100) or None,age_seconds=elapsed,stale=elapsed is None or elapsed>300,windows=windows,message=text(p.get('message')),product_shares=[dict(name=text(s.get('name'),80),percent=s.get('percent') if type(s.get('percent')) in (int,float) and math.isfinite(s['percent']) else None) for s in p.get('details',{}).get('product_shares',[])[:10] if isinstance(s,dict)]))
    return rows

def evidence(root, value):
    """Only existing files in the project can become downloadable evidence."""
    if not isinstance(value,str): return None
    p=Path(value)
    if not p.is_absolute(): p=root/p
    for item in (p, *p.parents):
        try: info=item.lstat()
        except OSError: return None
        if item.is_symlink() or getattr(info,'st_file_attributes',0)&0x400: return None
    p=p.resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file(): return None
    return str(p)

def history_data(document):
    document=document or {};timeline=[];previous={};observations={}
    for snapshot in document.get('quota_snapshots',[])[-420:]:
        for provider in quotas(snapshot):
            for window in provider['windows']:
                identity=(provider['provider'],window['id'],provider['fetched_at'],window['duration_minutes'],window['resets_at'])
                observations[identity]=(provider,window)
    def observation_time(pair):
        try:return datetime.fromisoformat(pair[0]['fetched_at'].replace('Z','+00:00')).timestamp()
        except (ValueError,TypeError,AttributeError):return 0
    for provider,window in sorted(observations.values(),key=observation_time):
        key=(provider['provider'],window['id']);old=previous.get(key);used=window['used_percent'];delta=None
        if old and window['duration_minutes'] is not None and old['duration_minutes']==window['duration_minutes'] and old['resets_at']==window['resets_at'] and used is not None and old['used_percent'] is not None:delta=round(used-old['used_percent'],2)
        timeline.append(dict(provider=provider['provider'],label=provider['label'],at=provider['fetched_at'],window=window['label'],duration_minutes=window['duration_minutes'],resets_at=window['resets_at'],used_percent=used,remaining_percent=window['remaining_percent'],delta_used_points=delta))
        previous[key]=window
    sessions=[]
    for session in document.get('usage_sessions',[])[-10:]:
        if not isinstance(session,dict):continue
        messages=[];seen=set()
        for row in reversed(session.get('messages',[])[-500:]):
            message_id=text(row.get('message_id'),120)
            if not message_id or message_id in seen:continue
            seen.add(message_id);messages.append(dict(message_id=message_id,at=text(row.get('at'),100),model=text(row.get('model'),120),tokens={text(k,80):v for k,v in row.get('tokens',{}).items() if type(v) is int and v>=0}))
        messages.sort(key=lambda row:row['at'],reverse=True)
        totals={key:sum(m['tokens'][key] for m in messages) if all(key in m['tokens'] for m in messages) else None for key in ['input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens','thinking_tokens']}
        kind=session.get('record_kind') if session.get('record_kind') in {'cli_result','session_cumulative'} else 'message'
        notice=('Total acumulado da sessão fornecido pelo Codex; atualizações substituem o total anterior. Não representa uma resposta isolada. Entrada informada pode incluir cache.' if kind=='session_cumulative' else 'Uso agregado de uma chamada CLI, identificado por result.uuid; message.id não fornecido. Não somado novamente às respostas de outra execução.' if kind=='cli_result' else 'Cada message.id é contado uma vez.')+' Raciocínio já incluído na saída. Cotas compartilhadas podem incluir outras sessões.'
        if session.get('partial') and kind!='session_cumulative':notice+=' Recorte local: o início do arquivo não foi coletado; totais apenas das respostas encontradas.'
        sessions.append(dict(session_id=text(session.get('session_id'),120),client=text(session.get('client'),120),label=text(session.get('label'),180),record_kind=kind,checked_at=text(session.get('checked_at'),100),unique_messages=len(messages),totals=totals,messages=messages,notice=notice))
    sessions.sort(key=lambda s:max((m.get('at') or '' for m in s['messages']),default=''),reverse=True)
    collection=document.get('collection',{})
    return dict(updated_at=text(document.get('updated_at'),100),quota_timeline=timeline[-300:],usage_sessions=sessions,
        collection={k:text(collection.get(k),600) for k in ('checked_at','status','notice')} if isinstance(collection,dict) else {})

def normalize(root, document, snapshot):
    source=root/RELATIVE/'operacao.json'
    rows=document.get('tasks',document.get('frentes',[]))
    if isinstance(rows,dict): rows=[dict(v,id=k) for k,v in rows.items() if isinstance(v,dict)]
    tasks=[]
    for row in rows[:100]:
        if not isinstance(row,dict): continue
        proof=row.get('evidence') or row.get('result') or row.get('path')
        tasks.append(dict(id=text(row.get('id'),100),title=text(row.get('title') or row.get('titulo') or row.get('id'),180),status=text(row.get('status') or 'NAO_MEDIDO',100),executor=text(row.get('executor') or row.get('responsavel'),180),summary=text(row.get('summary') or row.get('resumo')),evidence=evidence(root,proof)))
    executors=[]
    for row in document.get('executors',document.get('executores',[]))[:30]:
        if not isinstance(row,dict): continue
        tokens=row.get('tokens')
        tokens={text(k,80):v for k,v in tokens.items() if type(v) in (int,float) and math.isfinite(v) and v>=0} if isinstance(tokens,dict) else tokens if type(tokens) is int and tokens>=0 else None
        executors.append(dict(name=text(row.get('name') or row.get('nome'),180),client=text(row.get('client') or row.get('cliente'),180),status=text(row.get('status') or 'NAO_MEDIDO',100),model=text(row.get('model') or row.get('modelo'),180),tokens=tokens))
    results=[]
    for row in document.get('results',document.get('resultados',[]))[:80]:
        if not isinstance(row,dict): continue
        path=evidence(root,row.get('path') or row.get('arquivo'))
        email=row.get('email');email=email if isinstance(email,str) and re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',email) else None
        results.append(dict(email=email,title=text(row.get('title') or row.get('titulo'),180),path=path,file_id=ident(Path(path)) if path else None,verification=text(row.get('verification') or row.get('verificacao') or 'Não verificado',180)))
    return dict(title=text(document.get('title') or document.get('titulo') or 'Execução coordenada',180),status=text(document.get('status') or 'NAO_MEDIDO',100),updated_at=text(document.get('updated_at'),100) or None,summary=text(document.get('summary') or document.get('resumo')),source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_age_seconds=age(document.get('updated_at'),datetime.now(timezone.utc)),tasks=tasks,executors=executors,results=results,quotas=quotas(snapshot),quota_checked_at=(snapshot or {}).get('checked_at'),observation_only=True,notice='Andamento registrado pelos executores nas fontes do projeto. Este painel não controla conversas externas; arquivo atualizado não comprova conclusão.')

def sync(store, root=None, force=False):
    root=Path(root or ROOT).resolve()
    # One explicit source; no recursive scans and no paths from input choose a project.
    source=root/RELATIVE/'operacao.json'
    if not source.is_file(): return False
    document=read(source); snapshot=read(root/RELATIVE/'brainapp/cotas-atual.json')
    data=normalize(root,document,snapshot)
    history=read(root/RELATIVE/'brainapp/historico.json')
    if root==ROOT:
        from central_usage_history import collect,merge
        history=merge(history,collect())
    data['history']=history_data(history)
    job_id=ident(str(source)+'external-observer')
    revision=ident(dict(document=document,snapshot=snapshot))
    try: previous=store.job(job_id)
    except KeyError: previous={}
    if not force and previous.get('external_revision')==revision and previous.get('external_operation',{}).get('history')==data['history']: return False
    job=dict(id=job_id,project_id=ident(root),status='observed',title=data['title'],updated_at=now(),stage='Acompanhamento externo',external_operation=data,external_revision=revision)
    # observed never consumes the execution queue or becomes an automatic runnable job.
    store.add('jobs',ident(root),job)
    store.event(ident(root),'Execução coordenada: fonte atualizada','external_operation')
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');parser.add_argument('--seconds',type=int,default=7200);args=parser.parse_args()
    store=Store();deadline=time.monotonic()+min(max(args.seconds,1),14400)
    while True:
        try: sync(store,force=not args.watch)
        except (ValueError,OSError,json.JSONDecodeError): logging.exception('Fonte indisponível; última observação preservada')
        if not args.watch or time.monotonic()>=deadline:break
        time.sleep(4)

if __name__=='__main__':main()

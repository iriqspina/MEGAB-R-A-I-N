"""Bounded, incremental local usage metadata for explicitly connected sessions.

No network, models, message text or account credentials. The UI cache is bounded;
an append-only numeric journal preserves observations outside that display window.
"""
from __future__ import annotations
import contextlib, hashlib, json, os, re, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path

APP=Path(__file__).resolve().parent
UUID=re.compile(r'([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$')
KEYS=('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens','thinking_tokens')
INTERVAL=60
MAX_CHUNK=2_000_000
_lock=threading.Lock()
_last={}
_last_good={}

@contextlib.contextmanager
def writer(area):
    """One writer across both server threads and separate desktop processes."""
    area.mkdir(parents=True,exist_ok=True)
    fd=os.open(area/'collector.lock',os.O_CREAT|os.O_RDWR,0o600);locked=False
    try:
        if os.fstat(fd).st_size==0:os.write(fd,b'0')
        os.lseek(fd,0,os.SEEK_SET)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            locked=True
        except OSError:pass
        yield locked
    finally:
        if locked:
            os.lseek(fd,0,os.SEEK_SET)
            if os.name=='nt':msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
            else:fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

def event_id(event):
    data=event['data']
    return digest(dict(kind=event['kind'],session_id=data.get('session_id'),messages=data.get('messages'),observation_order_ns=data.get('observation_order_ns')) if event['kind']=='usage' else dict(kind='quota',data=data))

def append_events(area,events):
    """Immutable event files make append/retry idempotent even if cache replace fails."""
    journal=area/'events';journal.mkdir(exist_ok=True)
    for event in events:
        identity=event_id(event);dest=journal/(identity+'.json')
        if dest.exists():continue
        row=dict(id=identity,observed_at=now(),recorded_ns=time.time_ns(),**event)
        temp=journal/('.'+identity+'.tmp');temp.write_text(json.dumps(row,ensure_ascii=False),encoding='utf-8')
        os.replace(temp,dest)
        # Preserve a torn mirror tail as its own line; never join it to a new event.
        mirror=area/'events.jsonl';separator=False
        if mirror.exists() and mirror.stat().st_size:
            with mirror.open('rb') as stream:stream.seek(-1,2);separator=stream.read(1)!=b'\n'
        with mirror.open('a',encoding='utf-8') as stream:
            if separator:stream.write('\n')
            stream.write(json.dumps(row,ensure_ascii=False)+'\n')

def replay(area,state):
    """Recover recent observations from immutable journal; keep prior valid cache."""
    events=[];deadline=time.monotonic()+.5
    for path in sorted((area/'events').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:1000]:
        if time.monotonic()>deadline:break
        try:
            event=read_json(path,2_000_000);event['_replay_order']=event.get('recorded_ns',path.stat().st_mtime_ns);events.append(event)
        except (OSError,ValueError):continue
    # Compatibility with the numeric journal written before immutable events existed.
    legacy=area/'events.jsonl'
    if legacy.exists():
        with legacy.open('rb') as stream:
            size=legacy.stat().st_size;offset=max(0,size-8_000_000);stream.seek(offset);raw=stream.read(8_000_000)
        lines=raw.splitlines()[1:] if offset else raw.splitlines()
        for index,line in reversed(list(enumerate(lines))):
            if time.monotonic()>deadline:break
            try:
                event=json.loads(line)
                fallback=int(datetime.fromisoformat(event['observed_at'].replace('Z','+00:00')).timestamp()*1_000_000_000)+index
                event['_replay_order']=event.get('recorded_ns',fallback);events.append(event)
            except (ValueError,UnicodeDecodeError,KeyError,TypeError,AttributeError):continue
    if not events:return state
    sessions={s['session_id']:s for s in state.get('usage_sessions',[])};snapshots=list(state.get('quota_snapshots',[]));seen={digest(s) for s in snapshots}
    for event in sorted(events,key=lambda e:e.get('_replay_order',0)):
        data=event.get('data',{})
        if event.get('kind')=='usage' and isinstance(data,dict) and data.get('session_id'):
            old=sessions.get(data['session_id'],{})
            order=data.get('observation_order_ns',event.get('_replay_order',0))
            if order>=old.get('observation_order_ns',0):sessions[data['session_id']]=dict(data,observation_order_ns=order)
        elif event.get('kind')=='quota' and isinstance(data,dict) and digest(data) not in seen:
            snapshots.append(data);seen.add(digest(data))
    state=dict(state,usage_sessions=list(sessions.values()),quota_snapshots=snapshots[-360:])
    state.setdefault('checked_at',max((e.get('observed_at','') for e in events),default=''))
    state.setdefault('updated_at',state['checked_at']);state.setdefault('status','recovered')
    state.setdefault('notice','Última leitura recuperada do histórico numérico; coleta atual ainda não confirmada.')
    return state

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
def number(value):return value if type(value) is int and value>=0 else None
def stamp(value):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return value if parsed.tzinfo is not None and parsed.timestamp()<=time.time()+60 else None
    except (ValueError,TypeError,AttributeError):return None
def safe_file(path,root):
    try:
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):return False
        for part in (path,*path.parents):
            info=part.lstat()
            if part.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:return False
        return True
    except OSError:return False
def read_json(path,limit):
    if path.stat().st_size>limit:raise ValueError('Metadata source too large')
    value=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value,dict):raise ValueError('Invalid metadata source')
    return value

def discover(app,home,deadline):
    """Match filename UUID hashes to startup registrations, without loading transcripts."""
    registered={};sources=[];limited=False
    registry=app/'data/session-connections'
    for p in list(registry.glob('*.json'))[:500]:
        if time.monotonic()>deadline:return sources,True
        try:
            row=read_json(p,16384)
            if row.get('id')==p.stem and re.fullmatch('[a-f0-9]{24}',p.stem):registered[p.stem]=row
        except (OSError,ValueError):continue
    roots=[('Codex',home/'.codex/sessions'),('Codex GPT2',home/'.codex-gpt2/sessions'),('Claude Code',home/'.claude/projects')]
    for client,base in roots:
        if not base.is_dir():continue
        seen=0
        for folder,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=sorted((d for d in dirs if not (Path(folder)/d).is_symlink()),reverse=True)
            if time.monotonic()>deadline:limited=True;break
            for name in files:
                seen+=1
                if seen>20000 or time.monotonic()>deadline:limited=True;break
                if not name.endswith('.jsonl'):continue
                match=UUID.search(Path(name).stem)
                if not match:continue
                sid=match[1];registration=registered.get(hashlib.sha256(sid.encode()).hexdigest()[:24])
                path=Path(folder)/name
                if not registration or not safe_file(path,base):continue
                sources.append(dict(path=str(path),root=str(base),session_id=sid,client=client,
                    project=Path(registration.get('project_root','')).name,registration=registration['id']))
            if limited:break
    sources.sort(key=lambda s:Path(s['path']).stat().st_mtime,reverse=True)
    return sources[:100],limited or len(sources)>100

def consume(source,cursor,previous,deadline):
    """Read only an append/tail chunk; output whitelisted numeric metadata."""
    path=Path(source['path']);root=Path(source['root'])
    if not safe_file(path,root):raise ValueError('Usage source unavailable')
    size=path.stat().st_size
    with path.open('rb') as stream:
        prefix=stream.read(min(size,512));head=hashlib.sha256(prefix).hexdigest()
        offset=cursor.get('offset',0)
        old_length=min(cursor.get('size',0),512)
        old_prefix=hashlib.sha256(prefix[:old_length]).hexdigest()
        reset=offset>size or (cursor.get('head') and cursor['head']!=old_prefix)
        initial=not cursor or reset
        if initial:offset=max(0,size-MAX_CHUNK)
        stream.seek(offset)
        skipped=bool(initial and offset)
        raw=stream.read(MAX_CHUNK)
    start=0
    if skipped or cursor.get('discarding_line'):
        start=raw.find(b'\n')+1
        if not start:return previous,dict(offset=offset+len(raw),head=head,size=size,partial=True,discarding_line=True),False
    end=raw.rfind(b'\n')+1
    if end<=start:
        oversized=len(raw)==MAX_CHUNK
        return previous,dict(offset=offset+(len(raw) if oversized else start),head=head,size=size,partial=skipped or cursor.get('partial',False) or oversized,discarding_line=oversized),False
    messages={} if reset else {m['message_id']:m for m in (previous or {}).get('messages',[]) if isinstance(m,dict) and m.get('message_id')}
    model=(previous or {}).get('model','NAO_MEDIDO');observed=False;consumed=start
    for line in raw[start:end].splitlines(keepends=True):
        if time.monotonic()>deadline:break
        consumed+=len(line)
        try:row=json.loads(line)
        except (ValueError,UnicodeDecodeError):continue
        if not isinstance(row,dict):continue
        payload=row.get('payload')
        if row.get('type')=='turn_context' and isinstance(payload,dict):model=str(payload.get('model') or 'NAO_MEDIDO')[:120]
        at=stamp(row.get('timestamp'))
        if source['client'].startswith('Codex'):
            if row.get('type')!='event_msg' or not isinstance(payload,dict) or payload.get('type')!='token_count':continue
            info=payload.get('info') or {};usage=info.get('total_token_usage') if isinstance(info,dict) else None
            if not isinstance(usage,dict) or not at:continue
            names={'input_tokens':'input_tokens','cached_input_tokens':'cache_read_input_tokens','cache_write_input_tokens':'cache_creation_input_tokens','output_tokens':'output_tokens','reasoning_output_tokens':'thinking_tokens'}
            counters={dest:number(usage.get(src)) for src,dest in names.items()}
            if not any(v is not None for v in counters.values()):continue
            # Codex emits repeated cumulative updates, not guaranteed message IDs.
            messages={'session-total':dict(message_id='session-total',at=at,model=model,tokens={k:v for k,v in counters.items() if v is not None})}
        else:
            message=row.get('message');usage=message.get('usage') if isinstance(message,dict) else None
            if row.get('type')!='assistant' or not isinstance(usage,dict) or not message.get('id') or not at:continue
            counters={k:number(usage.get(k)) for k in KEYS}
            details=usage.get('output_tokens_details');counters['thinking_tokens']=number(details.get('thinking_tokens')) if isinstance(details,dict) else None
            if not any(v is not None for v in counters.values()):continue
            messages[str(message['id'])[:120]]=dict(message_id=str(message['id'])[:120],at=at,model=str(message.get('model') or 'NAO_MEDIDO')[:120],tokens={k:v for k,v in counters.items() if v is not None})
        observed=True
    rows=sorted(messages.values(),key=lambda m:m.get('at',''),reverse=True)[:200]
    state=dict(offset=offset+consumed,head=head,size=size,partial=skipped or cursor.get('partial',False) or reset)
    if not rows:return previous,state,False
    item=dict(session_id=source['client']+':'+source['session_id'],client=source['client'],label=source['client']+' · '+source['project'],
        record_kind='session_cumulative' if source['client'].startswith('Codex') else 'message',model=model,
        checked_at=now(),observation_order_ns=time.time_ns(),messages=rows,partial=state['partial'],source_size=size,registration=source['registration'])
    return item,state,observed

def quota_snapshot(view):
    providers=[]
    for account in view.get('accounts',[]):
        if not isinstance(account,dict):continue
        windows=[]
        for w in account.get('windows',[]):
            value=w.get('used_percent')
            if type(value) not in (int,float) or not 0<=value<=100:continue
            windows.append(dict(id=w.get('id'),label=w.get('label'),used_percent=value,duration_minutes=w.get('duration_minutes'),resets_at=w.get('resets_at')))
        at=stamp(account.get('observed_at'))
        if windows and at:providers.append(dict(provider=account.get('id'),label=account.get('label'),status='ok',source='Local quota source snapshot',fetched_at=at,windows=windows))
    return dict(providers=providers) if providers else None

def collect(app=APP,home=None,quota_reader=None,force=False,budget_seconds=1.5):
    app=Path(app);home=Path(home or Path.home());area=app/'data/usage-history';key=str(area)
    if not _lock.acquire(blocking=False):return cached(area)
    stack=contextlib.ExitStack()
    try:
        if not stack.enter_context(writer(area)):return cached(area)
        if not force and time.monotonic()-_last.get(key,-INTERVAL)<INTERVAL:return cached(area)
        _last[key]=time.monotonic();deadline=time.monotonic()+budget_seconds
        old=cached(area)
        state=json.loads(json.dumps(old));state.setdefault('usage_sessions',[]);state.setdefault('quota_snapshots',[]);state.setdefault('cursors',{})
        sources,limited=discover(app,home,deadline);sessions={s['session_id']:s for s in state['usage_sessions']};events=[];errors=0;updated=0
        for source in sources:
            if time.monotonic()>deadline:limited=True;break
            sid=source['client']+':'+source['session_id'];cursor=state['cursors'].get(sid,{})
            try:
                previous=sessions.get(sid);item,next_cursor,changed=consume(source,cursor,previous,deadline)
                state['cursors'][sid]=next_cursor
                if item:
                    sessions[sid]=item
                    if changed and digest(item.get('messages'))!=digest((previous or {}).get('messages')):
                        events.append(dict(kind='usage',data=item));updated+=1
            except (OSError,ValueError,TypeError):errors+=1
        if quota_reader is None:
            from central_quotas import quota_view
            quota_reader=quota_view
        try:
            snap=quota_snapshot(quota_reader())
            if snap:
                fingerprint=digest(snap)
                if not any(s.get('snapshot_sha256')==fingerprint for s in state['quota_snapshots']):
                    snap['snapshot_sha256']=fingerprint;state['quota_snapshots'].append(snap);events.append(dict(kind='quota',data=snap))
        except (OSError,ValueError,TypeError):errors+=1
        state['usage_sessions']=sorted(sessions.values(),key=lambda s:max((m.get('at','') for m in s.get('messages',[])),default=''),reverse=True)[:100]
        state['quota_snapshots']=state['quota_snapshots'][-360:]
        state.update(schema_version=1,checked_at=now(),updated_at=now(),status='partial' if limited or errors else 'observing',
            registered_sources=len(sources),new_observations=updated,new_tokens='NAO_MEDIDO',errors=errors,limited=limited,
            notice='Coleta local de sessões registradas, enquanto o MegaBrain está aberto. Codex: total acumulado da sessão. Claude: respostas encontradas, podendo ser recorte. Sem dado novo não significa zero tokens. Percentual pertence à conta; mensal ausente permanece não medido.')
        area.mkdir(parents=True,exist_ok=True)
        if events:append_events(area,events)
        temp=area/('.current-'+uuid.uuid4().hex+'.tmp')
        temp.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8');os.replace(temp,area/'current.json')
        return state
    except (OSError,ValueError,TypeError):return cached(area)
    finally:stack.close();_lock.release()

def cached(area):
    area=Path(area);key=str(area);valid=True
    try:state=read_json(area/'current.json',12_000_000)
    except (OSError,ValueError):state=json.loads(json.dumps(_last_good.get(key,{})));valid=False
    try:
        newer=any(p.exists() and (not (area/'current.json').exists() or p.stat().st_mtime_ns>(area/'current.json').stat().st_mtime_ns) for p in [area/'events',area/'events.jsonl'])
        if not valid or newer:state=replay(area,state)
    except (OSError,ValueError,TypeError):pass
    if state:_last_good[key]=json.loads(json.dumps(state))
    return state

def merge(historical,current):
    """Keep historical project data; newest connected-session metadata remains separate."""
    def identity(session):
        sid=str(session.get('session_id',''));client=str(session.get('client',''))
        return sid if sid.startswith(client+':') else client+':'+sid
    result=dict(historical or {});by_id={identity(s):s for s in result.get('usage_sessions',[]) if isinstance(s,dict)}
    by_id.update({identity(s):s for s in current.get('usage_sessions',[]) if isinstance(s,dict)})
    result['usage_sessions']=sorted(by_id.values(),key=lambda s:max((m.get('at','') for m in s.get('messages',[])),default=''))
    result['quota_snapshots']=list(result.get('quota_snapshots',[]))+current.get('quota_snapshots',[])
    result['updated_at']=current.get('checked_at') or result.get('updated_at')
    result['collection']=dict(checked_at=current.get('checked_at'),status=current.get('status','NAO_MEDIDO'),notice=current.get('notice','Coleta local ainda não medida.'))
    return result

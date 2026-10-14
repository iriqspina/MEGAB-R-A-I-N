"""Local, transactional state. Original project files remain read-only."""
from __future__ import annotations
import hashlib, json, re, sqlite3, threading, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parents[1]
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def ident(value): return hashlib.sha256(str(value).casefold().encode()).hexdigest()[:20]
def read_json(path, default=None):
    try: return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError): return {} if default is None else default

WORKSPACE = dict(openProjects=[], activeProject=None, compareProject=None, layouts={}, hiddenModules={}, density='comfortable', longPressMs=1000, views=[])
PROCESS = {'name':'Criação com revisão', 'mode':'analysis', 'stages':[
    {'id':'brief','title':'Entender e propor','role':'creator','model':'codex','effort':'xhigh','enabled':True,'instruction':''},
    {'id':'review','title':'Revisar com GLM principal','role':'reviewer','model':'glm','effort':'max','enabled':True,'instruction':''}]}

class Conflict(Exception): pass
class Store:
    def __init__(self, path=None):
        self.path = Path(path or APP/'data'/'central.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS documents(key TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, key TEXT, revision INTEGER, data TEXT, at TEXT);
              CREATE TABLE IF NOT EXISTS comments(id TEXT PRIMARY KEY, project TEXT, data TEXT);
              CREATE TABLE IF NOT EXISTS refs(id TEXT PRIMARY KEY, project TEXT, data TEXT);
              CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, data TEXT);
              CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project TEXT, data TEXT);
              CREATE TABLE IF NOT EXISTS auth_sessions(hash TEXT PRIMARY KEY, csrf TEXT, expires REAL);
              CREATE TABLE IF NOT EXISTS auth_pairs(hash TEXT PRIMARY KEY, expires REAL);''')
            c.execute('CREATE TABLE IF NOT EXISTS requests(scope TEXT, key TEXT, digest TEXT, item_id TEXT, PRIMARY KEY(scope,key))')
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path, timeout=15)
        c.execute('PRAGMA journal_mode=WAL'); c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback(); raise
        finally: c.close()
    def get(self,key,default):
        with self.db() as c: row=c.execute('SELECT * FROM documents WHERE key=?',(key,)).fetchone()
        return {'revision':row['revision'],'data':json.loads(row['data'])} if row else {'revision':0,'data':json.loads(json.dumps(default))}
    def put(self,key,revision,data):
        raw=json.dumps(data,ensure_ascii=False)
        if len(raw.encode())>300_000: raise ValueError('Configuração grande demais.')
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM documents WHERE key=?',(key,)).fetchone()
            if (row['revision'] if row else 0)!=revision: raise Conflict('Outra janela salvou uma versão nova. Recarregue antes de salvar.')
            if row: c.execute('INSERT INTO history(key,revision,data,at) VALUES(?,?,?,?)',(key,row['revision'],row['data'],now()))
            c.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',(key,revision+1,raw))
        return {'revision':revision+1,'data':data}
    def add(self, table, project, data):
        assert table in {'comments','refs','jobs'}
        data=dict(data,id=data.get('id') or uuid.uuid4().hex,at=data.get('at') or now())
        with self.db() as c: c.execute(f'INSERT OR REPLACE INTO {table} VALUES(?,?,?)',(data['id'],project,json.dumps(data,ensure_ascii=False)))
        return data
    def listing(self, table, project=None):
        assert table in {'comments','refs','jobs'}
        with self.db() as c:
            rows=c.execute(f'SELECT data FROM {table}'+(' WHERE project=?' if project else '')+' ORDER BY rowid DESC LIMIT 250',(project,) if project else ()).fetchall()
        return [json.loads(x[0]) for x in rows]
    def job(self,job_id):
        with self.db() as c: row=c.execute('SELECT data FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not row: raise KeyError('Pedido não encontrado.')
        return json.loads(row['data'])
    def request_cancel(self,job_id):
        with self.db() as c:
            c.execute("UPDATE jobs SET data=json_set(data,'$.cancel_requested',json('true')) WHERE id=? AND json_extract(data,'$.status') IN ('queued','running')",(job_id,))
        return self.job(job_id)
    def cancellation_requested(self,job_id):
        with self.db() as c:row=c.execute("SELECT json_extract(data,'$.cancel_requested') AS cancelled FROM jobs WHERE id=?",(job_id,)).fetchone()
        return bool(row and row['cancelled'])
    def event(self,project,title,kind='source_changed',**extra):
        data=dict(project_id=project,title=title,kind=kind,at=now(),**extra)
        with self.db() as c:
            cur=c.execute('INSERT INTO events(project,data) VALUES(?,?)',(project,json.dumps(data,ensure_ascii=False)))
            return cur.lastrowid
    def events(self,after=0):
        with self.db() as c:
            rows=c.execute('SELECT id,data FROM events WHERE id>? ORDER BY id LIMIT 150',(after,)).fetchall()
            rev=c.execute('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0]
        return {'revision':rows[-1]['id'] if rows else rev,'events':[dict(json.loads(r['data']),id=r['id']) for r in rows]}
    def create_once(self,table,project,data,key=None,digest=None):
        assert table in {'comments','refs','jobs'}
        scope=table+':'+project
        data=dict(data,id=uuid.uuid4().hex,at=now())
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT digest,item_id FROM requests WHERE scope=? AND key=?',(scope,key)).fetchone() if key else None
            if old:
                if old['digest']!=digest: raise Conflict('Esta tentativa já foi usada com outro conteúdo. Reabra a ação antes de salvar.')
                row=c.execute(f'SELECT data FROM {table} WHERE id=?',(old['item_id'],)).fetchone()
                return json.loads(row['data']),False
            if table=='jobs' and c.execute("SELECT 1 FROM jobs WHERE json_extract(data,'$.status') IN ('queued','running') LIMIT 1").fetchone():
                raise Conflict('Uma sessão já está em execução. Aguarde a conclusão.')
            c.execute(f'INSERT INTO {table} VALUES(?,?,?)',(data['id'],project,json.dumps(data,ensure_ascii=False)))
            if key: c.execute('INSERT INTO requests VALUES(?,?,?,?)',(scope,key,digest,data['id']))
        return data,True
    def auth_session(self,token):
        import time
        key=hashlib.sha256(token.encode()).hexdigest()
        with self.db() as c: row=c.execute('SELECT csrf,expires FROM auth_sessions WHERE hash=? AND expires>?',(key,time.time())).fetchone()
        return dict(row) if row else None
    def auth_create(self,token,csrf,expires):
        with self.db() as c: c.execute('INSERT INTO auth_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),csrf,expires))
    def auth_revoke(self,token):
        with self.db() as c: c.execute('DELETE FROM auth_sessions WHERE hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    def pairing_create(self,code,expires):
        import time
        with self.db() as c:
            c.execute('DELETE FROM auth_pairs WHERE expires<?',(time.time(),))
            c.execute('INSERT INTO auth_pairs VALUES(?,?)',(hashlib.sha256(code.encode()).hexdigest(),expires))
    def pairing_consume(self,code):
        import time
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE'); key=hashlib.sha256(code.encode()).hexdigest()
            row=c.execute('SELECT hash FROM auth_pairs WHERE hash=? AND expires>?',(key,time.time())).fetchone()
            if row: c.execute('DELETE FROM auth_pairs WHERE hash=?',(key,))
            return bool(row)
    def enqueue(self,project,data):
        return self.create_once('jobs',project,data)[0]
    def heartbeat(self,job_id):
        with self.db() as c:
            c.execute("UPDATE jobs SET data=json_set(data,'$.heartbeat',?) WHERE id=? AND json_extract(data,'$.status') IN ('queued','running')",(now(),job_id))
    def update_job_if_active(self,job):
        with self.db() as c:
            changed=c.execute("UPDATE jobs SET data=json_set(?,'$.cancel_requested',coalesce(json_extract(data,'$.cancel_requested'),0)) WHERE id=? AND json_extract(data,'$.status') IN ('queued','running')",(json.dumps(job,ensure_ascii=False),job['id'])).rowcount
        return bool(changed)
    def reconcile(self):
        from datetime import timedelta
        cutoff=(datetime.now(timezone.utc)-timedelta(minutes=3)).isoformat(timespec='seconds')
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            rows=c.execute("SELECT id,project,data FROM jobs WHERE json_extract(data,'$.status') IN ('queued','running')").fetchall()
            for row in rows:
                data=json.loads(row['data'])
                if data.get('heartbeat',data.get('updated_at',data.get('at','')))<cutoff:
                    data.update(status='interrupted',stage='Interrompida',error='O executor parou de responder. Nenhum modelo foi reiniciado automaticamente.',updated_at=now())
                    c.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(data,ensure_ascii=False),row['id']))
                    event=dict(project_id=row['project'],title='Pedido interrompido: executor não responde',kind='session_interrupted',at=now(),job_id=row['id'])
                    c.execute('INSERT INTO events(project,data) VALUES(?,?)',(row['project'],json.dumps(event,ensure_ascii=False)))

def validate_process(data):
    if not isinstance(data,dict) or data.get('mode') not in {'analysis','execution'}: raise ValueError('Modo de processo inválido.')
    stages=data.get('stages')
    if not isinstance(stages,list) or not 1<=len(stages)<=16: raise ValueError('Use de uma a dezesseis etapas.')
    ids=set(); creator=False
    for s in stages:
        if not isinstance(s,dict) or not isinstance(s.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}',s['id']) or s['id'] in ids: raise ValueError('Etapas precisam de identificadores distintos, sem caminhos ou separadores.')
        ids.add(s['id'])
        if s.get('model') not in {'codex','claude','glm'}: raise ValueError('Modelo não permitido; GLM Flash não é usado.')
        if s.get('role') not in {'creator','reviewer','worker'}: raise ValueError('Papel inválido.')
        if s.get('model')=='glm' and s.get('role')!='reviewer': raise ValueError('GLM principal está reservado para revisão.')
        if s.get('model')=='glm' and s.get('effort')!='max': raise ValueError('A rota GLM principal desta central usa esforço máximo comprovado.')
        if s.get('effort') not in {'low','medium','high','xhigh','max'}: raise ValueError('Esforço não suportado.')
        if s.get('effort')=='max' and s.get('model')!='glm': raise ValueError('Máximo é reservado ao GLM; Claude/Codex usam até extra high.')
        capability=s.get('capability','textual')
        if capability not in {'textual','research','code'}: raise ValueError('Capacidade de etapa inválida.')
        if capability=='research' and s.get('model')!='claude': raise ValueError('A pesquisa com ferramentas usa Claude nesta central.')
        if capability=='code' and s.get('model')!='codex': raise ValueError('A execução isolada de código usa Codex nesta central.')
        if s.get('role')=='reviewer' and capability!='textual': raise ValueError('O revisor recebe as evidências e não altera o trabalho revisado.')
        if not isinstance(s.get('instruction',''),str) or len(s.get('instruction',''))>6000: raise ValueError('Instrução inválida.')
        if not isinstance(s.get('title'),str) or not 1<=len(s['title'])<=120: raise ValueError('Dê um título à etapa.')
        if not isinstance(s.get('enabled',True),bool): raise ValueError('Estado da etapa deve ser ligado ou desligado.')
        if s.get('enabled',True):
            if s['role']=='reviewer' and not creator: raise ValueError('Coloque a criação antes da revisão.')
            if s['role']=='creator': creator=True
    if not creator: raise ValueError('Mantenha uma etapa de criação ativa.')
    return data

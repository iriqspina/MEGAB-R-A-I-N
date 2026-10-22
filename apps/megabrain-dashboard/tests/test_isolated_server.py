from pathlib import Path
import asyncio
import json
import re
import sqlite3
import tempfile
import unittest
import sys
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP)); sys.path.insert(0,str(APP/'scripts'))
import isolated_server as iso

def call(app,method,path,headers=()):
    sent=[]
    async def receive(): return {'type':'http.request','body':b'','more_body':False}
    async def send(message): sent.append(message)
    asyncio.run(app({'type':'http','method':method,'path':path,'headers':list(headers),'query_string':b'','client':('127.0.0.1',5),'server':('127.0.0.1',8768),'scheme':'http','root_path':'','http_version':'1.1'},receive,send))
    start=next(m for m in sent if m['type']=='http.response.start')
    body=b''.join(m.get('body',b'') for m in sent if m['type']=='http.response.body')
    return start['status'],dict(start['headers']),body

def db(path):
    c=sqlite3.connect(path); c.execute('PRAGMA journal_mode=WAL')
    c.executescript('''CREATE TABLE IF NOT EXISTS documents(key TEXT PRIMARY KEY, revision INTEGER, data TEXT);CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, key TEXT, revision INTEGER, data TEXT, at TEXT);
      CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, data TEXT);CREATE TABLE IF NOT EXISTS comments(id TEXT PRIMARY KEY, project TEXT, data TEXT);CREATE TABLE IF NOT EXISTS auth_sessions(hash TEXT)''')
    return c

def put(c,data):
    # Same archive-then-replace as central_store.Store.put.
    row=c.execute("SELECT revision,data FROM documents WHERE key='workspace'").fetchone()
    c.execute("INSERT INTO history(key,revision,data,at) VALUES('workspace',?,?,'t')",row)
    c.execute("UPDATE documents SET revision=?, data=? WHERE key='workspace'",(row[0]+1,json.dumps(data))); c.commit()

class IsolatedServerTests(unittest.TestCase):
    def test_every_writing_route_is_classified_and_outside_actions_are_blocked(self):
        import central_server
        from central_store import Store
        with tempfile.TemporaryDirectory() as folder:
            app=central_server.build_app(store=Store(Path(folder)/'c.sqlite3'),sources=object(),port=8768)
            writing={(m,r.path) for r in app.routes for m in getattr(r,'methods',None) or () if m not in iso.SAFE_METHODS}
        blocked={(m,p) for m,p in writing if not iso.allowed(m,re.sub(r'\{[^}]+\}','x',p))}
        # A new writing route lands here (blocked by default) until someone decides it only writes the copy.
        # Upload writes project files, so the default helper must keep it blocked;
        # image proofs use their own synthetic project roots and server instead.
        self.assertEqual(blocked,{('POST','/api/dispatch/{fid}'),('POST','/api/projects/{pid}/jobs'),('POST','/api/projects/{pid}/attachments'),('POST','/api/jobs/{jid}/cancel'),('POST','/api/quotas/open-widget'),('POST','/api/quotas/widget-settings'),('POST','/api/projects/{pid}/bridge/send'),('POST','/api/projects/{pid}/bridge/orders/{oid}/stop'),('POST','/api/projects/{pid}/bridge/pending/discard')})
        self.assertEqual(len(writing-blocked),14)

    def test_guard_marks_responses_and_refuses_blocked_writes(self):
        async def inner(scope,receive,send):
            await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'application/json')]})
            await send({'type':'http.response.body','body':b'{}'})
        app=iso.Guard(inner)
        status,headers,_=call(app,'PUT','/api/workspace')
        self.assertEqual((status,headers.get(b'x-mb-instancia')),(200,b'isolada'))
        status,headers,body=call(app,'POST','/api/quotas/open-widget')
        self.assertEqual((status,headers.get(b'x-mb-instancia')),(403,b'isolada'))
        self.assertIn('instância isolada',json.loads(body)['detail'])
        self.assertEqual(call(app,'GET','/api/projects/p1/jobs')[0],200)
        self.assertEqual(call(app,'DELETE','/api/workspace')[0],403)  # unclassified method on a known path stays blocked
        self.assertEqual(call(app,'PATCH','/api/novidade')[0],403)

    def test_build_app_port_only_accepts_its_own_host(self):
        import central_server
        from central_store import Store
        with tempfile.TemporaryDirectory() as folder:
            app=central_server.build_app(store=Store(Path(folder)/'c.sqlite3'),sources=object(),port=8768)
            self.assertEqual(call(app,'GET','/api/health',[(b'host',b'127.0.0.1:8768')])[0],200)
            self.assertEqual(call(app,'GET','/api/health',[(b'host',b'localhost:8768')])[0],200)
            self.assertEqual(call(app,'GET','/api/health',[(b'host',b'127.0.0.1:8766')])[0],403)
            default=central_server.build_app(store=Store(Path(folder)/'d.sqlite3'),sources=object())
            self.assertEqual(call(default,'GET','/api/health',[(b'host',b'127.0.0.1:8766')])[0],200)
            self.assertEqual(call(default,'GET','/api/health',[(b'host',b'127.0.0.1:8768')])[0],403)

    def test_refuses_real_database_and_reserved_ports(self):
        for port in (8766,8767):
            with self.assertRaises(ValueError): iso.Isolated(port=port)
        with self.assertRaises(SystemExit): iso.serve(iso.REAL_DB,8768,1)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(SystemExit): iso.serve(Path(folder)/'copia.sqlite3',8766,1)

    def test_snapshot_includes_wal_and_only_copy_writes_count_as_leaks(self):
        with tempfile.TemporaryDirectory() as folder:
            real=Path(folder)/'real.sqlite3'; copy=Path(folder)/'copia.sqlite3'
            w=db(real)
            try:
                w.execute('PRAGMA wal_autocheckpoint=0')
                w.execute("INSERT INTO documents VALUES('workspace',7,'{\"a\":0}')"); w.commit()
                self.assertTrue(Path(str(real)+'-wal').stat().st_size>0)  # the row lives only in the WAL while the writer stays open
                real_before=iso.db_state(real)
                iso.snapshot(copy,real)
                copy_before=iso.db_state(copy)
                self.assertEqual(copy_before['documents'],{'workspace':7})
                c=db(copy)
                try:
                    put(c,{'a':'prova'}); put(c,{'a':'prova 2'})
                finally: c.close()
                put(w,{'a':'dono'})  # the owner saves the real panel during the proof: both sides archive the same old version
                copy_new=iso.written_since(copy,copy_before); real_new=iso.written_since(real,real_before)
                self.assertEqual(len(copy_new),2)
                self.assertEqual(set(copy_new)&set(real_new),set())
                diff=iso.compare(real_before,iso.db_state(real))
                self.assertEqual((diff['unchanged'],diff['documents_changed']),(False,{'workspace':[7,8]}))
                put(w,{'a':'prova 2'})  # a copy write that reaches the real database is caught by content
                self.assertEqual(len(set(copy_new)&set(iso.written_since(real,real_before))),1)
            finally:
                w.close()

if __name__=='__main__':
    unittest.main()

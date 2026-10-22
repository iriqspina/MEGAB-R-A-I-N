"""Second central instance for proofs: a copy of the database on another port, never the real panel.

Command line (any Python with the app's runtime-packages works; Qt proofs need apps/ia-quota-widget/.venv):
  python scripts/isolated_server.py -- <proof command>   start, run the proof with MB_BASE/MB_DB, stop
  python scripts/isolated_server.py --hold               start, print a pairing link valid only on the copy, wait for Enter
Inside a Python proof:
  sys.path.insert(0, r'...\\apps\\megabrain-dashboard\\scripts'); from isolated_server import Isolated
  with Isolated() as inst: client = inst.pair(); client.http('/api/workspace'); inst.doc()
After the block, inst.report['ok'] says no write made on the copy reached the real database and the server stopped by itself.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, secrets, shutil, socket, sqlite3, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REAL_DB = APP / 'data' / 'central.sqlite3'
NATIVE_KEY = APP / 'data' / '.private' / 'native.key'
RESERVED = {8766, 8767}  # real local server and the remote gateway
MARK = (b'x-mb-instancia', b'isolada')
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
# Writing routes whose effect stays in the database copy. Anything else that writes is refused, so a new
# route stays blocked until someone classifies it (tests/test_isolated_server.py lists every route).
COPY_ONLY = tuple((m, re.compile(p)) for m, p in (
    ('POST', r'/api/pair$'), ('POST', r'/api/logout$'), ('PUT', r'/api/workspace$'), ('POST', r'/api/present$'),
    ('PUT', r'/api/projects/[^/]+/(?:process|routing|bridge|control)$'), ('POST', r'/api/projects/[^/]+/(?:route-preview|comments|references)$'), ('POST', r'/api/projects/[^/]+/comments/[^/]+/replies$'),
    ('POST', r'/api/reports/[^/]+/(?:draft|feedback|resolve)$')))


def allowed(method, path):
    return method in SAFE_METHODS or any(method == m and p.match(path) for m, p in COPY_ONLY)


def _ro(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=15)


def snapshot(dest, source=REAL_DB):
    """Consistent copy through the backup API (includes WAL pages); the source is opened read-only."""
    src = _ro(source); dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
        check = dst.execute('PRAGMA quick_check').fetchone()[0]
    finally:
        dst.close(); src.close()
    if check != 'ok': raise RuntimeError('Cópia do banco não passou na verificação: ' + str(check))
    return dest


def db_state(path=REAL_DB):
    """Revisions and counters that any write would move. Read-only."""
    c = _ro(path)
    try:
        docs = dict(c.execute('SELECT key, revision FROM documents').fetchall())
        row = c.execute("SELECT data FROM documents WHERE key='workspace'").fetchone()
        one = lambda sql: c.execute(sql).fetchone()[0]
        return dict(documents=docs, workspace=json.loads(row[0]) if row else None,
                    document_hashes={hashlib.sha256(d.encode()).hexdigest() for (d,) in c.execute('SELECT data FROM documents')},
                    history_max=one('SELECT COALESCE(MAX(id),0) FROM history'), events_max=one('SELECT COALESCE(MAX(id),0) FROM events'),
                    comments_max=one('SELECT COALESCE(MAX(rowid),0) FROM comments'), comments=one('SELECT COUNT(*) FROM comments'),
                    auth_sessions=one('SELECT COUNT(*) FROM auth_sessions'))
    finally:
        c.close()


def written_since(path, state):
    """Fingerprints of every row written after state: new document versions, history, events and comments.
    Content that already existed at state time is left out: the first save on each side archives that same old version."""
    c = _ro(path); h = lambda raw: hashlib.sha256(raw.encode()).hexdigest()
    try:
        out = {}
        for key, rev, data in c.execute('SELECT key, revision, data FROM documents'):
            if state['documents'].get(key) != rev: out[h(data)] = 'documento ' + key
        for key, data in c.execute('SELECT key, data FROM history WHERE id>?', (state['history_max'],)): out.setdefault(h(data), 'histórico ' + key)
        for (data,) in c.execute('SELECT data FROM events WHERE id>?', (state['events_max'],)): out.setdefault(h(data), 'evento')
        for cid, data in c.execute('SELECT id, data FROM comments WHERE rowid>?', (state['comments_max'],)): out.setdefault(h(data), 'comentário ' + cid)
        return {k: v for k, v in out.items() if k not in state['document_hashes']}
    finally:
        c.close()


def compare(before, after):
    canon = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True)
    keys = sorted(k for k in set(before['documents']) | set(after['documents']) if before['documents'].get(k) != after['documents'].get(k))
    ws0, ws1 = before['workspace'] or {}, after['workspace'] or {}
    return dict(unchanged=not keys and all(before[k] == after[k] for k in ('history_max', 'events_max', 'comments', 'auth_sessions')),
                documents_changed={k: [before['documents'].get(k), after['documents'].get(k)] for k in keys},
                workspace_keys_changed=sorted(k for k in set(ws0) | set(ws1) if canon(ws0.get(k)) != canon(ws1.get(k))),
                history_added=after['history_max'] - before['history_max'], events_added=after['events_max'] - before['events_max'],
                comments_added=after['comments'] - before['comments'], auth_sessions_added=after['auth_sessions'] - before['auth_sessions'])


def port_busy(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5): return True
    except OSError:
        return False


def alive(pid):
    if not pid: return False
    if os.name != 'nt':
        try: os.kill(pid, 0); return True
        except OSError: return False
    import ctypes  # os.kill(pid, 0) would terminate the process on Windows
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)
    if not h: return False
    code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
    return bool(ok) and code.value == 259


def sweep(hours=24):
    """Old copies from proofs whose parent died before cleaning up; they hold panel data and session hashes."""
    for d in Path(tempfile.gettempdir()).glob('mb-isolado-*'):
        try:
            if d.is_dir() and time.time() - d.stat().st_mtime > hours * 3600: shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


class Guard:
    """Marks every response as isolated and refuses writes that would leave the copy."""
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        if not allowed(scope['method'], scope['path']):
            body = json.dumps({'detail': 'Bloqueado na instância isolada: esta ação sai da cópia do banco.'}, ensure_ascii=False).encode()
            await send({'type': 'http.response.start', 'status': 403, 'headers': [(b'content-type', b'application/json'), (b'content-length', str(len(body)).encode()), MARK]})
            return await send({'type': 'http.response.body', 'body': body})
        async def marked(message):
            if message['type'] == 'http.response.start': message = dict(message, headers=[*message.get('headers', []), MARK])
            await send(message)
        return await self.app(scope, receive, marked)


def serve(db, port, ttl):
    """Child process. Stops by itself on stdin EOF (parent finished or died) or when ttl expires."""
    db = Path(db).resolve()
    if db == REAL_DB.resolve() or port in RESERVED: raise SystemExit('Recusado: a instância isolada não usa o banco real nem as portas 8766/8767.')
    reason, stop, holder = {}, threading.Event(), {}
    def finish(why):
        print(json.dumps({'event': 'stop', 'why': why, 'at': time.time()}), flush=True)
        os._exit(0)  # a stdin reader may still block; a normal shutdown would abort on its buffer lock
    def wait_parent():
        try: sys.stdin.buffer.read()
        except (OSError, ValueError, AttributeError): pass
        reason.setdefault('why', 'entrada fechada: o roteiro terminou ou caiu'); stop.set()
    def watchdog():
        if not stop.wait(ttl): reason.setdefault('why', f'prazo de {ttl}s')
        server = holder.get('server')
        if server is None: finish(reason['why'] + ' (antes de subir)')
        server.should_exit = True
        time.sleep(15); finish(reason['why'] + ' (forçado após 15 s)')
    # The watchdog starts before any import, so a hung startup still ends by itself.
    threading.Thread(target=wait_parent, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    print(json.dumps({'event': 'start', 'pid': os.getpid(), 'port': port, 'db': str(db), 'ttl': ttl}), flush=True)
    sys.path.insert(0, str(APP))
    import central_server, uvicorn  # central_server puts runtime-packages on sys.path
    from central_store import Store
    from central_sources import Sources
    store = Store(db); sources = Sources(store)
    # Polling also imports Downloads answers, freezes evidence into projects and runs the usage collector.
    # Those write shared files, so the copy only rediscovers projects.
    sources.poll = sources.discover
    app = Guard(central_server.build_app(store=store, sources=sources, port=port))
    holder['server'] = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, access_log=False, log_level='warning',
                                                     proxy_headers=False, timeout_graceful_shutdown=3))
    try: holder['server'].run()
    finally: finish(reason.get('why', 'servidor parou'))


class Client:
    def __init__(self, base, cookie):
        self.base, self.cookie, self.csrf = base, cookie, None
    def http(self, path, method='GET', body=None):
        if method != 'GET' and not self.csrf:
            self.csrf = (self.http('/api/session')[1] or {}).get('csrf')
        h = {'Cookie': self.cookie}
        if body is not None: h['Content-Type'] = 'application/json'
        if method != 'GET': h['X-MB-CSRF'] = self.csrf or ''
        rq = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body, ensure_ascii=False).encode(), headers=h, method=method)
        try:
            with urllib.request.urlopen(rq, timeout=30) as r:
                status, raw, headers = r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            status, raw, headers = e.code, e.read(), e.headers
        if headers.get(MARK[0].decode()) != MARK[1].decode(): raise RuntimeError('Resposta sem a marca da instância isolada.')
        try: return status, json.loads(raw or b'null')
        except ValueError: return status, None


class Isolated:
    def __init__(self, port=8768, ttl=900, keep=False):
        if port in RESERVED: raise ValueError('Use uma porta diferente de 8766 e 8767.')
        self.port, self.ttl, self.keep = port, ttl, keep
        self.base = f'http://127.0.0.1:{port}'
        self.report, self.proc, self.server_pid = {}, None, None
    def __enter__(self):
        if port_busy(self.port): raise RuntimeError(f'A porta {self.port} já está ocupada; nada foi iniciado.')
        sweep()
        self.t0 = time.time()
        self.dir = Path(tempfile.mkdtemp(prefix='mb-isolado-'))
        try:
            self._start()
        except BaseException:
            if self.proc: self.stop()
            self._cleanup(); raise
        return self
    def _start(self):
        self.db = self.dir / 'central.sqlite3'
        self.real_before = db_state()
        snapshot(self.db)
        self.copy_before = db_state(self.db)
        self.log_path = self.dir / 'servidor.log'
        self._log = self.log_path.open('wb')
        self.proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', '--db', str(self.db), '--port', str(self.port), '--ttl', str(self.ttl)],
                                     cwd=str(APP), stdin=subprocess.PIPE, stdout=self._log, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        end = time.time() + 60
        while time.time() < end:
            self.server_pid = self.server_pid or self._logged_pid()
            if self.proc.poll() is not None and not alive(self.server_pid): raise RuntimeError('A instância isolada não subiu: ' + self.log_tail())
            try:
                with urllib.request.urlopen(self.base + '/api/health', timeout=2) as r:
                    if r.headers.get(MARK[0].decode()) == MARK[1].decode() and json.loads(r.read()).get('ok'): break
            except (OSError, ValueError):
                pass
            time.sleep(0.3)
        else:
            raise RuntimeError('A instância isolada não respondeu em 60 s: ' + self.log_tail())
        # On Windows the first connect waits for the listener, so health can pass before the loop reread the log.
        self.server_pid = self.server_pid or self._logged_pid()
        if not alive(self.server_pid): raise RuntimeError('Servidor isolado sem pid conhecido no log: ' + self.log_tail())
        self.report.update(port=self.port, base=self.base, copy=str(self.db), server_pid=self.server_pid, launcher_pid=self.proc.pid,
                           copy_workspace_revision=self.doc()[0], up_in_s=round(time.time() - self.t0, 2))
    def _logged_pid(self):
        # A venv python.exe is a launcher that starts the real interpreter as its child; the child logs its own pid.
        return next((json.loads(l)['pid'] for l in self.log_tail(10000).splitlines() if l.startswith('{"event": "start"')), None)
    def pair(self):
        """Pairs with native.key like the native window does, but only the copy gains the session."""
        code = NATIVE_KEY.read_text(encoding='ascii').strip()
        rq = urllib.request.Request(self.base + '/api/pair', data=json.dumps({'code': code}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(rq, timeout=15) as r:
            return Client(self.base, r.headers.get('Set-Cookie', '').split(';')[0])
    def pairing_link(self, minutes=10):
        """One-time link valid only on the copy. localhost keeps its cookie apart from 127.0.0.1 (the real app)."""
        sys.path.insert(0, str(APP))
        from central_store import Store
        code = secrets.token_urlsafe(32)
        Store(self.db).pairing_create(code, time.time() + minutes * 60)
        return f'http://localhost:{self.port}/#pair={code}'
    def doc(self, key='workspace'):
        c = _ro(self.db)
        try: row = c.execute('SELECT revision, data FROM documents WHERE key=?', (key,)).fetchone()
        finally: c.close()
        return (row[0], json.loads(row[1])) if row else (0, None)
    def log_tail(self, n=2000):
        try: return self.log_path.read_text(encoding='utf-8', errors='replace')[-n:]
        except (OSError, AttributeError): return ''
    def stop(self):
        """Closing stdin asks the server to stop; only a server that ignores it is terminated."""
        forced = False
        try: self.proc.stdin.close()
        except OSError: pass
        try: self.proc.wait(timeout=25)
        except subprocess.TimeoutExpired:
            forced = True
            if os.name == 'nt': subprocess.run(['taskkill', '/T', '/F', '/PID', str(self.proc.pid)], capture_output=True)
            else: self.proc.terminate()
            self.proc.wait(timeout=10)
        end = time.time() + 10
        while alive(self.server_pid) and time.time() < end: time.sleep(0.2)
        if alive(self.server_pid):
            forced = True; os.kill(self.server_pid, 15)  # TerminateProcess on Windows, only for a server that ignored the stop
        return forced
    def _cleanup(self):
        try: self._log.close()
        except (AttributeError, OSError): pass
        if not self.keep: shutil.rmtree(self.dir, ignore_errors=True)
    def __exit__(self, *exc):
        forced = self.stop()
        after = db_state()
        copy_new = written_since(self.db, self.copy_before)
        real_new = written_since(REAL_DB, self.real_before)
        # The copy starts with the real rows, so only rows written after the copy are fingerprinted on each side.
        # A copy write that shows up in the real database is a leak; other real changes come from the real app or its owner.
        leaked = sorted(copy_new[h] for h in set(copy_new) & set(real_new))
        log = self.log_tail()
        self._cleanup()
        self.report.update(stopped_by_itself=not forced, exit_code=self.proc.returncode, server_alive_after=alive(self.server_pid),
                           port_free_after=not port_busy(self.port), seconds=round(time.time() - self.t0, 1),
                           copy_writes=len(copy_new), leaked_writes=leaked, real_db=compare(self.real_before, after),
                           copy_kept=str(self.db) if self.keep else None, server_log=[l for l in log.splitlines() if l.strip()][-6:])
        self.report['ok'] = not leaked and not forced and not self.report['server_alive_after'] and self.report['port_free_after']
        return False


def main(argv=None):
    p = argparse.ArgumentParser(description='Instância isolada da central: cópia do banco em outra porta, para provas que gravam.')
    p.add_argument('--port', type=int, default=8768)
    p.add_argument('--ttl', type=int, default=900, help='segundos até o servidor parar sozinho (padrão 900)')
    p.add_argument('--report', help='arquivo JSON para o relatório final')
    p.add_argument('--keep', action='store_true', help='não apagar a cópia do banco no fim')
    p.add_argument('--hold', action='store_true', help='sem comando: mostrar link de pareamento da cópia e esperar Enter')
    p.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--db', help=argparse.SUPPRESS)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args(argv)
    if a.serve: return serve(a.db, a.port, a.ttl)
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command and not a.hold: p.error('passe um comando depois de -- ou use --hold')
    code = 0
    with Isolated(a.port, a.ttl, a.keep) as inst:
        print(f'Instância isolada em {inst.base} (cópia {inst.db}); o painel real não é usado.', flush=True)
        if command:
            env = dict(os.environ, MB_BASE=inst.base, MB_PORT=str(inst.port), MB_DB=str(inst.db), MB_ISOLATED='1')
            code = subprocess.call(command, env=env)
            inst.report['command'] = dict(argv=command, exit_code=code)
        else:
            print('Abra numa janela anônima (vale 10 min, só na cópia):', inst.pairing_link(), flush=True)
            try: input('Enter encerra a instância isolada... ')
            except (EOFError, KeyboardInterrupt): pass
    text = json.dumps(inst.report, ensure_ascii=False, indent=1)
    if a.report: Path(a.report).write_text(text, encoding='utf-8')
    print(text)
    if inst.report['ok'] and not inst.report['real_db']['unchanged']:
        print('Aviso: o banco real mudou no período por outra janela ou pelo próprio app; nenhuma gravação da cópia chegou a ele.')
    return code or (0 if inst.report['ok'] else 3)


if __name__ == '__main__':
    raise SystemExit(main())

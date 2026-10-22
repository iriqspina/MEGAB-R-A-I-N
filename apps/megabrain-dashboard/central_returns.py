"""Persistent arrival order for reports; events share the activity journal."""
import hashlib, json, threading
from pathlib import Path
from central_store import now,ident
from central_reports import MAX_REPORT

# Events the user cares about: a report arrived, an answer came back, a request ended, a comment was made.
# Everything else (source changed, external operation, configuration...) is machine activity. It stays in
# the feed, grouped apart, and never counts as unread.
# 261018 (R1-01): report_answered = relatorio regravado enquanto havia comentario seu em aberto nele (a resposta da IA).
IMPORTANT_KINDS = ('report_arrived', 'report_answered', 'feedback_received', 'feedback_corrected', 'session_completed',
                   'session_partial', 'session_failed', 'session_interrupted', 'comment')
FEED_LIMIT = 100  # per group: a flood of machine events must not push real news out of the feed

class Returns:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        with store.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS report_inbox (key TEXT PRIMARY KEY, data TEXT NOT NULL)')

    def observe(self, sources):
        with self.lock:
            self._observe(sources)

    def _observe(self, sources):
        with self.store.db() as c:
            previous = {r['key']:json.loads(r['data']) for r in c.execute('SELECT * FROM report_inbox')}
            baseline = c.execute("SELECT 1 FROM documents WHERE key='returns:initialized'").fetchone() is None
        rows = []
        for pid, root in list(sources.projects.items()):
            titles = {}
            from mb_catalogo import coletar
            try:
                for d in coletar(root).get('entregas',[]):
                    if not d.get('arquivo'): continue
                    path=Path(d['arquivo']);path=path if path.is_absolute() else root/path
                    if d.get('titulo'):titles[ident(path.resolve())]=d['titulo']
            except (ValueError,OSError,KeyError): pass
            for d in sources.cache.get(pid, (0, {}))[1].get('deliveries', []):
                if d.get('file_id'): titles[d['file_id']] = d['title']
            for path in sources.report_paths(root):
                try:
                    asset = sources.index_file(path, root)
                    if not asset or asset['type'] != 'html': continue
                    key = pid+':'+asset['id']; old = previous.get(key, {})
                    stat = path.stat(); stamp = [stat.st_mtime_ns, stat.st_size]
                    if old.get('stamp') == stamp:
                        digest = old['hash']
                    else:
                        with path.open('rb') as f:
                            digest = hashlib.file_digest(f, 'sha256').hexdigest()
                        after = path.stat()
                        if stamp != [after.st_mtime_ns, after.st_size]: continue
                    rows.append(dict(key=key, id=asset['id'], project_id=pid,
                        title=titles.get(asset['id'], old.get('title') or path.stem.replace('_',' ')),
                        project_name='MegaBrain' if root == sources.parent/'MEGA B R A I  N' else root.name,
                        type='html', url=asset['url'], path=str(path), stamp=stamp, hash=digest,
                        renderable=stat.st_size<=MAX_REPORT,
                        source_updated_at=asset['updated_at'], historical=asset['historical']))
                except OSError:
                    continue  # Keep prior observations on temporary read failure.
        with self.store.db() as c:
            c.execute('BEGIN IMMEDIATE')
            # Re-read under the write lock: two scanners must not emit duplicates.
            baseline = c.execute("SELECT 1 FROM documents WHERE key='returns:initialized'").fetchone() is None
            for row in rows:
                found = c.execute('SELECT data FROM report_inbox WHERE key=?', (row['key'],)).fetchone()
                old = json.loads(found[0]) if found else {}
                changed = old.get('hash') != row['hash']
                at = now()
                row.update(first_seen=old.get('first_seen', at), arrived_at=old.get('arrived_at', at),
                           sequence=old.get('sequence', 0), baseline=old.get('baseline', baseline))
                if changed and not baseline and not row['historical']:
                    kind = 'report_arrived'
                    if old:
                        waiting = c.execute("SELECT 1 FROM comments WHERE json_extract(data,'$.target')=? AND json_extract(data,'$.status') LIKE 'Recebido%' LIMIT 1", ('file:'+row['id'],)).fetchone()
                        kind = 'report_answered' if waiting else 'report_updated'
                    event = dict(project_id=row['project_id'], title=row['title'], at=at,
                        kind=kind, file_id=row['id'], source_hash=row['hash'])
                    cur = c.execute('INSERT INTO events(project,data) VALUES(?,?)', (row['project_id'], json.dumps(event, ensure_ascii=False)))
                    row.update(sequence=cur.lastrowid, arrived_at=at, baseline=False)
                c.execute('INSERT OR REPLACE INTO report_inbox VALUES(?,?)', (row['key'], json.dumps(row, ensure_ascii=False)))
            c.execute("INSERT OR IGNORE INTO documents VALUES('returns:initialized',1,'{}')")

    def snapshot(self, sources, after=0):
        reports = []
        kind = "json_extract(data,'$.kind')"
        marks = ','.join('?' * len(IMPORTANT_KINDS))
        with self.store.db() as c:
            rows = c.execute('SELECT data FROM report_inbox').fetchall()
            news = c.execute(f'SELECT id,data FROM events WHERE {kind} IN ({marks}) ORDER BY id DESC LIMIT ?',
                             (*IMPORTANT_KINDS, FEED_LIMIT)).fetchall()
            machine = c.execute(f'SELECT id,data FROM events WHERE {kind} IS NULL OR {kind} NOT IN ({marks}) ORDER BY id DESC LIMIT ?',
                                (*IMPORTANT_KINDS, FEED_LIMIT)).fetchall()
            technical_count = c.execute(f'SELECT COUNT(*) FROM events WHERE {kind} IS NULL OR {kind} NOT IN ({marks})',
                                        IMPORTANT_KINDS).fetchone()[0]
            revision = c.execute('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0]
            unread = c.execute(f'SELECT COUNT(*) FROM events WHERE id>? AND {kind} IN ({marks})',
                               (max(0, after), *IMPORTANT_KINDS)).fetchone()[0]
        for r in rows:
            row = json.loads(r[0])
            try:
                asset = sources.index_file(row['path'], sources.root(row['project_id']))
                if not asset: continue
            except (KeyError,OSError): continue
            reports.append({k:v for k,v in row.items() if k not in {'path','stamp'}})
        reports.sort(key=lambda r:(r['sequence'],r['source_updated_at'] or ''), reverse=True)
        events = [dict(json.loads(r['data']), id=r['id'], important=True) for r in news] + \
                 [dict(json.loads(r['data']), id=r['id'], important=False) for r in machine]
        events.sort(key=lambda e: e['id'], reverse=True)
        return dict(reports=reports, events=events, revision=revision, unread=unread,
                    technical_count=technical_count, observed_at=now())

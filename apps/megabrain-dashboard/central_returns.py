"""Persistent arrival order for reports; events share the activity journal."""
import hashlib, json, threading
from pathlib import Path
from central_store import now,ident
from central_reports import MAX_REPORT

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
                    event = dict(project_id=row['project_id'], title=row['title'], at=at,
                        kind='report_updated' if old else 'report_arrived', file_id=row['id'], source_hash=row['hash'])
                    cur = c.execute('INSERT INTO events(project,data) VALUES(?,?)', (row['project_id'], json.dumps(event, ensure_ascii=False)))
                    row.update(sequence=cur.lastrowid, arrived_at=at, baseline=False)
                c.execute('INSERT OR REPLACE INTO report_inbox VALUES(?,?)', (row['key'], json.dumps(row, ensure_ascii=False)))
            c.execute("INSERT OR IGNORE INTO documents VALUES('returns:initialized',1,'{}')")

    def snapshot(self, sources, after=0):
        reports = []
        with self.store.db() as c:
            rows = c.execute('SELECT data FROM report_inbox').fetchall()
            events = c.execute('SELECT id,data FROM events ORDER BY id DESC LIMIT 100').fetchall()
            revision = c.execute('SELECT COALESCE(MAX(id),0) FROM events').fetchone()[0]
            unread = c.execute('SELECT COUNT(*) FROM events WHERE id>?', (max(0, after),)).fetchone()[0]
        for r in rows:
            row = json.loads(r[0])
            try:
                asset = sources.index_file(row['path'], sources.root(row['project_id']))
                if not asset: continue
            except (KeyError,OSError): continue
            reports.append({k:v for k,v in row.items() if k not in {'path','stamp'}})
        reports.sort(key=lambda r:(r['sequence'],r['source_updated_at'] or ''), reverse=True)
        return dict(reports=reports, events=[dict(json.loads(r['data']), id=r['id']) for r in events],
                    revision=revision, unread=unread, observed_at=now())

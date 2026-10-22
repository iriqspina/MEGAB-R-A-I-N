"""B-APP F0b · Localizador: índice persistente de metadados para GET /api/search.

O índice vive no mesmo SQLite do Store, é aditivo (nunca apaga linha) e guarda
somente metadados: sem caminho absoluto, URL de arquivo ou corpo de relatório.
Disponibilidade só muda para entregas (report/delivery), cuja observação em
detail() é completa; os demais tipos mantêm a última observação.
"""
from __future__ import annotations
import json
import logging
import unicodedata
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone

from central_store import JOB_TERMINAL_STATUSES, now

KINDS = frozenset({'project', 'report', 'delivery', 'file', 'reference', 'link', 'comment', 'job'})
SCOPES = frozenset({'todos', 'atuais', 'historico'})
MAX_QUERY = 200
MAX_LIMIT = 100
LIMIT_NOTE = 'Imagens e anexos: até 240 mais recentes por pasta do projeto.'
CURSOR_ERROR = 'Cursor inválido; recomece a busca.'
LOG = logging.getLogger('megabrain.catalog')


def normalize(text):
    """Minúsculas sem acento (NFKD, remove combinantes) para busca tolerante."""
    decomposed = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def sort_key(date):
    """Data com fuso vira UTC para ordenar texto com texto; sem fuso ou ilegível fica como veio."""
    if not date:
        return ''
    try:
        parsed = datetime.fromisoformat(str(date).replace('Z', '+00:00'))
    except ValueError:
        return str(date)
    return parsed.astimezone(timezone.utc).isoformat(timespec='seconds') if parsed.tzinfo else str(date)


def one_line(text, limit):
    return ' '.join(str(text or '').split())[:limit]


def encode_cursor(sort_date, key, revision):
    raw = json.dumps({'d': sort_date, 'k': key, 'r': revision}, separators=(',', ':'), ensure_ascii=False)
    return urlsafe_b64encode(raw.encode()).decode().rstrip('=')


def decode_cursor(value):
    try:
        padded = str(value) + '=' * (-len(str(value)) % 4)
        payload = json.loads(urlsafe_b64decode(padded.encode()).decode())
        d, k, r = payload['d'], payload['k'], payload['r']
        if not isinstance(d, str) or not isinstance(k, str) or not isinstance(r, int):
            raise ValueError('formato')
        return d, k, r
    except Exception:
        raise ValueError(CURSOR_ERROR)


class Catalog:
    """Índice de busca por fontes explícitas; consultas de leitura nunca ingerem."""

    def __init__(self, store):
        self.store = store
        with store.db() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS catalog_items(key TEXT PRIMARY KEY, project TEXT NOT NULL, project_name TEXT, kind TEXT NOT NULL, item_id TEXT NOT NULL, title TEXT NOT NULL, search_norm TEXT NOT NULL, sort_date TEXT NOT NULL, date TEXT, date_label TEXT, historical INTEGER NOT NULL DEFAULT 0, available INTEGER NOT NULL DEFAULT 1, first_seen TEXT, last_seen TEXT);
              CREATE TABLE IF NOT EXISTS catalog_coverage(project TEXT PRIMARY KEY, observed_at TEXT, items INTEGER, status TEXT);
              CREATE TABLE IF NOT EXISTS catalog_meta(key TEXT PRIMARY KEY, value TEXT);''')

    def revision(self):
        with self.store.db() as c:
            row = c.execute("SELECT value FROM catalog_meta WHERE key='revision'").fetchone()
        return int(row[0]) if row else 0

    def covered(self, pid):
        with self.store.db() as c:
            row = c.execute('SELECT 1 FROM catalog_coverage WHERE project=?', (str(pid),)).fetchone()
        return row is not None

    def ingest(self, pid, detail):
        """Indexa uma observação completa de detail() em uma transação; nada é apagado."""
        pid = str(pid)
        project = (detail.get('project') if isinstance(detail, dict) else None) or {}
        name = str(project.get('name') or pid)
        stamp = now()
        observed = {}

        def observe(kind, item_id, title, date, date_label, historical):
            item_id = str(item_id or '').strip()
            if not item_id:
                return
            title = str(title or '').strip() or item_id
            date = (str(date).strip() if date else '') or None
            key = f'{pid}:{kind}:{item_id}'
            observed[key] = dict(key=key, project=pid, project_name=name, kind=kind, item_id=item_id,
                                 title=title, search_norm=f'{normalize(title)} {normalize(name)}',
                                 sort_date=sort_key(date), date=date, date_label=date_label or None,
                                 historical=1 if historical else 0)

        # 1. Estado do projeto.
        observe('project', pid, name, project.get('updated_at'), 'Estado do projeto', False)
        # 2. Entregas: report quando é HTML com arquivo; senão delivery do registro.
        delivery_files = set()
        for row in detail.get('deliveries') or []:
            if not isinstance(row, dict):
                continue
            file_id = str(row.get('file_id') or '').strip()
            if file_id:
                delivery_files.add(file_id)
            is_report = bool(file_id) and row.get('type') == 'html'
            observe('report' if is_report else 'delivery', file_id or row.get('id'),
                    row.get('title'), row.get('updated_at'), 'Arquivo atualizado', row.get('historical'))
        # 3. Assets que não são arquivo de entrega já indexado.
        for row in detail.get('assets') or []:
            if not isinstance(row, dict) or str(row.get('id') or '') in delivery_files:
                continue
            observe('reference' if row.get('role') == 'reference' else 'file', row.get('id'),
                    row.get('name'), row.get('updated_at'), None, row.get('historical'))
        # 4/5/6. Registros próprios do Store, consulta direta sem o LIMIT 250 de listing().
        with self.store.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for table, kind in (('refs', 'link'), ('comments', 'comment'), ('jobs', 'job')):
                for row in c.execute(f'SELECT data FROM {table} WHERE project=?', (pid,)).fetchall():
                    try:
                        record = json.loads(row[0])
                    except ValueError:
                        LOG.warning('Registro ilegível ignorado no índice: %s/%s', table, pid)
                        continue
                    if not isinstance(record, dict):
                        continue
                    if kind == 'link':
                        title = record.get('title') or record.get('name') or 'Referência sem título'
                        observe('link', record.get('id'), title, record.get('at'), None, False)
                    elif kind == 'comment':
                        text = one_line(record.get('text'), 80) or 'Comentário'
                        # 'onde' traz só o nome do arquivo comentado; sem ele, 71 resumos "Respostas
                        # recebidas pelo relatório" ficavam iguais na busca (banco real, 261022).
                        onde = one_line(str(record.get('onde') or '').replace('\\', '/').rsplit('/', 1)[-1], 80)
                        observe('comment', record.get('id'), f'{text} · {onde}' if onde and onde not in text else text,
                                record.get('at'), None, record.get('status') == 'CORRIGIDO_VERIFICADO')
                    else:
                        observe('job', record.get('id'), one_line(record.get('title'), 120),
                                record.get('updated_at') or record.get('at'), None,
                                record.get('status') in JOB_TERMINAL_STATUSES)
            existing = {r['key']: r for r in c.execute('SELECT * FROM catalog_items WHERE project=?', (pid,)).fetchall()}
            added = updated = unavailable = 0
            inserts = []
            fields = ('project_name', 'title', 'search_norm', 'sort_date', 'date', 'date_label', 'historical')
            for item in observed.values():
                old = existing.get(item['key'])
                if old is None:
                    inserts.append((item['key'], pid, name, item['kind'], item['item_id'], item['title'],
                                    item['search_norm'], item['sort_date'], item['date'], item['date_label'],
                                    item['historical'], 1, stamp, stamp))
                    added += 1
                    continue
                # Presença na observação devolve disponibilidade; nunca apaga histórico.
                if not old['available'] or any(old[f] != item[f] for f in fields):
                    updated += 1
                c.execute('UPDATE catalog_items SET project_name=?,title=?,search_norm=?,sort_date=?,date=?,date_label=?,historical=?,available=1,last_seen=? WHERE key=?',
                          (name, item['title'], item['search_norm'], item['sort_date'], item['date'],
                           item['date_label'], item['historical'], stamp, item['key']))
            c.executemany('INSERT INTO catalog_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', inserts)
            gone = [key for key, row in existing.items()
                    if row['kind'] in ('report', 'delivery') and row['available'] and key not in observed]
            for key in gone:
                c.execute('UPDATE catalog_items SET available=0 WHERE key=?', (key,))
                unavailable += 1
            total = c.execute('SELECT COUNT(*) FROM catalog_items WHERE project=?', (pid,)).fetchone()[0]
            c.execute('INSERT OR REPLACE INTO catalog_coverage VALUES(?,?,?,?)', (pid, stamp, total, 'completo'))
            if added or updated or unavailable:
                current = c.execute("SELECT value FROM catalog_meta WHERE key='revision'").fetchone()
                c.execute("INSERT INTO catalog_meta(key,value) VALUES('revision',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (str(int(current[0]) + 1 if current else 1),))
        return dict(added=added, updated=updated, unavailable=unavailable)

    def search(self, q='', project=None, kind=None, scope='todos', cursor=None, limit=50, projects=()):
        if scope not in SCOPES:
            raise ValueError('Escopo inválido; use "todos", "atuais" ou "historico".')
        if kind is not None and kind not in KINDS:
            raise ValueError('Tipo inválido; use um de: ' + ', '.join(sorted(KINDS)) + '.')
        q = '' if q is None else str(q)
        if len(q) > MAX_QUERY:
            raise ValueError(f'Busca longa demais; use até {MAX_QUERY} caracteres.')
        tokens = [t for t in normalize(q).split() if t]
        try:
            limit = max(1, min(int(limit), MAX_LIMIT))
        except (TypeError, ValueError):
            limit = 50
        after = decode_cursor(cursor) if cursor is not None else None
        filters = []
        params = []
        for token in tokens:
            filters.append('instr(search_norm,?)>0')
            params.append(token)
        if project:
            filters.append('project=?')
            params.append(str(project))
        if kind:
            filters.append('kind=?')
            params.append(kind)
        count_where = (' WHERE ' + ' AND '.join(filters)) if filters else ''
        count_params = list(params)
        if scope == 'atuais':
            filters.append('historical=0')
        elif scope == 'historico':
            filters.append('historical=1')
        if after:
            d, k, _r = after
            filters.append('(sort_date<? OR (sort_date=? AND key>?))')
            params.extend([d, d, k])
        where = (' WHERE ' + ' AND '.join(filters)) if filters else ''
        with self.store.db() as c:
            # Uma leitura só: itens, contagens e cobertura da mesma revisão do índice.
            c.execute('BEGIN')
            rows = c.execute('SELECT * FROM catalog_items' + where + ' ORDER BY sort_date DESC, key ASC LIMIT ?',
                             params + [limit + 1]).fetchall()
            counts = c.execute('SELECT COUNT(*),COALESCE(SUM(historical=0),0),COALESCE(SUM(historical=1),0),COALESCE(SUM(available=0),0) FROM catalog_items' + count_where, count_params).fetchone()
            marks = {r['project']: r for r in c.execute('SELECT * FROM catalog_coverage').fetchall()}
            last = c.execute('SELECT MAX(last_seen) FROM catalog_items').fetchone()[0]
            seen = c.execute('SELECT MAX(observed_at) FROM catalog_coverage').fetchone()[0]
        revision = self.revision()
        items = [self._item(row) for row in rows[:limit]]
        next_cursor = encode_cursor(rows[limit - 1]['sort_date'], rows[limit - 1]['key'], revision) if len(rows) > limit else None
        coverage = []
        for entry in projects or ():
            pid = str((entry or {}).get('id') or '')
            if not pid:
                continue
            mark = marks.get(pid)
            coverage.append(dict(project=pid, name=(entry or {}).get('name'),
                                 observed_at=mark['observed_at'] if mark else None,
                                 items=mark['items'] if mark else 0,
                                 status=mark['status'] if mark else 'nao_lido'))
        return dict(items=items, next_cursor=next_cursor, query_revision=revision,
                    revision_changed=bool(after and after[2] != revision),
                    observed_at=max(x for x in (last, seen) if x) if (last or seen) else now(),
                    counts=dict(total=counts[0], atuais=counts[1], historico=counts[2], indisponiveis=counts[3]),
                    coverage=coverage, limits=[LIMIT_NOTE], limites=[LIMIT_NOTE])

    @staticmethod
    def _item(row):
        return dict(key=row['key'], kind=row['kind'], project_id=row['project'], project_name=row['project_name'],
                    title=row['title'], date=row['date'], date_label=row['date_label'],
                    historical=bool(row['historical']), available=bool(row['available']),
                    target=dict(kind=row['kind'], projectId=row['project'], itemId=row['item_id']))

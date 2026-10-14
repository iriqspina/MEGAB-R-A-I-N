"""Receive allowlisted exported decisions and notes; never execute their contents.

scan() is safe to call from the source poller or the standalone helper. SQLite
serializes receipt, comments and the notification as one transaction. The raw
download is retained unchanged and a content-addressed evidence copy is frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import stat
import threading
import time
import tempfile
from datetime import datetime
from pathlib import Path

from central_store import APP, ROOT, ident, now

KEY = 'local-export'
STATUS_LABEL = 'Recebido, aguardando correção'
MAX_BYTES = 350_000
MAX_DOCUMENT = 280_000
# Importador legado desativado; decisões nativas dos relatórios continuam disponíveis.
ALLOWLIST = {}
_SCAN_LOCK = threading.Lock()
LOG = logging.getLogger('megabrain.feedback')


def _no_links(path):
    """Reject symlinks and Windows junction/reparse points, including ancestors."""
    for item in [path, *path.parents]:
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('linked_path')


def _text(value, limit, empty=True):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value:
        raise ValueError('invalid_text')
    if not empty and not value.strip():
        raise ValueError('empty_text')
    return value


def validate(data):
    """Validate data only. JSON can supply no project, executable action or path."""
    if not isinstance(data, dict) or type(data.get('versao')) is not int or data['versao'] != 1:
        raise ValueError('invalid_version')
    if not isinstance(data.get('chave'), str) or data['chave'] not in ALLOWLIST:
        raise ValueError('unknown_key')
    for key in data:
        if key.startswith('autoriza_') and data[key] is not False:
            raise ValueError('permission_flag')
    if 'finalizado' in data and type(data['finalizado']) is not bool:
        raise ValueError('invalid_finalizado')
    _text(data.get('titulo', ''), 240)
    _text(data.get('enviado_em', ''), 100, empty=False)
    if data.get('enviado_em'):
        try:
            parsed = datetime.fromisoformat(data['enviado_em'].replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('missing_timezone')
        except ValueError:
            raise ValueError('invalid_export_time') from None
    answers = data.get('respostas')
    if not isinstance(answers, dict) or len(answers) > 100:
        raise ValueError('invalid_answers')
    for key, row in answers.items():
        if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', key):
            raise ValueError('invalid_answer_key')
        if not isinstance(row, dict) or type(row.get('mexeu')) is not bool:
            raise ValueError('invalid_mexeu')
        _text(row.get('valor'), 6000)
        _text(row.get('extra', ''), 6000)
    notes = data.get('notas', [])
    if not isinstance(notes, list) or len(notes) > 100:
        raise ValueError('invalid_notes')
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError('invalid_note')
        _text(note.get('texto'), 6000, empty=False)
        _text(note.get('onde', ''), 6000)
        _text(note.get('criado_em', ''), 100)
    # Unknown fields remain frozen in the original but never enter actionable state.
    useful = {key: data.get(key) for key in ('versao', 'chave', 'titulo', 'enviado_em', 'finalizado')}
    useful.update(respostas=answers, notas=notes)
    if len(json.dumps(useful, ensure_ascii=False).encode()) > MAX_DOCUMENT:
        raise ValueError('document_budget')
    return useful


def _read(path):
    _no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
        raise ValueError('file_size_or_type')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
        opened = os.fstat(stream.fileno())
    _no_links(path)
    after = path.stat()
    if len(raw) > MAX_BYTES:
        raise ValueError('file_size_or_type')
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or len(raw) != after.st_size or opened.st_ino != after.st_ino:
        raise OSError('file_changing')
    return raw, validate(json.loads(raw.decode('utf-8-sig')))


def _write_document(db, key, data):
    raw = json.dumps(data, ensure_ascii=False)
    if len(raw.encode()) > 300_000:
        raise ValueError('document_budget')
    row = db.execute('SELECT revision,data FROM documents WHERE key=?', (key,)).fetchone()
    if row:
        db.execute('INSERT INTO history(key,revision,data,at) VALUES(?,?,?,?)',
                   (key, row['revision'], row['data'], now()))
    db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
               (key, (row['revision'] if row else 0) + 1, raw))


def _freeze(root, route, digest, raw):
    directory = root / route['evidence']
    _no_links(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (digest + '.json')
    _no_links(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix='.receiving-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('evidence_mismatch')
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return path


def _receive(store, sources, path, raw, data, config):
    route = dict(ALLOWLIST[data['chave']])
    # Trusted code configuration only, used by isolated tests/deployment adapters.
    route.update((config or {}).get('routes', {}).get(data['chave'], {}))
    root = Path((config or {}).get('project_roots', {}).get(route['project'], ROOT.parent / route['project']))
    _no_links(root)
    root = root.resolve(strict=True)
    pid = next((p for p, value in sources.projects.items() if Path(value).resolve() == root), None)
    if not pid:
        raise ValueError('project_not_available')
    digest = hashlib.sha256(raw).hexdigest()
    key = data['chave']
    aggregate_key = f'feedback:{pid}:{key}'
    export_key = f'{aggregate_key}:{digest}'
    manifest_key = f'feedback-import:{pid}:{key}:{digest}'
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM documents WHERE key=?', (manifest_key,)).fetchone():
            return {'status': 'duplicate', 'hash': digest, 'project_id': pid}
        frozen = _freeze(root, route, digest, raw)
        at = now()
        row = db.execute('SELECT data FROM documents WHERE key=?', (aggregate_key,)).fetchone()
        aggregate = json.loads(row['data']) if row else {'notes': {}, 'decision_states': {}}
        # Existing correction/proof fields survive every new export.
        new_notes = 0
        for note in data['notas']:
            note_hash = hashlib.sha256(json.dumps([key, note['texto'], note.get('onde', ''),
                                                  note.get('criado_em', '')], ensure_ascii=False).encode()).hexdigest()
            note_id = f'feedback-{note_hash}'
            if not db.execute('SELECT 1 FROM comments WHERE id=?', (note_id,)).fetchone():
                comment = dict(id=note_id, author='<USUARIO>', text=note['texto'],
                               onde=note.get('onde', ''), criado_em=note.get('criado_em', ''),
                               at=note.get('criado_em') or at, received_at=at,
                               target=f'feedback:{key}', task=route['task'],
                               source=route['source'], source_hash=digest, feedback_key=key,
                               status='RECEBIDO', status_label=STATUS_LABEL)
                db.execute('INSERT INTO comments VALUES(?,?,?)', (note_id, pid, json.dumps(comment, ensure_ascii=False)))
                new_notes += 1
            aggregate.setdefault('notes', {}).setdefault(note_id, dict(status='RECEBIDO', status_label=STATUS_LABEL))
        decisions = {k: v for k, v in data['respostas'].items()
                     if v['mexeu'] and (v['valor'].strip() or v.get('extra', '').strip())}
        old_time = aggregate.get('export_at')
        new_time = data.get('enviado_em')
        latest = not old_time or not new_time or datetime.fromisoformat(new_time.replace('Z', '+00:00')) >= datetime.fromisoformat(old_time.replace('Z', '+00:00'))
        if latest:
            aggregate.update(key=key, project_id=pid, task=route['task'], source=route['source'],
                         received_at=at, export_at=data.get('enviado_em'), latest_hash=digest,
                         latest_document=export_key, decisions=decisions,
                         respostas=data['respostas'], path=str(frozen),
                         status='RECEBIDO', status_label=STATUS_LABEL)
        for name, decision in (decisions.items() if latest else []):
            # A changed answer becomes pending; the previous correction stays in history.
            decision_digest = hashlib.sha256(json.dumps(decision, ensure_ascii=False).encode()).hexdigest()
            state = aggregate.setdefault('decision_states', {}).get(name, {})
            if state.get('hash') != decision_digest:
                aggregate['decision_states'][name] = dict(hash=decision_digest, status='RECEBIDO', status_label=STATUS_LABEL)
        manifest = dict(hash=digest, path=str(frozen), downloaded_path=str(path),
                        feedback_key=key, document_key=export_key, received_at=at,
                        decision_count=len(decisions), note_count=len(data['notas']),
                        new_note_count=new_notes, project_id=pid, status='RECEBIDO')
        summary = dict(id=f'feedback-summary-{digest}', author='<USUARIO>',
                       target=f'feedback-summary:{key}', feedback_key=key, source_hash=digest,
                       text=f'{len(decisions)} escolhas e {len(data["notas"])} notas recebidas. Notas preservadas; correções ainda aguardam execução.',
                       at=data.get('enviado_em') or at, received_at=at, source=route['source'],
                       path=str(frozen), status='RECEBIDO', status_label=STATUS_LABEL,
                       decision_count=len(decisions), note_count=len(data['notas']))
        db.execute('INSERT INTO comments VALUES(?,?,?)', (summary['id'], pid, json.dumps(summary, ensure_ascii=False)))
        _write_document(db, export_key, dict(data, receipt=manifest))
        _write_document(db, aggregate_key, aggregate)
        _write_document(db, manifest_key, manifest)
        event = dict(project_id=pid, title='Marcelinho: respostas e notas recebidas',
                     kind='feedback_received', at=at, feedback_key=key, hash=digest,
                     path=str(frozen), document_key=aggregate_key,
                     decision_count=len(decisions), note_count=len(data['notas']),
                     new_note_count=new_notes, status='RECEBIDO', status_label=STATUS_LABEL)
        db.execute('INSERT INTO events(project,data) VALUES(?,?)', (pid, json.dumps(event, ensure_ascii=False)))
    if hasattr(sources, 'cache'):
        sources.cache.pop(pid, None)
    return dict(manifest, status='imported', status_label=STATUS_LABEL)


def scan(store, sources, download_dirs=None, config=None):
    """Scan immediate '*respostas*.json' downloads. Invalid files are retryable.

    Return counters and imported receipt metadata, never note/answer contents.
    No jobs, external messages, publishing, or source mutation are authorized.
    """
    result = dict(imported=0, duplicates=0, rejected=0, deferred=0, items=[])
    directories = download_dirs if download_dirs is not None else [Path('S:/Downloads'), Path.home() / 'Downloads']
    with _SCAN_LOCK:
        seen = set()
        for directory in directories:
            directory = Path(directory)
            try:
                _no_links(directory)
                if not directory.is_dir():
                    continue
                resolved = directory.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                candidates = [p for p in directory.iterdir() if 'respostas' in p.name.casefold() and p.suffix.casefold() == '.json']
            except (OSError, ValueError):
                result['deferred'] += 1
                continue
            for path in sorted(candidates, key=lambda p: p.name.casefold()):
                try:
                    raw, data = _read(path)
                    item = _receive(store, sources, path, raw, data, config)
                except (OSError, UnicodeError, json.JSONDecodeError):
                    result['deferred'] += 1
                    continue
                except ValueError:
                    result['rejected'] += 1
                    continue
                result['duplicates' if item['status'] == 'duplicate' else 'imported'] += 1
                if item['status'] == 'imported':
                    result['items'].append(item)
    return result


class Singleton:
    """An OS lock is released automatically after a crash; never kill a process."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('a+b')
        self.stream.seek(0)
        if self.path.stat().st_size == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            self.stream = None
            raise RuntimeError('feedback_helper_already_running')
        return self

    def __exit__(self, *args):
        if self.stream:
            if os.name == 'nt':
                import msvcrt
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            self.stream.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Receber respostas e notas locais, sem executar ações.')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--once', action='store_true')
    modes.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=float, default=4)
    args = parser.parse_args(argv)
    from central_store import Store
    from central_sources import Sources
    runtime = APP / 'data' / 'feedback'
    runtime.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(handlers=[RotatingFileHandler(runtime / 'helper.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')], level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    try:
        with Singleton(runtime / 'helper.lock'):
            store = Store()
            sources = Sources(store)
            while True:
                try:
                    sources.discover()
                    result = scan(store, sources)
                    heartbeat = dict(at=now(), pid=os.getpid(), state='watching' if args.watch else 'once',
                                     **{k: v for k, v in result.items() if k != 'items'})
                    LOG.info('scan imported=%s duplicates=%s rejected=%s deferred=%s',
                             result['imported'], result['duplicates'], result['rejected'], result['deferred'])
                except Exception as exc:
                    LOG.error('scan failed: %s', type(exc).__name__)
                    heartbeat = dict(at=now(), pid=os.getpid(), state='error', error=type(exc).__name__)
                temp = runtime / 'heartbeat.tmp'
                temp.write_text(json.dumps(heartbeat), encoding='utf-8')
                temp.replace(runtime / 'heartbeat.json')
                if not args.watch:
                    return 0 if heartbeat['state'] != 'error' else 1
                time.sleep(max(1, min(args.interval, 60)))
    except RuntimeError:
        LOG.info('Existing helper keeps its lock; no second watcher started.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())

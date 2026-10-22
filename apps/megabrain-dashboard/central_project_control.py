"""Controle cooperativo por projeto; retornos e processos em curso permanecem intactos."""
from contextlib import closing
import json
import sqlite3
from pathlib import Path
from central_store import ident, now

DEFAULT = {'modo': 'ativo'}
MODES = {'ativo', 'aguardando', 'pausado'}

def read(store, pid):
    return store.get('project-control:' + pid, DEFAULT)

def save(store, pid, revision, modo):
    if modo not in MODES:
        raise ValueError('Controle inválido: ativo, aguardando ou pausado.')
    return store.put('project-control:' + pid, revision, {'modo': modo, 'at': now()})

def check(store, pid, etapa=False):
    value = read(store, pid)['data']
    mode = value.get('modo', 'ativo')
    if mode == 'pausado' or (mode != 'ativo' and not etapa):
        raise ValueError('Projeto ' + mode + '. Use Retomar projeto no cursor antes de iniciar novas execuções.')

def check_path(root, central=None, etapa=False):
    # Somente leitura: CLI nunca cria banco ou sessão para consultar a barreira.
    app = Path(__file__).resolve().parent
    db = Path(central) / 'apps/megabrain-dashboard/data/central.sqlite3' if central else app / 'data/central.sqlite3'
    if not db.exists():
        return
    with closing(sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True, timeout=15)) as conn:
        row = conn.execute('SELECT data FROM documents WHERE key=?', ('project-control:' + ident(Path(root).resolve()),)).fetchone()
    mode = json.loads(row[0]).get('modo', 'ativo') if row else 'ativo'
    if mode == 'pausado' or (mode != 'ativo' and not etapa):
        raise ValueError('Projeto ' + mode + '. Retomada explícita necessária; nenhum processo foi encerrado.')

"""B-APP F0 · D12: pedido ativo antigo não pode sumir atrás do lote de 250 concluídos.

Fixture sintética (sem modelo, sem banco real): um pedido ativo antigo seguido de 300 concluídos.
"""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'tests'), str(APP / 'runtime-packages')]
from central_store import Store, JOB_TERMINAL_STATUSES
import test_central_security as security_fixture
asgi_request = security_fixture.asgi_request


def fill(store, pid, other='outro'):
    """Ativo antigo primeiro (rowid menor), depois 300 concluídos alternando projetos."""
    store.add('jobs', pid, dict(id='ativo-antigo', project_id=pid, status='queued', title='Ativo antigo'))
    with store.db() as db:
        db.executemany('INSERT INTO jobs VALUES(?,?,?)', [
            (f'feito-{i}', pid if i % 2 else other,
             json.dumps(dict(id=f'feito-{i}', project_id=pid if i % 2 else other, status='completed')))
            for i in range(300)])


class JobsOverviewStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'central.sqlite3')

    def test_listing_alone_drops_old_active_job(self):
        # Registro do defeito D12 (comportamento antigo preservado em listing()).
        fill(self.store, 'p')
        self.assertNotIn('ativo-antigo', [j['id'] for j in self.store.listing('jobs')])

    def test_overview_keeps_every_active_job_and_reports_cut(self):
        fill(self.store, 'p')
        out = self.store.jobs_overview()
        ids = [j['id'] for j in out['jobs']]
        self.assertIn('ativo-antigo', ids)
        self.assertEqual(out['active_count'], 1)
        self.assertEqual(out['history_total'], 300)
        self.assertEqual(out['history_returned'], 250)
        self.assertTrue(out['history_truncated'])
        self.assertEqual(len(ids), len(set(ids)))
        # Ativos vêm antes do histórico; histórico do mais novo para o mais antigo.
        self.assertEqual(ids[0], 'ativo-antigo')
        self.assertEqual(ids[1], 'feito-299')

    def test_project_filter_applies_before_limit(self):
        fill(self.store, 'p')
        out = self.store.jobs_overview('p')
        self.assertEqual({j['project_id'] for j in out['jobs']}, {'p'})
        self.assertIn('ativo-antigo', [j['id'] for j in out['jobs']])
        self.assertEqual(out['history_total'], 150)
        self.assertFalse(out['history_truncated'])

    def test_unknown_and_blocked_status_stay_visible_as_active(self):
        for jid, status in (('sem-status', None), ('bloqueado', 'blocked'), ('novo', 'status-inventado')):
            self.store.add('jobs', 'p', dict(id=jid, project_id='p', status=status))
        with self.store.db() as db:
            db.executemany('INSERT INTO jobs VALUES(?,?,?)', [
                (f'f{i}', 'p', json.dumps(dict(id=f'f{i}', status=s)))
                for i, s in enumerate(sorted(JOB_TERMINAL_STATUSES) * 40)])
        out = self.store.jobs_overview('p', history_limit=10)
        self.assertEqual({j['id'] for j in out['jobs'][:3]}, {'sem-status', 'bloqueado', 'novo'})
        self.assertEqual(out['active_count'], 3)
        self.assertEqual(out['history_returned'], 10)

    def test_history_limit_is_clamped(self):
        fill(self.store, 'p')
        self.assertEqual(self.store.jobs_overview(history_limit=10_000)['history_returned'], 250)
        self.assertEqual(self.store.jobs_overview(history_limit=-5)['history_returned'], 0)


class JobsApiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'MB_ISOLATED': '1', 'MB_PONTE': '0'})
        self.env.start()
        self.fixture = security_fixture.CentralSecurityTests()
        self.fixture.setUp()
        self.auth = self.fixture.local_login()
        self.pid = self.fixture.pid
        fill(self.fixture.store, self.pid)

    def tearDown(self):
        self.fixture.tearDown()
        self.env.stop()

    def get(self, path):
        status, _, content = asyncio.run(asgi_request(self.fixture.local, path, 'GET', None, self.auth))
        return status, json.loads(content)

    def test_api_jobs_includes_old_active_job(self):
        status, body = self.get('/api/jobs')
        self.assertEqual(status, 200)
        self.assertIn('ativo-antigo', [j['id'] for j in body['jobs']])
        self.assertTrue(body['history_truncated'])
        self.assertEqual(body['active_count'], 1)

    def test_api_jobs_project_filter(self):
        status, body = self.get(f'/api/jobs?project={self.pid}')
        self.assertEqual(status, 200)
        self.assertEqual({j['project_id'] for j in body['jobs']}, {self.pid})
        self.assertIn('ativo-antigo', [j['id'] for j in body['jobs']])


if __name__ == '__main__':
    unittest.main()

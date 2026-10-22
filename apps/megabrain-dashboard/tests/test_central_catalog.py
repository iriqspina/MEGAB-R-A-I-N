"""B-APP F0b · Localizador: índice persistente de busca + GET /api/search.

Fixture sintética (SQLite temporário, sem banco real): detalhes construídos à mão
e registros próprios gravados direto no Store. A API usa o fixture de segurança,
como tests/test_central_jobs_completeness.py.
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
from central_store import Store
from central_catalog import Catalog, decode_cursor
import test_central_security as security_fixture
asgi_request = security_fixture.asgi_request


def make_detail(pid, name='Projeto Sintético', updated_at='2026-01-05T00:00:00+00:00', deliveries=(), assets=()):
    return dict(project=dict(id=pid, name=name, updated_at=updated_at),
                deliveries=list(deliveries), assets=list(assets))


def delivery(did, title, at, *, file_id=None, type=None, historical=False):
    return dict(id=did, title=title, file_id=file_id, type=type, updated_at=at, historical=historical)


def asset(aid, name, at, *, role='result', historical=False):
    return dict(id=aid, name=name, role=role, updated_at=at, historical=historical)


class CatalogTestBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'central.sqlite3')
        self.catalog = Catalog(self.store)


class SearchPaginationTests(CatalogTestBase):
    def seed_two_projects(self):
        self.catalog.ingest('p1', make_detail('p1', 'Projeto Um', '2026-01-05T00:00:00+00:00', deliveries=[
            delivery('d1', 'Entrega um', '2026-01-04T00:00:00+00:00'),
            delivery('r1', 'Relatório um', '2026-01-03T01:00:00+00:00', file_id='f1', type='html'),
        ], assets=[
            asset('x1', 'foto.png', '2026-01-02T00:00:00+00:00'),
            asset('x2', 'guia.html', '2026-01-01T00:00:00+00:00', role='reference', historical=True),
        ]))
        self.store.add('refs', 'p2', dict(title='Vínculo externo', at='2026-01-07T00:00:00+00:00'))
        self.catalog.ingest('p2', make_detail('p2', 'Projeto Dois', '2026-01-06T00:00:00+00:00', deliveries=[
            delivery('d2', 'Entrega dois', '2026-01-03T02:00:00+00:00'),
            delivery('r2', 'Relatório dois', '2026-01-02T00:00:00+00:00', file_id='f2', type='html', historical=True),
        ]))

    def collect_all(self, limit=2, stop_after=None, cursor=None):
        keys, pages = [], 0
        while True:
            out = self.catalog.search(limit=limit, cursor=cursor)
            keys += [i['key'] for i in out['items']]
            cursor = out['next_cursor']
            pages += 1
            if cursor is None or (stop_after and pages >= stop_after):
                return keys, cursor, out

    def test_empty_query_returns_current_and_historical_from_both_projects(self):
        self.seed_two_projects()
        out = self.catalog.search()
        self.assertEqual(len(out['items']), 9)
        self.assertEqual(out['counts'], {'total': 9, 'atuais': 7, 'historico': 2, 'indisponiveis': 0})
        self.assertEqual({i['project_id'] for i in out['items']}, {'p1', 'p2'})
        self.assertEqual(len([i for i in out['items'] if i['historical']]), 2)
        self.assertTrue(all(i['available'] for i in out['items']))

    def test_pagination_walks_every_item_once_without_skips_or_duplicates(self):
        self.seed_two_projects()
        keys, cursor, _ = self.collect_all()
        self.assertIsNone(cursor)
        self.assertEqual(len(keys), 9)
        self.assertEqual(len(set(keys)), 9)

    def test_item_inserted_between_pages_neither_duplicates_seen_items_nor_skips_old_ones(self):
        self.seed_two_projects()
        seen, cursor, _ = self.collect_all(stop_after=2)
        self.assertEqual(len(seen), 4)
        # Item novo com data ainda não paginada (depois do cursor, antes dos restantes).
        self.catalog.ingest('p2', make_detail('p2', 'Projeto Dois', '2026-01-06T00:00:00+00:00', deliveries=[
            delivery('d2', 'Entrega dois', '2026-01-03T02:00:00+00:00'),
            delivery('r2', 'Relatório dois', '2026-01-02T00:00:00+00:00', file_id='f2', type='html', historical=True),
            delivery('novo', 'Entrega concorrente', '2026-01-03T12:00:00+00:00'),
        ]))
        rest, cursor, out = self.collect_all(cursor=cursor)
        all_keys = seen + rest
        self.assertIsNone(cursor)
        self.assertEqual(len(all_keys), 10, 'o item novo entra, os nove antigos continuam')
        self.assertEqual(len(set(all_keys)), 10, 'nenhum item já visto se repete')
        self.assertTrue(set(seen).isdisjoint(rest))
        self.assertEqual(out['counts']['total'], 10)


class SearchMatchingTests(CatalogTestBase):
    def test_mixed_offsets_sort_by_real_instant(self):
        # 22:00 -03:00 é 01:00 UTC do dia seguinte: vem antes de 23:00 UTC do mesmo dia.
        self.catalog.ingest('p1', make_detail('p1', 'Projeto Um', updated_at=None, deliveries=[
            delivery('utc', 'Em UTC', '2026-01-04T23:00:00+00:00'),
            delivery('local', 'Em Brasília', '2026-01-04T22:00:00-03:00'),
            delivery('z', 'Com Z', '2026-01-04T23:30:00Z')]))
        out = self.catalog.search(kind='delivery')
        self.assertEqual([i['title'] for i in out['items']], ['Em Brasília', 'Com Z', 'Em UTC'])
        self.assertEqual(out['items'][0]['date'], '2026-01-04T22:00:00-03:00', 'a data exibida continua a original')

    def test_old_item_found_without_project_by_unaccented_word(self):
        self.catalog.ingest('p1', make_detail('p1', 'Projeto Um', deliveries=[
            delivery('d1', 'Relatório final de design', '2025-03-03T00:00:00+00:00')]))
        out = self.catalog.search(q='relatorio')
        self.assertEqual([i['title'] for i in out['items']], ['Relatório final de design'])
        self.assertTrue(out['items'][0]['available'])

    def test_same_title_in_different_projects_are_two_distinct_items(self):
        for pid, at in (('p1', '2025-03-03T00:00:00+00:00'), ('p2', '2025-03-04T00:00:00+00:00')):
            self.catalog.ingest(pid, make_detail(pid, f'Projeto {pid}', deliveries=[
                delivery('d1', 'Relatório final de design', at)]))
        out = self.catalog.search(q='relatorio final')
        self.assertEqual(len(out['items']), 2)
        self.assertEqual({i['project_id'] for i in out['items']}, {'p1', 'p2'})
        self.assertEqual(len({i['key'] for i in out['items']}), 2)
        self.assertTrue(out['revision_changed'] is False)


class KindsAndAvailabilityTests(CatalogTestBase):
    def full(self):
        return make_detail('p3', 'Projeto Três', deliveries=[
            delivery('ent1', 'Relatório oficial', '2026-02-01T00:00:00+00:00', file_id='f1', type='html'),
            delivery('ent2', 'Manual em PDF', '2026-02-02T00:00:00+00:00', file_id='f2', type='pdf'),
            delivery('ent3', 'Registro sem arquivo', '2026-02-03T00:00:00+00:00'),
        ], assets=[
            asset('x1', 'foto.png', '2026-02-04T00:00:00+00:00'),
            asset('x2', 'guia.pdf', '2026-02-05T00:00:00+00:00', role='asset'),
            asset('x3', 'fonte.html', '2026-02-06T00:00:00+00:00', role='reference'),
        ])

    def test_each_source_lands_with_the_right_kind(self):
        self.catalog.ingest('p3', self.full())
        by_kind = {k: {i['target']['itemId'] for i in self.catalog.search(kind=k)['items']}
                   for k in ('project', 'report', 'delivery', 'file', 'reference')}
        self.assertEqual(by_kind['project'], {'p3'})
        self.assertEqual(by_kind['report'], {'f1'})
        self.assertEqual(by_kind['delivery'], {'f2', 'ent3'})
        self.assertEqual(by_kind['file'], {'x1', 'x2'})
        self.assertEqual(by_kind['reference'], {'x3'})

    def test_comment_title_names_the_commented_file_without_path(self):
        self.store.add('comments', 'p3', dict(text='Respostas recebidas pelo relatório', onde='00_PARA-VOCE\\x\\261014_BUBBLE.html',
                                              at='2026-02-07T00:00:00+00:00', status='RECEBIDO'))
        self.store.add('comments', 'p3', dict(text='Ver o 261017_MAPA.html', onde='261017_MAPA.html', at='2026-02-08T00:00:00+00:00'))
        self.catalog.ingest('p3', self.full())
        titles = [i['title'] for i in self.catalog.search(kind='comment')['items']]
        self.assertEqual(titles, ['Ver o 261017_MAPA.html', 'Respostas recebidas pelo relatório · 261014_BUBBLE.html'])
        self.assertEqual(self.catalog.search(q='bubble respostas', kind='comment')['counts']['total'], 1)

    def test_disappeared_report_stays_searchable_as_unavailable_and_returns_when_back(self):
        self.catalog.ingest('p3', self.full())
        without = make_detail('p3', 'Projeto Três', deliveries=[
            delivery('ent2', 'Manual em PDF', '2026-02-02T00:00:00+00:00', file_id='f2', type='pdf'),
            delivery('ent3', 'Registro sem arquivo', '2026-02-03T00:00:00+00:00'),
        ], assets=self.full()['assets'])
        self.catalog.ingest('p3', without)
        gone = self.catalog.search(q='oficial')
        self.assertEqual(len(gone['items']), 1)
        self.assertFalse(gone['items'][0]['available'])
        self.assertEqual(gone['counts']['indisponiveis'], 1)
        self.assertEqual(self.catalog.search(kind='report')['counts']['total'], 1, 'não sai da busca')
        self.catalog.ingest('p3', self.full())
        back = self.catalog.search(q='oficial')
        self.assertEqual(len(back['items']), 1)
        self.assertTrue(back['items'][0]['available'])
        self.assertEqual(back['counts']['indisponiveis'], 0)


class CoverageAndValidationTests(CatalogTestBase):
    def test_never_ingested_project_reports_itself_unread(self):
        self.catalog.ingest('p1', make_detail('p1', 'Projeto Um'))
        out = self.catalog.search(projects=[{'id': 'p1', 'name': 'Projeto Um'}, {'id': 'nunca', 'name': 'Nunca Visto'}])
        coverage = {row['project']: row for row in out['coverage']}
        self.assertEqual(coverage['p1']['status'], 'completo')
        self.assertTrue(coverage['p1']['observed_at'])
        self.assertEqual(coverage['p1']['items'], 1)
        self.assertEqual(coverage['nunca'], {'project': 'nunca', 'name': 'Nunca Visto',
                                             'observed_at': None, 'items': 0, 'status': 'nao_lido'})

    def test_invalid_scope_kind_and_cursor_raise_value_error(self):
        with self.assertRaises(ValueError): self.catalog.search(scope='qualquer')
        with self.assertRaises(ValueError): self.catalog.search(kind='zap')
        with self.assertRaises(ValueError) as broken: self.catalog.search(cursor='não-é-cursor')
        self.assertEqual(str(broken.exception), 'Cursor inválido; recomece a busca.')

    def test_limit_above_100_is_clamped_to_100(self):
        rows = [delivery(f'd{i:03}', f'Entrega {i:03}', f'2026-03-01T00:00:{i % 60:02d}+00:00') for i in range(150)]
        self.catalog.ingest('p9', make_detail('p9', 'Projeto Lote', deliveries=rows))
        out = self.catalog.search(limit=500)
        self.assertEqual(len(out['items']), 100)
        self.assertIsNotNone(out['next_cursor'])
        self.assertEqual(out['counts']['total'], 151)
        d, k, r = decode_cursor(out['next_cursor'])
        self.assertIsInstance(d, str); self.assertIsInstance(k, str); self.assertIsInstance(r, int)


class SearchApiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'MB_ISOLATED': '1', 'MB_PONTE': '0'})
        self.env.start()
        self.fixture = security_fixture.CentralSecurityTests()
        self.fixture.setUp()
        self.auth = self.fixture.local_login()
        self.pid = self.fixture.pid
        # Uma leitura de detalhe alimenta o índice; o watcher não roda nestes testes.
        self.fixture.sources.detail(self.pid, force=True)

    def tearDown(self):
        self.fixture.tearDown()
        self.env.stop()

    def get(self, path, headers):
        status, _, content = asyncio.run(asgi_request(self.fixture.local, path, 'GET', None, headers))
        return status, json.loads(content) if content else None

    def test_search_requires_session(self):
        status, _, _ = asyncio.run(asgi_request(self.fixture.local, '/api/search', 'GET', None, None))
        self.assertEqual(status, 401)

    def test_authenticated_search_returns_contract_shape(self):
        status, body = self.get('/api/search?q=final', self.auth)
        self.assertEqual(status, 200)
        for field in ('items', 'next_cursor', 'query_revision', 'revision_changed', 'observed_at', 'counts', 'coverage'):
            self.assertIn(field, body)
        self.assertTrue(body['items'])
        item = body['items'][0]
        self.assertEqual(set(item), {'key', 'kind', 'project_id', 'project_name', 'title', 'date', 'date_label',
                                     'historical', 'available', 'target'})
        self.assertEqual(item['kind'], 'report')
        self.assertEqual(item['project_id'], self.pid)
        self.assertEqual(item['target'], {'kind': 'report', 'projectId': self.pid, 'itemId': item['target']['itemId']})
        self.assertEqual(body['counts']['total'], 1)
        self.assertFalse(body['revision_changed'])
        self.assertIsNone(body['next_cursor'])
        self.assertEqual(body['coverage'][0]['project'], self.pid)
        self.assertEqual(body['coverage'][0]['status'], 'completo')
        self.assertTrue(body['observed_at'])
        limits = body.get('limits') or body.get('limites')
        self.assertTrue(any('240' in note for note in limits))

    def test_invalid_scope_is_a_client_error(self):
        status, body = self.get('/api/search?scope=qualquer', self.auth)
        self.assertEqual(status, 400)
        self.assertIn('Escopo', body['detail'])


class IngestFailureTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'MB_ISOLATED': '1', 'MB_PONTE': '0'})
        self.env.start()
        self.fixture = security_fixture.CentralSecurityTests()
        self.fixture.setUp()
        self.addCleanup(self.env.stop)

    def tearDown(self):
        self.fixture.tearDown()

    def test_malformed_ingest_keeps_detail_working(self):
        with patch.object(self.fixture.sources.catalog, 'ingest', side_effect=RuntimeError('detalhe malformado')), \
                self.assertLogs('megabrain.catalog', level='ERROR'):
            data = self.fixture.sources.detail(self.fixture.pid, force=True)
        self.assertIn('project', data)
        self.assertTrue(data['deliveries'], 'o detalhe volta normal; só o índice fica para trás')


if __name__ == '__main__':
    unittest.main()

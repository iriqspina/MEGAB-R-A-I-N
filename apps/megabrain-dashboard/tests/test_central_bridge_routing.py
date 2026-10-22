"""Contrato 261020. Relógio controlado e lançador falso: zero chamadas a modelos."""
from pathlib import Path
from unittest import mock
import copy
import json
import unittest

import test_central_bridge as fixtures
import central_bridge as bridge
from central_bridge_routing import catalogo, presets, validar_rota, normalizar_pipeline

GPT = dict(vendor='gpt', modelo='gpt-6.1-sol', effort='xhigh')
CLAUDE = dict(vendor='claude', modelo='claude-opus-5-5', effort='high')


class RoutingContractTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PonteStoreTests()
        self.f.setUp()
        self.t = 1000.0
        self.clock = mock.patch.object(bridge.time, 'time', lambda: self.t)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        self.f.tearDown()

    def comment(self, text='nota', route=None, note='nota-1'):
        c = self.f.comentario(text)
        patch = dict(cursor_source=dict(note_id=note, storage_key='relatorio-a', where='alvo'))
        if route is not None:
            patch['rota'] = route
        return self.f.store.patch('comments', c['id'], patch)

    def receive(self, c):
        return self.f.p.receber(self.f.pid, self.f.projeto, c)

    def orders(self):
        return self.f.store.get('bridge-orders', {})['data'].get('ordens', [])

    def test_default_and_versioned_legacy_sixty_become_180(self):
        self.assertEqual(self.f.p.config(self.f.pid)['data']['espera_segundos'], 180)

    def test_pending_legacy_sixty_extends_to_180_once(self):
        c = self.comment()
        key = 'bridge-pending:' + self.f.pid
        self.f.store.put(key, 0, dict(estado='aguardando', comentarios=[c['id']], raiz=str(self.f.projeto),
                                    vendor='gpt', modo='segundo_plano', lancar_apos=1060))
        self.f.p.tick()
        self.assertEqual(self.f.store.get(key, {})['data']['lancar_apos'], 1180)
        self.f.p.tick()
        self.assertEqual(self.f.store.get(key, {})['data']['lancar_apos'], 1180)
        self.t = 1179
        self.f.p.tick()
        self.assertEqual(self.f.lancados, [])
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(len(self.f.lancados), 1)
        self.f.store.put('bridge:' + self.f.pid, 0, dict(vendor='gpt', espera_segundos=60))
        cfg = self.f.p.config(self.f.pid)
        self.assertEqual(cfg['data']['espera_segundos'], 180)
        saved = self.f.p.salvar_config(self.f.pid, cfg['revision'], cfg['data'])
        self.assertEqual(saved['data']['versao_espera'], 2)
        self.assertEqual(self.f.p.config(self.f.pid)['data']['espera_segundos'], 180)

    def test_179_does_not_launch_180_does(self):
        self.receive(self.comment())
        self.t = 1179
        self.f.p.tick()
        self.assertEqual(self.f.lancados, [])
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(len(self.f.lancados), 1)

    def test_new_route_restarts_project_silence_and_routes_stay_separate(self):
        self.receive(self.comment('a', GPT, 'a'))
        self.t = 1100
        self.receive(self.comment('b', CLAUDE, 'b'))
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(self.f.lancados, [])
        self.t = 1279
        self.f.p.tick()
        self.assertEqual(self.f.lancados, [])
        self.t = 1280
        self.f.p.tick()
        self.assertEqual(len(self.f.lancados), 2)
        profiles = [bridge._ler(Path(o['dir']) / 'pedido.json')['pipeline']['planejador'] for o in self.orders()]
        self.assertCountEqual(profiles, [GPT, CLAUDE])

    def test_route_edit_before_dispatch_supersedes_original_pending_destination(self):
        first = self.comment('versão 1', GPT, 'same-note')
        self.receive(first)
        self.t = 1100
        last = self.comment('versão 2', CLAUDE, 'same-note')
        self.receive(last)
        self.t = 1280
        self.f.p.tick()
        self.assertEqual(len(self.orders()), 1)
        self.assertEqual(self.orders()[0]['vendor'], 'claude')
        self.assertEqual(self.f.comment(first['id'])['ponte']['estado'], 'substituido')
        pedido = bridge._ler(Path(self.orders()[0]['dir']) / 'pedido.json')
        self.assertEqual(pedido['comentarios'][0]['texto'], 'versão 2')

    def test_status_and_identical_replay_do_not_restart_silence(self):
        c = self.comment()
        self.receive(c)
        self.t = 1100
        c = self.f.store.patch('comments', c['id'], dict(status='outro status', correction='resumo da IA'))
        self.assertEqual(self.receive(c)['estado'], 'duplicata')
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(len(self.f.lancados), 1)

    def test_human_edit_restarts_silence_and_latest_text_is_frozen(self):
        c = self.comment('antes')
        self.receive(c)
        self.t = 1100
        c = self.f.store.patch('comments', c['id'], dict(text='depois'))
        self.receive(c)
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(self.f.lancados, [])
        self.t = 1280
        self.f.p.tick()
        pedido = bridge._ler(Path(self.orders()[0]['dir']) / 'pedido.json')
        self.assertEqual(pedido['comentarios'][0]['texto'], 'depois')

    def test_claim_revalidates_comment_changed_without_receber(self):
        c = self.comment('antes')
        self.receive(c)
        self.f.store.patch('comments', c['id'], dict(text='última edição'))
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(self.f.lancados, [])
        self.t = 1360
        self.f.p.tick()
        self.assertEqual(bridge._ler(Path(self.orders()[0]['dir']) / 'pedido.json')['comentarios'][0]['texto'], 'última edição')

    def test_arrival_while_claim_is_launching_is_not_overwritten(self):
        a = self.comment('a', note='a')
        self.receive(a)
        received = []
        def launch(*args):
            if not received:
                b = self.comment('b', note='b')
                received.append(b)
                self.receive(b)
        self.f.p.lancar = launch
        self.t = 1180
        self.f.p.tick()
        pending = [self.f.store.get(k, {})['data'] for k in self.f.p._pendentes(self.f.pid)]
        self.assertTrue(any(p.get('estado') == 'aguardando' and received[0]['id'] in p.get('comentarios', []) for p in pending))
        self.t = 1360
        self.f.p.tick()
        lines = (Path(self.orders()[0]['dir']) / 'complementos.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(json.loads(lines[0])['texto'], 'b')

    def test_profile_frozen_for_all_roles_and_child_inherits_role(self):
        pipeline = normalizar_pipeline(dict(planejador=GPT, worker=CLAUDE, revisor=dict(vendor='glm')), 'gpt')
        d = bridge.criar_ordem(self.f.projeto, [dict(id='c')], 'gpt', central=self.f.central, pipeline=pipeline)['dir']
        no = bridge.despachar(d, 'n0', 'worker', None, 'Tela', 'corrigir', central=self.f.central, lancador=lambda *a: None)
        self.assertEqual(no['perfil'], CLAUDE)
        self.assertEqual(bridge._ler(Path(d) / 'pedido.json')['pipeline'], pipeline)
        override = bridge.despachar(d, 'n0', 'worker', 'gpt', 'Lógica', 'corrigir', modelo=GPT['modelo'], effort='high', central=self.f.central, lancador=lambda *a: None)
        self.assertEqual(override['perfil'], dict(GPT, effort='high'))
        with self.assertRaises(bridge.PonteErro):
            bridge.despachar(d, 'n0', 'worker', None, 'inválido', 'x', modelo='inventado', central=self.f.central, lancador=lambda *a: None)

    def completed(self):
        c = self.comment('antes', GPT)
        self.f.p.enviar_agora(self.f.pid, self.f.projeto, [c['id']])
        o = self.orders()[0]
        bridge._atualizar_no(Path(o['dir']) / 'nos/n0', status='concluido', sessao_id='thread-real-123', sessao_fonte='saida.log:json CLI')
        bridge.concluir(o['dir'], 'corrigido', 'anterior')
        self.f.p.reconciliar()
        return c, o

    def test_edit_of_finished_note_returns_to_same_node_and_real_session(self):
        c, o = self.completed()
        c = self.f.store.patch('comments', c['id'], dict(text='revisado', rota=None))
        cfg = self.f.p.config(self.f.pid)
        self.f.p.salvar_config(self.f.pid, cfg['revision'], dict(cfg['data'], vendor='glm'))
        self.receive(c)
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(len(self.orders()), 1)
        no = bridge._ler(Path(o['dir']) / 'nos/n0/no.json')
        self.assertEqual((no['vendor'], no['retomar_sessao']), ('gpt', 'thread-real-123'))
        self.assertEqual(len(self.f.lancados), 2)
        self.assertFalse((Path(o['dir']) / 'resultado.json').exists())
        self.assertEqual(len(list((Path(o['dir']) / 'historico-resultados').glob('*.json'))), 1)

    def test_note_cannot_change_assigned_route(self):
        c, _ = self.completed()
        with self.assertRaisesRegex(bridge.PonteErro, 'já tem responsável'):
            self.f.p.validar_destino(self.f.pid, dict(c, rota=CLAUDE, text='edição'))

    def test_glm_window_is_refused_before_saving_queuing_or_creating_order(self):
        cfg = self.f.p.config(self.f.pid)
        with self.assertRaisesRegex(bridge.PonteErro, 'exige segundo plano'):
            self.f.p.salvar_config(self.f.pid, cfg['revision'], dict(cfg['data'], vendor='glm', modo='janela'))
        self.assertEqual(self.f.p.config(self.f.pid)['revision'], cfg['revision'])
        self.f.p.salvar_config(self.f.pid, cfg['revision'], dict(cfg['data'], vendor='gpt', modo='janela'))
        glm = dict(vendor='glm', modelo='GLM-5.3', effort='max')
        c = self.comment('GLM', glm)
        with self.assertRaisesRegex(bridge.PonteErro, 'exige segundo plano'):
            self.receive(c)
        self.assertEqual(self.f.p._pendentes(self.f.pid), [])
        with self.assertRaisesRegex(bridge.PonteErro, 'exige segundo plano'):
            self.f.p.enviar_agora(self.f.pid, self.f.projeto, [c['id']])
        self.assertEqual(self.orders(), [])
        self.assertFalse((self.f.projeto / bridge.PASTA).exists())

    def test_missing_native_identity_is_explicit_and_does_not_open_other_agent(self):
        c, o = self.completed()
        bridge._atualizar_no(Path(o['dir']) / 'nos/n0', sessao_id=None)
        c = self.f.store.patch('comments', c['id'], dict(text='edição', rota=None))
        self.receive(c)
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(len(self.f.lancados), 1)
        self.assertEqual(self.f.comment(c['id'])['ponte']['estado'], 'continuidade_indisponivel')

    def test_legacy_note_id_recovers_only_from_original_comment_in_database(self):
        c = self.f.comentario('')
        c = self.f.store.patch('comments', c['id'], dict(feedback=dict(notas=[dict(id='nota-legada', texto='primeiro')]), rota=GPT))
        self.f.p.enviar_agora(self.f.pid, self.f.projeto, [c['id']])
        o = self.orders()[0]
        pedido = bridge._ler(Path(o['dir']) / 'pedido.json')
        pedido['comentarios'][0]['notas'][0].pop('id')
        pedido.pop('pipeline')
        bridge._gravar(Path(o['dir']) / 'pedido.json', pedido)
        novo = self.f.comentario('')
        novo = self.f.store.patch('comments', novo['id'], dict(feedback=dict(notas=[dict(id='nota-legada', texto='editado')])) )
        self.assertEqual(self.f.p._dono(self.f.pid, novo)['id'], o['id'])

    def test_different_note_routes_split_without_finalizing_original_early(self):
        c = self.f.comentario('')
        c = self.f.store.patch('comments', c['id'], dict(feedback=dict(notas=[
            dict(id='n1', texto='código', rota=GPT), dict(id='n2', texto='design', rota=CLAUDE)])))
        result = self.receive(c)
        self.assertEqual(len(result['partes']), 2)
        self.t = 1180
        self.f.p.tick()
        self.assertEqual(len(self.orders()), 2)
        bridge.concluir(self.orders()[0]['dir'], 'corrigido', 'uma parte')
        self.f.p.reconciliar()
        self.assertEqual(self.f.comment(c['id'])['ponte']['estado'], 'em_partes')
        owners = [self.f.p._dono(self.f.pid, p) for p in bridge._fragmentos(c)]
        self.assertEqual(len({o['id'] for o in owners}), 2)


class NativeProfileTests(unittest.TestCase):
    def test_explicit_route_requires_complete_valid_profile_and_presets_have_sources(self):
        for invalid in ({}, {'vendor':'gpt'}, dict(GPT, effort='inventado'), dict(GPT, modelo='inventado')):
            with self.assertRaises(ValueError):
                validar_rota(invalid)
        for p in presets():
            self.assertTrue(p['experimental'])
            self.assertTrue(p['fonte'].endswith('261011_prioridades-vendors-por-tarefa.md'))
            self.assertEqual(set(p['pipeline']), set(bridge.PAPEIS))
        self.assertFalse(next(x for x in catalogo() if x['vendor'] == 'glm')['modelos'][0]['visual'])

    def test_native_model_effort_and_resume_flags_are_passed_without_account_change(self):
        with mock.patch.object(bridge, 'executavel', return_value=['cli']):
            argv = bridge.argv('gpt', 'P', Path('project'), perfil=GPT, sessao='thread-real-123')
            self.assertEqual(argv[1:3], ['exec', 'resume'])
            self.assertIn('thread-real-123', argv)
            self.assertIn('model_reasoning_effort="xhigh"', argv)
            self.assertIn('gpt-6.1-sol', argv)
            argv = bridge.argv('claude', 'P', Path('project'), perfil=CLAUDE, sessao='session-real-123')
            self.assertIn('--resume', argv)
            self.assertIn('--effort', argv)
            self.assertNotIn('--no-session-persistence', argv)

    def test_only_cli_emitted_session_identity_is_captured(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'saida.log').write_text('plain text thread_id invented\n'+json.dumps(dict(type='thread.started', thread_id='thread-real-123'))+'\n', encoding='utf-8')
            self.assertEqual(bridge._sessao_do_log(d, 'gpt')['sessao_id'], 'thread-real-123')
            self.assertEqual(bridge._sessao_do_log(d, 'claude'), {})
            (d / 'saida.log').write_text(json.dumps(dict(type='result', session_id='session-real-123'))+'\n', encoding='utf-8')
            self.assertEqual(bridge._sessao_do_log(d, 'claude')['sessao_id'], 'session-real-123')

    def test_glm_profile_is_child_only_secret_free_and_keeps_session_database(self):
        import hashlib
        import tempfile
        import model_clients
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            order = root / '.mb-ponte/order'
            no = order / 'nos/n0'
            no.mkdir(parents=True)
            bridge._gravar(order / 'pedido.json', dict(projeto=str(root)))
            bundle = root / 'runtime.cjs'
            bundle.write_text('// synthetic runtime; never executed', encoding='utf-8')
            config = root / 'global.json'
            reasoning = dict(enabled=True, levels=['low', 'high', 'max'], defaultLevel='max',
                             providerOptionsByLevel={x: {'anthropic': {'effort': x}} for x in ['low', 'high', 'max']})
            bridge._gravar(config, dict(model={'main':'zai/GLM-5.3-Flash'}, provider={'zai': dict(kind='anthropic',
                options=dict(baseURL='https://api.z.ai/api/anthropic', apiKey='synthetic-secret-never-written'),
                models={'GLM-5.3':dict(reasoning=reasoning)})}))
            before = config.read_bytes()
            profile = dict(vendor='glm', modelo='GLM-5.3', effort='high')
            with mock.patch.multiple(model_clients, ZCODE=bundle, ZCODE_SHA256=hashlib.sha256(bundle.read_bytes()).hexdigest(), ZCODE_CONFIG=config):
                env = dict(ZCODE_MODEL='zai/GLM-5.3-Flash', ZCODE_SESSION_DB='other.sqlite', ZCODE_BASE_URL='https://wrong.example')
                settings = bridge._glm_isolado(no, profile, env)
                actual = bridge._ler(settings)
                self.assertEqual(actual['model']['main'], 'zai/GLM-5.3')
                self.assertEqual(actual['provider']['zai']['models']['GLM-5.3']['reasoning']['defaultLevel'], 'high')
                self.assertEqual(actual['storage']['sessionDbPath'], str(no / 'zcode-session.sqlite'))
                self.assertNotIn('synthetic-secret', settings.read_text(encoding='utf-8'))
                self.assertEqual(env['ZAI_API_KEY'], 'synthetic-secret-never-written')
                self.assertNotIn('ZCODE_MODEL', env)
                self.assertNotIn('ZCODE_SESSION_DB', env)
                self.assertNotIn('ZCODE_BASE_URL', env)
                first = settings.read_bytes()
                self.assertEqual(bridge._glm_isolado(no, profile, {}), settings)
                self.assertEqual(settings.read_bytes(), first)
                self.assertEqual(config.read_bytes(), before)
                with mock.patch.object(bridge, 'executavel', return_value=['legacy-zcode']), mock.patch.object(bridge.shutil, 'which', return_value='node'):
                    command = bridge.argv('glm', 'P', root, perfil=profile, settings=settings, sessao='sess_real_123')
                self.assertEqual(command[:2], ['node', str(bundle)])
                self.assertIn('--settings', command)
                self.assertIn('sess_real_123', command)
                self.assertNotIn('--model', command)
                with self.assertRaisesRegex(bridge.PonteErro, 'original difere'):
                    bridge._glm_isolado(no, dict(profile, effort='max'), {})
                (root / '.git').mkdir()
                (root / 'zcode.json').write_text('{}', encoding='utf-8')
                with self.assertRaisesRegex(bridge.PonteErro, 'sobrepor'):
                    bridge._glm_isolado(no, profile, {})


if __name__ == '__main__':
    unittest.main()

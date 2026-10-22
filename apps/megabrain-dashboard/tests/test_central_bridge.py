"""261018 ponte: comentário enviado ao projeto → planejador → orquestradores → workers.

Tudo sintético, em pasta temporária: nenhuma CLI de IA é chamada. As execuções
reais usam um comando Python no lugar da CLI (supervisor, parada, tempo esgotado)
e o lançador falso registra o que seria aberto.
"""
from pathlib import Path
from unittest import mock
import json
import os
import sys
import tempfile
import time
import unittest

APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'runtime-packages'), str(APP / 'tests')]
import central_bridge as ponte
from central_store import Store

FAKE_EXE = lambda vid: [sys.executable]
GPT = dict(vendor='gpt', modelo='gpt-6.1-sol', effort='xhigh')
CLAUDE = dict(vendor='claude', modelo='claude-opus-5-5', effort='high')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ponte-')
        self.base = Path(self.tmp.name)
        self.central = self.base / 'central'
        (self.central / 'dados').mkdir(parents=True)
        self.registro({'claude': {'pacing': {'status': 'ok'}}, 'codex': {'pacing': {'status': 'desacelerar'}},
                       'zai': {'pacing': {}}, 'codex_gpt2_cancelado': {'cancelado_em': '2026-10-14'}})
        self.projeto = self.base / 'Projeto'
        self.projeto.mkdir()
        login = self.base / 'auth.json'
        login.write_text('{}', encoding='utf-8')
        self.patches = [mock.patch.object(ponte, 'executavel', FAKE_EXE),
                        mock.patch.dict(ponte.VENDORS['gpt'], login=login)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def registro(self, dados):
        (self.central / 'dados' / 'orcamento_ia.json').write_text(json.dumps(dados), encoding='utf-8')

    def ordem(self, vendor='gpt', comentarios=None):
        comentarios = comentarios or [dict(id='c1', at='2026-10-18T19:32:27+00:00', texto='arrume os comentários, usando codex 1',
                                           relatorio='00_PARA-VOCE\\mapa.html',
                                           notas=[dict(texto='corrigido por outro vendor', onde='Mapa do harness', ancora={'base': '#mh-mapa'})])]
        return ponte.criar_ordem(self.projeto, comentarios, vendor, central=self.central)


class VendorTests(Base):
    def test_active_vendors_follow_cli_and_megabrain_registry(self):
        lista = {v['id']: v for v in ponte.vendors(self.central)}
        self.assertEqual(ponte.ativos(self.central), ['claude', 'gpt', 'glm'])
        self.assertFalse(lista['gemini']['ativo'])
        self.assertIn('registradas', lista['gemini']['motivo'])
        self.assertEqual(lista['gpt']['aviso'], 'Cota pede para desacelerar.')

    def test_new_install_without_registry_trusts_installed_clis(self):
        (self.central / 'dados' / 'orcamento_ia.json').unlink()
        self.assertEqual(ponte.ativos(self.central), ['claude', 'gpt', 'glm', 'gemini'])

    def test_cancelled_or_missing_cli_or_missing_login_is_inactive(self):
        self.registro({'claude': {'cancelado_em': '2026-10-01'}, 'codex': {}, 'zai': {}})
        with mock.patch.object(ponte, 'executavel', lambda vid: None if vid == 'glm' else [sys.executable]):
            lista = {v['id']: v for v in ponte.vendors(self.central)}
        self.assertFalse(lista['claude']['ativo'])
        self.assertFalse(lista['glm']['ativo'])
        self.assertIn('não está instalado', lista['glm']['motivo'])
        with mock.patch.dict(ponte.VENDORS['gpt'], login=self.base / 'sem-login.json'):
            self.assertNotIn('gpt', ponte.ativos(self.central))

    def test_cli_commands_use_official_headless_modes_and_codex_one_home(self):
        raiz = self.projeto
        self.assertEqual(ponte.argv('claude', 'P', raiz)[1:], ['-p', 'P'])
        gpt = ponte.argv('gpt', 'P', raiz, raiz / 'u.txt')
        self.assertEqual(gpt[1:4], ['exec', '--skip-git-repo-check', '-C'])
        self.assertIn('-o', gpt)
        self.assertEqual(ponte.argv('glm', 'P', raiz)[1:], ['--prompt', 'P', '--cwd', str(raiz)])
        env = ponte.ambiente('gpt')
        self.assertEqual(env['CODEX_HOME'], str(Path.home() / '.codex'))
        with mock.patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'x', 'OPENAI_API_KEY': 'y', 'CLAUDECODE': '1', 'CLAUDE_CODE_GIT_BASH_PATH': 'b'}):
            env = ponte.ambiente('claude')
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('CLAUDECODE', env)
        self.assertEqual(env['CLAUDE_CODE_GIT_BASH_PATH'], 'b')


class OrderTests(Base):
    def test_planner_brief_carries_literal_comment_note_anchor_and_cli(self):
        info = self.ordem()
        tarefa = (Path(info['dir']) / 'nos' / 'n0' / 'TAREFA.md').read_text(encoding='utf-8')
        self.assertIn('arrume os comentários, usando codex 1', tarefa)
        self.assertIn('corrigido por outro vendor', tarefa)
        self.assertIn('#mh-mapa', tarefa)
        self.assertIn('despachar --ordem', tarefa)
        self.assertIn('concluir --ordem', tarefa)
        self.assertIn('git commit', tarefa)
        no = json.loads((Path(info['dir']) / 'nos' / 'n0' / 'no.json').read_text(encoding='utf-8'))
        self.assertEqual((no['papel'], no['vendor'], no['profundidade'], no['status']), ('planejador', 'gpt', 0, 'criado'))

    def test_inactive_vendor_or_bad_mode_is_refused(self):
        with self.assertRaisesRegex(ponte.PonteErro, 'não está ativo'):
            self.ordem(vendor='gemini')
        with self.assertRaises(ponte.PonteErro):
            ponte.criar_ordem(self.projeto, [dict(id='c')], 'gpt', modo='invisivel', central=self.central)

    def test_tree_of_orchestrators_and_workers_respects_depth_roles_and_limit(self):
        d = self.ordem()['dir']
        lancados = []
        lancar = lambda no_dir, modo: lancados.append(Path(no_dir).name)
        o1 = ponte.despachar(d, 'n0', 'orquestrador', 'claude', 'Interface', 'faça a interface', central=self.central, lancador=lancar)
        o2 = ponte.despachar(d, o1['id'], 'orquestrador', 'glm', 'Sub', 'parte', central=self.central, lancador=lancar)
        w = ponte.despachar(d, o2['id'], 'worker', 'gpt', 'Código', 'código', central=self.central, lancador=lancar)
        self.assertEqual([o1['profundidade'], o2['profundidade'], w['profundidade']], [1, 2, 3])
        self.assertEqual(lancados, [o1['id'], o2['id'], w['id']])
        with self.assertRaisesRegex(ponte.PonteErro, 'Só o planejador'):
            ponte.despachar(d, w['id'], 'worker', 'gpt', 'x', 'x', central=self.central, lancador=lancar)
        sub3 = ponte.despachar(d, o2['id'], 'orquestrador', 'gpt', 'neto', 'x', central=self.central, lancador=lancar)
        with self.assertRaisesRegex(ponte.PonteErro, 'Profundidade'):
            ponte.despachar(d, sub3['id'], 'worker', 'gpt', 'x', 'x', central=self.central, lancador=lancar)
        with self.assertRaisesRegex(ponte.PonteErro, 'não está ativa'):
            ponte.despachar(d, 'n0', 'worker', 'gemini', 'x', 'x', central=self.central, lancador=lancar)
        tarefa_worker = (Path(d) / 'nos' / w['id'] / 'TAREFA.md').read_text(encoding='utf-8')
        self.assertNotIn('Como abrir outras IAs', tarefa_worker)
        self.assertIn('Como abrir outras IAs', (Path(d) / 'nos' / o1['id'] / 'TAREFA.md').read_text(encoding='utf-8'))
        while True:
            try:
                ponte.despachar(d, 'n0', 'worker', 'gpt', 'mais', 'x', central=self.central, lancador=lancar)
            except ponte.PonteErro as erro:
                self.assertIn('Limite', str(erro))
                break
        self.assertEqual(len(list((Path(d) / 'nos').iterdir())), ponte.NOS_MAX)

    def test_state_moves_from_queue_to_running_to_corrected(self):
        d = self.ordem()['dir']
        self.assertEqual(ponte.estado_ordem(d)['situacao'], 'na_fila')
        ponte._atualizar_no(Path(d) / 'nos' / 'n0', status='rodando', modo='segundo_plano', supervisor_pid=os.getpid())
        est = ponte.estado_ordem(d)
        self.assertEqual((est['situacao'], est['ativos']), ('em_andamento', 1))
        ponte.concluir(d, 'corrigido', 'Mapa revisado pelo GPT.', ['pytest 12/12'], ['conferir no celular'])
        est = ponte.estado_ordem(d)
        self.assertEqual(est['situacao'], 'corrigido')
        self.assertEqual(est['resultado']['pendencias'], ['conferir no celular'])

    def test_background_launch_goes_outside_the_session_and_records_pid_without_racing(self):
        d = self.ordem()['dir']
        no_dir = Path(d) / 'nos' / 'n0'
        with mock.patch.object(ponte, '_fora_da_sessao', return_value=999998) as wmi, mock.patch.object(ponte.subprocess, 'Popen') as popen:
            self.assertEqual(ponte.lancar_segundo_plano(no_dir), 999998)
        wmi.assert_called_once()
        self.assertIn('_supervisionar', wmi.call_args[0][0])
        popen.assert_not_called()
        self.assertEqual(json.loads((no_dir / 'supervisor.json').read_text(encoding='utf-8'))['via'], 'wmi')
        no = json.loads((no_dir / 'no.json').read_text(encoding='utf-8'))
        self.assertEqual((no['status'], no['modo']), ('iniciando', 'segundo_plano'))
        est = ponte.estado_ordem(d)  # pid 999998 não existe: não fica "abrindo" para sempre
        self.assertEqual(est['nos'][0]['status_observado'], 'sem processo vivo')

    def test_dead_supervisor_is_reported_instead_of_running_forever(self):
        d = self.ordem()['dir']
        ponte._atualizar_no(Path(d) / 'nos' / 'n0', status='rodando', modo='segundo_plano', supervisor_pid=999999)
        est = ponte.estado_ordem(d)
        self.assertEqual(est['nos'][0]['status_observado'], 'sem processo vivo')
        self.assertEqual(est['situacao'], 'falhou')


class SupervisorTests(Base):
    """O supervisor roda um processo de verdade (Python no lugar da CLI)."""

    def no(self, codigo, timeout=600):
        d = self.ordem()['dir']
        no = ponte.despachar(d, 'n0', 'worker', 'gpt', 'teste', 'x', central=self.central, timeout=timeout, lancador=lambda *a: None)
        return Path(d) / 'nos' / no['id'], codigo

    def run_node(self, codigo, timeout=600):
        no_dir, codigo = self.no(codigo, timeout)
        with mock.patch.object(ponte, 'argv', lambda vid, prompt, raiz, ultima=None, interativo=False, **kwargs: [sys.executable, '-c', codigo]):
            return no_dir, ponte.supervisionar(no_dir, timeout)

    def test_success_failure_and_output_are_recorded(self):
        no_dir, no = self.run_node("print('feito pela IA')")
        self.assertEqual((no['status'], no['exit_code']), ('concluido', 0))
        self.assertIn('feito pela IA', (no_dir / 'saida.log').read_text(encoding='utf-8'))
        no_dir, no = self.run_node('import sys; sys.exit(3)')
        self.assertEqual((no['status'], no['exit_code']), ('falhou', 3))

    def test_stop_flag_interrupts_the_process_tree(self):
        no_dir, codigo = self.no('import time; time.sleep(120)')
        (no_dir / 'PARAR').write_text('agora', encoding='utf-8')
        inicio = time.monotonic()
        with mock.patch.object(ponte, 'argv', lambda *a, **k: [sys.executable, '-c', codigo]):
            no = ponte.supervisionar(no_dir, 600)
        self.assertEqual(no['status'], 'interrompido')
        self.assertLess(time.monotonic() - inicio, 60)


class FakeSources:
    def __init__(self):
        self.cache = {}


class PonteStoreTests(Base):
    def setUp(self):
        super().setUp()
        self.store = Store(self.base / 'c.sqlite3')
        self.lancados = []
        self.p = ponte.Ponte(self.store, FakeSources(), lancar=lambda no_dir, modo: self.lancados.append((Path(no_dir).name, modo)), central=self.central)
        self.pid = 'p1'

    def comentario(self, texto='mude a cor'):
        return self.store.add('comments', self.pid, dict(text=texto, target='file:x', status='Recebido, aguardando correção', source='00_PARA-VOCE\\a.html'))

    def comment(self, cid):
        return next(c for c in self.store.listing('comments', self.pid, include_resolved=True) if c['id'] == cid)

    def vencer_lote(self):
        for chave in self.p._pendentes(self.pid):
            doc = self.store.get(chave, {})
            self.store.put(chave, doc['revision'], dict(doc['data'], lancar_apos=0))
        clock = self.store.get('bridge-clock:' + self.pid, {})
        self.store.put('bridge-clock:' + self.pid, clock['revision'], dict(clock['data'], mudou_em=0))

    def test_comments_wait_in_one_batch_then_one_planner_receives_all(self):
        a, b = self.comentario('primeira nota'), self.comentario('leia o comentário e faça')
        self.assertEqual(self.p.receber(self.pid, self.projeto, a)['estado'], 'fila')
        self.p.receber(self.pid, self.projeto, b)
        self.assertIn('Na fila da ponte', self.comment(a['id'])['status'])
        self.p.tick()
        self.assertEqual(self.lancados, [])  # dentro da espera
        self.vencer_lote()
        self.p.tick()
        self.assertEqual(self.lancados, [('n0', 'segundo_plano')])
        ordem = self.store.get('bridge-orders', {})['data']['ordens'][0]
        self.assertEqual(ordem['comentarios'], [a['id'], b['id']])
        self.assertEqual(self.comment(b['id'])['status'], 'Com o planejador Claude')
        pedido = json.loads((Path(ordem['dir']) / 'pedido.json').read_text(encoding='utf-8'))
        self.assertEqual([c['texto'] for c in pedido['comentarios']], ['primeira nota', 'leia o comentário e faça'])
        self.p.tick()
        self.assertEqual(len(self.lancados), 1)  # lote não relança

    def test_new_comment_during_running_order_waits_for_silence_before_complement(self):
        a = self.comentario()
        self.p.receber(self.pid, self.projeto, a)
        self.vencer_lote()
        self.p.tick()
        b = self.comentario('mais um ajuste')
        r = self.p.receber(self.pid, self.projeto, b)
        self.assertEqual(r['estado'], 'fila')
        ordem = self.store.get('bridge-orders', {})['data']['ordens'][0]
        self.assertFalse((Path(ordem['dir']) / 'complementos.jsonl').exists())
        self.vencer_lote()
        self.p.tick()
        linhas = (Path(ordem['dir']) / 'complementos.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(json.loads(linhas[0])['texto'], 'mais um ajuste')
        self.assertIn('responsável original', self.comment(b['id'])['status'])

    def test_conclusion_flows_back_to_the_comment_and_keeps_original_fields(self):
        a = self.comentario()
        self.p.enviar_agora(self.pid, self.projeto, [a['id']], vendor='glm')
        ordem = self.store.get('bridge-orders', {})['data']['ordens'][0]
        ponte.concluir(ordem['dir'], 'parcial', 'Cor trocada.', [], ['falta testar no Pixel'])
        self.p.reconciliar()
        c = self.comment(a['id'])
        self.assertEqual(c['status'], 'Correção parcial (GLM) · veja as pendências')
        self.assertIn('falta testar no Pixel', c['correction'])
        self.assertEqual((c['text'], c['source']), ('mude a cor', '00_PARA-VOCE\\a.html'))
        self.assertEqual(self.store.get('bridge-orders', {})['data']['ordens'][0]['estado'], 'parcial')

    def test_disabled_bridge_and_verified_comments_are_left_alone(self):
        cfg = self.p.config(self.pid)
        self.p.salvar_config(self.pid, cfg['revision'], dict(cfg['data'], auto=False))
        a = self.comentario()
        self.assertEqual(self.p.receber(self.pid, self.projeto, a), {'estado': 'desligada'})
        self.assertEqual(self.comment(a['id'])['status'], 'Recebido, aguardando correção')
        v = self.store.add('comments', self.pid, dict(text='ok', target='file:x', status='CORRIGIDO_VERIFICADO'))
        self.p._patch(v['id'], self.pid, status='outra')
        self.assertEqual(self.comment(v['id'])['status'], 'CORRIGIDO_VERIFICADO')

    def test_config_only_accepts_active_vendors_and_preserves_unavailable_selection(self):
        cfg = self.p.config(self.pid)
        self.assertEqual(cfg['data']['vendor'], 'claude')
        with self.assertRaises(ponte.PonteErro):
            self.p.salvar_config(self.pid, cfg['revision'], dict(cfg['data'], vendor='gemini'))
        self.p.salvar_config(self.pid, cfg['revision'], dict(cfg['data'], vendor='glm', espera_segundos=0))
        self.registro({'claude': {}, 'codex': {}})
        cfg = self.p.config(self.pid)['data']
        self.assertEqual((cfg['vendor'], cfg['vendor_indisponivel']), ('glm', 'glm'))
        self.assertFalse(cfg['disponivel'])

    def test_probe_instance_never_opens_sessions(self):
        prova = ponte.Ponte(self.store, FakeSources(), lancar=False, central=self.central)
        a = self.comentario()
        self.assertEqual(prova.receber(self.pid, self.projeto, a)['estado'], 'prova')
        self.assertEqual(self.comment(a['id'])['status'], 'Recebido, aguardando correção')
        self.assertEqual(self.store.get('bridge-pending:' + self.pid, {})['revision'], 0)
        prova.tick()
        self.assertFalse((self.projeto / ponte.PASTA).exists())
        with self.assertRaises(ponte.PonteErro):
            prova.enviar_agora(self.pid, self.projeto, [a['id']])

    def controle(self, modo):
        import central_project_control as controle
        controle.save(self.store, self.pid, controle.read(self.store, self.pid)['revision'], modo)

    def test_paused_project_keeps_the_note_and_says_it_goes_on_resume(self):
        # 261022 Bubble: projeto pausado no logout de 21/10 e a nota dizia "Claude começa em instantes" por horas.
        self.controle('pausado')
        a = self.comentario('ajuste o rodapé')
        r = self.p.receber(self.pid, self.projeto, a)
        self.assertEqual((r['estado'], r['controle']), ('fila', 'pausado'))
        c = self.comment(a['id'])
        self.assertNotIn('instantes', c['status'])
        self.assertIn('Projeto pausado', c['status'])
        self.assertIn('Retomar projeto', c['status'])
        self.assertEqual((c['ponte']['estado'], c['ponte']['controle']), ('fila_pausada', 'pausado'))
        self.vencer_lote()
        self.p.tick()
        self.assertEqual(self.lancados, [])
        self.controle('ativo')
        self.p.tick()
        self.assertEqual(self.lancados, [('n0', 'segundo_plano')])
        self.assertEqual(self.comment(a['id'])['status'], 'Com o planejador Claude')

    def test_queue_label_follows_pause_and_resume_while_waiting(self):
        a = self.comentario()
        self.p.receber(self.pid, self.projeto, a)
        self.assertIn('começa em instantes', self.comment(a['id'])['status'])
        self.controle('aguardando')
        self.p.tick()
        self.assertIn('Projeto aguardando retorno', self.comment(a['id'])['status'])
        self.controle('ativo')
        self.p.tick()  # ainda dentro da espera: volta a prometer o início, sem lançar
        self.assertEqual(self.lancados, [])
        c = self.comment(a['id'])
        self.assertIn('começa em instantes', c['status'])
        self.assertEqual(c['ponte']['estado'], 'fila')

    def test_discarded_batch_is_marked_handled_outside_and_never_launches(self):
        # Lote já atendido à mão por outra sessão: retomar o projeto não pode abrir uma ordem duplicada.
        self.controle('pausado')
        a, b = self.comentario('backup no GitHub'), self.comentario('decisão 1.1')
        self.p.receber(self.pid, self.projeto, a)
        self.p.receber(self.pid, self.projeto, b)
        chave = 'bridge-pending:' + self.pid
        antes = self.store.get(chave, {})
        r = self.p.descartar_pendente(self.pid, motivo='feito por outra sessão')
        self.assertEqual(r['descartados'], [dict(chave=chave, comentarios=[a['id'], b['id']])])
        lote = self.store.get(chave, {})['data']
        self.assertEqual((lote['estado'], lote['comentarios'], lote['itens']), ('descartado', [], []))
        self.assertEqual(lote['descartado']['comentarios'], [a['id'], b['id']])
        self.assertEqual(lote['descartado']['motivo'], 'feito por outra sessão')
        # A versão anterior do lote, com os itens, continua no histórico do banco.
        with self.store.db() as c:
            hist = c.execute('SELECT data FROM history WHERE key=? AND revision=?', (chave, antes['revision'])).fetchone()
        self.assertEqual([i['id'] for i in json.loads(hist[0])['itens']], [a['id'], b['id']])
        for cid in (a['id'], b['id']):
            c = self.comment(cid)
            self.assertIn('Atendido fora da ponte', c['status'])
            self.assertEqual((c['ponte']['estado'], c['ponte']['lote']), ('atendido_fora', chave))
            self.assertIn(c['text'], ('backup no GitHub', 'decisão 1.1'))
        eventos = self.store.events()['events']
        self.assertTrue(any(e.get('kind') == 'bridge' and 'descartado' in e['title'] and e.get('comentarios') == [a['id'], b['id']] for e in eventos))
        self.controle('ativo')
        self.vencer_lote()
        self.p.tick()
        self.assertEqual(self.lancados, [])
        self.assertFalse((self.projeto / ponte.PASTA).exists())
        self.assertEqual(self.p.pendentes_view(self.pid), [])
        # Nada a descartar não inventa descarte; nota nova depois abre lote novo normalmente.
        self.assertEqual(self.p.descartar_pendente(self.pid)['descartados'], [])
        novo = self.comentario('nota nova')
        self.assertEqual(self.p.receber(self.pid, self.projeto, novo)['estado'], 'fila')
        self.assertEqual(self.store.get(chave, {})['data']['comentarios'], [novo['id']])

    def test_discard_refuses_a_batch_being_launched_or_from_another_project(self):
        a = self.comentario()
        self.p.receber(self.pid, self.projeto, a)
        chave = 'bridge-pending:' + self.pid
        doc = self.store.get(chave, {})
        self.store.put(chave, doc['revision'], dict(doc['data'], estado='lancando'))
        with self.assertRaises(ponte.PonteErro):
            self.p.descartar_pendente(self.pid, chave)
        self.assertEqual(self.p.descartar_pendente(self.pid)['ignorados'], [chave])
        self.assertEqual(self.store.get(chave, {})['data']['estado'], 'lancando')
        with self.assertRaises(ponte.PonteErro):
            self.p.descartar_pendente(self.pid, 'bridge-pending:outro')
        with self.assertRaises(ponte.PonteErro):
            self.p.descartar_pendente(self.pid, 123)

    def test_late_queue_label_cannot_overwrite_a_finished_discard(self):
        # R2 (Codex 2): tick leu o lote, o descarte terminou, e só então tick gravaria "fila_pausada".
        self.controle('pausado')
        a = self.comentario()
        self.p.receber(self.pid, self.projeto, a)
        chave = 'bridge-pending:' + self.pid
        visto = json.loads(json.dumps(self.store.get(chave, {})['data']))
        revisao = self.p.pendentes_view(self.pid)[0]['revisao']
        self.p.descartar_pendente(self.pid, chave, revisao=revisao)
        self.p._rotular_fila(self.pid, chave, visto, 'ativo')
        self.assertFalse(self.p._patch_na_fila(chave, a['id'], self.pid, None, status='Na fila'))
        c = self.comment(a['id'])
        self.assertEqual(c['ponte']['estado'], 'atendido_fora')
        self.assertIn('Atendido fora da ponte', c['status'])
        self.assertEqual(visto['comentarios'], [a['id']])

    def test_previous_order_does_not_overwrite_the_discarded_edit(self):
        # R3 (Codex 2): comentário com ordem anterior é editado; a edição é atendida à mão e descartada da fila.
        a = self.comentario('primeira versão')
        self.p.enviar_agora(self.pid, self.projeto, [a['id']])
        self.store.patch('comments', a['id'], dict(text='segunda versão'))
        self.assertEqual(self.p.receber(self.pid, self.projeto, self.comment(a['id']))['estado'], 'fila')
        self.p.descartar_pendente(self.pid, motivo='feito à mão')
        self.p.reconciliar()
        c = self.comment(a['id'])
        self.assertEqual(c['ponte']['estado'], 'atendido_fora')
        self.assertIn('Atendido fora da ponte', c['status'])
        ordem = self.store.get('bridge-orders', {})['data']['ordens'][0]
        ponte.concluir(ordem['dir'], 'corrigido', 'Primeira versão corrigida.')
        self.p.reconciliar()
        c = self.comment(a['id'])
        self.assertEqual((c['ponte']['estado'], c['correction']), ('atendido_fora', 'Primeira versão corrigida.'))
        # Nova edição volta a seguir a ponte normalmente.
        self.store.patch('comments', a['id'], dict(text='terceira versão'))
        self.p.receber(self.pid, self.projeto, self.comment(a['id']))
        self.assertEqual(self.comment(a['id'])['ponte']['estado'], 'fila')

    def antes_de_gravar(self, acao):
        """Executa `acao` uma vez, entre a leitura do chamador e a transação que grava o comentário."""
        original = self.p._patch_atomico
        feito = []
        def envolto(cid, pid, decidir):
            if not feito:
                feito.append(1)
                acao()
            return original(cid, pid, decidir)
        return mock.patch.object(self.p, '_patch_atomico', envolto)

    def test_discard_does_not_mark_an_edit_that_arrived_mid_discard(self):
        # R4 (Codex 2, volta 2): a nota é editada e volta à fila depois do descarte gravar o lote e antes do rótulo.
        self.controle('pausado')
        a = self.comentario('versão vista')
        self.p.receber(self.pid, self.projeto, a)
        def editar():
            self.store.patch('comments', a['id'], dict(text='versão editada'))
            self.p.receber(self.pid, self.projeto, self.comment(a['id']))
        with self.antes_de_gravar(editar):
            self.p.descartar_pendente(self.pid, motivo='feito à mão')
        c = self.comment(a['id'])
        self.assertEqual(c['ponte']['estado'], 'fila_pausada')
        self.assertNotIn('Atendido', c['status'])
        self.assertEqual([p['comentarios'] for p in self.p.pendentes_view(self.pid)], [[a['id']]])
        # Conteúdo diferente do descartado, mesmo fora da fila, também não vira "atendido".
        b = self.comentario('outra')
        self.p.receber(self.pid, self.projeto, b)
        doc = self.store.get('bridge-pending:' + self.pid, {})
        with self.antes_de_gravar(lambda: self.store.patch('comments', b['id'], dict(text='outra editada'))):
            self.p.descartar_pendente(self.pid, 'bridge-pending:' + self.pid, revisao=doc['revision'])
        self.assertNotEqual(self.comment(b['id'])['ponte']['estado'], 'atendido_fora')

    def test_reconcile_does_not_write_over_a_discard_that_happened_meanwhile(self):
        # R3 (Codex 2, volta 2): reconciliar leu a fila; a edição entrou e foi descartada antes da gravação.
        a = self.comentario('primeira versão')
        self.p.enviar_agora(self.pid, self.projeto, [a['id']])
        def editar_e_descartar():
            self.store.patch('comments', a['id'], dict(text='segunda versão'))
            self.p.receber(self.pid, self.projeto, self.comment(a['id']))
            self.p.descartar_pendente(self.pid, motivo='feito à mão')
        with self.antes_de_gravar(editar_e_descartar):
            self.p.reconciliar()
        c = self.comment(a['id'])
        self.assertEqual(c['ponte']['estado'], 'atendido_fora')
        self.assertIn('Atendido fora da ponte', c['status'])
        # E a edição que voltou à fila depois da leitura também não é reescrita com o estado da ordem.
        b = self.comentario('b primeira')
        self.p.enviar_agora(self.pid, self.projeto, [b['id']])
        def editar():
            self.store.patch('comments', b['id'], dict(text='b segunda'))
            self.p.receber(self.pid, self.projeto, self.comment(b['id']))
        with self.antes_de_gravar(editar):
            self.p.reconciliar()
        self.assertEqual(self.comment(b['id'])['ponte']['estado'], 'fila')

    def em_fatias(self, p=''):
        c = self.comentario('')
        return self.store.patch('comments', c['id'], dict(feedback=dict(notas=[
            dict(id=p + 'n1', texto='código', rota=GPT), dict(id=p + 'n2', texto='design', rota=CLAUDE)])))

    def lote_da_nota(self, nota):
        return next(p for p in self.p.pendentes_view(self.pid)
                    if any(n.get('id') == nota for i in self.store.get(p['chave'], {})['data']['itens'] for n in i['feedback']['notas']))

    def test_one_unchanged_slice_does_not_close_a_comment_with_another_slice_edited(self):
        # R6 (Codex 2, volta 3): fatia 1 descartada, depois editada sem voltar à fila; descartar a fatia 2 não fecha tudo.
        for editar in (False, True):
            p = 'e' if editar else 'i'
            c = self.em_fatias(p)
            self.assertEqual(len(self.p.receber(self.pid, self.projeto, c)['partes']), 2)
            primeiro = self.lote_da_nota(p + 'n1')
            self.p.descartar_pendente(self.pid, primeiro['chave'], revisao=primeiro['revisao'])
            atual = self.comment(c['id'])
            self.assertNotEqual(atual['ponte']['estado'], 'atendido_fora')  # a fatia 2 segue na fila
            self.assertEqual(len(atual['assinaturas_atendidas_fora']), 1)
            if editar:
                notas = [dict(n, texto='código novo') if n['id'] == p + 'n1' else n for n in atual['feedback']['notas']]
                self.store.patch('comments', c['id'], dict(feedback=dict(atual['feedback'], notas=notas)))
            segundo = self.lote_da_nota(p + 'n2')
            self.p.descartar_pendente(self.pid, segundo['chave'], revisao=segundo['revisao'])
            estado = self.comment(c['id'])['ponte']['estado']
            self.assertEqual(estado == 'atendido_fora', not editar, f'editar={editar}')

    def test_old_orders_do_not_close_a_slice_content_none_of_them_received(self):
        # R7 (Codex 2, volta 4): duas ordens concluídas; uma fatia muda sem nova ordem nem descarte.
        for editar in (False, True):
            p = 'e' if editar else 'i'
            c = self.em_fatias(p)
            self.p.receber(self.pid, self.projeto, c)
            self.vencer_lote()
            self.p.tick()
            for o in self.store.get('bridge-orders', {})['data']['ordens']:
                if c['id'] in o['comentarios']:
                    ponte.concluir(o['dir'], 'corrigido', 'parte feita')
            if editar:
                atual = self.comment(c['id'])
                notas = [dict(n, texto='código novo') if n['id'] == p + 'n1' else n for n in atual['feedback']['notas']]
                self.store.patch('comments', c['id'], dict(feedback=dict(atual['feedback'], notas=notas)))
            self.p.reconciliar()
            self.assertEqual(self.comment(c['id'])['ponte']['estado'], 'em_partes' if editar else 'corrigido', f'editar={editar}')

    def test_parts_label_keeps_the_paused_queue_label_of_a_slice_requeued_meanwhile(self):
        # R5 (Codex 2, volta 3): reconciliar de partes gravaria "corrigido" sobre a fatia que voltou à fila pausada.
        c = self.em_fatias()
        self.p.receber(self.pid, self.projeto, c)
        self.vencer_lote()
        self.p.tick()
        ordens = self.store.get('bridge-orders', {})['data']['ordens']
        self.assertEqual(len(ordens), 2)
        for o in ordens:
            ponte.concluir(o['dir'], 'corrigido', 'parte feita')
        def editar_em_pausa():
            self.controle('pausado')
            atual = self.comment(c['id'])
            notas = [dict(n, texto='código de novo') if n['id'] == 'n1' else n for n in atual['feedback']['notas']]
            self.store.patch('comments', c['id'], dict(feedback=dict(atual['feedback'], notas=notas)))
            self.p.receber(self.pid, self.projeto, self.comment(c['id']))
        with self.antes_de_gravar(editar_em_pausa):
            self.p.reconciliar()
        atual = self.comment(c['id'])
        self.assertEqual(atual['ponte']['estado'], 'fila_pausada')
        self.assertIn('Projeto pausado', atual['status'])


class ApiTests(unittest.TestCase):
    """Rota real do botão "Enviar ao projeto" com a ponte e o lançador falso."""

    def setUp(self):
        import test_central_security as harness
        import central_server as server
        self.fixture = harness.CentralSecurityTests()
        self.fixture.setUp()
        self.central = self.fixture.base / 'central'
        (self.central / 'dados').mkdir(parents=True)
        (self.central / 'dados' / 'orcamento_ia.json').write_text(json.dumps({'claude': {}, 'codex': {}, 'zai': {}}), encoding='utf-8')
        login = self.fixture.base / 'auth.json'
        login.write_text('{}', encoding='utf-8')
        self.patches = [mock.patch.object(ponte, 'executavel', FAKE_EXE), mock.patch.dict(ponte.VENDORS['gpt'], login=login)]
        for p in self.patches:
            p.start()
        self.lancados = []
        f = self.fixture
        self.app = server.build_app(store=f.store, sources=f.sources, bridge=ponte.Ponte(f.store, f.sources, lancar=lambda d, m: self.lancados.append(m), central=self.central))
        f.local = self.app
        self.auth = f.local_login()
        self.fid = f.sources.index_file(f.html, f.project)['id']

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.fixture.tearDown()

    def call(self, path, method='GET', body=None):
        status, _, raw = self.fixture.request(self.app, path, method=method, body=body, headers=self.auth)
        return status, json.loads(raw)

    def test_send_to_project_feeds_the_bridge_and_settings_round_trip(self):
        import hashlib
        self.fixture.request(self.app, f'/api/reports/{self.fid}/view?ticket=t_ponte_teste_123', headers=self.auth)
        digest = hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()
        status, body = self.call(f'/api/reports/{self.fid}/feedback', 'POST', {'hash': digest, 'note': 'corrija o título', 'feedback': None})
        self.assertEqual(status, 200)
        self.assertEqual((body['ponte']['estado'], body['ponte']['vendor']), ('fila', 'claude'))
        pid = self.fixture.pid
        status, view = self.call(f'/api/projects/{pid}/bridge')
        self.assertEqual(status, 200)
        self.assertEqual([v['id'] for v in view['vendors'] if v['ativo']], ['claude', 'gpt', 'glm'])
        status, saved = self.call(f'/api/projects/{pid}/bridge', 'PUT', {'revision': view['revision'], 'data': dict(view['data'], vendor='gpt', modo='janela')})
        self.assertEqual((status, saved['data']['vendor'], saved['data']['modo']), (200, 'gpt', 'janela'))
        status, erro = self.call(f'/api/projects/{pid}/bridge', 'PUT', {'revision': saved['revision'], 'data': dict(saved['data'], vendor='gemini')})
        self.assertEqual(status, 400)
        comentario = body['comment']['id']
        status, enviado = self.call(f'/api/projects/{pid}/bridge/send', 'POST', {'comment_ids': [comentario], 'coordenacao': 'outra sessão mexe no mapa'})
        self.assertEqual((status, enviado['vendor'], enviado['estado']), (200, 'gpt', 'na_fila'))
        self.assertEqual(self.lancados, ['janela'])
        tarefa = (Path(enviado['dir']) / 'nos' / 'n0' / 'TAREFA.md').read_text(encoding='utf-8')
        self.assertIn('## Coordenação', tarefa)
        self.assertIn('outra sessão mexe no mapa', tarefa)
        self.assertIn('corrija o título', tarefa)
        status, view = self.call(f'/api/projects/{pid}/bridge')
        self.assertEqual(view['ordens'][0]['situacao'], 'na_fila')
        oid = view['ordens'][0]['ordem_id']
        status, parado = self.call(f'/api/projects/{pid}/bridge/orders/{oid}/stop', 'POST', {})
        self.assertEqual((status, parado['parados']), (200, ['n0']))

    def test_note_on_the_app_desk_enters_the_bridge_like_a_report_reply(self):
        # 261020: notas do cursor na mesa (target app:home) nunca chegavam à ponte e dependiam de resgate manual.
        pid = self.fixture.pid
        nota = {'text': 'deixe só relatórios aqui', 'target': 'app:home', 'anchor': {'x': 0.1, 'y': 0.6},
                'cursor_source': {'note_id': 'nteste1', 'storage_key': 'mb-cursor-notas:home', 'where': 'Relatórios e arquivos', 'created_at': ''}}
        status, body = self.call(f'/api/projects/{pid}/comments', 'POST', nota)
        self.assertEqual(status, 200)
        self.assertEqual((body['ponte']['estado'], body['ponte']['vendor']), ('fila', 'claude'))
        status, view = self.call(f'/api/projects/{pid}')
        salvo = next(c for c in view['comments'] if c['id'] == body['comment']['id'])
        self.assertEqual((salvo['target'], salvo['ponte']['estado']), ('app:home', 'fila'))
        # Reenvio idempotente (mesma tentativa) não entra duas vezes no lote.
        lote = self.fixture.store.get('bridge-pending:' + pid, {})['data']
        self.assertEqual(lote['comentarios'], [body['comment']['id']])
        # Nota de quadro (module:*) continua fora do despacho automático até decisão do <USUARIO>.
        status, quadro = self.call(f'/api/projects/{pid}/comments', 'POST', {'text': 'nota no quadro', 'target': 'module:now'})
        self.assertEqual((status, quadro['ponte']), (200, None))
        self.assertEqual(self.fixture.store.get('bridge-pending:' + pid, {})['data']['comentarios'], [body['comment']['id']])

    def test_note_on_the_correction_bridge_board_enters_the_bridge_other_boards_stay(self):
        # 261022: a nota de 21/10 18h12 escrita na seção Ponte de correção (quadro Agora) ficou parada horas.
        # A seção leva data-cf-zona="ponte-correcao" e a nota do cursor envia a zona; o rótulo visível não decide.
        pid = self.fixture.pid
        def nota(texto, target, where, note_id, zona=None):
            fonte = {'note_id': note_id, 'storage_key': 'mb-cursor-notas:home', 'where': where, 'created_at': ''}
            if zona is not None:
                fonte['zona'] = zona
            return {'text': texto, 'target': target, 'anchor': {'x': 0.7, 'y': 0.02}, 'cursor_source': fonte}
        status, ponte = self.call(f'/api/projects/{pid}/comments', 'POST',
                                  nota('finalize e lance a versão um', 'module:now', 'Ponte de correção', 'nponte1', 'ponte-correcao'))
        self.assertEqual(status, 200)
        self.assertEqual((ponte['ponte']['estado'], ponte['ponte']['vendor']), ('fila', 'claude'))
        status, view = self.call(f'/api/projects/{pid}')
        salvo = next(c for c in view['comments'] if c['id'] == ponte['comment']['id'])
        self.assertEqual((salvo['target'], salvo['ponte']['estado'], salvo['cursor_source']['zona']), ('module:now', 'fila', 'ponte-correcao'))
        # Botão e campo dentro da seção têm rótulo próprio; a Ponte na página inicial vem como module:home-module:now.
        dentro = []
        for texto, target, where, nid in (('pare esta', 'module:now', 'Parar esta ordem', 'nbotao'),
                                          ('planejador', 'module:now', 'Planejador', 'ncampo'),
                                          ('na página inicial', 'module:home-module:now', 'Ponte de correção', 'nhome')):
            status, entrou = self.call(f'/api/projects/{pid}/comments', 'POST', nota(texto, target, where, nid, 'ponte-correcao'))
            self.assertEqual((status, entrou['ponte']['estado']), (200, 'fila'), texto)
            dentro.append(entrou['comment']['id'])
        # Fora da seção: mesmo rótulo sem a marca, resto do quadro Agora, outra zona e nota sem cursor só ficam guardados.
        for texto, target, where, nid, zona in (('título igual', 'module:now', 'Ponte de correção', 'nrotulo', None),
                                                ('resumo do projeto', 'module:now', 'Resumo ainda não registrado.', 'nagora', None),
                                                ('outra zona', 'module:results', 'Resultados', 'nzona', 'resultados')):
            status, fora = self.call(f'/api/projects/{pid}/comments', 'POST', nota(texto, target, where, nid, zona))
            self.assertEqual((status, fora['ponte']), (200, None), texto)
        status, sem_cursor = self.call(f'/api/projects/{pid}/comments', 'POST', {'text': 'sem cursor', 'target': 'module:now'})
        self.assertEqual((status, sem_cursor['ponte']), (200, None))
        lote = self.fixture.store.get('bridge-pending:' + pid, {})['data']
        self.assertEqual(lote['comentarios'], [ponte['comment']['id'], *dentro])

    def test_resend_of_the_same_attempt_with_or_without_zone_returns_the_same_note(self):
        # Revisão Codex 2 (R5): cliente intermediário enviou com zona e perdeu a resposta; o atual reenvia sem zona.
        pid = self.fixture.pid
        cabecalho = dict(self.auth, **{'idempotency-key': 'tentativa_zona_0001'})
        def enviar(fonte):
            corpo = {'text': 'nota reenviada', 'target': 'module:now', 'anchor': {'x': 0.5, 'y': 0.1}, 'cursor_source': fonte}
            status, _, raw = self.fixture.request(self.app, f'/api/projects/{pid}/comments', method='POST', body=corpo, headers=cabecalho)
            return status, json.loads(raw)
        base = {'note_id': 'nreenvio', 'storage_key': 'mb-cursor-notas:home', 'where': 'Ponte de correção', 'created_at': ''}
        status, primeiro = enviar(dict(base, zona='ponte-correcao'))
        self.assertEqual((status, primeiro['ponte']['estado']), (200, 'fila'))
        for fonte in (base, dict(base, zona='ponte-correcao')):
            status, de_novo = enviar(fonte)
            self.assertEqual((status, de_novo['comment']['id'], de_novo['ponte']), (200, primeiro['comment']['id'], None))
        # Mudar o texto com a mesma tentativa continua sendo conflito.
        status, _, _ = self.fixture.request(self.app, f'/api/projects/{pid}/comments', method='POST',
                                            body={'text': 'outro texto', 'target': 'module:now', 'cursor_source': base}, headers=cabecalho)
        self.assertEqual(status, 409)

    def test_receipt_written_by_the_previous_server_is_recognized_with_or_without_zone(self):
        # Revisão Codex 2 (volta 4): o servidor anterior assinava o corpo inteiro (com a zona enviada pelo front
        # recompilado) e não guardava a zona. Depois do reinício, o reenvio não pode cair em 409 sem fim.
        import hashlib
        pid = self.fixture.pid
        chave = 'recibo_antigo_000001'
        base = {'note_id': 'nantigo', 'storage_key': 'mb-cursor-notas:home', 'where': 'Ponte de correção', 'created_at': ''}
        corpo_antigo = {'text': 'nota do servidor anterior', 'target': 'module:now', 'anchor': {'x': 0.5, 'y': 0.1},
                        'cursor_source': dict(base, zona='ponte-correcao')}
        assinatura_antiga = hashlib.sha256(json.dumps(corpo_antigo, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        salvo, criado = self.fixture.store.create_once('comments', pid, {'text': corpo_antigo['text'], 'target': 'module:now',
                                                       'cursor_source': base}, chave, assinatura_antiga)
        self.assertTrue(criado)
        cabecalho = dict(self.auth, **{'idempotency-key': chave})
        for fonte in (base, dict(base, zona='ponte-correcao')):
            status, _, raw = self.fixture.request(self.app, f'/api/projects/{pid}/comments', method='POST',
                                                  body=dict(corpo_antigo, cursor_source=fonte), headers=cabecalho)
            resposta = json.loads(raw)
            self.assertEqual((status, resposta['comment']['id'], resposta['ponte']), (200, salvo['id'], None), fonte)
        status, _, _ = self.fixture.request(self.app, f'/api/projects/{pid}/comments', method='POST',
                                            body=dict(corpo_antigo, text='texto trocado'), headers=cabecalho)
        self.assertEqual(status, 409)
        # R6 (revisão Codex 2, volta 5): zona diferente da única existente não herda a equivalência.
        status, _, _ = self.fixture.request(self.app, f'/api/projects/{pid}/comments', method='POST',
                                            body=dict(corpo_antigo, cursor_source=dict(base, zona='zona-inventada')), headers=cabecalho)
        self.assertEqual(status, 409)

    def test_bridge_panel_marks_its_zone_and_cursor_notes_send_it(self):
        # O servidor só decide pela zona se o front marca a seção, a nota grava a zona AO NASCER e o envio a repete.
        # Revisão Codex 2 (R4/R5): recalcular pela posição na hora de salvar dava a marca a nota nascida fora.
        web = APP / 'web'
        painel = (web / 'src' / 'BridgePanel.tsx').read_text(encoding='utf-8')
        cursor = (web / 'src' / 'CursorTools.tsx').read_text(encoding='utf-8')
        self.assertIn('aria-label="Ponte de correção" data-cf-zona="ponte-correcao"', painel)
        self.assertIn("const zona=typeof note.zona==='string'&&note.zona?note.zona:undefined;", cursor)
        self.assertNotIn("closest<HTMLElement>('[data-cf-zona]')", cursor, 'zona não pode ser recalculada no envio')
        self.assertIn('...(zona?{zona}:{})', cursor)
        captura = "var zona = ctx.alvo.closest && ctx.alvo.closest('[data-cf-zona]');\n      if (zona) nota.zona = zona.getAttribute('data-cf-zona');\n      notas.push(nota);"
        canonico = APP.parents[1] / 'motor' / 'modelos' / 'interacoes' / '261010_cursor-ferramentas' / 'cursor-ferramentas.js'
        for biblioteca in (web / 'public' / 'cursor-ferramentas-v1.2.js', web / 'dist' / 'cursor-ferramentas-v1.2.js', canonico):
            texto = biblioteca.read_text(encoding='utf-8').replace('\r\n', '\n')
            self.assertIn(captura, texto, f'{biblioteca.name}: a nota precisa gravar a zona ao nascer')
            self.assertEqual(texto.count("closest('[data-cf-zona]')"), 1, biblioteca.name)
        compilado = '\n'.join(p.read_text(encoding='utf-8') for p in (web / 'dist' / 'assets').glob('index-*.js'))
        self.assertIn('ponte-correcao', compilado, 'web/dist sem a marca: rodar npm run build')
        self.assertNotIn('[data-cf-zona]', compilado, 'web/dist ainda recalcula a zona: rodar npm run build')

    def test_paused_queue_shows_in_the_panel_and_discard_route_needs_csrf(self):
        pid = self.fixture.pid
        status, ctl = self.call(f'/api/projects/{pid}/control')
        status, ctl = self.call(f'/api/projects/{pid}/control', 'PUT', {'revision': ctl['revision'], 'modo': 'pausado'})
        self.assertEqual((status, ctl['data']['modo']), (200, 'pausado'))
        nota = {'text': 'já feito à mão', 'target': 'app:home',
                'cursor_source': {'note_id': 'npausa1', 'storage_key': 'mb-cursor-notas:home', 'where': 'Relatórios', 'created_at': ''}}
        status, body = self.call(f'/api/projects/{pid}/comments', 'POST', nota)
        self.assertEqual((status, body['ponte']['estado'], body['ponte']['controle']), (200, 'fila', 'pausado'))
        status, view = self.call(f'/api/projects/{pid}/bridge')
        self.assertEqual(view['controle'], 'pausado')
        self.assertEqual([(p['chave'], p['comentarios'], p['estado']) for p in view['pendentes']],
                         [('bridge-pending:' + pid, [body['comment']['id']], 'aguardando')])
        self.assertIn('já feito à mão', view['pendentes'][0]['resumo'])
        rota = f'/api/projects/{pid}/bridge/pending/discard'
        visto = view['pendentes'][0]
        pedido = {'chave': visto['chave'], 'revisao': visto['revisao'], 'motivo': 'outra sessão fez'}
        sem_csrf = {k: v for k, v in self.auth.items() if k != 'x-mb-csrf'}
        status, _, _ = self.fixture.request(self.app, rota, method='POST', body=pedido, headers=sem_csrf)
        self.assertEqual(status, 403)
        self.assertEqual(self.fixture.store.get('bridge-pending:' + pid, {})['data']['estado'], 'aguardando')
        for errado in ({'chave': 'bridge-pending:outro', 'revisao': 1}, {'chave': visto['chave']}, {'chave': visto['chave'], 'revisao': '1'}):
            status, _ = self.call(rota, 'POST', errado)
            self.assertEqual(status, 400, errado)
        # R1 (Codex 2): nota nova chega depois de o painel mostrar a fila; a confirmação antiga não leva as duas.
        nova = dict(nota, text='nota nova depois', cursor_source=dict(nota['cursor_source'], note_id='npausa2'))
        status, segunda = self.call(f'/api/projects/{pid}/comments', 'POST', nova)
        status, erro = self.call(rota, 'POST', pedido)
        self.assertEqual(status, 400)
        self.assertIn('mudou', erro['detail'])
        lote = self.fixture.store.get('bridge-pending:' + pid, {})['data']
        self.assertEqual((lote['estado'], lote['comentarios']), ('aguardando', [body['comment']['id'], segunda['comment']['id']]))
        status, view = self.call(f'/api/projects/{pid}/bridge')
        status, feito = self.call(rota, 'POST', dict(pedido, revisao=view['pendentes'][0]['revisao']))
        self.assertEqual((status, feito['descartados'][0]['comentarios']), (200, [body['comment']['id'], segunda['comment']['id']]))
        status, view = self.call(f'/api/projects/{pid}/bridge')
        self.assertEqual(view['pendentes'], [])
        status, projeto = self.call(f'/api/projects/{pid}')
        salvo = next(c for c in projeto['comments'] if c['id'] == body['comment']['id'])
        self.assertEqual(salvo['ponte']['estado'], 'atendido_fora')
        self.assertEqual(self.lancados, [])

    def test_bridge_panel_offers_discard_and_explains_pause(self):
        web = APP / 'web'
        painel = (web / 'src' / 'BridgePanel.tsx').read_text(encoding='utf-8')
        self.assertIn('/bridge/pending/discard', painel)
        self.assertIn('Retomar projeto', painel)
        compilado = '\n'.join(p.read_text(encoding='utf-8') for p in (web / 'dist' / 'assets').glob('index-*.js'))
        self.assertIn('/bridge/pending/discard', compilado, 'web/dist sem o botão de descarte: rodar npm run build')


if __name__ == '__main__':
    unittest.main()

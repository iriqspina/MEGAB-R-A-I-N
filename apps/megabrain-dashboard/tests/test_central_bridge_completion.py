"""Conclusão posterior e supervisor perdido não apagam o trabalho real."""
from pathlib import Path
import copy,json,unittest
from unittest.mock import patch
import test_central_bridge as fixtures
import central_bridge as bridge

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.PonteStoreTests();self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def order(self):
        f=self.fixture;a=f.comentario('instrução literal preservada')
        f.p.enviar_agora(f.pid,f.projeto,[a['id']],vendor='gpt')
        order=f.store.get('bridge-orders',{})['data']['ordens'][0]
        bridge._atualizar_no(Path(order['dir'])/'nos/n0',status='rodando',pid=111,supervisor_pid=222,modo='segundo_plano')
        return a,order
    def test_live_worker_survives_missing_supervisor_and_both_dead_is_failure(self):
        a,order=self.order()
        for living in (111,222):
            with patch.object(bridge,'_vivo',lambda pid:pid==living):
                state=bridge.estado_ordem(order['dir'])
                self.assertEqual(state['situacao'],'em_andamento')
                self.assertFalse(state['nos'][0].get('status_observado'))
        with patch.object(bridge,'_vivo',lambda pid:False):
            self.assertEqual(bridge.estado_ordem(order['dir'])['situacao'],'falhou')
    def test_explicit_late_result_updates_failed_comment_without_launch_or_loss(self):
        f=self.fixture;a,order=self.order();before=copy.deepcopy(a)
        with patch.object(bridge,'_vivo',lambda pid:False):
            f.p.reconciliar()
            self.assertEqual(f.store.get('bridge-orders',{})['data']['ordens'][0]['estado'],'falhou')
            self.assertIn('não concluiu',f.comment(a['id'])['status'])
            bridge.concluir(order['dir'],'corrigido','Implementação verificada.',['prova.json'],[])
            f.p.reconciliar();f.p.reconciliar()
        final=f.comment(a['id'])
        self.assertEqual(final['ponte']['estado'],'corrigido')
        self.assertEqual(final['correction'],'Implementação verificada.')
        self.assertEqual((final['id'],final['at'],final['text'],final['source'],final['target']),
                         (before['id'],before['at'],before['text'],before['source'],before['target']))
        self.assertEqual(len(f.lancados),1)
        self.assertEqual(f.store.get('bridge-orders',{})['data']['ordens'][0]['estado'],'corrigido')
    def test_no_new_result_keeps_final_order_and_human_verified_comment(self):
        f=self.fixture;a,order=self.order()
        f.store.patch('comments',a['id'],dict(status='CORRIGIDO_VERIFICADO'))
        with patch.object(bridge,'_vivo',lambda pid:False):f.p.reconciliar()
        state=f.store.get('bridge-orders',{})
        f.p.reconciliar()
        self.assertEqual(f.store.get('bridge-orders',{}),state)
        self.assertEqual(f.comment(a['id'])['status'],'CORRIGIDO_VERIFICADO')
        self.assertEqual(len(f.lancados),1)

import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'bin'))
from mb_triagem import classificar, SENSIBILIDADES, instrucao
class TriagemTest(unittest.TestCase):
    def test_conversa_nao_cria_burocracia(self):
        for p in ('oi','valeu!','obrigado'):
            r=classificar(p); self.assertEqual(r['rota'],'conversa')
            self.assertEqual(r['gates'][6]['estado'],'dispensado')
    def test_entregas_curtas(self):
        for p in ('faz um PDF','corrija o código','organiza pastas','revise isso','crie um ícone','analise o Mega Brain'):
            self.assertEqual(classificar(p)['rota'],'entrega',p)
    def test_nao_autoriza_acao_por_palavra_ou_sim(self):
        for p in ('publica','não publique','o que é deploy?','apague a pasta','sim','qual a dose do remédio?'):
            r=classificar(p); self.assertFalse(r['autoriza_execucao'],p)
        self.assertEqual(classificar('sim',contexto={'pending_action':True})['rota'],'critica')
    def test_contexto_recupera_curto(self):
        self.assertTrue(classificar('sim')['precisa_contexto'])
        self.assertEqual(classificar('isso',contexto={'active_artifact':True})['rota'],'entrega')
    def test_piso_independente_sensibilidade(self):
        for p in ('crie um relatório','publique na produção','o que mudou hoje?'):
            results=[classificar(p,s) for s in SENSIBILIDADES]
            self.assertEqual(results[0]['obrigatorios'],results[2]['obrigatorios'])
            self.assertTrue(set(results[0]['opcionais']).issubset(results[2]['opcionais']))
    def test_gates_com_motivo(self):
        for p in ('','oi','planeje uma migração','o que é HTML?'):
            r=classificar(p); self.assertEqual([g['id'] for g in r['gates']],list(range(8)))
            self.assertTrue(all(g['motivo'] for g in r['gates']))
    def test_erro_visivel(self):
        with self.assertRaises(ValueError): classificar('oi','nada')
        with self.assertRaises(ValueError): classificar('oi',contexto={'explicit_kind':'nada'})
    def test_verbos_de_trabalho_sao_entrega(self):
        # 260916: 'atualize/adapte/julgue/escreva' caiam em 'resposta' e o gate de entrega não subia
        for p in ('atualize as noções sobre o megabrain e adapte o trabalho do astra','escreva a proposta','julgue e adapte se necessário','instale o hook','desenhe o layout do deck'):
            self.assertEqual(classificar(p)['rota'],'entrega',p)
        self.assertEqual(classificar('oi')['rota'],'conversa')
        self.assertEqual(classificar('qual a diferença entre RGB e CMYK?')['rota'],'resposta')
    def test_pergunta_conceitual(self):
        self.assertEqual(classificar('O que é HTML?')['rota'],'resposta')
    def test_no_false_substring(self):
        self.assertNotEqual(classificar('O que significa pagode?')['rota'],'critica')
    def test_sensibilidade_chega_na_instrucao_do_hook(self):
        enxuta=instrucao(classificar('crie um relatório','enxuta'))
        criteriosa=instrucao(classificar('crie um relatório','criteriosa'))
        self.assertNotIn('segunda lente',enxuta)
        self.assertIn('segunda lente',criteriosa)
if __name__=='__main__': unittest.main()

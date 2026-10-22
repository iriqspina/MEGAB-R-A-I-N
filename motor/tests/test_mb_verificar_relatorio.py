"""B-APP F0 · verificador mínimo do mestre POP: cada regra reprova um caso negativo próprio."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('mb_verificar_relatorio', RAIZ / 'bin' / 'mb-verificar-relatorio.py')
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)
FIXTURE = json.loads((v.POP / 'fixtures' / 'minima.json').read_text(encoding='utf-8'))


class ConteudoTests(unittest.TestCase):
    def estado(self, mudar):
        dados = copy.deepcopy(FIXTURE)
        mudar(dados)
        return v.verificar_conteudo(dados)

    def test_fixture_conforme(self):
        out = v.verificar_conteudo(copy.deepcopy(FIXTURE))
        self.assertEqual(out['estado'], v.CONFORME, out['motivos'])

    def test_topico_sem_figura(self):
        out = self.estado(lambda d: d['topics'][0].update(figures=[]))
        self.assertEqual(out['estado'], v.NAO_CONFORME)

    def test_prova_sem_data_nem_hash(self):
        so_hash = self.estado(lambda d: d['topics'][0]['figures'][0].pop('observedAt'))
        self.assertEqual(so_hash['estado'], v.CONFORME, so_hash['motivos'])  # regra é data OU hash
        out = self.estado(lambda d: [d['topics'][0]['figures'][0].pop(k) for k in ('observedAt', 'hash')])
        self.assertTrue(any('prova' in m for m in out['motivos']))

    def test_numero_sem_fonte_exige_estimativa(self):
        sem_fonte = self.estado(lambda d: d['topics'][0]['metrics'][0].pop('source'))
        self.assertEqual(sem_fonte['estado'], v.NAO_CONFORME)
        estimado = self.estado(lambda d: d['topics'][0]['metrics'][0].update(source=None, estimate=True) or
                               d['topics'][0]['metrics'][0].pop('source'))
        self.assertEqual(estimado['estado'], v.CONFORME, estimado['motivos'])

    def test_recomendada_fora_das_opcoes(self):
        out = self.estado(lambda d: d['decisions'][0].update(recommended='Outra'))
        self.assertTrue(any('recomendada' in m for m in out['motivos']))

    def test_decisao_com_topico_inexistente(self):
        out = self.estado(lambda d: d['decisions'][0].update(contextTopicId='nao-existe'))
        self.assertTrue(any('inexistente' in m for m in out['motivos']))

    def test_historico_fora_de_ordem(self):
        out = self.estado(lambda d: d['history'].reverse())
        self.assertTrue(any('recente primeiro' in m for m in out['motivos']))

    def test_campo_estranho_reprovado_pelo_schema(self):
        out = self.estado(lambda d: d.update(css='body{color:red}'))
        self.assertTrue(any(m.startswith('schema') for m in out['motivos']))

    def test_tema_fora_da_lista(self):
        out = self.estado(lambda d: d['options'].update(theme='neon'))
        self.assertEqual(out['estado'], v.NAO_CONFORME)

    def test_resposta_sem_fuso(self):
        out = self.estado(lambda d: d.update(responseAt='2026-10-21T19:00:00'))
        self.assertTrue(any('responseAt' in m for m in out['motivos']))

    def test_decisao_sem_opcoes_nem_explicacao(self):
        out = self.estado(lambda d: d['decisions'][0].update(options=[], recommended=None, explanation=False)
                          or d['decisions'][0].pop('recommended'))
        self.assertTrue(any('sem opções' in m for m in out['motivos']))

    def test_recomendada_sem_opcoes(self):
        out = self.estado(lambda d: d['decisions'][0].update(options=[]))
        self.assertTrue(any('recomendada' in m for m in out['motivos']))

    def test_ids_e_numeracao_repetidos(self):
        def dobrar(d):
            d['topics'][1].update(id='resultado', number='1')
            d['decisions'].append(copy.deepcopy(d['decisions'][0]))
        motivos = self.estado(dobrar)['motivos']
        for trecho in ('id repetido', 'numeração repetida', 'decisions: id repetido'):
            self.assertTrue(any(trecho in m for m in motivos), trecho)

    def test_datas_invalidas_em_figura_fonte_e_estimativa(self):
        def estragar(d):
            d['topics'][0]['figures'][0]['observedAt'] = '2026-13-40T00:00:00-03:00'
            d['sources'][0]['observedAt'] = 'ontem'
            d['topics'][0]['metrics'][0].update(estimate=True, observedAt='sem data')
        motivos = self.estado(estragar)['motivos']
        for trecho in ('figura com data inválida', 'sources/0', 'com data inválida'):
            self.assertTrue(any(trecho in m for m in motivos), trecho)


class HtmlTests(unittest.TestCase):
    def test_bloco_vigente_com_versao_conforme(self):
        html = '<html><head><meta name="mb-template" content="megabrain-pop@0.1.0-f0"></head><body></body></html>'
        html, _ = v.mb_pop_tema.aplicar_interacoes(html)
        out = v.verificar_html(html)
        self.assertEqual(out['estado'], v.CONFORME, out)
        self.assertEqual(out['versao'], 'megabrain-pop@0.1.0-f0')

    def test_sem_ferramentas_do_cursor(self):
        self.assertEqual(v.verificar_html('<html><body>oi</body></html>')['estado'], v.NAO_CONFORME)

    def test_componente_sem_marcas_fica_nao_verificado(self):
        html = '<meta name="mb-template" content="x"><script id="cf-script">window.CursorFerramentas={}</script>'
        self.assertEqual(v.verificar_html(html)['estado'], v.NAO_VERIFICADO)

    def test_bloco_antigo_reprovado(self):
        antigo = v.mb_pop_tema.MARCA_INTERACOES_INICIO + '<script id="cf-script">velho</script>' + v.mb_pop_tema.MARCA_INTERACOES_FIM
        out = v.verificar_html('<meta name="mb-template" content="x">' + antigo)
        self.assertTrue(any('diferente' in m for m in out['motivos']))

    def test_recurso_remoto_reprovado(self):
        for trecho in ('<script src="https://cdn.exemplo/x.js"></script>',
                       '<img srcset="https://cdn.exemplo/a.png 2x">',
                       '<link href="https://fonts.exemplo/a.css" rel="stylesheet">',
                       '<style>body{background:url(https://cdn.exemplo/f.png)}</style>',
                       '<style>@import "https://cdn.exemplo/b.css";</style>'):
            html, _ = v.mb_pop_tema.aplicar_interacoes('<meta name="mb-template" content="x">' + trecho)
            self.assertTrue(any('remoto' in m for m in v.verificar_html(html)['motivos']), trecho)

    def test_link_e_preconnect_nao_sao_recurso(self):
        html, _ = v.mb_pop_tema.aplicar_interacoes('<meta name="mb-template" content="x"><a href="https://exemplo.com">fonte</a>'
                                                   '<link rel="preconnect" href="https://exemplo.com">')
        self.assertEqual(v.verificar_html(html)['estado'], v.CONFORME)

    def test_sem_meta_de_versao_fica_nao_verificado(self):
        html, _ = v.mb_pop_tema.aplicar_interacoes('<html><body></body></html>')
        out = v.verificar_html(html)
        self.assertEqual(out['estado'], v.NAO_VERIFICADO)
        self.assertTrue(any('mb-template' in p for p in out['nao_verificado']))


class ManifestoTests(unittest.TestCase):
    def test_manifesto_confere_com_componentes(self):
        out = v.verificar_manifesto()
        self.assertEqual(out['estado'], v.CONFORME, out['motivos'])
        self.assertEqual(out['componentes'], len(v.COMPONENTES))

    def test_hash_divergente_e_regravacao_com_historico(self):
        import tempfile
        with tempfile.TemporaryDirectory() as pasta:
            alvo = Path(pasta) / 'manifest.json'
            alvo.write_text(json.dumps(dict(componentes=[dict(path=p, sha256='0' * 64) for p, _ in v.COMPONENTES])), encoding='utf-8')
            self.assertEqual(v.verificar_manifesto(arquivo=alvo)['estado'], v.NAO_CONFORME)
            regravado = v.verificar_manifesto(gravar=True, arquivo=alvo)
            self.assertEqual(len(regravado['regravados']), len(v.COMPONENTES))
            self.assertTrue(regravado['nao_verificado'])  # regravar não é conferência
            salvo = json.loads(alvo.read_text(encoding='utf-8'))
            self.assertEqual(salvo['historico'][0]['componentes'][0]['sha256'], '0' * 64)
            self.assertTrue(salvo['gravado_em'])
            self.assertEqual(v.verificar_manifesto(arquivo=alvo)['estado'], v.CONFORME)


class UsoTests(unittest.TestCase):
    def test_gravar_fora_do_manifesto_e_json_invalido(self):
        import io, tempfile
        from contextlib import redirect_stdout
        with redirect_stdout(io.StringIO()):
            self.assertEqual(v.main(['conteudo', str(v.POP / 'fixtures' / 'minima.json'), '--gravar']), 2)
            with tempfile.TemporaryDirectory() as pasta:
                ruim = Path(pasta) / 'x.json'
                ruim.write_text('{nao e json', encoding='utf-8')
                self.assertEqual(v.main(['conteudo', str(ruim)]), 1)


if __name__ == '__main__':
    unittest.main()

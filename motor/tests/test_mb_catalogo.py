import importlib.util, json, sys, tempfile, unittest, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'bin'))
from mb_catalogo import coletar, gerar, gerar_html
class CatalogoTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
        (self.p/'00_PARA-VOCE'/'Tarefa # ação').mkdir(parents=True)
        (self.p/'00_PARA-VOCE'/'Tarefa # ação'/'index.html').write_text('oi')
    def registro(self,**changes):
        d={'id':'um','titulo':'<script>alert(1)</script>','pasta':'00_PARA-VOCE/Tarefa # ação','arquivo':'00_PARA-VOCE/Tarefa # ação/index.html','estado':'em_revisao','proxima_acao':'ver'};d.update(changes)
        (self.p/'dados').mkdir(exist_ok=True);(self.p/'dados/entregas.json').write_text(json.dumps({'schema_version':1,'entregas':[d]}));return d
    def test_legacy_never_approved(self):
        d=coletar(self.p);self.assertEqual(len(d['entregas']),1);self.assertEqual(d['entregas'][0]['estado'],'nao_verificado')
    def test_unicode_html_escaped_link_encoded(self):
        self.registro();h=gerar_html(coletar(self.p));self.assertIn('&lt;script&gt;',h);self.assertIn('%23',h);self.assertIn('Copiar caminho',h)
    def test_escape_rejected(self):
        self.registro(pasta='../fora')
        with self.assertRaises(ValueError):coletar(self.p)
    def test_absent_destination_not_hidden(self):
        self.registro(arquivo='00_PARA-VOCE/nada.html')
        with self.assertRaises(ValueError):coletar(self.p)
    def test_corrupt_registry_does_not_replace_page(self):
        out=gerar(self.p);before=out.read_bytes();(self.p/'dados').mkdir(exist_ok=True);(self.p/'dados/entregas.json').write_text('broken')
        with self.assertRaises(ValueError):gerar(self.p)
        self.assertEqual(out.read_bytes(),before)
    def test_human_entry_preserved(self):
        (self.p/'00_PARA-VOCE/INICIO.html').write_text('human')
        with self.assertRaises(ValueError):gerar(self.p)
    def test_readonly_collect(self):
        coletar(self.p);self.assertFalse((self.p/'dados').exists());self.assertFalse((self.p/'00_PARA-VOCE/INICIO.html').exists())
    def test_pronto_requires_current_proof(self):
        self.registro(estado='pronto');self.assertEqual(coletar(self.p)['entregas'][0]['estado'],'em_revisao')
    def test_executable_rejected(self):
        f=self.p/'00_PARA-VOCE/Tarefa # ação/x.exe';f.write_bytes(b'MZ');self.registro(arquivo=str(f))
        with self.assertRaises(ValueError):coletar(self.p)
    def test_edited_generated_page_is_preserved(self):
        out=gerar(self.p);out.write_text(out.read_text(encoding='utf-8')+'human edit',encoding='utf-8')
        with self.assertRaises(ValueError):gerar(self.p)
        self.assertTrue(out.read_text(encoding='utf-8').endswith('human edit'))
    def test_current_proof_expires_on_edit(self):
        p=self.p/'00_PARA-VOCE/Tarefa # ação/index.html'
        self.registro(estado='pronto',verificado_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),verificacao='prova local teste')
        self.assertEqual(coletar(self.p)['entregas'][0]['estado'],'pronto')
        p.write_text('alterado');self.assertEqual(coletar(self.p)['entregas'][0]['estado'],'em_revisao')
    def test_compass_uses_explicit_context_and_preserves_legacy(self):
        self.registro(pedido_inicial='Organizar <pastas>',pedido_atual='Incorporar Claude',etapa='Verificação')
        h=gerar_html(coletar(self.p))
        self.assertIn('Começou: Organizar &lt;pastas&gt;',h);self.assertIn('Agora: Incorporar Claude',h)
        self.assertIn('Etapa: Verificação',h)
        self.registro();self.assertNotIn('Contexto desta entrega',gerar_html(coletar(self.p)))
if __name__=='__main__':unittest.main()

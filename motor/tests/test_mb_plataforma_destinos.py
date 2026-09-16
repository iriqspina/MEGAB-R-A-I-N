import os,sys,json,tempfile,unittest,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'bin'))
from mb_catalogo import gerar,coletar
from mb_triagem import salvar_config,registrar_observacao,classificar
from mb_entregas_registro import registrar
class DestinosTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.p=self.root/'projeto';self.ext=self.root/'fora';self.p.mkdir();self.ext.mkdir()
    def link(self,name):
        dst=self.p/name
        if os.name=='nt':
            r=subprocess.run(['cmd.exe','/c','mklink','/J',str(dst),str(self.ext)],capture_output=True)
            if r.returncode:self.skipTest('Junction não disponível neste ambiente')
        else:dst.symlink_to(self.ext,target_is_directory=True)
        self.assertEqual(dst.resolve(),self.ext)
    def test_junction_inbox_does_not_write_outside(self):
        self.link('00_PARA-VOCE')
        with self.assertRaises(ValueError):gerar(self.p)
        self.assertEqual(list(self.ext.iterdir()),[])
    def test_junction_data_does_not_write_outside(self):
        self.link('dados')
        for action in (lambda:salvar_config(self.p,'criteriosa'),lambda:registrar_observacao(self.p,classificar('oi')),lambda:registrar(self.p,{}),lambda:coletar(self.p)):
            with self.assertRaises(ValueError):action()
        self.assertEqual(list(self.ext.iterdir()),[])
    def test_observation_has_no_prompt_or_reply(self):
        registrar_observacao(self.p,classificar('texto de entrada privado para teste'),'teste')
        text=(self.p/'dados/triagem-observacoes.json').read_text(encoding='utf-8')
        self.assertNotIn('texto de entrada',text);self.assertNotIn('prompt',text);self.assertEqual(json.loads(text)['total'],1)
if __name__=='__main__':unittest.main()

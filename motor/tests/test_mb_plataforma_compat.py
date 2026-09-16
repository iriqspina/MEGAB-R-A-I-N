import importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'bin'))
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'bin'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class CompatTest(unittest.TestCase):
    def test_nested_project_beats_central(self):
        m=load('mb-contexto')
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);central=base/'central';pet=central/'pets';(pet/'MEGABRAIN').mkdir(parents=True)
            (central/'memoria/estado').mkdir(parents=True);(central/'memoria/estado/META.md').write_text('central')
            with mock.patch.object(m,'projetos_root',return_value=base):self.assertEqual(m.achar_projeto(str(pet/'backend')),pet)
    def test_explicit_current_empty_suppresses_old_action(self):
        m=load('mb-relatorio-vivo')
        text='<!-- MB:PARA-VOCE:ATUAL:INICIO -->\n## PARA VOCÊ\n<!-- MB:PARA-VOCE:ATUAL:FIM -->\n## PARA VOCÊ\n1. aprove de novo\n'
        with mock.patch.object(m.u,'safe_read_text',return_value=text):self.assertEqual(m.secao_para_voce(ROOT),[])
    def test_legacy_handoff_still_supported(self):
        m=load('mb-relatorio-vivo')
        with mock.patch.object(m.u,'safe_read_text',return_value='## PARA VOCÊ\n1. Decisão real\n'):self.assertEqual(m.secao_para_voce(ROOT),['Decisão real'])
if __name__=='__main__':unittest.main()

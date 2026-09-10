import importlib.util
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("mb_inicio_sessao", RAIZ / "bin" / "mb-inicio-sessao.py")
MODULO = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULO
SPEC.loader.exec_module(MODULO)


class InicioSessaoTests(unittest.TestCase):
    def test_catalogo_tem_skills_do_fluxo_padrao(self):
        dados = MODULO.resumo(RAIZ)
        nomes = {item["nome"] for item in dados["skills"]}
        self.assertTrue(dados["pronto"])
        self.assertTrue({"megabrain", "orquestracao1", "orquestracao2"}.issubset(nomes))

    def test_instrucao_declara_excecoes_sem_desligar_v6(self):
        texto = MODULO.resumo(RAIZ)["instrucao_para_ia"]
        self.assertIn("/orquestracao1 (V6)", texto)
        self.assertIn("pergunta simples", texto)
        self.assertIn("/orquestracao2", texto)


if __name__ == "__main__":
    unittest.main()

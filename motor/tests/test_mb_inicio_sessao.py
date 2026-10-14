import importlib.util
import sys
import unittest
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("mb_inicio_sessao", RAIZ / "bin" / "mb-inicio-sessao.py")
MODULO = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULO
SPEC.loader.exec_module(MODULO)


class InicioSessaoTests(unittest.TestCase):
    def test_visual_carrega_texto_e_caso_com_resultado_real(self):
        data = MODULO.contexto_visual(RAIZ, True, "residencia-genetica")
        self.assertTrue(data["carregado"])
        self.assertIn("DECISÃO HUMANA", data["texto_protocolo"])
        case = data["caso_contextual"]
        self.assertTrue(case["raw_sha256"])
        negatives = [r for run in case["runs"] for r in run["results"] if r["result"] == "FALHOU"]
        self.assertTrue(negatives)
        self.assertIn("YouTube", str(case))

    def test_visual_catalogo_nao_forca_caso_de_outro_projeto(self):
        data = MODULO.contexto_visual(RAIZ, True)
        self.assertTrue(data["carregado"])
        self.assertTrue(data["catalogo_casos"])
        self.assertNotIn("caso_contextual", data)

    def test_caso_nao_cadastrado_nao_finge_carregamento(self):
        data = MODULO.contexto_visual(RAIZ, True, "inexistente")
        self.assertFalse(data["carregado"])
        self.assertIn("erro", data)

    def test_visual_ausente_nao_finge_carregamento(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = MODULO.contexto_visual(Path(tmp), True)
        self.assertFalse(data["carregado"])
        self.assertIn("erro", data)

    def test_sem_visual_nao_injeta_caso_inteiro(self):
        data = MODULO.contexto_visual(RAIZ)
        self.assertFalse(data["carregado"])
        self.assertNotIn("caso_contextual", data)

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

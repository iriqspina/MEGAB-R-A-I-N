import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pendencias_core import registro as reg  # noqa: E402


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self.tmp.name) / "pendencias.json"
        self.r = reg.Registro(self.caminho).carregar()

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_listar_feito_ciclo(self):
        self.r.add("Marketeiro", "Mandar proposta pra Hanada", detalhe="lote 1")
        self.r.add("Marketeiro", "Segunda pendência")
        self.r.add("Ótica Hanada", "Reunião de briefing")
        grupos = self.r.resumo()
        self.assertEqual(len(grupos), 2)
        self.assertEqual(len(grupos[0]["itens"]), 2)
        item = self.r.feito("Marketeiro", "Mandar proposta pra Hanada")
        self.assertEqual(item["estado"], reg.ITEM_FEITA)
        self.assertEqual(len(self.r.resumo()[0]["itens"]), 1)

    def test_nome_com_acento_e_casefold(self):
        self.r.add("Ótica Hanada", "x")
        p = self.r.projeto("otica hanada")
        self.assertEqual(p["nome"], "Ótica Hanada")

    def test_prefixo_unico_e_ambiguo(self):
        self.r.garantir_projeto("Portfolio")
        self.r.garantir_projeto("Pobrema no Pc")
        self.assertEqual(self.r.projeto("port").get("nome"), "Portfolio")
        self.r.garantir_projeto("Portifolio-antigo")
        with self.assertRaises(reg.ErroRegistro):
            self.r.projeto("port")

    def test_pausar_retomar_preserva_itens(self):
        self.r.add("Pets", "deploy dev.7")
        self.r.pausar("Pets")
        self.assertEqual(self.r.resumo(), [])
        self.r.retomar("Pets")
        self.assertEqual(len(self.r.resumo()), 1)

    def test_rmMarca_nao_apaga(self):
        self.r.add("Pets", "x")
        self.r.rm("Pets", "x")
        p = self.r.projeto("Pets")
        self.assertEqual(p["itens"][0]["estado"], reg.ITEM_REMOVIDA)
        self.assertEqual(self.r.resumo()[0]["itens"], [])

    def test_ocultar_auto_por_hash(self):
        self.r.garantir_projeto("Marketeiro")["estado_hash"] = "abc"
        self.r.projeto("Marketeiro")["proximo_passo"] = "crítica das fichas"
        self.assertTrue(self.r.resumo()[0]["proximo_passo"])
        self.r.ocultar_auto("Marketeiro")
        self.assertIsNone(self.r.resumo()[0]["proximo_passo"])
        self.r.projeto("Marketeiro")["estado_hash"] = "def"  # ESTADO.md mudou
        self.assertEqual(self.r.resumo()[0]["proximo_passo"], "crítica das fichas")

    def test_salvar_atomico_recupera_do_bak(self):
        self.r.add("Portfolio", "escolher base do comparativo")
        self.r.salvar()
        self.assertTrue(self.caminho.exists())
        # corrompe o principal; a carga deve cair no .bak
        self.caminho.write_text("{inválido", encoding="utf-8")
        r2 = reg.Registro(self.caminho).carregar()
        self.assertEqual(len(r2.resumo()), 1)

    def test_campos_desconhecidos_preservados(self):
        self.r.add("Portfolio", "x")
        self.r.dados["campo_novo"] = {"nao": "apagar"}
        self.r.salvar()
        carregado = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertEqual(carregado["campo_novo"], {"nao": "apagar"})

    def test_contagem_ativa(self):
        self.r.add("A", "um")
        self.r.add("B", "dois")
        self.r.garantir_projeto("C")["proximo_passo"] = "auto"
        itens, projetos = self.r.contagem_ativa()
        self.assertEqual((itens, projetos), (3, 3))


if __name__ == "__main__":
    unittest.main()

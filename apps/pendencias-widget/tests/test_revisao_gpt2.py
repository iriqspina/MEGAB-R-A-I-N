import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pendencias_core import registro as reg  # noqa: E402
from pendencias_core import scanner  # noqa: E402


class TestRevisaoGpt2(unittest.TestCase):
    """Cobre os 12 achados da revisão gpt2 high (260916)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self.tmp.name) / "pendencias.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_bak_sobrevive_a_principal_corrompido(self):
        # achado 1: salvar depois de recuperar NÃO destrói o .bak
        r = reg.Registro(self.caminho).carregar()
        r.add("A", "x")
        r.salvar()
        self.caminho.write_text("{corrompido", encoding="utf-8")
        r2 = reg.Registro(self.caminho).carregar()  # recupera do .bak
        r2.add("A", "y")
        r2.salvar()
        self.caminho.write_text("{corrompido de novo", encoding="utf-8")
        r3 = reg.Registro(self.caminho).carregar()
        titulos = [i["titulo"] for i in r3.projeto("A")["itens"] if i["estado"] == "aberta"]
        self.assertIn("y", titulos)

    def test_json_invalido_vira_erro_registro(self):
        # achado 3: exceção crua vira ErroRegistro (widget não cai)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho.write_bytes(bytes([0xFF, 0xFE, 0x00]) + b"binario")
        with self.assertRaises(reg.ErroRegistro):
            reg.Registro(self.caminho).carregar()

    def test_add_ambiguo_nao_cria(self):
        # achado 4: ambiguidade nunca cria projeto novo
        r = reg.Registro(self.caminho).carregar()
        r.garantir_projeto("Portfolio")
        r.garantir_projeto("Pobrema no Pc")
        with self.assertRaises(reg.ErroRegistro):
            r.add("po", "x")
        self.assertEqual([p["nome"] for p in r.dados["projetos"]], ["Portfolio", "Pobrema no Pc"])

    def test_resumo_exclui_ausente(self):
        # achado 5: presente=False sai do radar
        r = reg.Registro(self.caminho).carregar()
        r.add("Velho", "x")
        r.projeto("Velho")["presente"] = False
        self.assertEqual(r.resumo(), [])

    def test_ref_parcial_ambiguo_erro(self):
        # achado 6: ref parcial com vários matches = erro com ids, não o primeiro
        r = reg.Registro(self.caminho).carregar()
        r.add("A", "mandar proposta X")
        r.add("A", "mandar proposta Y")
        with self.assertRaises(reg.ErroRegistro) as ctx:
            r.feito("A", "mandar proposta")
        self.assertIn("varios", str(ctx.exception))

    def test_validar_rejeita_item_malformado(self):
        # achado 7: item sem título válido rejeitado na gravação
        r = reg.Registro(self.caminho).carregar()
        r.garantir_projeto("A")["itens"].append({"titulo": 123})
        with self.assertRaises(reg.ErroRegistro):
            r.salvar()

    def test_parse_markdown(self):
        # achado 8: "## TL;DR:" e "**Próximo passo:**" parseiam
        texto = "## TL;DR: resumo top\n**Próximo passo:** escolher base\n"
        info = scanner.parse_estado(texto)
        self.assertEqual(info["resumo"], "resumo top")
        self.assertEqual(info["proximo_passo"], "escolher base")

    def test_travado_nao_livre(self):
        # achado 10: "não livre" é travado; "livre — ..." é livre
        self.assertTrue(scanner.parse_estado("TRAVADO_POR: não livre")["pausado_sugerido"])
        self.assertFalse(scanner.parse_estado("TRAVADO_POR: livre — sessão encerrada.")["pausado_sugerido"])

    def test_scan_zera_derivados_sem_estado(self):
        # achado 5: projeto que perdeu o ESTADO.md não herda resumo velho
        pasta = Path(self.tmp.name) / "raiz" / "Proj"
        pasta.mkdir(parents=True)
        (pasta / "MEGABRAIN").mkdir()
        r = reg.Registro(self.caminho).carregar()
        p = r.garantir_projeto("Proj", caminho=str(pasta))
        p["resumo"] = "velho"
        p["proximo_passo"] = "velho passo"
        scanner.scan(r, Path(self.tmp.name) / "raiz")
        self.assertIsNone(r.projeto("Proj")["resumo"])
        self.assertIsNone(r.projeto("Proj")["proximo_passo"])

    def test_trava_deixa_passar_sequencial(self):
        # achado 2: trava de arquivo não atrapalha uso sequencial
        r = reg.Registro(self.caminho).carregar()
        with reg.trava(self.caminho):
            r.add("A", "dentro da trava")
        r.salvar()
        self.assertEqual(len(reg.Registro(self.caminho).carregar().resumo()[0]["itens"]), 1)


if __name__ == "__main__":
    unittest.main()

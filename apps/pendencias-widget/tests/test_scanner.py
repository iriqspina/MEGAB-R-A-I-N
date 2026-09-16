import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pendencias_core import registro as reg  # noqa: E402
from pendencias_core import scanner  # noqa: E402


def _mk(root: Path, nome: str, estado: str | None):
    p = root / nome
    p.mkdir(parents=True, exist_ok=True)
    if estado is not None:
        (p / "ESTADO.md").write_text(estado, encoding="utf-8")
    return p


class TestParseEstado(unittest.TestCase):
    def test_resumo_e_proximo_passo_padroes_reais(self):
        casos = [
            "# ESTADO — X\n\nTL;DR: lote 1 pronto para crítica.\n\n- Próximo passo: <USUARIO> escolher base.\n",
            "TL;DR — método pronto.\nPRÓXIMO PASSO: calibração de 9 pontos.\n",
            "TL;DR: núcleo revisado.\n5. Gate seguinte: calibração de 9 pontos, ainda sem cursor.\n",
            "TL;DR: pausa por logout.\nPendente: registrar lição.\n",
        ]
        esperado = [
            ("lote 1 pronto para crítica.", "<USUARIO> escolher base."),
            ("método pronto.", "calibração de 9 pontos."),
            ("núcleo revisado.", "calibração de 9 pontos, ainda sem cursor."),
            ("pausa por logout.", "registrar lição."),
        ]
        for texto, (resumo, passo) in zip(casos, esperado):
            info = scanner.parse_estado(texto)
            self.assertEqual(info["resumo"], resumo, texto[:40])
            self.assertEqual(info["proximo_passo"], passo, texto[:40])

    def test_pausado(self):
        pausados = [
            "**Atual: PAUSADO por logout do <USUARIO>. Não retomar automaticamente.**",
            "Fase: pausada a pedido de <USUARIO>.",
            "TRAVADO_POR: sessão encerrada em 260913.",
        ]
        for t in pausados:
            self.assertTrue(scanner.parse_estado(t)["pausado_sugerido"], t)
        vivos = [
            "TRAVADO_POR: livre — sessão encerrada.",
            "Fase: pesquisa e definição; não iniciar campanha sem crítica.",
        ]
        for t in vivos:
            self.assertFalse(scanner.parse_estado(t)["pausado_sugerido"], t)

    def test_sem_estado(self):
        self.assertEqual(scanner.parse_estado(None)["resumo"], None)


class TestScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.reg_path = self.raiz / "dados" / "pendencias.json"
        self.r = reg.Registro(self.reg_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_deteccao_e_preserva_manual(self):
        _mk(self.raiz, "Marketeiro", "TL;DR: lote 1.\nPróximo passo: crítica das fichas.\n")
        _mk(self.raiz, "SóMegabrain", None)
        (self.raiz / "SóMegabrain" / "MEGABRAIN").mkdir()
        _mk(self.raiz, "_oculto", "TL;DR: não deve aparecer.")
        _mk(self.raiz, "PastaComum", None)  # nem ESTADO nem MEGABRAIN
        self.r.add("Marketeiro", "manual sobrevive ao scan")
        self.r.pausar("Marketeiro")
        stats = scanner.scan(self.r, self.raiz)
        nomes = [p["nome"] for p in self.r.dados["projetos"]]
        self.assertIn("Marketeiro", nomes)
        self.assertIn("SóMegabrain", nomes)
        self.assertNotIn("_oculto", nomes)
        self.assertNotIn("PastaComum", nomes)
        self.assertEqual(stats["projetos"], 2)
        self.assertFalse(self.r.projeto("Marketeiro")["ativo"], "pausa do dono foi desfeita")
        self.assertEqual(len(self.r.projeto("Marketeiro")["itens"]), 1)
        self.assertEqual(self.r.projeto("Marketeiro")["proximo_passo"], "crítica das fichas.")
        self.assertTrue(self.r.projeto("Marketeiro").get("estado_hash"))

    def test_projeto_sumido_marcado(self):
        p = _mk(self.raiz, "Velho", "TL;DR: x.")
        scanner.scan(self.r, self.raiz)
        p_fantasma = reg.vazio()
        self.r.garantir_projeto("Fantasma", caminho=str(self.raiz / "nao-existe"))
        import shutil

        shutil.rmtree(p)
        scanner.scan(self.r, self.raiz)
        self.assertFalse(self.r.projeto("Velho").get("presente", True))
        self.assertFalse(self.r.projeto("Fantasma").get("presente", True))

    def test_scan_idempotente(self):
        _mk(self.raiz, "A", "TL;DR: x.\nPróximo passo: y.\n")
        scanner.scan(self.r, self.raiz)
        antes = self.r.dados
        scanner.scan(self.r, self.raiz)
        self.assertEqual(
            [p["nome"] for p in antes["projetos"]], [p["nome"] for p in self.r.dados["projetos"]]
        )
        self.assertEqual(self.r.contagem_ativa(), (1, 1))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Testes do compreensor de padrões (bin/mb-compreensor.py — spec §7).

O que estes testes protegem:
- a RÉGUA. O primeiro rascunho do detector devolveu "claude", "nota", "file"
  e "markdown" como temas a templatizar — slop puro. Três regras mataram isso
  e cada uma tem teste aqui: (a) prosa de estado corrobora mas não qualifica;
  (b) tema precisa de um lugar FORTE (coisa que ele faz e guarda); (c)
  arquivo-léxico (lista de dependências) empresta só o próprio nome.
- a COBERTURA. Se existe bin/mb-obsidian.py, o tema "obsidian" já virou
  máquina e não pode ser proposto de novo. E bigrama só é coberto pelo
  bigrama — "referencias" + "visuais" separados NÃO cobrem
  "referencias visuais" (esse bug contradizia a pendência aberta).
- o DECLARADO. Pendência com "templatizar" no nome sai sempre, sem depender
  de estatística nenhuma.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb_utils.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
sys.path.insert(0, str(RAIZ / "bin"))

_spec = importlib.util.spec_from_file_location("mb_compreensor", RAIZ / "bin" / "mb-compreensor.py")
comp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comp)


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.c = Path(self._t.name)
        (self.c / "bin").mkdir()
        (self.c / "bin" / "mb_utils.py").write_text("# âncora\n", encoding="utf-8")
        for p in ("memoria/pendencias", "memoria/cerebro/wiki", "memoria/cerebro/raw",
                  "03_docs", "motor/modelos", "motor/skills", "01_acoes", "00_painel"):
            (self.c / p).mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._t.cleanup)

    def pend(self, nome: str, titulo: str = "Nota pendente — 260818 · Assunto qualquer"):
        d = self.c / "memoria" / "pendencias" / nome
        d.mkdir()
        (d / "260818_nota.md").write_text(f"# {titulo}\n", encoding="utf-8")
        return d

    def wiki(self, nome: str, titulo: str = ""):
        f = self.c / "memoria" / "cerebro" / "wiki" / f"{nome}.md"
        f.write_text(f"# {titulo or nome}\n", encoding="utf-8")
        return f

    def doc(self, nome: str, corpo: str = ""):
        f = self.c / "03_docs" / f"{nome}.md"
        f.write_text(corpo or f"# {nome}\n", encoding="utf-8")
        return f


class TestTokens(unittest.TestCase):
    def test_carimbo_de_data_nao_e_termo(self):
        self.assertNotIn("260818", comp.tokens("260818-review-figma-wp"))

    def test_acento_e_normalizado(self):
        self.assertIn("referencias", comp.tokens("Referências Visuais"))

    def test_palavra_de_estrutura_cai(self):
        for morta in ("megabrain", "arquivo", "claude", "kimi", "modelo"):
            self.assertNotIn(morta, comp.tokens(f"{morta} figma"))

    def test_bigrama_adjacente_existe(self):
        self.assertIn("review figma", comp.termos("review figma wp"))

    def test_token_curto_cai(self):
        self.assertNotIn("wp", comp.tokens("review figma wp"))


class TestRegua(Base):
    def _itens(self):
        return comp.coletar(self.c, dias=0)

    def test_prosa_de_estado_nao_qualifica_sozinha(self):
        """Palavra em doc + DECISOES não é padrão: é vocabulário."""
        self.doc("nota-sobre-carimbo", "# carimbo\n")
        (self.c / "memoria" / "estado").mkdir(parents=True, exist_ok=True)
        (self.c / "memoria" / "estado" / "DECISOES.md").write_text(
            "# 260818 — carimbo aqui\n# 260819 — carimbo ali\n", encoding="utf-8")
        r = comp.detectar(self._itens(), set())
        self.assertNotIn("carimbo", [a["termo"] for a in r["achados"]])

    def test_precisa_de_lugar_forte(self):
        """doc + fonte bruta = assunto que ele LEU. Não rende modelo."""
        self.doc("sobre-carimbo", "# carimbo\n")
        (self.c / "memoria" / "cerebro" / "raw" / "260822_carimbo.md").write_text(
            "# carimbo\n", encoding="utf-8")
        r = comp.detectar(self._itens(), set())
        self.assertNotIn("carimbo", [a["termo"] for a in r["achados"]])
        self.assertIn("carimbo", [q["termo"] for q in r["quase"]])

    def test_pendencia_mais_cerebro_passa(self):
        """Isso sim é padrão: ele guardou o tema em dois lugares que ele faz."""
        self.pend("260818-camada-carimbo")
        self.wiki("260822_carimbo-dashboard")
        r = comp.detectar(self._itens(), set())
        self.assertIn("carimbo", [a["termo"] for a in r["achados"]])

    def test_arquivo_lexico_empresta_so_o_nome(self):
        """Lista de dependências tem 200 palavras soltas e fingia padrão."""
        muitos = "\n".join(f"# palavra{i}zzz tema{i}zzz" for i in range(80))
        it = comp._item(self.c, "doc", "lista", self.c / "03_docs" / "lista.md", muitos)
        self.assertLessEqual(len(it["termos"]), comp.TETO_TERMOS)


class TestCobertura(Base):
    def test_script_em_bin_ja_e_cobertura(self):
        self.pend("260818-camada-obsidian")
        self.wiki("260822_obsidian-vault")
        (self.c / "bin" / "mb-obsidian.py").write_text("# x\n", encoding="utf-8")
        r = comp.detectar(comp.coletar(self.c, dias=0), comp.indice_coberto(self.c))
        self.assertNotIn("obsidian", [a["termo"] for a in r["achados"]])
        self.assertIn("obsidian", [c["termo"] for c in r["cobertos"]])

    def test_bigrama_nao_e_coberto_por_palavras_soltas(self):
        """O bug que contradizia a pendência aberta: 'referencias' e 'visuais'
        existiam separados e faziam 'referencias visuais' parecer pronto."""
        self.pend("260818-camada-referencias-visuais")
        self.wiki("260822_referencias-visuais-dashboard")
        r = comp.detectar(comp.coletar(self.c, dias=0), {"referencias", "visuais"})
        self.assertIn("referencias visuais", [a["termo"] for a in r["achados"]])


class TestDeclarado(Base):
    def test_pendencia_templatizar_sempre_sai(self):
        self.pend("260818-templatizar-review-figma-wp",
                  "Nota pendente — 260818 · Templatizar revisão fragmentada Figma × WP")
        d = comp.declarados(comp.coletar(self.c, dias=0), self.c)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["assunto"], "review-figma-wp")
        self.assertEqual(d[0]["titulo"], "Templatizar revisão fragmentada Figma × WP")
        self.assertFalse(d[0]["ja_existe"])
        self.assertIsInstance(d[0]["dias_parado"], int)

    def test_modelo_que_ja_existe_e_marcado(self):
        self.pend("260818-templatizar-carimbo")
        (self.c / "motor" / "modelos" / "carimbo.md").write_text("x", encoding="utf-8")
        d = comp.declarados(comp.coletar(self.c, dias=0), self.c)
        self.assertTrue(d[0]["ja_existe"])


class TestSaida(Base):
    def test_central_vazia_nao_quebra(self):
        d = comp.montar(self.c, dias=0, min_tipos=2)
        self.assertEqual(d["achados"], [])
        self.assertIn("# Padrões", comp.markdown(d))

    def test_markdown_declara_o_que_nao_olhou(self):
        self.pend("260818-templatizar-carimbo")
        md = comp.markdown(comp.montar(self.c, dias=0, min_tipos=2))
        self.assertIn("NÃO olhou", md)
        self.assertIn("privacidade", md.lower())


if __name__ == "__main__":
    unittest.main()

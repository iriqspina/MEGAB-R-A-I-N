# -*- coding: utf-8 -*-
"""Tema claro do POP v1.2 — contrato estrutural (sem navegador).

Cobre: template com o tema embutido, módulo compartilhado alinhado ao
template, flag --tema dos geradores (claro/escuro/ausente/inválido),
pele legado com variante opt-in, contraste AA da paleta clara e zero
recurso remoto. O teste funcional do toggle em navegador real é o
bin/mb-verificar-pop-tema.mjs (roda fora da suíte: precisa de Chrome).
"""
from __future__ import annotations

import importlib.util
import py_compile
import re
import sys
import tempfile
import unittest
from pathlib import Path

CENTRAL = Path(__file__).resolve().parents[2]
BIN = CENTRAL / "bin"
TEMPLATE = CENTRAL / "motor" / "modelos" / "relatorios" / "260914_pop" / "relatorio-pop.html"
PELE = CENTRAL / "motor" / "modelos" / "relatorios" / "260914_pop" / "260915_pele-pop-legado.css"

TOKENS_COMPARTILHADOS = (
    'data-tema="claro"',
    "megabrain.pop.tema",
    "#F5F3EE",
    'aria-pressed',
    'id="btn-tema"',
    'role="status"',
    "Não foi possível salvar a preferência",
    # acentos vivos nos gráficos + versão escura -tx nos textos (260915c)
    "--coral-tx:", "--verde-tx:", "--azul-tx:", "--amarelo-tx:", "--roxo-tx:", "--rosa-tx:",
)


def _carregar(nome: str, caminho: Path):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(BIN))  # geradores importam mb_utils de bin/
mb_pop_tema = _carregar("mb_pop_tema", BIN / "mb_pop_tema.py")


class TestTemplateTemaClaro(unittest.TestCase):
    def setUp(self):
        self.html = TEMPLATE.read_text(encoding="utf-8")

    def test_tokens_do_tema_estao_no_template(self):
        for tk in TOKENS_COMPARTILHADOS:
            self.assertIn(tk, self.html, f"template sem {tk!r}")

    def test_restauracao_sincrona_antes_da_pintura(self):
        cabeca = self.html[: self.html.find("</head>")]
        self.assertIn("localStorage.getItem('megabrain.pop.tema')", cabeca)
        corpo = self.html.find("<body")
        self.assertGreater(corpo, 0)
        self.assertLess(self.html.find("localStorage.getItem('megabrain.pop.tema')"), corpo)

    def test_botao_nasce_desabilitado_e_visivel(self):
        m = re.search(r'<button[^>]*id="btn-tema"[^>]*>', self.html)
        self.assertIsNotNone(m, "botão do tema ausente")
        tag = m.group(0)
        self.assertIn("disabled", tag)
        self.assertIn("type=\"button\"", tag)
        self.assertNotIn("hidden", tag)

    def test_sem_recurso_remoto(self):
        externos = re.findall(
            r'(?:src|href|url)\s*[=(]\s*["\']?https?://[^"\')]+', self.html)
        self.assertEqual(externos, [], f"recursos remotos: {externos[:3]}")

    def test_precedencia_documentada_no_head(self):
        cabeca = self.html[: self.html.find("</head>")]
        self.assertIn("preferência salva válida", cabeca)


class TestModuloCompartilhado(unittest.TestCase):
    """O módulo dos geradores e o template não podem divergir."""

    def test_tokens_iguais_entre_modulo_e_template(self):
        embutido = mb_pop_tema.CSS_TEMA + mb_pop_tema.JS_TEMA_HEAD + mb_pop_tema.HTML_TEMA_CONTROLE
        template = TEMPLATE.read_text(encoding="utf-8")
        for tk in ("#F5F3EE", "megabrain.pop.tema", "data-tema", "btn-tema",
                   "tema-status", "#191923"):
            self.assertIn(tk, embutido, f"módulo sem {tk!r}")
            self.assertIn(tk, template, f"template sem {tk!r}")

    def test_modulo_somente_temas_validos(self):
        self.assertIn("claro", mb_pop_tema.JS_TEMA_HEAD)
        self.assertIn("escuro", mb_pop_tema.JS_TEMA_HEAD)


class TestGeradorVivo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vivo = _carregar("mb_relatorio_vivo_test", BIN / "mb-relatorio-vivo.py")

    def _gerar(self, tema=None):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "vivo-prova.html"
            ok = self.vivo.gerar_html(CENTRAL, saida=tmp, tema=tema)
            self.assertTrue(ok)
            return tmp.read_text(encoding="utf-8")

    @staticmethod
    def _tag_html(texto: str) -> str:
        m = re.search(r"<html\b[^>]*>", texto)
        return m.group(0) if m else ""

    def test_padrao_nasce_escuro(self):
        html_txt = self._gerar(None)
        self.assertEqual(self._tag_html(html_txt), '<html lang="pt-BR">')
        self.assertIn('id="btn-tema"', html_txt)

    def test_tema_claro_grava_atributo(self):
        html_txt = self._gerar("claro")
        self.assertEqual(self._tag_html(html_txt), '<html lang="pt-BR" data-tema="claro">')

    def test_tema_escuro_nao_grava_atributo(self):
        html_txt = self._gerar("escuro")
        self.assertNotIn("data-tema", self._tag_html(html_txt))


class TestGeradorDNA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dna = _carregar("mb_relatorio_dna_test", BIN / "mb-relatorio-dna.py")

    def test_claro_e_escuro(self):
        claro = self.dna.gerar_html(CENTRAL, "v-teste", "2026-09-15T00:00:00", tema="claro")
        self.assertIn('data-tema="claro"', re.search(r"<html\b[^>]*>", claro).group(0))
        escuro = self.dna.gerar_html(CENTRAL, "v-teste", "2026-09-15T00:00:00", tema=None)
        self.assertNotIn("data-tema", re.search(r"<html\b[^>]*>", escuro).group(0))
        self.assertIn('id="btn-tema"', claro)


class TestGeradorProjeto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proj = _carregar("mb_relatorio_projeto_test", BIN / "mb-relatorio-projeto.py")

    def _args(self, tema_tela=None):
        import argparse
        return argparse.Namespace(
            projeto=str(CENTRAL), titulo="prova", plano="ESTADO.md", context="CONTEXT.md",
            extra=[], sem_todos_md=True, skill=None, tldr=None, tldr_classe="ok",
            tema="console", tema_tela=tema_tela, megabrain_central=None,
            sem_resolucao=True, resolucao_titulo=[], sem_acao_imediata=True,
            acao_imediata_titulo=[], acao=[], sem_pele=True, links_relativos=True,
        )

    def test_claro_e_default(self):
        claro = self.proj.gerar(self._args("claro"), "2026-09-15T00:00:00")
        self.assertIn('data-tema="claro"', re.search(r"<html\b[^>]*>", claro).group(0))
        padrao = self.proj.gerar(self._args(None), "2026-09-15T00:00:00")
        self.assertNotIn("data-tema", re.search(r"<html\b[^>]*>", padrao).group(0))


class TestPeleLegado(unittest.TestCase):
    def setUp(self):
        self.css = PELE.read_text(encoding="utf-8")

    def test_variante_clara_existe_e_e_opt_in(self):
        self.assertIn('html[data-tema="claro"]', self.css)
        # sem o atributo, nada muda: a base continua escura
        self.assertIn("#101014", self.css)

    def test_aplicar_tema_do_pele_pop(self):
        pele = _carregar("mb_pele_pop_test", BIN / "mb-pele-pop.py")
        base = '<html lang="pt-BR"><head></head><body>x</body></html>'
        claro = pele.aplicar_tema(base, "claro")
        self.assertIn('data-tema="claro"', claro)
        de_volta = pele.aplicar_tema(claro, "escuro")
        self.assertNotIn("data-tema", de_volta)
        # idempotente: aplicar claro duas vezes não duplica o atributo
        duas = pele.aplicar_tema(pele.aplicar_tema(base, "claro"), "claro")
        self.assertEqual(duas.count("data-tema"), 1)

    def test_aplicar_tema_do_reskin(self):
        reskin = _carregar("mb_relatorio_reskin_test", BIN / "mb-relatorio-reskin.py")
        base = '<html lang="pt-BR"><head></head><body>y</body></html>'
        com_pele = reskin.aplicar(base, "vivo-antigo")
        claro = reskin.aplicar_tema(com_pele, "claro")
        self.assertIn('data-tema="claro"', claro)
        # pele + tema juntos: integridade compara fora da pele E fora do atributo
        self.assertTrue(reskin.integro(base, claro, tema_mudou=True))
        # mudança fora da pele SEM a exceção do tema não pode passar
        self.assertFalse(reskin.integro(base, claro, tema_mudou=False))


class TestContrasteAAPaletaClara(unittest.TestCase):
    PALETA = {
        "fundo": "#F5F3EE", "card": "#FFFFFF", "tinta": "#191923",
        "corpo": "#454552", "fraco": "#5E5E6E",
        "coral-tx": "#AD2838", "verde-tx": "#216B42", "azul-tx": "#185ABD",
        "amarelo-tx": "#805000", "roxo-tx": "#6236A5", "rosa-tx": "#96356D",
    }

    @staticmethod
    def _lum(hexcor: str) -> float:
        r, g, b = (int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5))
        def lin(v):
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    def _razao(self, texto: str, fundo: str) -> float:
        l1, l2 = sorted((self._lum(texto), self._lum(fundo)), reverse=True)
        return (l1 + 0.05) / (l2 + 0.05)

    def test_textos_e_acentos_tx_aa_sobre_fundos_claros(self):
        p = self.PALETA
        textos = {"tinta": p["tinta"], "corpo": p["corpo"], "fraco": p["fraco"]}
        acentos = {k: p[k] for k in ("coral-tx", "verde-tx", "azul-tx", "amarelo-tx", "roxo-tx", "rosa-tx")}
        for nome, fundo in (("fundo", p["fundo"]), ("card", p["card"])):
            for tn, tc in {**textos, **acentos}.items():
                r = self._razao(tc, fundo)
                self.assertGreaterEqual(r, 4.5, f"{tn} sobre {nome}: {r:.2f}:1 < 4.5")

    def test_acentos_vivos_sao_os_mesmos_do_escuro(self):
        """O jeitão vivo do escuro (#FF4B4B, #58CC02...) é mantido nos gráficos do claro."""
        css = mb_pop_tema.CSS_TEMA
        for vivo in ("#FF4B4B", "#58CC02", "#1CB0F6", "#FFC800", "#CE82FF", "#FF82C4"):
            self.assertIn(vivo, css, f"acento vivo {vivo} sumiu do claro")


class TestCompilacao(unittest.TestCase):
    def test_py_compile_geradores_e_peles(self):
        alvos = ["mb-relatorio-vivo.py", "mb-relatorio-dna.py", "mb-relatorio-projeto.py",
                 "mb_pop_tema.py", "mb-pele-pop.py", "mb-relatorio-reskin.py"]
        for nome in alvos:
            py_compile.compile(str(BIN / nome), doraise=True)


if __name__ == "__main__":
    unittest.main()

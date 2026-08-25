"""Testes do restaurador — a peça que destrava a cópia magra (260825x).

Por que existe: `mb-recuperar-megabrain.py` é um dos mutadores de alto impacto
que o levantamento de 260825 achou SEM teste direto. E ele acabou de mudar de
contrato: "outro projeto" deixou de ser fonte, e ele passou a PROVAR que
restaurou em vez de só terminar sem exceção.

Nada aqui destrói nada: só temporários.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent.parent / "bin"
sys.path.insert(0, str(BIN))

_spec = importlib.util.spec_from_file_location("mb_rec", BIN / "mb-recuperar-megabrain.py")
rec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rec)


class Base(unittest.TestCase):
    def tmp(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)

    def central_falsa(self, raiz: Path) -> Path:
        """Central mínima que passa em u.e_central()."""
        c = raiz / "central"
        (c / "bin").mkdir(parents=True)
        (c / "memoria" / "nucleo").mkdir(parents=True)
        (c / "memoria" / "nucleo" / "VERSAO.txt").write_text(
            "2026-08-25 · v7.5 — teste\n", encoding="utf-8")
        (c / "memoria" / "nucleo" / "MEGABRAIN.md").write_text(
            "# MEGABRAIN\n", encoding="utf-8")
        return c


class TestConferir(Base):
    """A prova. Antes disto, 'recuperado' só queria dizer 'não explodiu'."""

    def test_pasta_inexistente_reprova(self):
        ok, problemas = rec.conferir(self.tmp() / "nao-existe")
        self.assertFalse(ok)
        self.assertTrue(problemas)

    def test_faltando_arquivo_minimo_reprova(self):
        d = self.tmp() / "MEGABRAIN"
        (d / "memoria" / "nucleo").mkdir(parents=True)
        (d / "memoria" / "nucleo" / "VERSAO.txt").write_text(
            "2026-08-25 · v7.5 — x\n", encoding="utf-8")
        ok, problemas = rec.conferir(d)
        self.assertFalse(ok)
        self.assertTrue(any("MEGABRAIN.md" in p for p in problemas))

    def test_versao_vazia_reprova(self):
        d = self.tmp() / "MEGABRAIN"
        d.mkdir(parents=True)
        (d / "VERSAO.txt").write_text("   \n", encoding="utf-8")
        (d / "MEGABRAIN.md").write_text("# x\n", encoding="utf-8")
        ok, problemas = rec.conferir(d)
        self.assertFalse(ok)
        self.assertTrue(any("vazio" in p for p in problemas))

    def test_restauracao_quase_vazia_reprova(self):
        """3.371 arquivos era o defeito antigo; 2 arquivos é o defeito oposto."""
        d = self.tmp() / "MEGABRAIN"
        d.mkdir(parents=True)
        (d / "VERSAO.txt").write_text("2026-08-25 · v7.5 — x\n", encoding="utf-8")
        (d / "MEGABRAIN.md").write_text("# x\n", encoding="utf-8")
        ok, problemas = rec.conferir(d)
        self.assertFalse(ok)
        self.assertTrue(any("incompleta" in p for p in problemas))

    def test_restauracao_boa_passa(self):
        d = self.tmp() / "MEGABRAIN"
        d.mkdir(parents=True)
        (d / "VERSAO.txt").write_text("2026-08-25 · v7.5 — x\n", encoding="utf-8")
        (d / "MEGABRAIN.md").write_text("# x\n", encoding="utf-8")
        for i in range(6):
            (d / f"arq{i}.md").write_text("conteudo\n", encoding="utf-8")
        ok, problemas = rec.conferir(d)
        self.assertTrue(ok, f"deveria passar, mas: {problemas}")


class TestFontes(Base):
    def test_outro_projeto_nao_e_mais_fonte(self):
        """A regressão que trava a cópia magra: se 'outro projeto' voltar como
        fonte, emagrecer as 19 cópias quebra a recuperação em silêncio."""
        raiz = self.tmp()
        central = self.central_falsa(raiz)
        (raiz / "projeto-a").mkdir()
        vizinho = raiz / "projeto-b" / "MEGABRAIN"
        (vizinho / "memoria" / "nucleo").mkdir(parents=True)
        (vizinho / "memoria" / "nucleo" / "VERSAO.txt").write_text(
            "2026-08-01 · v6.0 — vizinho\n", encoding="utf-8")

        fontes = rec.fontes_disponiveis(raiz / "projeto-a", central)
        caminhos = [str(c) for _, c, _ in fontes]
        self.assertFalse(any("projeto-b" in x for x in caminhos),
                         "'outro projeto' voltou a ser fonte de restauração")

    def test_central_viva_e_a_primeira(self):
        raiz = self.tmp()
        central = self.central_falsa(raiz)
        (raiz / "proj").mkdir()
        fontes = rec.fontes_disponiveis(raiz / "proj", central)
        self.assertTrue(fontes, "nenhuma fonte com central viva presente")
        self.assertEqual(fontes[0][0], "central viva")

    def test_sem_nada_nao_inventa_fonte(self):
        raiz = self.tmp()
        (raiz / "proj").mkdir()
        fontes = rec.fontes_disponiveis(raiz / "proj", raiz / "central-que-nao-existe")
        self.assertEqual(fontes, [])

    def test_ponteiro_de_origem_e_lido(self):
        raiz = self.tmp()
        central = self.central_falsa(raiz)
        proj = raiz / "proj"
        (proj / "MEGABRAIN").mkdir(parents=True)
        (proj / "MEGABRAIN" / ".mb-origem.json").write_text(
            json.dumps({"central": str(central)}), encoding="utf-8")
        self.assertEqual(rec.central_do_ponteiro(proj), central)

    def test_ponteiro_ausente_devolve_none(self):
        raiz = self.tmp()
        (raiz / "proj").mkdir()
        self.assertIsNone(rec.central_do_ponteiro(raiz / "proj"))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Testes de caminhos canônicos (mb_utils.pasta / mb_utils.achar).

É o contrato atual: a central usa memoria/ + motor/. O plano permanece
somente onde ainda existe de verdade — restaurações cheias e backups anteriores
à cópia magra. O layout v6.4 (00_nucleo/ etc.) não é mais resolvido.

Se um destes cair, algum script vai procurar arquivo no lugar errado e falhar
em silêncio, que é exatamente o risco que a condição do <USUARIO> ("não quebrar
nada") mandou blindar.
"""
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

import mb_utils as u  # noqa: E402


class Base(unittest.TestCase):
    def tmp(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)


class TestPasta(Base):
    def test_motor_ganha_quando_existe(self):
        c = self.tmp()
        (c / "motor" / "skills").mkdir(parents=True)
        self.assertEqual(u.pasta(c, "skills"), c / "motor" / "skills")

    def test_plano_vale_na_restauracao_cheia(self):
        c = self.tmp()
        (c / "skills").mkdir()
        self.assertEqual(u.pasta(c, "skills"), c / "skills")

    def test_sem_nada_aponta_pro_layout_novo(self):
        c = self.tmp()
        self.assertEqual(u.pasta(c, "skills"), c / "motor" / "skills")

    def test_pasta_humana_nao_virou_motor(self):
        c = self.tmp()
        self.assertEqual(u.pasta(c, "relatorios"), c / "00_painel")
        self.assertEqual(u.pasta(c, "cerebro"), c / "memoria" / "cerebro")


class TestAchar(Base):
    def test_arquivo_de_maquina_na_central_e_na_restauracao_cheia(self):
        novo = self.tmp()
        (novo / "motor" / "skills" / "megabrain").mkdir(parents=True)
        self.assertEqual(u.achar(novo, "skills/megabrain/SKILL.md"),
                         novo / "motor" / "skills" / "megabrain" / "SKILL.md")
        velho = self.tmp()
        (velho / "skills" / "megabrain").mkdir(parents=True)
        self.assertEqual(u.achar(velho, "skills/megabrain/SKILL.md"),
                         velho / "skills" / "megabrain" / "SKILL.md")

    def test_nome_de_pasta_sozinho(self):
        c = self.tmp()
        (c / "motor" / "dna").mkdir(parents=True)
        self.assertEqual(u.achar(c, "dna"), c / "motor" / "dna")
        self.assertEqual(u.achar(c, "referencias"), c / "motor" / "referencias")

    def test_canonicos_continuam_na_memoria(self):
        c = self.tmp()
        (c / "memoria" / "nucleo").mkdir(parents=True)
        (c / "memoria" / "estado").mkdir(parents=True)
        self.assertEqual(u.achar(c, "VERSAO.txt"), c / "memoria" / "nucleo" / "VERSAO.txt")
        self.assertEqual(u.achar(c, "HANDOFF.md"), c / "memoria" / "estado" / "HANDOFF.md")

    def test_orfao_na_raiz_nao_sombreia_canonico(self):
        """260825: um licoes-megabrain.md solto na raiz sequestrou o índice —
        8 lições no lugar de 166. Canônico de PASTAS_RAIZ tem UM lugar."""
        c = self.tmp()
        (c / "memoria" / "nucleo").mkdir(parents=True)
        (c / "memoria" / "nucleo" / "licoes-megabrain.md").write_text("real\n", encoding="utf-8")
        (c / "licoes-megabrain.md").write_text("orfao\n", encoding="utf-8")
        self.assertEqual(u.achar(c, "licoes-megabrain.md"),
                         c / "memoria" / "nucleo" / "licoes-megabrain.md")

    def test_barra_invertida_tambem_resolve(self):
        c = self.tmp()
        (c / "motor" / "modelos").mkdir(parents=True)
        self.assertEqual(u.achar(c, "modelos\\META.md"),
                         c / "motor" / "modelos" / "META.md")


class TestTabela(Base):
    def test_toda_pasta_de_maquina_esta_mapeada_pra_motor(self):
        for nome in u.PASTAS_MAQUINA:
            self.assertEqual(u.PASTAS_NUMERADAS.get(nome), f"{u.MOTOR}/{nome}",
                             f"{nome} não está apontando pra motor/ na tabela")

    def test_bin_nao_entra_no_motor(self):
        """bin/ fica na raiz: o hook dos agentes aponta pra ele por caminho
        absoluto, fora da central."""
        self.assertNotIn("bin", u.PASTAS_MAQUINA)
        self.assertNotIn("bin", u.PASTAS_NUMERADAS)


if __name__ == "__main__":
    unittest.main()

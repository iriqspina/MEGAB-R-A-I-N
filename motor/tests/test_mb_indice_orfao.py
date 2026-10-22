#!/usr/bin/env python3
"""Prova do absorvedor de lições órfãs da raiz da central (261016).

A skill registrar-licao antiga grava `licoes-megabrain.md` na raiz, fora do
índice. buscar() roda a cada prompt e chama indexar(), que absorve o órfão no
canônico `memoria/nucleo/licoes-megabrain.md`. Aqui a central é uma pasta
temporária (MEGABRAIN_CENTRAL) e o embedding fica desligado.
"""

from __future__ import annotations

import importlib.util
import os
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
_spec = importlib.util.spec_from_file_location(
    "mb_indice_teste", str(RAIZ / "bin" / "mb-indice-licoes.py"))
indice = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(indice)

NUCLEO = "## 260901 — antiga\nGATILHO: a\nLIÇÃO: b\nATALHO: c\n"


class TestAbsorverOrfao(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.central = Path(self._tmp.name)
        (self.central / "memoria" / "nucleo").mkdir(parents=True)
        self.nucleo = self.central / "memoria" / "nucleo" / "licoes-megabrain.md"
        self.nucleo.write_bytes(NUCLEO.encode("utf-8"))
        self.raiz = self.central / "licoes-megabrain.md"
        self._env = os.environ.get("MEGABRAIN_CENTRAL")
        os.environ["MEGABRAIN_CENTRAL"] = str(self.central)
        self._embed = indice.embed
        indice.embed = lambda *a, **k: None

    def tearDown(self):
        indice.embed = self._embed
        if self._env is None:
            os.environ.pop("MEGABRAIN_CENTRAL", None)
        else:
            os.environ["MEGABRAIN_CENTRAL"] = self._env
        self._tmp.cleanup()

    def test_absorve_sem_duplicar_e_arquiva(self):
        self.raiz.write_bytes(
            ("# Lições — megabrain\r\n\r\n# Tema: x\r\n\r\n" + NUCLEO
             + "\r\n## 261016 — nova\r\nGATILHO: d\r\nATALHO: e\r\n"
             ).replace("\n", "\r\n").replace("\r\r\n", "\r\n").encode("utf-8"))
        self.assertEqual(indice.absorver_orfao(), 1)
        self.assertFalse(self.raiz.exists())
        depois = self.nucleo.read_bytes()
        self.assertTrue(depois.startswith(NUCLEO.encode("utf-8")))
        self.assertNotIn(b"\r\n", depois)
        self.assertNotIn(b"# Tema", depois)
        self.assertTrue(depois.endswith(
            "\n\n## 261016 — nova\nGATILHO: d\nATALHO: e\n".encode("utf-8")))
        arquivados = list((self.central / ".mb-log" / "licoes-orfas").iterdir())
        self.assertEqual(len(arquivados), 1)
        self.assertIn(b"261016", arquivados[0].read_bytes())

    def test_segunda_rodada_nao_repete(self):
        self.raiz.write_text("## 261016 — nova\nGATILHO: d\n", encoding="utf-8")
        self.assertEqual(indice.absorver_orfao(), 1)
        self.raiz.write_text("## 261016 — nova\nGATILHO: d\n", encoding="utf-8")
        self.assertEqual(indice.absorver_orfao(), 0)
        self.assertFalse(self.raiz.exists())
        self.assertEqual(
            self.nucleo.read_text(encoding="utf-8").count("261016 — nova"), 1)

    def test_indexar_absorve_e_indexa(self):
        self.raiz.write_text("## 261016 — nova\nGATILHO: d\n", encoding="utf-8")
        idx = indice.indexar(force=True, silencioso=True)
        self.assertEqual([e["titulo"] for e in idx["entradas"]],
                         ["260901 — antiga", "261016 — nova"])

    def test_sem_orfao_nao_mexe(self):
        antes = self.nucleo.read_bytes()
        self.assertEqual(indice.absorver_orfao(), 0)
        self.assertEqual(self.nucleo.read_bytes(), antes)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Provas do mb-gravar-texto: barra invertida intacta, CRLF preservado,
caractere nulo recusado e prefixar sem duplicar (lição 261016 [3×])."""

from __future__ import annotations

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
_spec = importlib.util.spec_from_file_location(
    "mb_gravar_texto_teste", str(RAIZ / "bin" / "mb-gravar-texto.py"))
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

CAMINHO = "S:" + chr(92) + "x" + chr(92) + "00_PARA-VOCE" + chr(92) + "02_site"


class GravarTexto(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.lock = self.d / "lockroot"

    def tearDown(self):
        self._tmp.cleanup()

    def _entrada(self, dados: bytes) -> Path:
        p = self.d / "entrada.txt"
        p.write_bytes(dados)
        return p

    def _rodar(self, modo, alvo, dados, **kw):
        return g.main([modo, "--alvo", str(alvo), "--entrada",
                       str(self._entrada(dados)), "--raiz", str(self.lock),
                       *sum(([f"--{k.replace('_', '-')}", v]
                             for k, v in kw.items()), [])])

    def test_caminho_windows_chega_intacto(self):
        alvo = self.d / "ESTADO.md"
        alvo.write_bytes(b"# ESTADO\n\nlinha velha\n")
        linha = f"entrega em {CAMINHO}".encode()
        self.assertEqual(self._rodar("prefixar", alvo, linha + b"\n"), 0)
        bruto = alvo.read_bytes()
        self.assertIn(linha, bruto)
        self.assertNotIn(b"\x00", bruto)
        self.assertTrue(bruto.endswith(b"# ESTADO\n\nlinha velha\n"))
        self.assertEqual(self._rodar("anexar", alvo, b"fim " + linha), 0)
        self.assertTrue(alvo.read_bytes().endswith(b"fim " + linha + b"\n"))

    def test_crlf_continua_crlf(self):
        alvo = self.d / "HANDOFF.md"
        antigo = b"# HANDOFF\r\nSTATUS: velho\r\nfim\r\n"
        alvo.write_bytes(antigo)
        self.assertEqual(self._rodar("anexar", alvo, b"a\nb\n"), 0)
        bruto = alvo.read_bytes()
        self.assertTrue(bruto.startswith(antigo))
        self.assertEqual(bruto.count(b"\n"), bruto.count(b"\r\n"))
        self.assertEqual(self._rodar("trocar-linha", alvo, b"STATUS: novo\n",
                                     prefixo="STATUS:"), 0)
        self.assertIn(b"STATUS: novo\r\n", alvo.read_bytes())
        self.assertEqual(alvo.read_bytes().count(b"\n"),
                         alvo.read_bytes().count(b"\r\n"))

    def test_caractere_nulo_recusado(self):
        alvo = self.d / "x.md"
        alvo.write_bytes(b"velho\n")
        self.assertEqual(self._rodar("anexar", alvo, b"S:\x00_PARA\n"), 1)
        self.assertEqual(alvo.read_bytes(), b"velho\n")
        self.assertEqual(self._rodar("prefixar", alvo, b"\x08x\n"), 1)
        self.assertEqual(alvo.read_bytes(), b"velho\n")

    def test_prefixar_nao_duplica(self):
        alvo = self.d / "y.md"
        alvo.write_bytes(b"corpo\n")
        bloco = b"## 261016 - bloco\nlinha 2\n"
        self.assertEqual(self._rodar("prefixar", alvo, bloco), 0)
        depois = alvo.read_bytes()
        self.assertEqual(self._rodar("prefixar", alvo, bloco), 0)
        self.assertEqual(alvo.read_bytes(), depois)
        self.assertEqual(depois.count(b"## 261016"), 1)

    def test_trocar_linha_exige_prefixo_unico(self):
        alvo = self.d / "z.md"
        alvo.write_bytes(b"A: 1\nA: 2\n")
        self.assertEqual(self._rodar("trocar-linha", alvo, b"A: 3\n",
                                     prefixo="A:"), 1)
        self.assertEqual(alvo.read_bytes(), b"A: 1\nA: 2\n")

    def test_conferir_recusa_antigo_alterado(self):
        with self.assertRaises(g.Recusado):
            g.conferir("anexar", b"abc\n", b"abX\nnovo\n")
        with self.assertRaises(g.Recusado):
            g.conferir("prefixar", b"abc\n", b"novo\nabX\n")


if __name__ == "__main__":
    unittest.main()

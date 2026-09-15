#!/usr/bin/env python3
"""Provas da pele POP sobre esqueleto antigo (bin/mb-relatorio-reskin.py).

O que não pode quebrar: conteúdo histórico byte a byte intacto, bloco único
(rodar de novo substitui, não duplica), backup sagrado nunca tocado e paleta
com contraste mínimo 4.5:1 no pior caso (vidro sobre o pico da aurora).
"""

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
    "mb_relatorio_reskin", str(RAIZ / "bin" / "mb-relatorio-reskin.py"))
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)

VIVO = ('<!doctype html>\r\n<html lang="pt-BR" data-tema="02-wildfire"><head><style>.x{}</style>'
        '</head>\r\n<body><div class="wrap"><div class="versao">v7.5 — ação</div>'
        '<script>var s="</head>";</script></div></body></html>\r\n')
GLASS = ('<html><head><style>:root{}</style></head><body data-view="executive">'
         '<main class="report"><div class="evidence-card">x</div></main></body></html>')


class TestReskin(unittest.TestCase):
    def test_detecta_os_dois_esqueletos(self):
        self.assertEqual(rs.detectar(VIVO), "vivo-antigo")
        self.assertEqual(rs.detectar(GLASS), "glass")
        self.assertIsNone(rs.detectar("<html><head></head><body><p>x</p></body></html>"))

    def test_injeta_antes_do_head_e_preserva_conteudo(self):
        novo = rs.aplicar(VIVO, "vivo-antigo")
        self.assertLess(novo.index('id="mb-pop-skin"'), novo.index("</head>"))
        self.assertTrue(rs.integro(VIVO, novo))
        self.assertEqual(rs.sem_pele(novo), VIVO)  # CRLF e script com "</head>" intactos

    def test_idempotente_substitui_sem_duplicar(self):
        uma = rs.aplicar(VIVO, "vivo-antigo")
        duas = rs.aplicar(uma, "vivo-antigo")
        self.assertEqual(uma, duas)
        troca = rs.aplicar(uma, "glass")
        self.assertEqual(troca.count('id="mb-pop-skin"'), 1)
        self.assertIn('data-skin="glass"', troca)

    def test_processar_grava_e_segunda_rodada_fica_igual(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.html"
            p.write_bytes(VIVO.encode("utf-8"))
            self.assertEqual(rs.processar(p, None, seco=True), ("vivo-antigo", "novo"))
            self.assertEqual(p.read_bytes(), VIVO.encode("utf-8"))  # dry-run não grava
            self.assertEqual(rs.processar(p, None, seco=False), ("vivo-antigo", "novo"))
            self.assertEqual(rs.processar(p, None, seco=False), ("vivo-antigo", "igual"))

    def test_backup_sagrado_nunca_e_tocado(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "260915_0410_RELATORIO_pre-POP.html"
            p.write_bytes(VIVO.encode("utf-8"))
            skin, estado = rs.processar(p, "vivo-antigo", seco=False)
            self.assertTrue(estado.startswith("pulado"))
            self.assertEqual(p.read_bytes(), VIVO.encode("utf-8"))
        self.assertNotIn("260915_0410_RELATORIO_pre-POP.html", [a.name for a in rs.alvos_padrao()])

    def test_contraste_minimo(self):
        ruins = [l for l in rs.checar_contraste() if l[3] < 4.5]
        self.assertEqual(ruins, [])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contrato do esquema visual embutido no relatório vivo."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin"))

import mb_workspace as ws  # noqa: E402


class TestEsquemaVisual(unittest.TestCase):
    def setUp(self):
        self.html = ws.html_esquema({
            "copias": {"total": 19, "em_dia": 19},
            "suite": {"testes": 157, "verde": True},
        })

    def test_compara_antes_e_agora_com_medidas_registradas(self):
        for trecho in ("antes", "agora", "182 MB", "617 KB", "141 KB",
                       "19/19 cópias em dia", "157 testes · suíte verde"):
            self.assertIn(trecho, self.html)

    def test_mapa_separa_memoria_maquina_leitores_e_distribuicao(self):
        for trecho in ("memoria\\", "motor\\ + bin\\", "dados/estado.json",
                       "00_painel/RELATORIO.html", ".mb-origem.json",
                       "GitHub público", "nunca sai do PC"):
            self.assertIn(trecho, self.html)

    def test_fluxo_tem_cinco_passos_em_ordem(self):
        passos = re.findall(r'class="esq-step__n">(\d+)</span>', self.html)
        self.assertEqual(passos, ["01", "02", "03", "04", "05"])

    def test_ids_do_esquema_sao_unicos(self):
        ids = re.findall(r'\bid="([^"]+)"', self.html)
        self.assertEqual(len(ids), len(set(ids)))

    def test_css_tem_refluxo_para_tela_pequena(self):
        self.assertIn("@media (max-width:800px)", ws.CSS)
        self.assertIn(".esq-compare { grid-template-columns:1fr; }", ws.CSS)
        self.assertIn(".esq-flow { grid-template-columns:1fr;", ws.CSS)
        self.assertIn("@media (max-width:640px) { .rail { display:none; } }", ws.CSS)

    def test_aba_esquema_pode_ser_aberta_por_hash(self):
        js = ws.js_workspace()
        self.assertIn("location.hash", js)
        for ident, _rotulo in ws.ABAS:
            self.assertIn(f'"{ident}"', js)
        self.assertIn("history.replaceState", js)

    def test_sem_estado_degrada_sem_inventar_zero(self):
        html = ws.html_esquema()
        self.assertIn("— cópias em dia", html)
        self.assertIn("— testes · suíte sem medição", html)


if __name__ == "__main__":
    unittest.main()

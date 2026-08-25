#!/usr/bin/env python3
"""Testes do reviewer de acceptance criteria (bin/mb-review-criteria.py).

Protegem: extração de critérios de SPEC.md e META.md, heurística de
evidence no diff, e formatação do parecer.
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

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("mb_review_criteria", str(RAIZ / "bin" / "mb-review-criteria.py"))
rev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rev)


class TestExtracao(unittest.TestCase):
    def test_extrai_criterios_de_spec(self):
        texto = "## Acceptance Criteria\n- [ ] testes passam\n- [ ] docs atualizadas\n"
        self.assertEqual(rev._extrair_criterios_spec(texto), ["testes passam", "docs atualizadas"])

    def test_ignora_comentarios_na_spec(self):
        texto = "## Acceptance Criteria\n<!-- comentário -->\n- [ ] item real\n"
        self.assertEqual(rev._extrair_criterios_spec(texto), ["item real"])

    def test_ignora_placeholders(self):
        texto = "## Acceptance Criteria\n- [ ] <critério 1 — placeholder>\n- [ ] real\n"
        self.assertEqual(rev._extrair_criterios_spec(texto), ["real"])

    def test_extrai_criterio_de_pronto_do_meta(self):
        texto = "CRITÉRIO DE PRONTO: A; B; C\nPRÓXIMO PASSO: D\n"
        self.assertEqual(rev._extrair_criterios_meta(texto), ["A", "B", "C"])


class TestEvidencia(unittest.TestCase):
    def test_evidencia_por_palavra_no_diff(self):
        ok, motivo = rev._evidencia("testes passam", "python -m unittest\ntests passam", [])
        self.assertTrue(ok)
        self.assertIn("diff", motivo.lower())

    def test_evidencia_por_nome_de_arquivo(self):
        ok, motivo = rev._evidencia("arquivo fila.json", "outra coisa", [Path("dados/fila.json")])
        self.assertTrue(ok)
        self.assertIn("fila.json", motivo)

    def test_sem_evidencia(self):
        ok, motivo = rev._evidencia("deploy em produção", "nada relacionado", [Path("x.py")])
        self.assertFalse(ok)


class TestRevisar(unittest.TestCase):
    def test_aprovado_quando_todos_atendem(self):
        r = rev.revisar(Path("."), ["testes passam"], "testes passam", [])
        self.assertEqual(r["veredito"], "APROVADO")
        self.assertEqual(r["aprovados"], 1)

    def test_reprovado_quando_falta_um(self):
        r = rev.revisar(Path("."), ["testes passam", "deploy"], "testes passam", [])
        self.assertEqual(r["veredito"], "REPROVADO")
        self.assertEqual(r["aprovados"], 1)
        self.assertEqual(r["reprovados"], 1)


if __name__ == "__main__":
    unittest.main()

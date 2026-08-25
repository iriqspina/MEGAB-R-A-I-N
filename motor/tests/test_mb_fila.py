#!/usr/bin/env python3
"""Testes do board local de tasks (bin/mb-fila.py — djinnai.io mecânica 2).

Protegem: cálculo de ondas, detecção de ciclos, respeito a dependências
para tarefas "prontas", e a CLI de avanço de estado.
"""
import json
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
_spec = importlib.util.spec_from_file_location("mb_fila", str(RAIZ / "bin" / "mb-fila.py"))
fila = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fila)


class Base(unittest.TestCase):
    def tmpdir(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)

    def _dados(self, tasks: list) -> dict:
        return {"schema": 1, "tasks": tasks}


class TestOndas(Base):
    def test_sem_dependencias_todos_onda_zero(self):
        dados = self._dados([
            {"id": "a", "blocked_by": [], "estado": "todo"},
            {"id": "b", "blocked_by": [], "estado": "todo"},
        ])
        self.assertEqual(fila.calcular_ondas(dados["tasks"]), {"a": 0, "b": 0})

    def test_cadeia_aumenta_onda(self):
        dados = self._dados([
            {"id": "a", "blocked_by": [], "estado": "todo"},
            {"id": "b", "blocked_by": ["a"], "estado": "todo"},
            {"id": "c", "blocked_by": ["b"], "estado": "todo"},
        ])
        self.assertEqual(fila.calcular_ondas(dados["tasks"]), {"a": 0, "b": 1, "c": 2})

    def test_dois_pais_na_mesma_onda(self):
        dados = self._dados([
            {"id": "a", "blocked_by": [], "estado": "todo"},
            {"id": "b", "blocked_by": [], "estado": "todo"},
            {"id": "c", "blocked_by": ["a", "b"], "estado": "todo"},
        ])
        self.assertEqual(fila.calcular_ondas(dados["tasks"]), {"a": 0, "b": 0, "c": 1})

    def test_ciclo_levanta_excecao(self):
        dados = self._dados([
            {"id": "a", "blocked_by": ["c"], "estado": "todo"},
            {"id": "b", "blocked_by": ["a"], "estado": "todo"},
            {"id": "c", "blocked_by": ["b"], "estado": "todo"},
        ])
        with self.assertRaises(ValueError) as ctx:
            fila.calcular_ondas(dados["tasks"])
        self.assertIn("ciclo", str(ctx.exception).lower())

    def test_dependencia_desconhecida_levanta_excecao(self):
        dados = self._dados([
            {"id": "a", "blocked_by": ["x"], "estado": "todo"},
        ])
        with self.assertRaises(ValueError):
            fila.calcular_ondas(dados["tasks"])


class TestResumo(Base):
    def test_prontas_respeitam_estado_feito(self):
        dados = self._dados([
            {"id": "a", "titulo": "A", "blocked_by": [], "estado": "feito", "prioridade": 1},
            {"id": "b", "titulo": "B", "blocked_by": ["a"], "estado": "todo", "prioridade": 1},
        ])
        r = fila.resumo(dados)
        self.assertEqual(r["prontas"], 1)
        self.assertEqual([p["id"] for p in r["proximas"]], ["b"])

    def test_bloqueadas_nao_aparecem_em_prontas(self):
        dados = self._dados([
            {"id": "a", "titulo": "A", "blocked_by": [], "estado": "todo", "prioridade": 1},
            {"id": "b", "titulo": "B", "blocked_by": ["a"], "estado": "todo", "prioridade": 1},
        ])
        r = fila.resumo(dados)
        self.assertEqual(r["prontas"], 1)
        self.assertEqual(r["bloqueadas"], 1)
        self.assertEqual([p["id"] for p in r["proximas"]], ["a"])

    def test_resumo_detecta_ciclo(self):
        dados = self._dados([
            {"id": "a", "blocked_by": ["b"], "estado": "todo"},
            {"id": "b", "blocked_by": ["a"], "estado": "todo"},
        ])
        r = fila.resumo(dados)
        self.assertIsNotNone(r["erro"])


class TestCLI(Base):
    def _escreve(self, raiz: Path, tasks: list) -> Path:
        (raiz / "dados").mkdir(parents=True, exist_ok=True)
        caminho = raiz / "dados" / "fila.json"
        caminho.write_text(json.dumps({"schema": 1, "tasks": tasks}, ensure_ascii=False), encoding="utf-8")
        return caminho

    def test_avancar_salva_estado(self):
        raiz = self.tmpdir()
        self._escreve(raiz, [{"id": "a", "blocked_by": [], "estado": "todo", "prioridade": 1}])
        dados = fila._carregar(raiz / "dados" / "fila.json")
        fila.cmd_avancar(dados, "a")
        self.assertEqual(dados["tasks"][0]["estado"], "feito")

    def test_avancar_task_inexistente_levanta(self):
        dados = self._dados([{"id": "a", "blocked_by": [], "estado": "todo"}])
        with self.assertRaises(ValueError):
            fila.cmd_avancar(dados, "x")


if __name__ == "__main__":
    unittest.main()

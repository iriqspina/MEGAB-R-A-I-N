#!/usr/bin/env python3
"""Provas do hook de contexto: achar o projeto onde ele realmente está.

Item 4.2 da auditoria de 260825: no worktree do Traycer
(~/.traycer/worktrees/...) o hook dizia "este projeto ainda não tem META.md"
com o `memoria/estado/META.md` rastreado dentro do worktree — achar_projeto só
reconhecia projeto descendo de projetos_root. Os testes fixam os dois lados:
worktree com marcador é projeto (e o META entra no contexto); pasta sem
marcador segue não sendo.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
import uuid
import tempfile
from pathlib import Path
from unittest import mock


def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb_utils.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
sys.path.insert(0, str(RAIZ / "bin"))

_spec = importlib.util.spec_from_file_location(
    "mb_contexto", str(RAIZ / "bin" / "mb-contexto.py"))
contexto = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contexto)


class Base(unittest.TestCase):
    def tmpdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def ambiente(self) -> tuple[Path, Path]:
        """(central fake, raiz de projetos fake) já exportados no ambiente."""
        central = self.tmpdir()
        (central / "memoria/estado").mkdir(parents=True)
        raiz_projetos = self.tmpdir()
        patch = mock.patch.dict(os.environ, {
            "MEGABRAIN_CENTRAL": str(central),
            "MEGABRAIN_PROJETOS_ROOT": str(raiz_projetos),
        })
        patch.start()
        self.addCleanup(patch.stop)
        return central, raiz_projetos

    def worktree(self) -> Path:
        """Checkout fora da raiz de projetos, layout v7.x com META rastreado."""
        wt = self.tmpdir()
        meta = wt / "memoria/estado/META.md"
        meta.parent.mkdir(parents=True)
        meta.write_text("# META — teste\n\nMODO: otimizado\n\nOBJETIVO: x\n",
                        encoding="utf-8")
        (wt / "motor/skills").mkdir(parents=True)
        return wt


class TestAcharProjeto(Base):
    def test_projeto_sob_a_raiz_resolve_o_topo(self):
        _, raiz_projetos = self.ambiente()
        fundo = raiz_projetos / "projeto-x/sub/mais-fundo"
        fundo.mkdir(parents=True)
        self.assertEqual(contexto.achar_projeto(str(fundo)),
                         raiz_projetos / "projeto-x")

    def test_worktree_fora_da_raiz_acha_pelo_meta(self):
        self.ambiente()
        wt = self.worktree()
        self.assertEqual(contexto.achar_projeto(str(wt / "motor/skills")), wt)

    def test_pasta_sem_marcador_nao_e_projeto(self):
        self.ambiente()
        avulsa = self.tmpdir() / "qualquer/coisa"
        avulsa.mkdir(parents=True)
        self.assertIsNone(contexto.achar_projeto(str(avulsa)))


class TestMontar(Base):
    def montar(self, cwd: Path) -> str:
        return contexto.montar(
            {"prompt": "", "cwd": str(cwd),
             "session_id": f"teste-{uuid.uuid4().hex[:12]}"}, "claude")

    def test_worktree_com_meta_injeta_meta_e_nao_manda_criar(self):
        self.ambiente()
        bloco = self.montar(self.worktree())
        self.assertIn("META do projeto", bloco)
        self.assertNotIn("ainda não tem META.md", bloco)

    def test_projeto_sem_meta_continua_instruindo_a_criar(self):
        self.ambiente()
        wt = self.tmpdir()
        (wt / "MEGABRAIN").mkdir()
        bloco = self.montar(wt)
        self.assertIn("ainda não tem META.md", bloco)


if __name__ == "__main__":
    unittest.main()

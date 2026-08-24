"""
test_mb_sync.py — prova que a trava de handoff realmente trava.

Roda sozinho:      python tests/test_mb_sync.py
Roda na suíte:     python -m unittest discover tests
Roda com pytest:   pytest tests/

A trava e a unica garantia do protocolo (regra de ouro 21: garantia real e
script, nao markdown). O corolario: script sem teste e markdown com extensao
.py. Estes casos cobrem o contrato que o SKILL.md promete no Gate 0.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# v7.1: a suíte pode viver plana (tests/) ou dentro de motor/ (etapa 2 da
# reorg). Achar a raiz subindo até bin/mb_utils.py vale nos dois casos.
def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb_utils.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
MB_SYNC = RAIZ / "bin" / "mb-sync.py"


def rodar(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MB_SYNC), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd) if cwd else None,
    )


class TestMbSync(unittest.TestCase):
    def novo_projeto(self) -> Path:
        p = Path(tempfile.mkdtemp(prefix="mb-teste-"))
        self.addCleanup(shutil.rmtree, p, ignore_errors=True)
        return p

    def test_projeto_sem_handoff_esta_livre(self):
        p = self.novo_projeto()
        r = rodar("--dir", str(p), "status")
        self.assertEqual(r.returncode, 0, f"projeto novo devia estar livre: {r.stdout}{r.stderr}")

    def test_lock_grava_e_status_acusa_travado(self):
        p = self.novo_projeto()
        r = rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", "src/", "--horas", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((p / "HANDOFF.md").exists(), "lock nao criou HANDOFF.md")

        texto = (p / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("TRAVADO_POR: claude", texto)
        self.assertNotIn("<USUARIO>", texto, "placeholder literal vazou para o HANDOFF")

        r = rodar("--dir", str(p), "status")
        self.assertEqual(r.returncode, 1, "status devia sair 1 quando travado")

    def test_release_alheio_e_recusado(self):
        p = self.novo_projeto()
        rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", "--horas", "2")
        r = rodar("--dir", str(p), "release", "--agente", "kimi")
        self.assertNotEqual(r.returncode, 0, "kimi nao pode liberar trava do claude")
        self.assertIn("TRAVADO_POR: claude", (p / "HANDOFF.md").read_text(encoding="utf-8"))

    def test_release_proprio_libera(self):
        p = self.novo_projeto()
        rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", "--horas", "2")
        r = rodar("--dir", str(p), "release", "--agente", "claude")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rodar("--dir", str(p), "status").returncode, 0, "devia estar livre apos release")

    def test_force_libera_trava_alheia(self):
        p = self.novo_projeto()
        rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", "--horas", "2")
        r = rodar("--dir", str(p), "release", "--agente", "kimi", "--force")
        self.assertEqual(r.returncode, 0, f"--force devia liberar: {r.stderr}")

    def test_dir_fora_do_cwd_funciona(self):
        """Regressao v4.9: --dir fora do diretorio atual era recusado.

        O comando documentado roda o script pelo caminho absoluto da central,
        apontando --dir para um projeto que vive em outro lugar do disco.
        """
        p = self.novo_projeto()
        r = rodar("--dir", str(p), "lock", "--agente", "claude", "--escopo", ".", cwd=RAIZ)
        self.assertEqual(r.returncode, 0, f"--dir externo devia funcionar: {r.stderr}")

    def test_dir_inexistente_falha_claro(self):
        r = rodar("--dir", "/caminho/que/nao/existe/mb", "status")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nao encontrada", (r.stderr + r.stdout).lower())


if __name__ == "__main__":
    unittest.main()

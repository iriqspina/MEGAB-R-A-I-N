#!/usr/bin/env python3
"""Testes do sign-off de specs (bin/mb-spec-signoff.py — djinnai.io mecânica 1).

Protegem: extração de sign-offs, detecção de obsolescência por histórico do
git, adição de sign-off e formatação do status.
"""
import subprocess
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
_spec = importlib.util.spec_from_file_location("mb_spec_signoff", str(RAIZ / "bin" / "mb-spec-signoff.py"))
sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sig)


TEXTO_COM_SIGNOFF = """# SPEC — x

## Acceptance Criteria
- [ ] a

## Sign-offs

| Quem | Quando | Commit | Estado |
|------|--------|--------|--------|
| Ana  | 260825 10:00 | abc1234 | ok |
| Bob  | 260825 11:00 | def5678 | ok |

## Notas
x
"""

TEXTO_SEM_SIGNOFF = """# SPEC — x

## Acceptance Criteria
- [ ] a

## Notas
x
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, msg: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


class TestExtracao(unittest.TestCase):
    def test_extrai_todos_os_signoffs(self):
        signoffs = sig._extrair_signoffs(TEXTO_COM_SIGNOFF)
        self.assertEqual(len(signoffs), 2)
        self.assertEqual(signoffs[0]["quem"], "Ana")
        self.assertEqual(signoffs[1]["commit"], "def5678")

    def test_ultimo_signoff(self):
        signoffs = sig._extrair_signoffs(TEXTO_COM_SIGNOFF)
        ultimo = sig._ultimo_signoff(signoffs)
        self.assertEqual(ultimo["quem"], "Bob")

    def test_sem_signoff(self):
        self.assertEqual(sig._extrair_signoffs(TEXTO_SEM_SIGNOFF), [])
        self.assertIsNone(sig._ultimo_signoff([]))


class TestDescoberta(unittest.TestCase):
    def test_modelo_de_spec_nao_entra_no_tracker(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init", "--quiet")
            _git(repo, "config", "user.email", "test@x")
            _git(repo, "config", "user.name", "Test")
            modelo = repo / "motor/modelos/SPEC.md"
            real = repo / "projeto/SPEC.md"
            for p in (modelo, real):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
            _commit(repo, "specs")
            encontrados = sig._encontrar_specs(repo)
            self.assertEqual(encontrados, [real])


class TestEstado(unittest.TestCase):
    def tmpdir(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)

    def _repo(self) -> Path:
        repo = self.tmpdir()
        _git(repo, "init", "--quiet")
        _git(repo, "config", "user.email", "test@x")
        _git(repo, "config", "user.name", "Test")
        return repo

    def test_signoff_cobre_versao_atual(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
        h = _commit(repo, "spec inicial")
        estado = sig._estado_signoff(repo, spec, {"commit": h, "quem": "x", "quando": "y"})
        self.assertEqual(estado["estado"], "ok")
        self.assertFalse(estado["obsoleto"])

    def test_signoff_fica_obsoleto_apos_modificacao(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
        h = _commit(repo, "spec inicial")
        spec.write_text(TEXTO_SEM_SIGNOFF.replace("x\n", "y\n"), encoding="utf-8")
        _commit(repo, "spec alterada")
        estado = sig._estado_signoff(repo, spec, {"commit": h, "quem": "x", "quando": "y"})
        self.assertEqual(estado["estado"], "obsoleto")
        self.assertTrue(estado["obsoleto"])

    def test_sem_signoff_e_obsoleto(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
        _commit(repo, "spec inicial")
        estado = sig._estado_signoff(repo, spec, None)
        self.assertEqual(estado["estado"], "sem_signoff")
        self.assertTrue(estado["obsoleto"])

    def test_arquivo_nao_rastreado_e_desconhecido(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
        # sem commit
        estado = sig._estado_signoff(repo, spec, {"commit": "abc", "quem": "x", "quando": "y"})
        self.assertEqual(estado["estado"], "desconhecido")

    def test_commit_inexistente_e_invalido(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
        _commit(repo, "base")
        estado = sig._estado_signoff(repo, spec, {"commit": "abc1234", "quem": "x", "quando": "y"})
        self.assertEqual(estado["estado"], "sem_commit")
        self.assertTrue(estado["obsoleto"])


class TestAssinar(unittest.TestCase):
    def tmpdir(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)

    def _repo(self) -> Path:
        repo = self.tmpdir()
        _git(repo, "init", "--quiet")
        _git(repo, "config", "user.email", "test@x")
        _git(repo, "config", "user.name", "Test")
        return repo

    def test_assinar_cria_secao(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_SEM_SIGNOFF, encoding="utf-8")
        _commit(repo, "base")
        sig._adicionar_signoff(repo, spec, "<USUARIO>")
        texto = spec.read_text(encoding="utf-8")
        self.assertIn("## Sign-offs", texto)
        self.assertIn("| <USUARIO> |", texto)

    def test_assinar_insere_linha_em_secao_existente(self):
        repo = self._repo()
        spec = repo / "SPEC.md"
        spec.write_text(TEXTO_COM_SIGNOFF, encoding="utf-8")
        _commit(repo, "base")
        sig._adicionar_signoff(repo, spec, "Carlos", notas="revisão")
        signoffs = sig._extrair_signoffs(spec.read_text(encoding="utf-8"))
        self.assertEqual(len(signoffs), 3)
        self.assertEqual(signoffs[-1]["quem"], "Carlos")


class TestFormatar(unittest.TestCase):
    def test_formatacao_marca_obsoleto(self):
        specs = [{
            "caminho": "SPEC.md",
            "estado": "obsoleto",
            "ultimo_signoff": {"quem": "Ana", "quando": "260825", "commit": "abc"},
            "motivo": "3 commits tocaram o arquivo",
        }]
        saida = sig._formatar_status(specs)
        self.assertIn("obsoleto", saida)
        self.assertIn("Ana", saida)


if __name__ == "__main__":
    unittest.main()

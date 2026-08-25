from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin"))


def carregar(arquivo: str):
    spec = importlib.util.spec_from_file_location(
        arquivo.replace("-", "_"), RAIZ / "bin" / f"{arquivo}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


frescor = carregar("mb_frescor")
preflight = carregar("mb-preflight")
estado_mod = carregar("mb-estado")


class Base(unittest.TestCase):
    def tmpdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def git(self, repo: Path, *args: str) -> str:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                           text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def fontes(self, repo: Path, sufixo: str = "v1") -> None:
        for nome in frescor.FONTES_ESTADO:
            p = repo / nome
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"{nome} {sufixo}\n", encoding="utf-8")

    def gravar_derivados(self, repo: Path) -> dict:
        fp = frescor.calcular(repo, "worktree")
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, check=False)
        head = r.stdout.strip() if r.returncode == 0 else None
        origem = {
            "git_head": head,
            "fontes": fp["fontes"],
            "fingerprint": {"algoritmo": fp["algoritmo"], "valor": fp["valor"]},
        }
        (repo / "dados").mkdir(exist_ok=True)
        (repo / "00_painel").mkdir(exist_ok=True)
        (repo / "dados/estado.json").write_text(json.dumps({
            "schema": 3, "gerado_de": origem,
        }), encoding="utf-8")
        (repo / "00_painel/RELATORIO.html").write_text(
            "<!doctype html>\n" + frescor.bloco_html(origem) + "\n",
            encoding="utf-8")
        return origem

    def repo_inicial(self) -> Path:
        repo = self.tmpdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.name", "Teste")
        self.git(repo, "config", "user.email", "teste@example.invalid")
        self.git(repo, "config", "core.autocrlf", "false")
        (repo / ".gitignore").write_text("dados/\n", encoding="utf-8")
        self.fontes(repo)
        self.gravar_derivados(repo)
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-qm", "base")
        self.gravar_derivados(repo)
        return repo


class TestFingerprint(Base):
    def test_normaliza_crlf_sem_ignorar_conteudo(self):
        a, b = self.tmpdir(), self.tmpdir()
        self.fontes(a)
        self.fontes(b)
        (a / "META.md").write_bytes(b"linha 1\r\nlinha 2\r\n")
        (b / "META.md").write_bytes(b"linha 1\nlinha 2\n")
        self.assertEqual(frescor.calcular(a)["valor"], frescor.calcular(b)["valor"])
        (b / "META.md").write_bytes(b"linha 1\nlinha X\n")
        self.assertNotEqual(frescor.calcular(a)["valor"], frescor.calcular(b)["valor"])

    def test_json_nao_vazio_e_lido(self):
        p = self.tmpdir() / "estado.json"
        p.write_text('{"etapas":[1]}', encoding="utf-8")
        self.assertEqual(estado_mod._json(p), {"etapas": [1]})

    def test_metadado_html_faz_roundtrip(self):
        repo = self.tmpdir()
        self.fontes(repo)
        fp = frescor.calcular(repo)
        origem = {"fontes": fp["fontes"], "fingerprint": fp}
        dados, erro = frescor.extrair_html(frescor.bloco_html(origem).encode("utf-8"))
        self.assertIsNone(erro)
        self.assertEqual(dados["valor"], fp["valor"])


class TestVisoesGit(Base):
    def test_precommit_le_indice_e_ignora_mudanca_unstaged(self):
        repo = self.repo_inicial()
        (repo / "META.md").write_text("META.md staged\n", encoding="utf-8")
        self.gravar_derivados(repo)
        self.git(repo, "add", "META.md", "00_painel/RELATORIO.html")
        (repo / "META.md").write_text("META.md unstaged\n", encoding="utf-8")

        ok_staged, txt_staged = preflight.cheque_estado(repo, "staged")
        ok_worktree, _ = preflight.cheque_estado(repo, "worktree")
        self.assertTrue(ok_staged, txt_staged)
        self.assertFalse(ok_worktree)

    def test_precommit_reprova_relatorio_nao_staged(self):
        repo = self.repo_inicial()
        (repo / "META.md").write_text("META.md staged\n", encoding="utf-8")
        self.gravar_derivados(repo)
        self.git(repo, "add", "META.md")
        ok, txt = preflight.cheque_estado(repo, "staged")
        self.assertFalse(ok)
        self.assertIn("fingerprint do relatório", txt)

    def test_postcommit_le_head_sem_gerar_diff_rastreado(self):
        repo = self.repo_inicial()
        (repo / "META.md").write_text("META.md v2\n", encoding="utf-8")
        self.gravar_derivados(repo)
        self.git(repo, "add", "META.md", "00_painel/RELATORIO.html")
        self.git(repo, "commit", "-qm", "v2")
        self.gravar_derivados(repo)

        (repo / "META.md").write_text("META.md unstaged depois\n", encoding="utf-8")
        antes = self.git(repo, "status", "--porcelain")
        ok_head, txt_head = preflight.cheque_estado(repo, "head")
        ok_worktree, _ = preflight.cheque_estado(repo, "worktree")
        depois = self.git(repo, "status", "--porcelain")

        self.assertTrue(ok_head, txt_head)
        self.assertFalse(ok_worktree)
        self.assertEqual(antes, depois)


if __name__ == "__main__":
    unittest.main()

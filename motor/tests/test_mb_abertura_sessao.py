#!/usr/bin/env python3
"""Testes da abertura de sessão (mb-abertura-sessao.py e 00_abrir-sessao.cmd).

POR QUE ESTE ARQUIVO EXISTE
----------------------------
A abertura roda em toda sessão nova, mexe com git (fetch/pull) e decide se
sincroniza central → projeto. A garantia que mais importa aqui não é "faz a
coisa certa" — é "nunca faz a coisa proibida": nunca commit, nunca push,
`--seco` nunca grava nada em disco. Isso não pode depender de revisão manual
a cada mudança no script; tem que estar travado em teste.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb_utils.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
SCRIPT = RAIZ / "bin" / "mb-abertura-sessao.py"
CMD = RAIZ / "01_acoes" / "00_abrir-sessao.cmd"
FONTE = SCRIPT.read_text(encoding="utf-8")

# O script faz `import mb_utils` — precisa achar o módulo no sys.path antes
# do exec_module, tanto aqui (import direto) quanto no subprocess (que herda
# o path do interpretador a partir da pasta do próprio script).
sys.path.insert(0, str(RAIZ / "bin"))

_SPEC = importlib.util.spec_from_file_location("mb_abertura_sessao", SCRIPT)
MODULO = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MODULO
_SPEC.loader.exec_module(MODULO)


class Base(unittest.TestCase):
    def tmp(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)


# ---------------------------------------------------------------------------
# (a) o script existe; --seco nunca grava nada
# ---------------------------------------------------------------------------

class TestSecoNaoGrava(Base):
    def _rodar(self, projeto: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["MEGABRAIN_CENTRAL"] = str(RAIZ)
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT),
             "--seco", "--offline", "--projeto", str(projeto)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, env=env, timeout=120, check=False,
        )

    @staticmethod
    def _confere_retrato(stdout: str) -> None:
        for token in ("TL;DR", "abertura MEGABRAIN", "[seco]"):
            assert token in stdout, f"faltou {token!r} em: {stdout}"
        for prefixo in ("1. versão:", "2. sync:", "3. git central:",
                        "4. git projeto:", "5. trava"):
            assert prefixo in stdout, f"faltou {prefixo!r} em: {stdout}"

    def test_script_existe(self):
        self.assertTrue(SCRIPT.is_file(), SCRIPT)

    def test_seco_offline_tmpdir_vazio_fica_vazio(self):
        projeto = self.tmp()
        self.assertEqual(list(projeto.iterdir()), [])
        r = self._rodar(projeto)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self._confere_retrato(r.stdout)
        self.assertEqual(list(projeto.iterdir()), [],
                          "--seco gravou algo no tmpdir vazio")

    def test_seco_offline_projeto_megabrain_nao_cria_mb_log(self):
        """tmpdir com `.mb-origem.json` vira projeto (e_projeto) — mesmo assim
        --seco não pode criar `.mb-log/sessao.jsonl`."""
        projeto = self.tmp()
        (projeto / ".mb-origem.json").write_text("{}", encoding="utf-8")
        r = self._rodar(projeto)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self._confere_retrato(r.stdout)
        self.assertFalse((projeto / ".mb-log").exists(),
                          "--seco criou .mb-log/ — devia só dizer o que faria")

    def test_central_invalida_via_env_retorna_1(self):
        central_falsa = self.tmp()
        projeto = self.tmp()
        env = dict(os.environ)
        env["MEGABRAIN_CENTRAL"] = str(central_falsa)
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT),
             "--seco", "--offline", "--projeto", str(projeto)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, env=env, timeout=120, check=False,
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_projeto_inexistente_retorna_1(self):
        env = dict(os.environ)
        env["MEGABRAIN_CENTRAL"] = str(RAIZ)
        alvo = self.tmp() / "nao-existe"
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT),
             "--seco", "--offline", "--projeto", str(alvo)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, env=env, timeout=120, check=False,
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# (b) nunca commit/push
# ---------------------------------------------------------------------------

class TestNuncaCommitOuPush(unittest.TestCase):
    PROIBIDOS = {"commit", "push", "add", "reset", "checkout", "stash", "clean",
                 "rebase", "merge", "rm", "tag", "restore", "switch",
                 "cherry-pick", "revert", "am", "apply", "config", "init",
                 "clone", "gc", "prune", "update-ref", "branch"}

    def test_nenhuma_constante_e_verbo_proibido(self):
        arvore = ast.parse(FONTE, filename=str(SCRIPT))
        achados = [(n.lineno, n.value) for n in ast.walk(arvore)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and n.value in self.PROIBIDOS]
        self.assertEqual(achados, [], f"verbo git proibido como constante: {achados}")

    def test_fonte_sem_git_commit_ou_git_push_literal(self):
        self.assertNotIn("git commit", FONTE)
        self.assertNotIn("git push", FONTE)

    def test_git_verbos_e_subconjunto_do_permitido(self):
        permitido = {"rev-parse", "remote", "status", "rev-list", "fetch", "pull"}
        self.assertLessEqual(set(MODULO.GIT_VERBOS), permitido)

    def test_git_recusa_commit(self):
        with self.assertRaises(ValueError):
            MODULO._git(RAIZ, "commit")

    def test_git_recusa_push(self):
        with self.assertRaises(ValueError):
            MODULO._git(RAIZ, "push")

    def test_git_recusa_pull_sem_ff_only(self):
        with self.assertRaises(ValueError):
            MODULO._git(RAIZ, "pull")

    def test_apenas_uma_chamada_subprocess_com_git_literal(self):
        """Só `_git()` pode falar com o executável git — uma segunda chamada
        seria um segundo ponto sem a guarda de verbo."""
        arvore = ast.parse(FONTE, filename=str(SCRIPT))
        n_git = sum(1 for n in ast.walk(arvore)
                    if isinstance(n, ast.Constant) and n.value == "git")
        self.assertEqual(n_git, 1, 'esperava 1 literal "git" no fonte (dentro de _git)')


# ---------------------------------------------------------------------------
# (c) .cmd em CRLF, com a exceção citada no cabeçalho
# ---------------------------------------------------------------------------

class TestCmdCRLF(unittest.TestCase):
    def setUp(self):
        # Lição 260825: 01_acoes/ não vai pro pacote público. Sem a PASTA, pula
        # (instância sem essa camada); com a pasta e sem o arquivo, falha.
        if not CMD.parent.is_dir():
            self.skipTest("instância sem 01_acoes (pacote público)")

    def test_cmd_wrapper_existe(self):
        self.assertTrue(CMD.is_file(), CMD)

    def test_todo_lf_precedido_de_cr(self):
        bruto = CMD.read_bytes()
        for i, byte in enumerate(bruto):
            if byte == 0x0A:  # \n
                self.assertGreater(i, 0, "arquivo começa com \\n solto")
                self.assertEqual(bruto[i - 1], 0x0D,
                                  f"\\n sem \\r antes dele, offset {i}")

    def test_cabecalho_cita_a_excecao_ao_registro(self):
        texto = CMD.read_bytes().decode("utf-8", errors="replace")
        self.assertIn("EXCECAO", texto)
        self.assertIn("mb_registro", texto)


# ---------------------------------------------------------------------------
# extras: _buscar_e_avancar isolado (sem rede, _git mockado)
# ---------------------------------------------------------------------------

class TestBuscarEAvancar(unittest.TestCase):
    @staticmethod
    def _fake(respostas: dict, chamadas: list):
        def fake(repo, *args, timeout=None):
            chamadas.append(args)
            return respostas.get(args[0], (1, "verbo inesperado no fake"))
        return fake

    def test_fetch_falha_vira_aviso(self):
        chamadas: list = []
        with mock.patch.object(MODULO, "_git",
                                side_effect=self._fake({"fetch": (1, "sem rede")}, chamadas)):
            estado, texto = MODULO._buscar_e_avancar(Path("."))
        self.assertEqual(estado, "aviso")
        self.assertIn("sem rede", texto)

    def test_sem_upstream_e_ok_e_nao_chama_pull(self):
        chamadas: list = []
        respostas = {"fetch": (0, ""), "rev-parse": (1, "")}
        with mock.patch.object(MODULO, "_git", side_effect=self._fake(respostas, chamadas)):
            estado, _ = MODULO._buscar_e_avancar(Path("."))
        self.assertEqual(estado, "ok")
        self.assertNotIn("pull", [c[0] for c in chamadas])

    def test_so_atras_chama_pull_ff_only(self):
        chamadas: list = []
        respostas = {"fetch": (0, ""), "rev-parse": (0, "origin/main"),
                     "rev-list": (0, "0\t3"), "pull": (0, "")}
        with mock.patch.object(MODULO, "_git", side_effect=self._fake(respostas, chamadas)):
            estado, texto = MODULO._buscar_e_avancar(Path("."))
        self.assertEqual(estado, "ok")
        pulls = [c for c in chamadas if c[0] == "pull"]
        self.assertEqual(len(pulls), 1, texto)
        self.assertIn("--ff-only", pulls[0])

    def test_divergiu_e_aviso_e_nunca_chama_pull(self):
        chamadas: list = []
        respostas = {"fetch": (0, ""), "rev-parse": (0, "origin/main"),
                     "rev-list": (0, "2\t3")}
        with mock.patch.object(MODULO, "_git", side_effect=self._fake(respostas, chamadas)):
            estado, texto = MODULO._buscar_e_avancar(Path("."))
        self.assertEqual(estado, "aviso", texto)
        self.assertNotIn("pull", [c[0] for c in chamadas])

    def test_so_a_frente_e_ok_sem_pull(self):
        chamadas: list = []
        respostas = {"fetch": (0, ""), "rev-parse": (0, "origin/main"),
                     "rev-list": (0, "2\t0")}
        with mock.patch.object(MODULO, "_git", side_effect=self._fake(respostas, chamadas)):
            estado, texto = MODULO._buscar_e_avancar(Path("."))
        self.assertEqual(estado, "ok", texto)
        self.assertNotIn("pull", [c[0] for c in chamadas])


# ---------------------------------------------------------------------------
# extras: ler_trava
# ---------------------------------------------------------------------------

class TestLerTrava(Base):
    def test_livre(self):
        p = self.tmp()
        (p / "HANDOFF.md").write_text("nota\nTRAVADO_POR: livre\n", encoding="utf-8")
        self.assertEqual(MODULO.ler_trava(p), "livre")

    def test_travado_com_ate(self):
        p = self.tmp()
        (p / "HANDOFF.md").write_text(
            "TRAVADO_POR: codex\nATÉ: 260915 18:00\n", encoding="utf-8")
        resultado = MODULO.ler_trava(p)
        self.assertTrue(resultado.startswith("TRAVADO_POR: codex"), resultado)
        self.assertIn("260915", resultado)

    def test_sem_handoff(self):
        p = self.tmp()
        self.assertEqual(MODULO.ler_trava(p), "sem HANDOFF.md")


# ---------------------------------------------------------------------------
# extras: resolver_projeto, e_central_real, achar_central
# ---------------------------------------------------------------------------

class TestResolverProjeto(Base):
    def test_subpasta_sobe_ate_o_marcador(self):
        p = self.tmp()
        (p / ".mb-origem.json").write_text("{}", encoding="utf-8")
        sub = p / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(MODULO.resolver_projeto(sub), p)

    def test_sem_marcador_fica_onde_esta(self):
        p = self.tmp()
        self.assertEqual(MODULO.resolver_projeto(p), p)


class TestECentralReal(Base):
    def test_recusa_copia_cheia_falsa_sem_motor(self):
        p = self.tmp()
        (p / "VERSAO.txt").write_text("v1", encoding="utf-8")
        (p / "MEGABRAIN.md").write_text("#", encoding="utf-8")
        (p / "bin").mkdir()
        (p / "bin" / "mb-check-version.py").write_text("", encoding="utf-8")
        self.assertFalse(MODULO.e_central_real(p))

    def test_aceita_raiz(self):
        self.assertTrue(MODULO.e_central_real(RAIZ))


class TestAcharCentral(Base):
    def test_env_invalida_retorna_none_com_mensagem(self):
        central_falsa = self.tmp()
        projeto = self.tmp()
        with mock.patch.dict(os.environ, {"MEGABRAIN_CENTRAL": str(central_falsa)}):
            central, msg = MODULO.achar_central(projeto)
        self.assertIsNone(central)
        self.assertIn("MEGABRAIN_CENTRAL", msg)

    def test_env_valida_aponta_pra_raiz(self):
        projeto = self.tmp()
        with mock.patch.dict(os.environ, {"MEGABRAIN_CENTRAL": str(RAIZ)}):
            central, como = MODULO.achar_central(projeto)
        self.assertEqual(central, RAIZ)
        self.assertEqual(como, "MEGABRAIN_CENTRAL")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Provas do assunto de commit derivado do VERSAO.txt.

260825: a ação 10 cortava com `delims=.` e parava no ponto da versão — o
commit público saiu "megabrain: 2026-08-25 · v7.". O caso do disco real está
aqui como teste, junto das fronteiras que o batch não sabia distinguir.
"""

from __future__ import annotations

import importlib.util
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

_spec = importlib.util.spec_from_file_location(
    "mb_titulo_versao", str(RAIZ / "bin" / "mb-titulo-versao.py"))
tv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tv)

# A linha que produziu o commit truncado, encurtada no meio (o texto real tem
# ~1500 chars; o que importa é o começo e a existência do ponto final).
LINHA_REAL = ("2026-08-25 · v7.5 — auditoria de 3 agentes: o encanamento "
              "consertado, a versao com uma fonte so e o painel que responde "
              "por numero. MEMORIA: um licoes-megabrain.md orfao de 4,6 KB na "
              "raiz sombreava o canonico.")


class TestTitulo(unittest.TestCase):
    def test_nao_para_no_ponto_da_versao(self):
        assunto = tv.titulo(LINHA_REAL)
        self.assertNotEqual(assunto, "megabrain: 2026-08-25 · v7.")
        self.assertIn("v7.5", assunto)

    def test_corta_no_primeiro_ponto_final(self):
        assunto = tv.titulo("2026-08-25 · v7.5 — titulo curto. MEMORIA: resto.")
        self.assertEqual(assunto, "megabrain: 2026-08-25 · v7.5 — titulo curto")

    def test_cabe_no_limite_de_assunto(self):
        assunto = tv.titulo(LINHA_REAL)
        self.assertLessEqual(len(assunto), 72)
        self.assertTrue(assunto.endswith("..."), assunto)

    def test_corte_respeita_fronteira_de_palavra(self):
        assunto = tv.titulo(LINHA_REAL)
        # sem "..." o texto termina numa palavra inteira da linha original
        corpo = assunto[len("megabrain: "):-len("...")]
        self.assertIn(corpo, LINHA_REAL)
        self.assertFalse(corpo.endswith(" "), assunto)

    def test_sanitiza_aspas_e_metacaractere_de_batch(self):
        assunto = tv.titulo('2026-08-25 · v7.5 — o "painel" 100% & cia')
        self.assertNotIn('"', assunto)
        self.assertNotIn("%", assunto)
        self.assertNotIn("&", assunto)
        self.assertIn("'painel'", assunto)

    def test_linha_vazia_cai_na_reserva(self):
        self.assertEqual(tv.titulo(""), "megabrain: megabrain v7")

    def test_titulo_curto_passa_inteiro(self):
        self.assertEqual(tv.titulo("2026-01-02 · v8.0 — dois ajustes"),
                         "megabrain: 2026-01-02 · v8.0 — dois ajustes")


class TestAcao10(unittest.TestCase):
    """O bloco LITERAL da ação 10, rodado no cmd.exe.

    A primeira tentativa de ligar o script no .cmd usava backtick com %PY%
    entre aspas: o cmd.exe reprocessa as aspas, a captura vinha VAZIA e o
    commit caía no texto de reserva sem erro nenhum — o mesmo silêncio do bug
    original. Testar o script sozinho não pega isso; só rodar o batch pega.
    """

    ACAO = RAIZ / "01_acoes" / "10_publicar-e-fotografar.cmd"

    def bloco(self) -> str:
        txt = self.ACAO.read_text(encoding="utf-8", errors="replace")
        ini = txt.index('set "MBTITARQ=')
        fim = txt.index("git commit -m", ini)
        return txt[ini:fim]

    def test_bloco_existe_e_nao_usa_delims_ponto(self):
        self.assertIn("mb-titulo-versao.py", self.bloco())
        # só linha EXECUTÁVEL: o `rem` que conta a história do bug cita
        # `delims=.` de propósito e não pode reprovar o arquivo.
        executaveis = [l for l in self.ACAO.read_text(
            encoding="utf-8", errors="replace").splitlines()
            if not l.strip().lower().startswith("rem ")]
        self.assertNotIn("delims=.", "\n".join(executaveis))

    @unittest.skipUnless(sys.platform == "win32", "cmd.exe só existe no Windows")
    def test_bloco_captura_o_titulo_no_cmd(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "01_acoes").mkdir()
            (raiz / "bin").mkdir()
            (raiz / "memoria/nucleo").mkdir(parents=True)
            # %~dp0..\bin resolve dentro da árvore temporária
            for nome in ("mb-titulo-versao.py", "mb_utils.py"):
                (raiz / "bin" / nome).write_bytes((RAIZ / "bin" / nome).read_bytes())
            (raiz / "memoria/nucleo/VERSAO.txt").write_text(
                LINHA_REAL + "\n", encoding="utf-8")
            prova = raiz / "01_acoes" / "prova.cmd"
            corpo = ("@echo off\r\nsetlocal\r\nchcp 65001 >nul\r\n"
                     f'set "PY={sys.executable}"\r\n'
                     f'set "CLONE={raiz}"\r\n'
                     + self.bloco().replace("\n", "\r\n")
                     + 'if "%MBTIT%"=="" set "MBTIT=<<VAZIO>>"\r\n'
                     f'echo %MBTIT%> "{raiz}\\saida.txt"\r\n')
            prova.write_bytes(corpo.encode("utf-8"))
            subprocess.run(["cmd", "/c", str(prova)], capture_output=True,
                           timeout=60)
            saida = (raiz / "saida.txt").read_bytes().decode("utf-8").strip()
        self.assertNotIn("VAZIO", saida)
        self.assertNotEqual(saida, "megabrain v7")     # texto de reserva
        self.assertIn("v7.5", saida)                   # não parou no ponto da versão
        self.assertIn("·", saida)                      # UTF-8 preservado pelo batch
        self.assertLessEqual(len(saida), 72)


class TestCLI(unittest.TestCase):
    def test_le_a_primeira_linha_do_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "VERSAO.txt"
            arq.write_text(LINHA_REAL + "\n2026-08-01 · v7.4 — anterior.\n",
                           encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(RAIZ / "bin" / "mb-titulo-versao.py"),
                 "--arquivo", str(arq)],
                capture_output=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0, r.stderr)
            saida = r.stdout.strip()
            self.assertIn("v7.5", saida)
            self.assertNotIn("v7.4", saida)
            self.assertLessEqual(len(saida), 72)


if __name__ == "__main__":
    unittest.main()

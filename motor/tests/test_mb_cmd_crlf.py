#!/usr/bin/env python3
"""Testes da guarda de CRLF nos .cmd (mb-preflight.cheque_crlf).

POR QUE ESTE ARQUIVO EXISTE
---------------------------
A lição "260819 — .cmd gerado por agente precisa de CRLF" está no
`licoes-megabrain.md` desde 19/08, e reapareceu em 260824 ("`.cmd` não se
edita por patch remoto") e em 260825 (o sync). Três registros, zero garantia:
a regra de ouro 21 do protocolo diz que o que precisa acontecer sempre vive em
script, não em markdown — e essa nunca virou script.

O custo medido da terceira vez: `01_acoes/260824_sincronizar-projetos.cmd` foi
reescrito em 260824 17:26 com quebra de linha Unix. O cmd.exe lê batch por
deslocamento de byte assumindo CRLF; com LF ele desalinha e come as primeiras
letras da linha seguinte — `setlocal` vira `tlocal`, `python` vira `thon`. Os
`set "FONTE=..."` viraram lixo, o robocopy copiou de origem vazia, e o
`if errorlevel 8` do fim media o python, não o robocopy: **18 "OK" e zero byte
copiado, por 20 horas**, com as 18 cópias de projeto paradas em 152 lições.

Não dá erro. Executa outra coisa. É por isso que precisa de teste e não de
lembrete.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb-preflight.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
sys.path.insert(0, str(RAIZ / "bin"))


def _preflight():
    """O hífen no nome impede o import normal — daí o importlib.

    O detector mora no `mb-preflight.py` e o teste consome de lá: um dono só.
    Cópia da lógica aqui dentro seria uma segunda verdade pra manter.
    """
    arq = RAIZ / "bin" / "mb-preflight.py"
    spec = importlib.util.spec_from_file_location("mb_preflight", arq)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pf = _preflight()

CRLF = b'@echo off\r\nsetlocal\r\nset "X=1"\r\necho %X%\r\n'
LF = b'@echo off\nsetlocal\nset "X=1"\necho %X%\n'


class Base(unittest.TestCase):
    def tmp(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)


class TestDetector(Base):
    def test_crlf_passa(self):
        c = self.tmp()
        (c / "bom.cmd").write_bytes(CRLF)
        self.assertEqual(pf.batch_com_lf(c), [])
        ok, msg = pf.cheque_crlf(c)
        self.assertTrue(ok, msg)

    def test_lf_e_pego_com_a_contagem(self):
        c = self.tmp()
        (c / "ruim.cmd").write_bytes(LF)
        self.assertEqual(pf.batch_com_lf(c), [("ruim.cmd", 4)])
        ok, msg = pf.cheque_crlf(c)
        self.assertFalse(ok)
        self.assertIn("ruim.cmd", msg)

    def test_bat_tambem_conta(self):
        """`.bat` quebra igual — a extensão muda, o parser do cmd.exe não."""
        c = self.tmp()
        (c / "legado.bat").write_bytes(LF)
        self.assertEqual([x[0] for x in pf.batch_com_lf(c)], ["legado.bat"])

    def test_misto_conta_so_as_linhas_em_lf(self):
        """O sincronizar-projetos real tinha 0 CR; o publicar tinha 2 CR e 56 LF.

        Arquivo meio-convertido é o pior caso: parece consertado numa olhada
        e quebra do mesmo jeito. O detector tem que enxergar o resto.
        """
        c = self.tmp()
        (c / "misto.cmd").write_bytes(b'@echo off\r\nsetlocal\necho a\necho b\r\n')
        self.assertEqual(pf.batch_com_lf(c), [("misto.cmd", 2)])

    def test_so_batch_e_verificado(self):
        """`.md`, `.py` e `.json` em LF são normais e não podem virar ruído."""
        c = self.tmp()
        for nome in ("nota.md", "script.py", "dados.json", "hook.mjs"):
            (c / nome).write_bytes(LF)
        self.assertEqual(pf.batch_com_lf(c), [])

    def test_espelho_gerado_e_ignorado(self):
        """Quem conserta espelho é o gerador, não a mão.

        `_github/`, `90_arquivo/` e a cópia `MEGABRAIN/` de projeto são saída.
        Acusar ali manda o humano editar o lugar que a próxima geração
        sobrescreve — a lição 260821 ("arquivo direto no espelho gerado").
        """
        c = self.tmp()
        for sub in ("_github/export", "90_arquivo", "99_to_delete",
                    ".mb-backup", "MEGABRAIN"):
            d = c / sub
            d.mkdir(parents=True)
            (d / "gerado.cmd").write_bytes(LF)
        (c / "fonte.cmd").write_bytes(CRLF)
        self.assertEqual(pf.batch_com_lf(c), [])

    def test_pular_crlf_nao_aceita_caminho_composto(self):
        """Mesma armadilha da decisão 260825b, agora travada aqui.

        A lista casa contra UM pedaço de caminho (`os.walk` devolve nome de
        pasta, não caminho). Entrada composta como "_github/export" nunca
        casaria e o filtro viraria no-op silencioso — que foi o defeito que
        fez cada documento entrar 3× no RELATORIO.html.
        """
        for x in pf.PULAR_CRLF:
            self.assertNotIn("/", x, f"entrada composta em PULAR_CRLF: {x!r}")
            self.assertNotIn("\\", x, f"entrada composta em PULAR_CRLF: {x!r}")


class TestCentralReal(Base):
    def test_nenhum_cmd_da_central_em_lf(self):
        """A guarda ao vivo: a central de verdade, agora.

        Se este cair, algum `.cmd` foi escrito por ferramenta que grava LF e
        vai executar outra coisa sem avisar. Conserto: reescrever o arquivo
        INTEIRO em CRLF (nunca patch parcial — lição 260824).
        """
        achados = pf.batch_com_lf(RAIZ)
        self.assertEqual(
            achados, [],
            "\n".join([".cmd/.bat em LF na central (o cmd.exe vai comer letras):"]
                      + [f"  {c} — {n} linha(s)" for c, n in achados]))


if __name__ == "__main__":
    unittest.main()

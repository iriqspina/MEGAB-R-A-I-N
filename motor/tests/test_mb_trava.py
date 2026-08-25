#!/usr/bin/env python3
"""Provas da trava por arquivo usada pelos escritores compartilhados.

O teste de subprocesso é deliberado: duas chamadas na mesma função não provam
concorrência entre agentes. A primeira execução deixa a trava viva; a segunda
precisa sair 1 e preservar o dono original.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import time
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
sys.path.insert(0, str(RAIZ / "bin"))
import mb_trava as trava  # noqa: E402

_estado_spec = importlib.util.spec_from_file_location(
    "mb_estado_teste", str(RAIZ / "bin" / "mb-estado.py"))
mb_estado = importlib.util.module_from_spec(_estado_spec)
_estado_spec.loader.exec_module(mb_estado)


class Base(unittest.TestCase):
    def tmpdir(self) -> Path:
        d = tempfile.TemporaryDirectory(prefix="mb-trava-")
        self.addCleanup(d.cleanup)
        return Path(d.name)


class TestContrato(Base):
    def test_segundo_dono_e_recusado(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text("# decisões\n", encoding="utf-8")
        trava.travar(alvo, "claude", raiz=raiz)
        with self.assertRaises(trava.TravaOcupada):
            trava.travar(alvo, "kimi", raiz=raiz)
        self.assertEqual(trava.ler(alvo, raiz)["agente"], "claude")

    def test_reentrada_so_libera_na_ultima_saida(self):
        raiz = self.tmpdir()
        alvo = raiz / "ESTADO.md"
        trava.travar(alvo, "codex", raiz=raiz)
        trava.travar(alvo, "codex", raiz=raiz)
        self.assertEqual(trava.ler(alvo, raiz)["contagem"], 2)
        self.assertTrue(trava.liberar(alvo, "codex", raiz))
        self.assertIsNotNone(trava.ler(alvo, raiz))
        self.assertTrue(trava.liberar(alvo, "codex", raiz))
        self.assertIsNone(trava.ler(alvo, raiz))

    def test_trava_vencida_e_livre(self):
        raiz = self.tmpdir()
        alvo = raiz / "META.md"
        trava.travar(alvo, "claude", raiz=raiz)
        p = trava.caminho_trava(alvo, raiz)
        dados = json.loads(p.read_text(encoding="utf-8"))
        dados["ate"] = (dt.datetime.now() - dt.timedelta(minutes=1)).strftime(trava.FMT)
        p.write_text(json.dumps(dados), encoding="utf-8")
        novo = trava.travar(alvo, "kimi", raiz=raiz)
        self.assertEqual(novo["agente"], "kimi")

    def test_disputa_por_vencida_nao_apaga_trava_nova(self):
        raiz = self.tmpdir()
        alvo = raiz / "META.md"
        trava.travar(alvo, "antigo", raiz=raiz)
        p = trava.caminho_trava(alvo, raiz)
        dados = json.loads(p.read_text(encoding="utf-8"))
        dados["ate"] = (dt.datetime.now() - dt.timedelta(minutes=1)).strftime(
            trava.FMT)
        p.write_text(json.dumps(dados), encoding="utf-8")

        chegou_na_criacao = threading.Event()
        pode_criar = threading.Event()
        resultados = {}
        criar_real = trava._criar_exclusivo

        def criar_lento(arq, novos_dados):
            if novos_dados["agente"] == "primeiro":
                chegou_na_criacao.set()
                pode_criar.wait(2)
            return criar_real(arq, novos_dados)

        def tomar(nome):
            try:
                resultados[nome] = trava.travar(alvo, nome, raiz=raiz)
            except Exception as e:  # resultado do concorrente faz parte da prova
                resultados[nome] = e

        with mock.patch.object(trava, "_criar_exclusivo", side_effect=criar_lento):
            primeiro = threading.Thread(target=tomar, args=("primeiro",))
            segundo = threading.Thread(target=tomar, args=("segundo",))
            primeiro.start()
            self.assertTrue(chegou_na_criacao.wait(2))
            segundo.start()
            time.sleep(0.1)
            pode_criar.set()
            primeiro.join(3)
            segundo.join(3)

        self.assertFalse(primeiro.is_alive())
        self.assertFalse(segundo.is_alive())
        self.assertIsInstance(resultados["primeiro"], dict)
        self.assertIsInstance(resultados["segundo"], trava.TravaOcupada)
        self.assertEqual(trava.ler(alvo, raiz)["agente"], "primeiro")

    def test_falha_de_gravacao_na_reentrada_sobe_erro(self):
        raiz = self.tmpdir()
        alvo = raiz / "ESTADO.md"
        trava.travar(alvo, "codex", raiz=raiz)
        with mock.patch.object(trava.u, "atomic_write_text", return_value=False):
            with self.assertRaises(OSError):
                trava.travar(alvo, "codex", raiz=raiz)
        self.assertEqual(trava.ler(alvo, raiz)["contagem"], 1)

    def test_falha_de_gravacao_no_decremento_sobe_erro(self):
        raiz = self.tmpdir()
        alvo = raiz / "ESTADO.md"
        trava.travar(alvo, "codex", raiz=raiz)
        trava.travar(alvo, "codex", raiz=raiz)
        with mock.patch.object(trava.u, "atomic_write_text", return_value=False):
            with self.assertRaises(OSError):
                trava.liberar(alvo, "codex", raiz=raiz)
        self.assertEqual(trava.ler(alvo, raiz)["contagem"], 2)

    def test_falha_no_unlink_final_sobe_erro(self):
        raiz = self.tmpdir()
        alvo = raiz / "ESTADO.md"
        trava.travar(alvo, "codex", raiz=raiz)
        arq = trava.caminho_trava(alvo, raiz)
        with mock.patch.object(
                type(arq), "unlink", side_effect=OSError("arquivo aberto")):
            with self.assertRaisesRegex(OSError, "não foi possível remover"):
                trava.liberar(alvo, "codex", raiz=raiz)
        self.assertIsNotNone(trava.ler(alvo, raiz))

    def test_contexto_libera_depois_de_excecao(self):
        raiz = self.tmpdir()
        alvo = raiz / "HANDOFF.md"
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with trava.travado(alvo, "codex", raiz=raiz):
                raise RuntimeError("boom")
        self.assertIsNone(trava.ler(alvo, raiz))

    def test_escrita_recusada_preserva_conteudo(self):
        raiz = self.tmpdir()
        alvo = raiz / "PROGRESSO.json"
        alvo.write_text("antes\n", encoding="utf-8")
        trava.travar(alvo, "claude", raiz=raiz)
        with self.assertRaises(trava.TravaOcupada):
            trava.escrever(alvo, "depois\n", "kimi", raiz=raiz)
        self.assertEqual(alvo.read_text(encoding="utf-8"), "antes\n")


class TestIds(Base):
    def test_cabecalho_legado_so_com_data_nao_e_id(self):
        texto = "## 260824 — um\n## 260824 — dois\n## 260825a — novo\n"
        self.assertEqual(trava.ids_de(texto), ["260825a"])

    def test_rotulo_de_lote_anterior_ao_contrato_e_preservado(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text(
            "## 260824b — um\n## 260824b — dois\n## 260825a — novo\n",
            encoding="utf-8",
        )
        self.assertEqual(trava.conferir_ids(alvo), [])

    def test_conferir_ids_encontra_duplicata(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text(
            "## 260825a — um\n\n## 260825a — dois\n",
            encoding="utf-8",
        )
        self.assertEqual(trava.conferir_ids(alvo), ["260825a"])

    def test_anexar_decisao_recusa_endereco_existente(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text("## 260825a — um\n", encoding="utf-8")
        with self.assertRaises(trava.IdDuplicado):
            trava.anexar_decisao(
                alvo, "\n## 260825a — dois\n", "codex", raiz=raiz)
        self.assertNotIn("dois", alvo.read_text(encoding="utf-8"))

    def test_anexar_decisao_nova_grava_e_termina_com_lf(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text("## 260825a — um\n", encoding="utf-8")
        gravado = trava.anexar_decisao(
            alvo, "\n## 260825b — dois\n", "codex", raiz=raiz)
        self.assertEqual(gravado, "260825b")
        self.assertTrue(alvo.read_bytes().endswith(b"\n"))

    def test_anexar_preserva_prefixo_e_crlf_existentes(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        prefixo = "## 260825a — um\r\ntexto\r\n".encode("utf-8")
        alvo.write_bytes(prefixo)
        trava.anexar_decisao(
            alvo, "## 260825b — dois\nlinha 2\n", "codex", raiz=raiz)
        depois = alvo.read_bytes()
        self.assertTrue(depois.startswith(prefixo))
        self.assertTrue(depois.endswith(
            "## 260825b — dois\r\nlinha 2\r\n".encode("utf-8")))

    def test_anexar_normaliza_legado_latin1_para_utf8(self):
        raiz = self.tmpdir()
        alvo = raiz / "licoes-megabrain.md"
        alvo.write_bytes(b"caf\xe9\r\n")
        trava.anexar(alvo, "nova lição\n", "codex", raiz=raiz)
        self.assertEqual(
            alvo.read_bytes(), "café\r\nnova lição\r\n".encode("utf-8"))

    def test_proximo_id_nao_recicla_buraco(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text(
            "## 260825a — um\n## 260825c — três\n",
            encoding="utf-8",
        )
        self.assertEqual(trava.proximo_id(alvo, "260825"), "260825d")

    def test_proximo_id_avanca_de_z_para_aa(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text("## 260825z — vinte e seis\n", encoding="utf-8")
        self.assertEqual(trava.proximo_id(alvo, "260825"), "260825aa")

    def test_proximo_id_avanca_de_zz_para_aaa(self):
        raiz = self.tmpdir()
        alvo = raiz / "DECISOES.md"
        alvo.write_text("## 260825zz — setecentos e dois\n", encoding="utf-8")
        self.assertEqual(trava.proximo_id(alvo, "260825"), "260825aaa")


class TestProcessos(Base):
    def rodar(self, raiz: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(RAIZ / "bin" / "mb_trava.py"), *args,
             "--raiz", str(raiz)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_dois_processos_segundo_e_recusado(self):
        raiz = self.tmpdir()
        alvo = raiz / "licoes-megabrain.md"
        primeiro = self.rodar(
            raiz, "travar", "--arquivo", str(alvo), "--agente", "processo-1")
        self.assertEqual(primeiro.returncode, 0, primeiro.stdout + primeiro.stderr)

        segundo = self.rodar(
            raiz, "travar", "--arquivo", str(alvo), "--agente", "processo-2")
        self.assertEqual(segundo.returncode, 1, segundo.stdout + segundo.stderr)
        self.assertIn("RECUSADO", segundo.stdout)
        self.assertEqual(trava.ler(alvo, raiz)["agente"], "processo-1")

        liberado = self.rodar(
            raiz, "liberar", "--arquivo", str(alvo), "--agente", "processo-1")
        self.assertEqual(liberado.returncode, 0, liberado.stdout + liberado.stderr)


class TestEscritorIntegrado(Base):
    def test_estado_usa_ultima_trava_do_handoff(self):
        raiz = self.tmpdir()
        estado_dir = raiz / "memoria" / "estado"
        estado_dir.mkdir(parents=True)
        (estado_dir / "ESTADO.md").write_text(
            "TL;DR: teste\nBLOQUEIO: nenhum\n", encoding="utf-8")
        (estado_dir / "PROGRESSO.json").write_text(
            '{"etapas": []}', encoding="utf-8")
        (estado_dir / "HANDOFF.md").write_text(
            "TRAVADO_POR: livre\n\n<!-- mb-sync:lock:start -->\n"
            "TRAVADO_POR: codex\n<!-- mb-sync:lock:end -->\n",
            encoding="utf-8",
        )
        self.assertEqual(mb_estado.col_estado(raiz)["trava"], "codex")

    def test_mb_fila_respeita_trava_antes_do_read_modify_write(self):
        raiz = self.tmpdir()
        dados = raiz / "dados"
        dados.mkdir()
        alvo = dados / "fila.json"
        original = {
            "schema": 1,
            "tasks": [{"id": "a", "titulo": "A", "blocked_by": [],
                       "estado": "todo", "prioridade": 1}],
        }
        alvo.write_text(json.dumps(original), encoding="utf-8")
        trava.travar(alvo, "outro-agente", raiz=RAIZ)
        self.addCleanup(trava.liberar, alvo, "outro-agente", RAIZ)

        r = subprocess.run(
            [sys.executable, str(RAIZ / "bin" / "mb-fila.py"),
             "--dir", str(raiz), "avancar", "a"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("outro-agente", r.stderr + r.stdout)
        depois = json.loads(alvo.read_text(encoding="utf-8"))
        self.assertEqual(depois["tasks"][0]["estado"], "todo")


if __name__ == "__main__":
    unittest.main()

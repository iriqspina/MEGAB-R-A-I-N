#!/usr/bin/env python3
"""Testes da telemetria local (bin/mb_telemetria.py — spec §4).

O que estes testes protegem:
- registrar() nunca derruba a sessão e escreve 1 linha JSONL por evento;
- a raiz é DEDUZIDA subindo o caminho (a máquina pode mudar de pasta —
  etapa 2 da reorg — sem reapontar nada na mão);
- ler() respeita a janela de dias e junta os formatos legados;
- agregar() conta por chave e calcula os pesos de frequência de skill;
- valor NUNCA é generalizado ("RTX 4070" continua "RTX 4070").
"""
import datetime as dt
import json
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
sys.path.insert(0, str(RAIZ / "bin"))

import mb_telemetria as tel  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        (self.raiz / "bin").mkdir()
        (self.raiz / "bin" / "mb_utils.py").write_text("# âncora\n", encoding="utf-8")
        (self.raiz / ".mb-log").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _linhas(self):
        arq = tel.arquivo_do_dia(self.raiz)
        return [json.loads(x) for x in arq.read_text(encoding="utf-8").splitlines() if x.strip()]


class TestRegistro(Base):
    def test_registra_uma_linha_por_evento(self):
        self.assertTrue(tel.registrar("sessao", raiz=self.raiz, skill="megabrain", cliente="cowork"))
        self.assertTrue(tel.registrar("gate", raiz=self.raiz, resultado="ok"))
        linhas = self._linhas()
        self.assertEqual(len(linhas), 2)
        self.assertEqual(linhas[0]["evento"], "sessao")
        self.assertEqual(linhas[0]["skill"], "megabrain")
        self.assertIn("ts", linhas[0])
        self.assertIn("so", linhas[0])

    def test_valor_nao_e_generalizado(self):
        tel.registrar("hardware", raiz=self.raiz, gpu="RTX 4070")
        self.assertEqual(self._linhas()[0]["gpu"], "RTX 4070")

    def test_campo_none_nao_entra(self):
        tel.registrar("sessao", raiz=self.raiz, skill=None, cliente="cli")
        linha = self._linhas()[0]
        self.assertNotIn("skill", linha)
        self.assertEqual(linha["cliente"], "cli")

    def test_falha_e_silenciosa(self):
        # raiz impossível: o arquivo do dia cairia dentro de um ARQUIVO
        falsa = self.raiz / "arquivo-nao-pasta"
        falsa.write_text("x", encoding="utf-8")
        self.assertFalse(tel.registrar("sessao", raiz=falsa))


class TestRaiz(Base):
    def test_raiz_e_deduzida_subindo(self):
        fundo = self.raiz / "motor" / "gerenteneuron" / "providers"
        fundo.mkdir(parents=True)
        self.assertEqual(tel.raiz_central(fundo), self.raiz)

    def test_raiz_sem_ancora_nao_explode(self):
        with tempfile.TemporaryDirectory() as vazio:
            self.assertIsInstance(tel.raiz_central(Path(vazio)), Path)


class TestLeitura(Base):
    def _escreve(self, nome, linhas):
        (self.raiz / ".mb-log" / nome).write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in linhas) + "\n", encoding="utf-8")

    def test_junta_legado_e_ignora_linha_quebrada(self):
        hoje = dt.date.today().isoformat()
        self._escreve("neuron.jsonl", [{"ts": f"{hoje}T10:00:00", "modelo": "kimi-k2", "provider": "moonshot"}])
        (self.raiz / ".mb-log" / "telemetria-000000.jsonl").write_text(
            '{"ts": "%sT11:00:00", "evento": "sessao", "skill": "megabrain"}\nlixo{\n' % hoje,
            encoding="utf-8")
        eventos = tel.ler(self.raiz, dias=30)
        self.assertEqual(len(eventos), 2)
        self.assertEqual([e.get("evento") or e.get("modelo") for e in eventos],
                         ["kimi-k2", "sessao"])

    def test_janela_de_dias_corta_o_velho(self):
        velho = (dt.date.today() - dt.timedelta(days=400)).isoformat()
        hoje = dt.date.today().isoformat()
        self._escreve("telemetria-antigo.jsonl", [{"ts": f"{velho}T10:00:00", "evento": "velho"},
                                                  {"ts": f"{hoje}T10:00:00", "evento": "novo"}])
        self.assertEqual([e["evento"] for e in tel.ler(self.raiz, dias=30)], ["novo"])
        self.assertEqual(len(tel.ler(self.raiz, dias=0)), 2)

    def test_log_ausente_devolve_lista_vazia(self):
        with tempfile.TemporaryDirectory() as vazio:
            self.assertEqual(tel.ler(Path(vazio)), [])


class TestAgregacao(Base):
    def test_conta_por_chave_e_calcula_pesos(self):
        for _ in range(3):
            tel.registrar("sessao", raiz=self.raiz, skill="megabrain", cliente="cowork", agente="claude")
        tel.registrar("sessao", raiz=self.raiz, skill="ingerir", cliente="cli", agente="claude",
                      duracao_s=2.0, resultado="ok")
        r = tel.agregar(tel.ler(self.raiz))
        self.assertEqual(r["eventos"], 4)
        self.assertEqual(r["por"]["skill"], {"megabrain": 3, "ingerir": 1})
        self.assertEqual(r["por"]["agente"]["claude"], 4)
        self.assertAlmostEqual(r["pesos_skills"]["megabrain"], 0.75)
        self.assertEqual(r["duracao_media_s"], 2.0)
        self.assertEqual(list(r["pesos_skills"])[0], "megabrain")

    def test_vazio_nao_quebra(self):
        r = tel.agregar([])
        self.assertEqual(r["eventos"], 0)
        self.assertEqual(r["pesos_skills"], {})
        self.assertIsNone(r["duracao_media_s"])


class TestFuso(Base):
    """O bug de 260824: a ponte roda em UTC, então entre 21h e meia-noite o log
    ia pro arquivo do dia SEGUINTE (telemetria-260825.jsonl nasceu às 22h38 de
    260824) e o ts saía com 3 horas de erro. Data é sempre o relógio dele."""

    def test_agora_e_sempre_sao_paulo(self):
        self.assertEqual(tel.agora().utcoffset(), dt.timedelta(hours=-3))

    def test_ts_gravado_ignora_o_fuso_da_maquina(self):
        tel.registrar("sessao", raiz=self.raiz)
        self.assertTrue(self._linhas()[0]["ts"].endswith("-03:00"))

    def test_arquivo_do_dia_usa_o_relogio_da_central(self):
        self.assertTrue(tel.arquivo_do_dia(self.raiz).name.endswith(f"{tel.hoje():%y%m%d}.jsonl"))

    def test_ts_em_utc_conta_no_dia_certo_na_leitura(self):
        # 01:38 UTC do dia 25 = 22:38 do dia 24 em SP
        d = tel._data_do_evento({"ts": "2026-08-25T01:38:50+00:00"})
        self.assertEqual(d, dt.date(2026, 8, 24))

    def test_ts_sem_fuso_e_tratado_como_local(self):
        d = tel._data_do_evento({"ts": "2026-08-25T01:38:50"})
        self.assertEqual(d, dt.date(2026, 8, 25))

    def test_corrigir_fuso_devolve_a_linha_pro_dia_certo(self):
        errado = self.raiz / ".mb-log" / "telemetria-260825.jsonl"
        errado.write_text(
            '{"ts": "2026-08-25T01:38:50+00:00", "evento": "slop_visual"}\n', encoding="utf-8")
        seco = tel.corrigir_fuso(self.raiz)
        self.assertEqual(seco["reescritas"], 1)
        self.assertEqual(seco["movidas"], 1)
        self.assertFalse(seco["aplicado"])
        self.assertTrue(errado.is_file())      # sem --aplicar não toca em nada

        r = tel.corrigir_fuso(self.raiz, aplicar=True)
        self.assertTrue(r["aplicado"])
        certo = self.raiz / ".mb-log" / "telemetria-260824.jsonl"
        self.assertTrue(certo.is_file())
        linha = json.loads(certo.read_text(encoding="utf-8").strip())
        self.assertEqual(linha["ts"], "2026-08-24T22:38:50-03:00")
        self.assertEqual(linha["ts_original"], "2026-08-25T01:38:50+00:00")
        self.assertFalse(errado.is_file())     # migrou pro saco de backup
        self.assertTrue((self.raiz / ".mb-log" / r["backup"]).is_dir())

    def test_corrigir_fuso_nao_toca_em_log_de_hook(self):
        alheio = self.raiz / ".mb-log" / "eventos-260824.jsonl"
        alheio.write_text('{"ts": "2026-08-24T18:39:16-03:00", "evento": "prompt"}\n',
                          encoding="utf-8")
        antes = alheio.read_text(encoding="utf-8")
        tel.corrigir_fuso(self.raiz, aplicar=True)
        self.assertEqual(alheio.read_text(encoding="utf-8"), antes)


if __name__ == "__main__":
    unittest.main()

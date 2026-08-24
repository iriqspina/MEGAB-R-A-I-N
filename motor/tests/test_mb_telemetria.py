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


if __name__ == "__main__":
    unittest.main()

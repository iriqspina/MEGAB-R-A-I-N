#!/usr/bin/env python3
"""Provas do hook de contexto: achar o projeto onde ele realmente está.

261017 (H6/C01): prompt curto não injeta lição/cérebro fracos; o corte de
score vale também no 1º prompt; fala ditada com vários pedidos ganha a
instrução "Entendi N itens:" (liga/desliga por limpeza_ditado).

Item 4.2 da auditoria de 260825: no worktree do Traycer
(~/.traycer/worktrees/...) o hook dizia "este projeto ainda não tem META.md"
com o `memoria/estado/META.md` rastreado dentro do worktree — achar_projeto só
reconhecia projeto descendo de projetos_root. Os testes fixam os dois lados:
worktree com marcador é projeto (e o META entra no contexto); pasta sem
marcador segue não sendo.
"""

from __future__ import annotations

import importlib.util
import json
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


# Fala real do <USUARIO> em 2026-10-17 (ditado por voz, 361 palavras, ~10 pedidos).
# Fixture da limpeza de ditado (C01); não editar o texto.
DITADO_REAL = """A interação do usuário com é, o aplicativo está um pouco bugado em alguns momentos. Por exemplo, eu estou sentindo que depois que eu faço um comentário, por algum motivo eu não consigo voltar a trocar o, a função da ferramenta do cursor. Eu clico seguro e nada acontece. E acaba tendo alguns outros bugs. Eu, independente da área que eu clico, às vezes parece que eu não consigo mais voltar essa ferramenta para o lugar. Então tem dar uma checagem. Não sei se o problema é a ferramenta ou algum tipo de organização, é, ou talvez não está configurado para quando eu estou vendo um resultado. Eu percebo isso que acontece quando eu estou vendo os resultados dos relatórios. E o que acontece é o seguinte. Quando geralmente buga é quando eu estou usando os, os relatórios. E quero que você faça uma geral no, no Megabrain sobre isso, se ainda deixar algum comentário e analisar se o Megabrain como um todo, o que, que tem de atrito, tanto da forma com que eu me comunico e como que você pode ajustar o sistema do Megabrain para facilitar para o usuário. E funcionalidades também, então checar geral do o Megabrain geral. É... Não só aplicativo, mas também como, como harness. E eu gostaria que você fizesse uma representação visual do funcionamento do harness completo de uma forma simplificada. Eu vejo que existem templates na internet, como alguns que fazem uma cidade, outros têm outras opções, e eu quero que você vá atrás dessas opções e crie. Pode escolher uma, uma que você achar melhor, mas é que eu quero ter visão facilitada e editável, é, não durante o processo, mas depois eu, eu, editável eu digo que eu posso depois pegar esse harness e editar os processos como eu quero. E arquitetar direitinho, mas eu preciso que exista uma visualização facilitada, dinâmica e animada que representa esses processos novos rolando ou, e o que... Bom, não sei. Existe, é isso que eu não sei. Eu preciso que você vá atrás de compreender como que você representa isso para um ser humano também. todas as permissoes já concedidas atraves dessa frase"""

PREFERENCIAS_BASE = {"schema_version": 1, "sensibilidade": "equilibrada"}


class _IndiceFalso:
    """Troca os índices de lições e do cérebro por respostas fixas (sem embedding)."""

    def __init__(self, entradas):
        self.entradas = entradas

    def buscar(self, *args, **kwargs):
        return [dict(e) for e in self.entradas]

    def carregar_indice(self):
        return {"entradas": list(self.entradas)}


class TestHigieneContexto(Base):
    """H6: prompt curto e corte de score; C01: limpeza de ditado."""

    def montar(self, prompt: str, cwd: Path, licoes=(), paginas=(), session_id=None) -> str:
        with mock.patch.object(contexto, "carregar_indice_licoes",
                               lambda: _IndiceFalso(list(licoes))), \
             mock.patch.object(contexto, "carregar_indice_cerebro",
                               lambda: _IndiceFalso(list(paginas))):
            return contexto.montar(
                {"prompt": prompt, "cwd": str(cwd),
                 "session_id": session_id or f"teste-{uuid.uuid4().hex[:12]}"}, "claude")

    @staticmethod
    def licao(chave: str, score: float) -> dict:
        return {"chave": chave, "texto": f"TEXTO_{chave}", "score": score}

    def projeto(self, preferencias: dict | None = None) -> Path:
        self.ambiente()
        wt = self.worktree()
        if preferencias is not None:
            (wt / "dados").mkdir()
            (wt / "dados/preferencias-megabrain.json").write_text(
                json.dumps(preferencias), encoding="utf-8")
        return wt

    # --- H6: prompt curto -------------------------------------------------
    def test_prompt_curto_nao_injeta_licao_nem_pagina_fracas(self):
        wt = self.projeto()
        for prompt in ("continua", "ok", "sim, pode", "corrige o .cmd"):
            bloco = self.montar(prompt, wt, [self.licao("L1", 0.62)], [self.licao("P1", 0.62)])
            self.assertNotIn("TEXTO_L1", bloco, prompt)
            self.assertNotIn("TEXTO_P1", bloco, prompt)

    def test_prompt_curto_aceita_licao_e_pagina_muito_proximas(self):
        wt = self.projeto()
        bloco = self.montar("continua", wt, [self.licao("L1", 0.75)], [self.licao("P1", 0.75)])
        self.assertIn("TEXTO_L1", bloco)
        self.assertIn("TEXTO_P1", bloco)

    def test_prompt_curto_mantem_a_triagem(self):
        wt = self.projeto()
        self.assertIn("### Triagem MEGABRAIN", self.montar("continua", wt))

    def test_prompt_normal_segue_com_corte_055(self):
        wt = self.projeto()
        prompt = "corrige o arquivo de ações de hoje por favor"
        bloco = self.montar(prompt, wt, [self.licao("L1", 0.6), self.licao("L2", 0.5)])
        self.assertIn("TEXTO_L1", bloco)
        self.assertNotIn("TEXTO_L2", bloco)

    def test_corte_de_score_vale_tambem_no_primeiro_prompt(self):
        wt = self.projeto()
        bloco = self.montar("corrige o arquivo de ações de hoje por favor", wt,
                            [self.licao("L1", 0.4)], [self.licao("P1", 0.4)])
        self.assertIn("META do projeto", bloco)   # 1º prompt: a META continua entrando
        self.assertNotIn("TEXTO_L1", bloco)
        self.assertNotIn("TEXTO_P1", bloco)

    def test_licao_ja_injetada_nao_repete(self):
        wt = self.projeto()
        sid = f"teste-{uuid.uuid4().hex[:12]}"
        prompt = "corrige o arquivo de ações de hoje por favor"
        licoes = [self.licao("L1", 0.9)]
        self.assertIn("TEXTO_L1", self.montar(prompt, wt, licoes, session_id=sid))
        self.assertNotIn("TEXTO_L1", self.montar(prompt, wt, licoes, session_id=sid))

    # --- C01: limpeza de ditado ------------------------------------------
    def test_pedido_ditado_real_dispara_a_limpeza(self):
        wt = self.projeto()
        medido = contexto.detectar_ditado(DITADO_REAL)
        self.assertIsNotNone(medido)
        self.assertGreaterEqual(medido["palavras"], 300)
        self.assertGreaterEqual(medido["pedidos"], 3)
        self.assertGreaterEqual(medido["marcas"], 3)
        bloco = self.montar(DITADO_REAL, wt)
        self.assertIn("Entendi N itens:", bloco)
        for etiqueta in ("[pedido]", "[minha leitura]", "[autorização]"):
            self.assertIn(etiqueta, bloco)
        self.assertIn("default", bloco)
        self.assertIn("Não bloqueie trabalho reversível", bloco)

    def test_fala_curta_nao_dispara_a_limpeza(self):
        wt = self.projeto()
        for prompt in ("continua", "ok", "sim, pode", "corrige o .cmd",
                       "faz um PDF do relatório de hoje", "tipo, é, né"):
            self.assertIsNone(contexto.detectar_ditado(prompt), prompt)
            self.assertNotIn("Entendi N itens:", self.montar(prompt, wt), prompt)

    def test_texto_longo_sem_pedidos_nem_marcas_nao_dispara(self):
        texto = ("O relatório de setembro mostra queda de acessos no site institucional "
                 "durante as três primeiras semanas, com recuperação parcial no fim do mês. "
                 "A principal origem de tráfego continua sendo a busca orgânica, seguida de "
                 "indicações diretas de clientes antigos. Os números de conversão ficaram "
                 "estáveis, em torno de dois por cento, sem variação relevante entre desktop "
                 "e celular durante todo o período analisado pela equipe.")
        self.assertGreaterEqual(len(texto.split()), 60)
        self.assertIsNone(contexto.detectar_ditado(texto))

    def test_marcas_de_ditado_sem_verbos_de_pedido_disparam(self):
        texto = ("É, tipo, o, o relatório do, do cliente, né, aquele que a gente viu ontem "
                 "lá na reunião, sabe, ficou meio estranho, então, a cor, a cor da faixa "
                 "não combinou direito com o logo da empresa")
        medido = contexto.detectar_ditado(texto)
        self.assertIsNotNone(medido)
        self.assertLess(medido["pedidos"], 3)
        self.assertGreaterEqual(medido["marcas"], 3)

    def test_log_colado_com_reticencias_nao_dispara(self):
        # 261018 (R1-04): log de terminal colado nao e fala ditada
        linhas = ["npm install", "> megabrain-workspace@0.1.0 build", "Installing dependencies...",
                  "Resolving packages...", "Fetching packages...", "Linking dependencies...",
                  "[1/4] Building fresh packages...", "error Command failed with exit code 1.",
                  "at Object.<anonymous> (C:/app/build.js:12:3)",
                  "info Visit https://yarnpkg.com/en/docs/cli/run for documentation about this command."]
        self.assertIsNone(contexto.detectar_ditado(chr(10).join(linhas * 3)))

    def test_verbo_saber_comum_nao_conta_como_hesitacao(self):
        texto = ("Voce sabe que o cliente pediu a revisao do logo na semana passada e ninguem sabe ainda se a "
                 "versao final vai ter a faixa roxa ou azul; ele sabe que a decisao depende do diretor de arte, "
                 "que volta de viagem so na segunda feira depois do feriado prolongado da cidade dele")
        self.assertGreaterEqual(len(texto.split()), 40)
        self.assertIsNone(contexto.detectar_ditado(texto))

    def test_mensagem_de_sistema_com_tag_nao_dispara(self):
        texto = "<cross-session-message from=\"x\"> " + DITADO_REAL
        self.assertIsNone(contexto.detectar_ditado(texto))

    def test_limpeza_desligada_pela_chave_da_preferencia(self):
        wt = self.projeto(dict(PREFERENCIAS_BASE, limpeza_ditado=False))
        self.assertNotIn("Entendi N itens:", self.montar(DITADO_REAL, wt))

    def test_limpeza_ligada_por_padrao_e_com_chave_verdadeira(self):
        wt = self.projeto(dict(PREFERENCIAS_BASE))
        self.assertIn("Entendi N itens:", self.montar(DITADO_REAL, wt))
        wt2 = self.projeto(dict(PREFERENCIAS_BASE, limpeza_ditado=True))
        self.assertIn("Entendi N itens:", self.montar(DITADO_REAL, wt2))

    def test_preferencia_central_traz_a_chave_ligada(self):
        arquivo = RAIZ / "dados" / "preferencias-megabrain.json"
        dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
        self.assertIs(dados.get("limpeza_ditado"), True)


if __name__ == "__main__":
    unittest.main()

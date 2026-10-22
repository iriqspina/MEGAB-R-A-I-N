# -*- coding: utf-8 -*-
"""Mapa da cidade MegaBrain (harness) — gerador, planta, remendos e fotografia.

Cobre: planta real válida; mensagens do validador em português; remendos
(mover, editar, criar, incluir, ordem, nota, nova linha, remover) e recusa
sem gravar; mesma semântica no Python e no mapa.js (Node, quando disponível);
custo do rascunho igual ao json.dumps do servidor do app; HTML gerado offline,
com dados seguros dentro do <script> e Ferramentas do cursor; fotografia que
só lê (banco e arquivos intactos); --aplicar-remendos com backup e histórico.
A prova no QtWebEngine (animação, movimento reduzido, rascunho, cursor) roda
fora da suíte: evidence/261017_cursor-harness/mapa/.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import importlib.util
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

CENTRAL = Path(__file__).resolve().parents[2]
GERADOR = CENTRAL / "bin" / "mb-harness-mapa.py"
FONTE = CENTRAL / "dados" / "harness-mapa.json"
MAPA_JS = CENTRAL / "motor" / "modelos" / "harness-mapa" / "mapa.js"


def _carregar():
    spec = importlib.util.spec_from_file_location("mb_harness_mapa", GERADOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _carregar()

REMENDOS = [
    {"op": "mover", "estacao": "triagem", "x": 385.5, "y": 335},
    {"op": "editar", "tipo": "estacao", "id": "plano", "campo": "nome", "valor": "Planejar"},
    {"op": "editar", "tipo": "linha", "id": "pergunta", "campo": "cor", "valor": "#A0E426"},
    {"op": "nova_estacao", "id": "e_teste", "nome": "Checagem extra", "linha": "entrega", "depois_de": "producao", "x": 875, "y": 350},
    {"op": "nota", "id": "n_t1", "alvo": "estacao:rev_final", "texto": "Quero que a revisão final seja do Codex 2.", "em": "2026-10-17T23:00:00Z"},
    {"op": "incluir", "linha": "cotas", "estacao": "ia_principal", "depois_de": "leitor"},
    {"op": "nova_linha", "id": "l_teste", "nome": "Linha de teste", "cor": "#00CD9C", "estacoes": ["voce", "triagem", "resposta"]},
    {"op": "remover_estacao", "id": "copiadora"},
    {"op": "ordem", "linha": "app", "estacoes": ["voce", "novo_pedido", "ia_etapa", "executor", "rev_glm", "resultados"]},
    {"op": "remover_nota", "id": "n_t1"},
    {"op": "nota", "id": "n_t2", "alvo": "linha:celular", "texto": "Testar no Pixel 7 de verdade.", "em": "2026-10-17T23:01:00Z"},
    {"op": "remover_linha", "id": "l_teste"},
]


def _base():
    return json.loads(FONTE.read_text(encoding="utf-8"))


class PlantaReal(unittest.TestCase):
    def test_fonte_real_valida(self):
        d = _base()
        self.assertEqual(G.validar(d), [])
        self.assertLessEqual(len(d["legenda"]), 7)
        self.assertGreaterEqual(len(d["linhas"]), 7)
        tipos = {e.get("tipo", "estacao") for e in d["estacoes"]}
        self.assertEqual(tipos, {"estacao", "placa", "deposito"})
        # só o que tem prova fica verificado; o que nunca foi testado aparece como tal
        self.assertFalse(next(e for e in d["estacoes"] if e["id"] == "pixel7")["verificado"])
        for e in d["estacoes"]:
            if e["verificado"]:
                self.assertTrue(e["arquivos"], e["id"])

    def test_validador_explica_em_portugues(self):
        d = _base()
        d["linhas"][0]["estacoes"].append("nao_existe")
        d["estacoes"][0]["descricao"] = " ".join(["palavra"] * 25)
        d["estacoes"][1]["nome"] = "um nome comprido demais"
        d["linhas"][1]["cor"] = "azul"
        d["legenda"] = d["legenda"] + [{"id": "x", "texto": "x"}]
        d["estacoes"].append(copy.deepcopy(d["estacoes"][2]))
        erros = "\n".join(G.validar(d))
        self.assertIn('estação desconhecida "nao_existe"', erros)
        self.assertIn("tem 25 palavras; o limite é 20", erros)
        self.assertIn("passa de 3 palavras", erros)
        self.assertIn("cor inválida", erros)
        self.assertIn("de 1 a 7 símbolos", erros)
        self.assertIn("id repetido", erros)

    def test_volta_precisa_voltar(self):
        d = _base()
        l = next(x for x in d["linhas"] if x.get("volta"))
        l["volta"] = {"de": l["volta"]["para"], "para": l["volta"]["de"], "max": 1}
        self.assertTrue(any("voltar para uma estação anterior" in e for e in G.validar(d)))


class Remendos(unittest.TestCase):
    def test_aplica_e_continua_valida(self):
        base = _base()
        m = G.aplicar(base, REMENDOS)
        self.assertEqual(G.validar(m), [])
        est = {e["id"]: e for e in m["estacoes"]}
        self.assertEqual((est["triagem"]["x"], est["triagem"]["y"]), (386, 335))
        self.assertEqual(est["plano"]["nome"], "Planejar")
        self.assertFalse(est["e_teste"]["verificado"])
        entrega = next(l for l in m["linhas"] if l["id"] == "entrega")["estacoes"]
        self.assertEqual(entrega[entrega.index("producao") + 1], "e_teste")
        cotas = next(l for l in m["linhas"] if l["id"] == "cotas")["estacoes"]
        self.assertEqual(cotas[cotas.index("leitor") + 1], "ia_principal")
        self.assertNotIn("copiadora", est)
        self.assertFalse(any(g["de"] == "copiadora" or g["para"] == "copiadora" for g in m["ligacoes"]))
        self.assertFalse(any(l["id"] == "l_teste" for l in m["linhas"]))
        self.assertFalse(any(c["linha"] == "l_teste" for c in m["cenarios"]))
        self.assertEqual([n["id"] for n in m["notas"]], ["n_t2"])
        self.assertEqual(base, _base(), "aplicar não pode mexer na planta original")

    def test_recusa_sem_meio_termo(self):
        base = _base()
        with self.assertRaises(G.RemendoErro) as c:
            G.aplicar(base, [REMENDOS[0], {"op": "editar", "tipo": "estacao", "id": "plano", "campo": "nome", "valor": "um dois três quatro"}])
        self.assertIn("Remendo 2", str(c.exception))
        self.assertIn("até 3 palavras", str(c.exception))
        with self.assertRaises(G.RemendoErro):
            G.aplicar(base, [{"op": "explodir"}])
        with self.assertRaises(G.RemendoErro):
            G.aplicar(base, [{"op": "editar", "tipo": "estacao", "id": "plano", "campo": "arquivos", "valor": "x"}])

    def test_nao_deixa_linha_com_uma_estacao(self):
        base = _base()
        base["linhas"].append({"id": "curta", "nome": "Curta", "cor": "#123456", "gatilho": "x", "frequencia": "x", "estacoes": ["voce", "resposta"], "verificado": False})
        with self.assertRaises(G.RemendoErro) as c:
            G.aplicar(base, [{"op": "remover_estacao", "id": "resposta"}])
        self.assertIn("menos de 2 estações", str(c.exception))

    def test_extrai_de_todos_os_formatos(self):
        ps = [{"op": "mover", "estacao": "voce", "x": 1, "y": 2}]
        self.assertEqual(G.extrair_remendos(ps), (ps, None))
        self.assertEqual(G.extrair_remendos({"patches": ps, "lote": "abc"}), (ps, "abc"))
        self.assertEqual(G.extrair_remendos({"respostas": {"mapa_harness": {"patches": ps, "lote": "x1"}}}), (ps, "x1"))
        self.assertEqual(G.extrair_remendos({"feedback": {"kind": "decisions", "respostas": {"mapa_harness": {"patches": ps}}}}), (ps, None))
        self.assertEqual(G.extrair_remendos({"nada": 1}), ([], None))


@unittest.skipUnless(shutil.which("node"), "Node ausente")
class ParidadeNode(unittest.TestCase):
    """O mapa (navegador) e o gerador (Python) precisam produzir a mesma planta."""

    def _node(self, codigo: str, *args: str):
        r = subprocess.run(["node", "-e", codigo, *args], capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_ritmo_acompanha_texto_e_velocidade(self):
        out = self._node(
            "const c=require(process.argv[1]);const t=Array(26).fill('palavra').join(' ');"
            "process.stdout.write(JSON.stringify({curto:c.tempoLeitura('Uma parada',1,.6),longo:c.tempoLeitura(t,1,.6),"
            "lento:c.tempoLeitura(t,.5,.6),rapido:c.tempoLeitura(t,2,.6),vazio:c.tempoLeitura('',1,.6)}));",
            str(MAPA_JS))
        self.assertGreaterEqual(out['curto'], 1.8)
        self.assertGreater(out['longo'], 7)
        self.assertGreater(out['longo'], out['curto'])
        self.assertAlmostEqual(out['lento'], out['longo'] * 2)
        self.assertAlmostEqual(out['rapido'], out['longo'] / 2)
        self.assertGreaterEqual(out['vazio'], 1.8)

    def test_pontas_e_orientacao_usam_cada_processo(self):
        out = self._node(
            "const fs=require('fs'),c=require(process.argv[1]),m=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
            "process.stdout.write(JSON.stringify(m.linhas.map(l=>({id:l.id,pontas:c.pontasDaLinha(l),"
            "desk:c.orientacao(m,l,false),mob:c.orientacao(m,l,true)}))));", str(MAPA_JS), str(FONTE))
        base = _base()
        for linha, row in zip(base['linhas'], out):
            self.assertEqual(row['pontas'], [linha['estacoes'][0], linha['estacoes'][-1]])
            names = {e['id']: e['nome'] for e in base['estacoes']}
            for sid in row['pontas']:
                self.assertIn(names[sid], row['desk'])
                self.assertIn(names[sid], row['mob'])
            self.assertIn('esquerda para a direita', row['desk'])
            self.assertIn('cima para baixo', row['mob'])
            self.assertNotIn('esquerda', row['mob'])

    def test_mesma_planta_e_diff_reconstroi(self):
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "ops.json"
            arq.write_text(json.dumps(REMENDOS, ensure_ascii=False), encoding="utf-8")
            codigo = (
                "const fs=require('fs');const c=require(process.argv[1]);"
                "const base=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const ops=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));"
                "const r=c.aplicar(base,ops,false).modelo;const d=c.diff(base,r);const r2=c.aplicar(base,d,false).modelo;"
                "process.stdout.write(JSON.stringify({r:r,d:d,r2:r2,resumo:c.resumo(d,base,r)}));"
            )
            out = self._node(codigo, str(MAPA_JS), str(FONTE), str(arq))
        py = G.aplicar(_base(), REMENDOS)
        self.assertEqual(out["r"], json.loads(json.dumps(py)))
        self.assertEqual(out["r2"], out["r"], "diff → aplicar precisa reconstruir a mesma planta")
        self.assertEqual(G.aplicar(_base(), out["d"]), py, "Python aplica o pacote exportado pelo mapa")
        self.assertTrue(all(isinstance(s, str) and s for s in out["resumo"]))

    def test_custo_igual_ao_servidor(self):
        amostra = 'Revisão “final” — ação\\n "aspas" \\\\ barra é\U0001F600 fim'
        par = [["mb-harness-mapa:v1", amostra], ["megabrain.pop.tema", "claro"], ["cf-notas:/x", "[]"]]
        codigo = ("const c=require(process.argv[1]);const s=JSON.parse(process.argv[2]);const p=JSON.parse(process.argv[3]);"
                  "process.stdout.write(JSON.stringify({u:c.custoServidor(s),t:c.custoArmazenamento(p)}));")
        out = self._node(codigo, str(MAPA_JS), json.dumps(amostra), json.dumps(par))
        self.assertEqual(out["u"], len(json.dumps(amostra)))
        self.assertEqual(out["t"], len(json.dumps(dict(par))))


class Gerador(unittest.TestCase):
    def test_html_offline_com_dados_seguros(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / "mapa.html"
            info = G.gerar(FONTE, saida, sem_fotografia=True)
            t = saida.read_text(encoding="utf-8")
        self.assertLess(info["bytes"], 250_000)
        self.assertEqual(info["cursor"], "inserido")
        self.assertIn("<!-- mb-interacoes:inicio -->", t)
        self.assertIn("megabrain.pop.tema", t)
        self.assertNotRegex(t, r'(?i)(src|href)\s*=\s*["\']?\s*(https?:)?//')
        self.assertNotRegex(t, r"(?i)<link[^>]+stylesheet")
        m = re.search(r"window\.HARNESS = (.*?);</script>", t, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn("<", m.group(1), "dados embutidos não podem conter '<' cru")
        dados = json.loads(m.group(1))
        self.assertEqual(dados["base"], {k: v for k, v in _base().items() if k not in G.FORA_DO_HTML})
        self.assertIsNone(dados["foto"])
        self.assertEqual(dados["base_id"], G.base_id(_base()))
        for marca in ("data-cf-ancora", "data-cf-ignorar", "mb-harness-mapa:v1", "saveFeedback", "prefers-reduced-motion", "aria-live"):
            self.assertIn(marca, t, marca)
        self.assertNotIn("confirm(", t.split("<!-- mb-interacoes:inicio -->")[0])
        self.assertIn("261017_MAPA-DO-HARNESS.html", str(G.SAIDA_PADRAO))

    def test_ajuste_r1_leitura_em_5_segundos(self):
        """Crítica r1: título diz o que é o harness, começo/fim marcados, legenda ≤ 7, celular com seletor e menu."""
        d = _base()
        self.assertIn("harness", d["titulo"].lower())
        self.assertIn("em volta das IAs", d["subtitulo"])
        self.assertLessEqual(len(d["subtitulo_curto"]), len(d["subtitulo"]))
        self.assertIn("esquerda", d["narracao_inicial"])
        ids = [x["id"] for x in d["legenda"]]
        self.assertLessEqual(len(ids), 7)
        for chave in ("quem", "revisao", "baldeacao", "nao_testada"):
            self.assertIn(chave, ids)
        self.assertEqual({e["id"] for e in d["estacoes"] if e.get("papel") == "revisao"}, {"rev_plano", "rev_final", "rev_glm"})
        self.assertEqual(d["responsaveis"]["voce"]["sigla"], "V")
        # P7: a linha anil fica meio passo fora da lilás e com rótulos embaixo (fora do par de linhas)
        est = {e["id"]: e for e in d["estacoes"]}
        lilas = {est[s]["x"] for s in ("plano", "rev_plano", "producao", "rev_final")}
        for s in ("novo_pedido", "executor", "ia_etapa", "rev_glm"):
            self.assertNotIn(est[s]["x"], lilas, s)
            self.assertIn(est[s].get("rotulo", "baixo"), ("baixo",), s)
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / "mapa.html"
            G.gerar(FONTE, saida, sem_fotografia=True)
            t = saida.read_text(encoding="utf-8")
        self.assertIn('<p class="mh-sub">', t)
        self.assertIn(G._esc(d["subtitulo"]), t)
        for marca in ('id="mh-linha-sel"', 'id="mh-menu-btn"', 'id="mh-regua"', 'id="g-rastro"', 'id="g-marcos"', "COMEÇA AQUI", "CHEGA AQUI",
                      "Mostrar o que está parado agora", "volta ' + (l.volta.max || 1) + '× se a revisão pedir ajuste", "isPointInStroke", "Entendi"):
            self.assertIn(marca, t, marca)
        self.assertNotIn('id="mh-leg"', t)

    def test_cursor_multilinha_exige_revisao(self):
        with self.assertRaisesRegex(ValueError, 'texto multilinha'):
            G.compactar_cursor('const texto = `linha 1\n  linha 2`;')
        with self.assertRaisesRegex(ValueError, 'texto multilinha'):
            G.compactar_cursor("const x = 'linha" + chr(92) + chr(10) + "fim';")
        self.assertIn("'http://x'", G.compactar_cursor("var x = 'http://x'; // nota"))

    def test_compactar_preserva_js_e_css(self):
        js = MAPA_JS.read_text(encoding="utf-8")
        c = G.compactar(js)
        self.assertLess(len(c), len(js))
        self.assertNotIn("\n  ", c)
        self.assertIn("'mb-harness-mapa:v1'", c)
        amostra = "/* a\n b */ var a = 1; // fim\n  // linha\n  /* x */ var b = 'http://x' ; // sai\nvar c = /\\/\\*/.test('x');\n"
        self.assertEqual(G.compactar(amostra), "var a = 1;\nvar b = 'http://x' ;\nvar c = /\\/\\*/.test('x');")
        self.assertIn("'http://www.w3.org/2000/svg'", c)
        self.assertEqual(G.compactar(".a{x:1} /* c */\n  .b{y:2}\n", css=True), ".a{x:1}\n.b{y:2}")
        if shutil.which("node"):
            with tempfile.TemporaryDirectory() as tmp:
                arq = Path(tmp) / "c.js"
                arq.write_text(c, encoding="utf-8")
                r = subprocess.run(["node", "--check", str(arq)], capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_valida_campos_novos(self):
        d = _base()
        d["estacoes"][10]["papel"] = "chefe"
        d["elevadores"] = [{"estacao": "contexto", "texto": ""}]
        d["subtitulo"] = "x" * 300
        erros = "\n".join(G.validar(d))
        self.assertIn('papel precisa ser "revisao"', erros)
        self.assertIn("Elevador precisa", erros)
        self.assertIn('"subtitulo" precisa ser texto', erros)
        # elevador que aponta para estação removida por remendo não invalida a planta (só deixa de ser desenhado)
        m = G.aplicar(_base(), [{"op": "remover_estacao", "id": "contexto"}])
        self.assertEqual(G.validar(m), [])

    def test_recusa_planta_invalida(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruim = Path(tmp) / "ruim.json"
            d = _base(); d["linhas"][0]["estacoes"] = ["voce"]
            ruim.write_text(json.dumps(d), encoding="utf-8")
            with self.assertRaises(ValueError) as c:
                G.gerar(ruim, Path(tmp) / "x.html", sem_fotografia=True)
            self.assertIn("pelo menos 2 estações", str(c.exception))
            self.assertFalse((Path(tmp) / "x.html").exists())
            self.assertEqual(G.main(["--fonte", str(ruim), "--validar"]), 2)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Fotografia(unittest.TestCase):
    def test_so_le_e_conta(self):
        agora = dt.datetime(2026, 10, 18, 1, 0, tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            sc = raiz / "apps" / "megabrain-dashboard" / "data" / "session-connections"
            sc.mkdir(parents=True)
            (sc / "a.json").write_text(json.dumps({"application": "desconhecido", "updated_at": "2026-10-17T23:00:00+00:00"}), encoding="utf-8")
            (sc / "b.json").write_text(json.dumps({"application": "claude-code-desktop", "updated_at": "2026-10-17T20:00:00Z"}), encoding="utf-8")
            (sc / "c.json").write_text(json.dumps({"application": "Codex", "updated_at": "2026-10-10T20:00:00+00:00"}), encoding="utf-8")
            (sc / "a.json.lock").write_text("", encoding="utf-8")
            banco = raiz / "apps" / "megabrain-dashboard" / "data" / "central.sqlite3"
            c = sqlite3.connect(str(banco))
            c.executescript("create table jobs(id text primary key, project text, data text);"
                            "create table events(id integer primary key autoincrement, project text, data text);"
                            "create table comments(id text primary key, project text, data text);")
            c.execute("insert into jobs values('1','p',?)", (json.dumps({"title": "Pesquisa <b>X</b>", "status": "completed", "updated_at": "2026-10-17T22:00:00+00:00"}),))
            c.execute("insert into jobs values('2','p',?)", (json.dumps({"title": "Parou", "status": "interrupted", "updated_at": "2026-10-11T22:00:00+00:00"}),))
            c.execute("insert into events(project,data) values('p',?)", (json.dumps({"kind": "report_arrived", "title": "R1", "at": "2026-10-17T21:00:00+00:00"}),))
            c.execute("insert into events(project,data) values('p',?)", (json.dumps({"kind": "report_updated", "title": "R0", "at": "2026-10-15T21:00:00+00:00"}),))
            c.execute("insert into events(project,data) values('p',?)", (json.dumps({"kind": "source_changed", "at": "2026-10-17T21:00:00+00:00"}),))
            c.execute("insert into comments values('c1','p',?)", (json.dumps({"status": "CORRIGIDO_VERIFICADO"}),))
            c.execute("insert into comments values('c2','p',?)", (json.dumps({"status": "Recebido, aguardando correção"}),))
            c.commit(); c.close()
            (raiz / "dados").mkdir()
            (raiz / "dados" / "orcamento_ia.json").write_text(json.dumps({
                "claude": {"pacing": {"windows": {"s": {"used_percent": 12.0, "label": "Sessão"}, "w": {"used_percent": 40.4, "label": "Semana"}}}, "updated_at": "2026-10-18T00:55:00+00:00"},
                "codex": {"pacing": {"windows": {"p": {"used_percent": 7.0, "label": "7 d"}}}, "updated_at": "2026-10-18T00:55:00+00:00"}}), encoding="utf-8")
            antes = {p: _sha(p) for p in raiz.rglob("*") if p.is_file()}
            arquivos_antes = sorted(str(p) for p in raiz.rglob("*"))
            foto = G.coletar_fotografia(raiz, agora)
            depois = {p: _sha(p) for p in raiz.rglob("*") if p.is_file()}
            self.assertEqual(antes, depois, "a fotografia não pode gravar nada")
            self.assertEqual(arquivos_antes, sorted(str(p) for p in raiz.rglob("*")), "nem criar arquivos (-wal/-shm)")
        self.assertEqual(foto["quando_txt"], "17/10/2026 22:00")
        self.assertEqual(foto["sessoes"]["total"], 2)
        self.assertEqual(foto["sessoes"]["por_cliente"], {"sem nome (aberta sem --hook)": 1, "Claude Code desktop": 1})
        self.assertEqual(foto["pedidos"]["total"], 2)
        self.assertEqual(foto["pedidos"]["ultimos"][0]["status_txt"], "concluído")
        self.assertEqual(foto["relatorios"]["total"], 1)
        self.assertEqual(foto["comentarios"]["pendentes"], 1)
        self.assertEqual(foto["cotas"]["maior"], {"conta": "Claude", "pct": 40})
        # P8: cada pílula tem palavra, não só número
        curtos = {p["estacao"]: p["curto"] for p in foto["estacionados"]}
        self.assertEqual(curtos["sessoes"], "2 sessões")
        self.assertEqual(curtos["executor"], "1 pedido interrompido")
        self.assertEqual(curtos["balcao"], "1 sem correção")
        self.assertEqual(curtos["retrato"], "40% da cota")
        estac = {(p["estacao"], p["n"]) for p in foto["estacionados"]}
        self.assertIn(("sessoes", 2), estac)
        self.assertIn(("resultados", 1), estac)
        self.assertIn(("executor", 1), estac)
        self.assertIn(("balcao", 1), estac)
        self.assertNotIn("ao vivo", json.dumps(foto, ensure_ascii=False).replace("Não é ao vivo", ""))

    def test_sem_fontes_vira_nao_medido(self):
        with tempfile.TemporaryDirectory() as tmp:
            foto = G.coletar_fotografia(Path(tmp))
        self.assertEqual(len(foto["avisos"]), 3)
        self.assertTrue(all("NAO_MEDIDO" in a for a in foto["avisos"]))
        self.assertIsNone(foto["pedidos"]["total"])


class AplicarRemendosCLI(unittest.TestCase):
    def test_backup_historico_e_validacao(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fonte = tmp / "harness-mapa.json"
            shutil.copyfile(FONTE, fonte)
            original = fonte.read_bytes()
            pacote = tmp / "respostas.json"
            pacote.write_text(json.dumps({"respostas": {"mapa_harness": {"lote": "abc12345", "patches": REMENDOS[:5]}}}, ensure_ascii=False), encoding="utf-8")
            rc = G.main(["--fonte", str(fonte), "--aplicar-remendos", str(pacote), "--backup-dir", str(tmp / "bk"), "--sem-gerar"])
            self.assertEqual(rc, 0)
            backups = list((tmp / "bk").glob("harness-mapa_*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            novo = json.loads(fonte.read_text(encoding="utf-8"))
            self.assertEqual(G.validar(novo), [])
            self.assertTrue(any(e["id"] == "e_teste" for e in novo["estacoes"]))
            self.assertEqual(novo["historico"][-1]["lote"], "abc12345")
            self.assertEqual(novo["notas"][-1]["texto"], "Quero que a revisão final seja do Codex 2.")
            # remendo que não se aplica: nada é gravado
            antes = fonte.read_bytes()
            ruim = tmp / "ruim.json"
            ruim.write_text(json.dumps({"patches": [{"op": "remover_estacao", "id": "nao_existe"}]}), encoding="utf-8")
            self.assertEqual(G.main(["--fonte", str(fonte), "--aplicar-remendos", str(ruim), "--backup-dir", str(tmp / "bk"), "--sem-gerar"]), 2)
            self.assertEqual(fonte.read_bytes(), antes)
            self.assertEqual(len(list((tmp / "bk").glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()

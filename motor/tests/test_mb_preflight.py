#!/usr/bin/env python3
"""Provas do preflight: drift fonte→plugin tem que reprovar.

Lição 260825: plugin velho + cópia instalada velha formam par consistente e o
cheque de skills passa verde — o drift só aparece comparando o plugin com a
DERIVAÇÃO da fonte. Os testes fixam os dois lados (em dia → verde, fonte
editada → ✗) e o subprocesso prova que o veredito completo sai 2, com
USERPROFILE falso para as cópias instaladas reais não contaminarem o cenário.
"""

from __future__ import annotations

import importlib.util
import json
import os
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


def _carregar(nome: str):
    spec = importlib.util.spec_from_file_location(
        nome.replace("-", "_"), str(RAIZ / "bin" / f"{nome}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preflight = _carregar("mb-preflight")
build = _carregar("mb-build-plugin-claude")


class Base(unittest.TestCase):
    def tmpdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def central_fake(self) -> Path:
        c = self.tmpdir()
        fonte = c / "skills/megabrain/SKILL.md"
        fonte.parent.mkdir(parents=True)
        texto = "---\nname: megabrain\ndescription: x\n---\ncorpo\n"
        fonte.write_text(texto, encoding="utf-8")
        copia = c / "plugin-megabrain-claude/skills/megabrain/SKILL.md"
        copia.parent.mkdir(parents=True)
        copia.write_text(build.derivar_skill_megabrain(texto), encoding="utf-8")
        return c


class TestChequePlugin(Base):
    def gravar_manifesto_publico(self, c: Path) -> None:
        plugin = c / "plugin-megabrain-claude"
        arquivos = {
            p.relative_to(plugin).as_posix(): preflight.hashlib.sha256(p.read_bytes()).hexdigest()
            for p in plugin.rglob("*") if p.is_file()
        }
        (c / ".mb-manifest.json").write_text(json.dumps({
            "schema": 2,
            "plugin_publicado": {
                "algoritmo": "sha256",
                "transformacao": "mb-generate-template:sanitizar-v1",
                "proveniencia": {
                    "plugin_fonte": "motor/plugin-megabrain-claude",
                    "builder": "bin/mb-build-plugin-claude.py",
                    "builder_sha256": "a" * 64,
                    "derivacao_canonica": "verificada",
                    "arquivos_fonte": {"skills/megabrain/SKILL.md": "b" * 64},
                    "fontes_canonicas": {"skills/megabrain/SKILL.md": "c" * 64},
                },
                "arquivos": arquivos,
            },
        }), encoding="utf-8")

    def test_plugin_em_dia_passa(self):
        ok, txt = preflight.cheque_plugin(self.central_fake())
        self.assertTrue(ok, txt)

    def test_fonte_editada_reprova(self):
        # o cenário real de 260825: fonte commitada com regra nova, plugin e
        # cópias instaladas ainda na versão anterior — par consistente entre si
        c = self.central_fake()
        fonte = c / "skills/megabrain/SKILL.md"
        fonte.write_text(fonte.read_text(encoding="utf-8") + "\nregra nova\n",
                         encoding="utf-8")
        ok, txt = preflight.cheque_plugin(c)
        self.assertFalse(ok)
        self.assertIn("skills/megabrain/SKILL.md", txt)
        self.assertIn("mb-build-plugin-claude", txt)

    def test_copia_orfa_no_plugin_reprova(self):
        c = self.central_fake()
        orfa = c / "plugin-megabrain-claude/skills/grelhar/SKILL.md"
        orfa.parent.mkdir(parents=True)
        orfa.write_text("sem fonte\n", encoding="utf-8")
        ok, txt = preflight.cheque_plugin(c)
        self.assertFalse(ok)
        self.assertIn("skills/grelhar/SKILL.md", txt)

    def test_central_sem_plugin_nao_acusa(self):
        ok, txt = preflight.cheque_plugin(self.tmpdir())
        self.assertTrue(ok, txt)

    def test_plugin_publico_passa_por_manifesto_com_proveniencia(self):
        c = self.central_fake()
        self.gravar_manifesto_publico(c)
        ok, txt = preflight.cheque_plugin(c)
        self.assertTrue(ok, txt)
        self.assertIn("proveniência", txt)

    def test_manifesto_tautologico_sem_proveniencia_reprova(self):
        c = self.central_fake()
        plugin = c / "plugin-megabrain-claude"
        arquivos = {
            p.relative_to(plugin).as_posix(): preflight.hashlib.sha256(p.read_bytes()).hexdigest()
            for p in plugin.rglob("*") if p.is_file()
        }
        (c / ".mb-manifest.json").write_text(json.dumps({
            "plugin_publicado": {"algoritmo": "sha256", "arquivos": arquivos},
        }), encoding="utf-8")
        ok, txt = preflight.cheque_plugin(c)
        self.assertFalse(ok)
        self.assertIn("proveniência schema 2", txt)

    def test_plugin_publico_alterado_reprova(self):
        c = self.central_fake()
        plugin = c / "plugin-megabrain-claude"
        arq = plugin / "skills/megabrain/SKILL.md"
        self.gravar_manifesto_publico(c)
        arq.write_text("alterado\n", encoding="utf-8")
        ok, txt = preflight.cheque_plugin(c)
        self.assertFalse(ok)
        self.assertIn("diverge:skills/megabrain/SKILL.md", txt)


class TestChequeRuntimes(Base):
    def central_skill(self) -> Path:
        c = self.tmpdir()
        p = c / "motor/skills/megabrain/SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_text("---\nname: megabrain\ndescription: x\n---\natual\n", encoding="utf-8")
        return c

    def test_runtime_configurado_sem_skill_reprova(self):
        c = self.central_skill()
        home = self.tmpdir()
        (home / ".codex").mkdir()
        ok, txt = preflight.cheque_skills(c, True, home)
        self.assertFalse(ok)
        self.assertIn("Codex", txt)

    def test_codex_direto_e_cache_atual_passam(self):
        c = self.central_skill()
        home = self.tmpdir()
        fonte = c / "motor/skills/megabrain/SKILL.md"
        direto = home / ".codex/skills/megabrain/SKILL.md"
        cache = home / ".codex/plugins/cache/personal/megabrain/2/skills/megabrain/SKILL.md"
        for p in (direto, cache):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(fonte.read_bytes())
        ok, txt = preflight.cheque_skills(c, True, home)
        self.assertTrue(ok, txt)
        self.assertIn("Codex", txt)

    def test_cache_codex_antigo_nao_mascara_o_atual(self):
        c = self.central_skill()
        home = self.tmpdir()
        fonte = c / "motor/skills/megabrain/SKILL.md"
        antigo = home / ".codex/plugins/cache/personal/megabrain/1/skills/megabrain/SKILL.md"
        atual = home / ".codex/plugins/cache/personal/megabrain/2/skills/megabrain/SKILL.md"
        antigo.parent.mkdir(parents=True)
        atual.parent.mkdir(parents=True)
        antigo.write_text("velho\n", encoding="utf-8")
        atual.write_bytes(fonte.read_bytes())
        ok, txt = preflight.cheque_skills(c, True, home)
        self.assertTrue(ok, txt)


class TestChequeEstado(Base):
    def central_estado(self) -> Path:
        c = self.tmpdir()
        (c / "dados").mkdir()
        (c / "00_painel").mkdir()
        for nome in preflight.FONTES_ESTADO:
            (c / nome).parent.mkdir(parents=True, exist_ok=True)
            (c / nome).write_text("fonte\n", encoding="utf-8")
        fp = preflight.frescor.calcular(c)
        origem = {
            "git_head": None,
            "fontes": fp["fontes"],
            "fingerprint": {"algoritmo": fp["algoritmo"], "valor": fp["valor"]},
        }
        (c / "dados/estado.json").write_text(json.dumps({
            "schema": 3,
            "gerado_de": origem,
        }), encoding="utf-8")
        (c / "00_painel/RELATORIO.html").write_text(
            "<!doctype html>\n" + preflight.frescor.bloco_html(origem) + "\n",
            encoding="utf-8")
        return c

    def test_estado_e_relatorio_atuais_passam(self):
        c = self.central_estado()
        ok, txt = preflight.cheque_estado(c)
        self.assertTrue(ok, txt)

    def test_fonte_alterada_reprova_sem_depender_de_mtime(self):
        c = self.central_estado()
        fonte = c / "META.md"
        fonte.write_text("mudou\n", encoding="utf-8")
        ok, txt = preflight.cheque_estado(c)
        self.assertFalse(ok)
        self.assertIn("fingerprint", txt)

    def test_relatorio_ausente_reprova(self):
        c = self.central_estado()
        (c / "00_painel/RELATORIO.html").unlink()
        ok, txt = preflight.cheque_estado(c)
        self.assertFalse(ok)
        self.assertIn("RELATORIO.html ausente", txt)

    def test_relatorio_sem_metadado_reprova(self):
        c = self.central_estado()
        (c / "00_painel/RELATORIO.html").write_text("<!doctype html>\n", encoding="utf-8")
        ok, txt = preflight.cheque_estado(c)
        self.assertFalse(ok)
        self.assertIn("mb-frescor ausente", txt)

    def test_estado_ausente_reprova(self):
        c = self.central_estado()
        (c / "dados/estado.json").unlink()
        ok, txt = preflight.cheque_estado(c)
        self.assertFalse(ok)
        self.assertIn("estado.json AUSENTE", txt)


class TestChequeCanonicos(Base):
    def central_v7(self) -> Path:
        c = self.tmpdir()
        for logica, nomes in (("nucleo", ("licoes-megabrain.md", "VERSAO.txt")),
                              ("estado", ("ESTADO.md", "DECISOES.md"))):
            d = c / "memoria" / logica
            d.mkdir(parents=True, exist_ok=True)
            for nome in nomes:
                (d / nome).write_text("canônico\n", encoding="utf-8")
        return c

    def test_central_arrumada_passa(self):
        ok, txt = preflight.cheque_canonicos(self.central_v7())
        self.assertTrue(ok, txt)

    def test_sosia_na_pasta_logica_errada_reprova(self):
        # 260825: anexar decisão no caminho errado criou memoria/nucleo/
        # DECISOES.md do zero; u.achar seguia lendo memoria/estado/, então o
        # texto novo virou escrita órfã e nenhum contador acusou.
        c = self.central_v7()
        (c / "memoria/nucleo/DECISOES.md").write_text("órfã\n", encoding="utf-8")
        ok, txt = preflight.cheque_canonicos(c)
        self.assertFalse(ok)
        self.assertIn("memoria/nucleo/DECISOES.md", txt)

    def test_sosia_na_raiz_continua_reprovando(self):
        c = self.central_v7()
        (c / "licoes-megabrain.md").write_text("órfã\n", encoding="utf-8")
        ok, txt = preflight.cheque_canonicos(c)
        self.assertFalse(ok)
        self.assertIn("licoes-megabrain.md", txt)

    def test_despejo_bruto_no_cerebro_raw_nao_e_orfao(self):
        c = self.central_v7()
        raw = c / "memoria/cerebro/raw"
        raw.mkdir(parents=True)
        (raw / "ESTADO.md").write_text("fonte de cliente\n", encoding="utf-8")
        ok, txt = preflight.cheque_canonicos(c)
        self.assertTrue(ok, txt)

    def test_nome_datado_de_pendencia_nao_e_orfao(self):
        c = self.central_v7()
        pend = c / "memoria/pendencias/260819-retrabalho"
        pend.mkdir(parents=True)
        (pend / "260819_HANDOFF-RETRABALHO.md").write_text("nota\n", encoding="utf-8")
        ok, txt = preflight.cheque_canonicos(c)
        self.assertTrue(ok, txt)


class TestVereditoCompleto(Base):
    def test_preflight_sai_2_com_drift_fonte_plugin(self):
        c = self.central_fake()
        fonte = c / "skills/megabrain/SKILL.md"
        fonte.write_text(fonte.read_text(encoding="utf-8") + "\nregra nova\n",
                         encoding="utf-8")
        home_falsa = self.tmpdir()
        env = dict(os.environ, USERPROFILE=str(home_falsa), HOME=str(home_falsa))
        r = subprocess.run(
            [sys.executable, str(RAIZ / "bin" / "mb-preflight.py"),
             "--repo", str(c), "--forcar"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env,
        )
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("plugin", r.stdout)
        self.assertIn("DIVERGE", r.stdout)


if __name__ == "__main__":
    unittest.main()

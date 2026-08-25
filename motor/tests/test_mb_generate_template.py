#!/usr/bin/env python3
"""Guarda do CRLF no pacote público (mb-generate-template.copiar_sanitizando).

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Em 260825 a suíte pública (`test_nenhum_cmd_da_central_em_lf` rodando contra o
`_github/export`) falhou nos 15 `.cmd` do pacote: o gerador lia texto com
newline universal (CRLF->LF) e gravava com `newline=""`, que não traduz de
volta. O export saía em LF e o cmd.exe executaria outra coisa sem erro — a
mesma lição de 260819, agora mordendo a SAÍDA do gerador em vez da fonte.

O detector continua morando no mb-preflight; estes testes provam que o GERADOR
não produz mais o defeito, sem duplicar a lógica de detecção.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb-generate-template.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
sys.path.insert(0, str(RAIZ / "bin"))

_spec = importlib.util.spec_from_file_location(
    "mb_generate_template", str(RAIZ / "bin" / "mb-generate-template.py"))
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def linhas_lf_solto(bruto: bytes) -> int:
    """Quebras LF sem CR antes — o que derruba o cmd.exe."""
    return bruto.count(b"\n") - bruto.count(b"\r\n")


class Base(unittest.TestCase):
    def tmp(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)


class TestBatchSaiCrlf(Base):
    def test_cmd_em_lf_vira_crlf_no_export(self):
        t = self.tmp()
        src = t / "fonte.cmd"
        src.write_bytes(b'@echo off\nsetlocal\necho oi\n')
        dst = t / "saida" / "fonte.cmd"
        self.assertTrue(gt.copiar_sanitizando(str(src), str(dst)))
        bruto = dst.read_bytes()
        self.assertEqual(linhas_lf_solto(bruto), 0, bruto)
        self.assertIn(b"echo oi\r\n", bruto)

    def test_cmd_ja_crlf_nao_dobra_cr(self):
        """Normalizar na ordem errada (\\n -> \\r\\n primeiro) dobraria o CR."""
        t = self.tmp()
        src = t / "bom.cmd"
        src.write_bytes(b'@echo off\r\nsetlocal\r\n')
        dst = t / "bom.cmd"
        gt.copiar_sanitizando(str(src), str(dst))
        bruto = dst.read_bytes()
        self.assertNotIn(b"\r\r\n", bruto)
        self.assertEqual(linhas_lf_solto(bruto), 0)

    def test_cmd_misto_fica_todo_crlf(self):
        """O pior caso real (260825): 2 linhas CRLF e o resto LF."""
        t = self.tmp()
        src = t / "misto.cmd"
        src.write_bytes(b'@echo off\r\nsetlocal\necho a\necho b\r\n')
        dst = t / "misto.cmd"
        gt.copiar_sanitizando(str(src), str(dst))
        self.assertEqual(linhas_lf_solto(dst.read_bytes()), 0)

    def test_sanitizacao_continua_valendo_no_cmd(self):
        """CRLF não pode virar rota de fuga da sanitização."""
        t = self.tmp()
        src = t / "privado.cmd"
        src.write_bytes('echo C:\\Users\\<USUARIO>\n'.encode("utf-8"))
        dst = t / "privado.cmd"
        gt.copiar_sanitizando(str(src), str(dst))
        bruto = dst.read_bytes()
        self.assertIn(b"<USER_HOME>", bruto)
        self.assertEqual(linhas_lf_solto(bruto), 0)


class TestNaoBatchNaoMuda(Base):
    def test_md_em_lf_continua_lf(self):
        """Só batch é forçado — .md/.py/.json em LF são normais."""
        t = self.tmp()
        src = t / "nota.md"
        src.write_bytes(b"# titulo\n\ntexto\n")
        dst = t / "nota.md"
        gt.copiar_sanitizando(str(src), str(dst))
        self.assertEqual(dst.read_bytes(), b"# titulo\n\ntexto\n")


class TestTemporariosNaoSaem(Base):
    def test_reconhece_nomes_temporarios_sem_bloquear_metadados_validos(self):
        for nome in (".tmp-verificacao", ".temp-build", "tmp", "TEMP"):
            self.assertTrue(gt.nome_temporario(nome), nome)
        for nome in (".github", ".codex-plugin", "templates"):
            self.assertFalse(gt.nome_temporario(nome), nome)

    def test_gerador_nao_copia_temporario_do_topo_ou_aninhado(self):
        t = self.tmp()
        central = t / "central"
        central.mkdir()
        (central / "VERSAO.txt").write_text(
            "2026-08-25 · v7.5 — fixture\n", encoding="utf-8")
        (central / "bin" / ".tmp-captura").mkdir(parents=True)
        (central / "bin" / ".tmp-captura" / "perfil.log").write_text(
            r"<PROJETOS_ROOT>\privado", encoding="utf-8")
        (central / ".tmp-verificacao").mkdir()
        (central / ".tmp-verificacao" / "perfil.log").write_text(
            r"<USER_HOME>\privado", encoding="utf-8")
        estado = central / "memoria" / "estado"
        estado.mkdir(parents=True)
        for nome in ("ESTADO.md", "HANDOFF.md", "DECISOES.md"):
            (estado / nome).write_text("contexto privado\n", encoding="utf-8")
        destino = central / "_github" / "export"

        self.assertTrue(gt.gerar_template(str(central), str(destino)))
        self.assertFalse((destino / ".tmp-verificacao").exists())
        self.assertFalse((destino / "bin" / ".tmp-captura").exists())
        for nome in ("ESTADO.md", "HANDOFF.md", "DECISOES.md"):
            self.assertEqual(list(destino.rglob(nome)), [], nome)


class TestManifestoComProveniencia(Base):
    def fixture_plugin(self) -> tuple[Path, Path]:
        central = self.tmp() / "central"
        canonica = central / "motor/skills/megabrain/SKILL.md"
        canonica.parent.mkdir(parents=True)
        canonica.write_text(
            "---\nname: megabrain\ndescription: x\n---\nconteúdo canônico\n",
            encoding="utf-8",
        )
        plugin = central / "motor/plugin-megabrain-claude"
        skill = plugin / "skills/megabrain/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_bytes(canonica.read_bytes())
        (plugin / ".claude-plugin").mkdir()
        (plugin / ".claude-plugin/plugin.json").write_text(
            '{"name":"megabrain"}\n', encoding="utf-8")
        (plugin / "README.md").write_text(
            "fonte em C:\\Users\\<USUARIO>\\privado\n", encoding="utf-8")

        builder = central / "bin/mb-build-plugin-claude.py"
        builder.parent.mkdir(parents=True)
        builder.write_text(
            "from pathlib import Path\n"
            "def mapa_fontes(c):\n"
            "    return {'skills/megabrain/SKILL.md': "
            "(Path(c) / 'motor/skills/megabrain/SKILL.md', lambda t: t)}\n"
            "def conferir_drift(c):\n"
            "    f = Path(c) / 'motor/skills/megabrain/SKILL.md'\n"
            "    p = Path(c) / 'motor/plugin-megabrain-claude/skills/megabrain/SKILL.md'\n"
            "    return [] if f.read_text(encoding='utf-8') == p.read_text(encoding='utf-8') "
            "else ['skills/megabrain/SKILL.md']\n",
            encoding="utf-8",
        )

        destino = central / "_github/export"
        for fonte in plugin.rglob("*"):
            if fonte.is_file():
                rel = fonte.relative_to(plugin)
                self.assertTrue(gt.copiar_sanitizando(
                    str(fonte), str(destino / "plugin-megabrain-claude" / rel)))
        return central, destino

    def test_manifesto_prova_fonte_derivacao_e_sanitizacao(self):
        central, destino = self.fixture_plugin()
        self.assertTrue(gt.gravar_manifesto(central, destino))
        dados = json.loads((destino / ".mb-manifest.json").read_text(encoding="utf-8"))
        publicado = dados["plugin_publicado"]
        proveniencia = publicado["proveniencia"]

        self.assertEqual(dados["schema"], 2)
        self.assertEqual(proveniencia["derivacao_canonica"], "verificada")
        self.assertIn("motor/skills/megabrain/SKILL.md",
                      proveniencia["fontes_canonicas"])
        readme_publico = destino / "plugin-megabrain-claude/README.md"
        self.assertIn("<USER_HOME>", readme_publico.read_text(encoding="utf-8"))
        self.assertEqual(publicado["arquivos"]["README.md"],
                         gt._sha256(readme_publico.read_bytes()))
        self.assertNotEqual(publicado["arquivos"]["README.md"],
                            proveniencia["arquivos_fonte"]["README.md"])

    def test_saida_adulterada_nao_ganha_manifesto_novo(self):
        central, destino = self.fixture_plugin()
        manifesto = destino / ".mb-manifest.json"
        manifesto.write_text("sentinela\n", encoding="utf-8")
        (destino / "plugin-megabrain-claude/README.md").write_text(
            "adulterado\n", encoding="utf-8")

        self.assertFalse(gt.gravar_manifesto(central, destino))
        self.assertEqual(manifesto.read_text(encoding="utf-8"), "sentinela\n")

    def test_drift_da_fonte_canonica_recusa_proveniencia(self):
        central, destino = self.fixture_plugin()
        (central / "motor/skills/megabrain/SKILL.md").write_text(
            "nova fonte\n", encoding="utf-8")
        self.assertFalse(gt.gravar_manifesto(central, destino))
        self.assertFalse((destino / ".mb-manifest.json").exists())


if __name__ == "__main__":
    unittest.main()

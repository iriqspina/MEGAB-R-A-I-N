"""Testes da cópia magra (260825aa) — o que não pode regredir.

O risco real desta mudança não é ela falhar hoje: é o sync ENGORDAR as cópias
de volta no primeiro `--auto`, em silêncio, desfazendo tudo. É a lição
"melhoria que para na fronteira" aplicada ao contrário. Estes testes travam
exatamente isso.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent.parent / "bin"
sys.path.insert(0, str(BIN))


def _mod(nome: str, arquivo: str):
    spec = importlib.util.spec_from_file_location(nome, BIN / arquivo)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


magra = _mod("mb_magra", "mb-magra.py")
chk = _mod("mb_chk", "mb-check-version.py")


class Base(unittest.TestCase):
    def tmp(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)


class TestFormatoMagro(Base):
    def test_ponteiro_declara_formato(self):
        raiz = self.tmp()
        mb = raiz / "proj" / "MEGABRAIN"
        mb.mkdir(parents=True)
        central = raiz / "central"
        (central / "memoria" / "nucleo").mkdir(parents=True)
        (central / "memoria" / "nucleo" / "VERSAO.txt").write_text(
            "2026-08-25 · v7.5 — teste\n", encoding="utf-8")
        d = magra.ponteiro(mb, central)
        self.assertEqual(d["formato"], "magra")
        self.assertEqual(d["central"], str(central))
        self.assertIn("central", d["como_usar"])

    def test_sync_reconhece_copia_magra(self):
        raiz = self.tmp()
        mb = raiz / "MEGABRAIN"
        mb.mkdir(parents=True)
        (mb / ".mb-origem.json").write_text(
            json.dumps({"formato": "magra", "central": "X"}), encoding="utf-8")
        self.assertTrue(chk.e_copia_magra(mb))

    def test_sync_nao_confunde_copia_cheia_com_magra(self):
        """Se isto quebrar, o sync trata cópia CHEIA como magra e para de
        atualizar a máquina de quem ainda depende dela."""
        raiz = self.tmp()
        mb = raiz / "MEGABRAIN"
        mb.mkdir(parents=True)
        (mb / ".mb-origem.json").write_text(
            json.dumps({"central": "X", "versao": "v7.4"}), encoding="utf-8")
        self.assertFalse(chk.e_copia_magra(mb))

    def test_sem_ponteiro_nao_e_magra(self):
        raiz = self.tmp()
        mb = raiz / "MEGABRAIN"
        mb.mkdir(parents=True)
        self.assertFalse(chk.e_copia_magra(mb))

    def test_ponteiro_corrompido_nao_e_magra(self):
        """JSON quebrado não pode virar 'magra' por acidente — seria o sync
        deixando de copiar máquina numa cópia que precisa dela."""
        raiz = self.tmp()
        mb = raiz / "MEGABRAIN"
        mb.mkdir(parents=True)
        (mb / ".mb-origem.json").write_text("{nao é json", encoding="utf-8")
        self.assertFalse(chk.e_copia_magra(mb))


class TestClassificacao(Base):
    def test_compartilhado_em_5_copias_nao_e_do_projeto(self):
        """A regra que substituiu a lista fixa: arquivo byte-idêntico em 5+
        projetos é legado da central, não conteúdo de projeto."""
        raiz = self.tmp()
        alvos = []
        for i in range(5):
            mb = raiz / f"p{i}" / "MEGABRAIN"
            mb.mkdir(parents=True)
            (mb / "legado.md").write_text("mesmo conteudo\n", encoding="utf-8")
            alvos.append(mb)
        comp = magra.indice_compartilhado(alvos, minimo=5)
        self.assertTrue(any(rel == "legado.md" for rel, _ in comp))

    def test_arquivo_de_um_projeto_so_nao_entra_no_compartilhado(self):
        raiz = self.tmp()
        alvos = []
        for i in range(5):
            mb = raiz / f"p{i}" / "MEGABRAIN"
            mb.mkdir(parents=True)
            (mb / "comum.md").write_text("igual\n", encoding="utf-8")
            alvos.append(mb)
        (alvos[0] / "so-meu.md").write_text("unico deste projeto\n", encoding="utf-8")
        comp = magra.indice_compartilhado(alvos, minimo=5)
        self.assertFalse(any(rel == "so-meu.md" for rel, _ in comp))

    def test_dna_usuario_e_tratado_como_vazamento(self):
        """dna/usuario/ numa cópia é identidade vazada (v7.2 fechou no gerador,
        cópia antiga pode ter). Não pode ser classificado como 'sai' comum."""
        raiz = self.tmp()
        mb = raiz / "proj" / "MEGABRAIN"
        (mb / "dna" / "usuario" / "260824").mkdir(parents=True)
        (mb / "dna" / "usuario" / "260824" / "pessoal.md").write_text(
            "identidade\n", encoding="utf-8")
        plano = magra.planejar(mb, raiz / "central-vazia", {}, set())
        self.assertEqual(len(plano["vazamento"]), 1)
        self.assertEqual(plano["sai"], [])

    def test_derivado_sai_sempre(self):
        raiz = self.tmp()
        mb = raiz / "proj" / "MEGABRAIN"
        mb.mkdir(parents=True)
        (mb / "RELATORIO.html").write_text("<html></html>", encoding="utf-8")
        plano = magra.planejar(mb, raiz / "central-vazia", {}, set())
        self.assertTrue(any(x.name == "RELATORIO.html" for x in plano["sai"]))

    def test_desconhecido_fica_na_duvida(self):
        """Regra de segurança: o que não é reconhecido é PRESERVADO."""
        raiz = self.tmp()
        mb = raiz / "proj" / "MEGABRAIN"
        mb.mkdir(parents=True)
        (mb / "coisa-do-projeto.md").write_text("conteudo unico\n", encoding="utf-8")
        plano = magra.planejar(mb, raiz / "central-vazia", {}, set())
        self.assertTrue(any(x.name == "coisa-do-projeto.md" for x in plano["fica"]))

    def test_ja_magra_e_detectada(self):
        raiz = self.tmp()
        mb = raiz / "proj" / "MEGABRAIN"
        mb.mkdir(parents=True)
        (mb / ".mb-origem.json").write_text("{}", encoding="utf-8")
        (mb / "LEIAME.md").write_text("# x\n", encoding="utf-8")
        self.assertTrue(magra.ja_magra(mb))
        (mb / "sobrou.py").write_text("x\n", encoding="utf-8")
        self.assertFalse(magra.ja_magra(mb))


if __name__ == "__main__":
    unittest.main()
